"""WhatsApp Business API Webhook Handler for Silver Tier.

FastAPI-based webhook handler for receiving WhatsApp messages via Meta's
Business API. Creates action files for messages containing configured keywords.

Implements:
- FR-002: WhatsApp Business API message detection
- FR-002a: Keyword filtering for business relevance
- Plan.md Section 3.3: Webhook interface specification

Security Features:
- X-Hub-Signature-256 validation using HMAC-SHA256
- Rate limiting (100 requests/min per IP)
- Response within 500ms to avoid webhook retries

Usage:
    # Run standalone
    uvicorn src.watchers.whatsapp_webhook:app --host 0.0.0.0 --port 8000

    # Or integrate with base watcher
    handler = WhatsAppWebhookHandler(config)
    await handler.run()
"""

import asyncio
import hashlib
import hmac
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from src.common.audit_logger import get_audit_logger
from src.common.idempotency import get_idempotency_db
from src.common.integrity import generate_hash
from src.common.vault import get_vault
from src.watchers.base_watcher import ServerWatcher, WatcherPriority

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================


class WhatsAppConfig(BaseModel):
    """WhatsApp webhook configuration."""

    enabled: bool = True
    priority: int = 2
    memory_limit_mb: int = 100
    keywords: list[str] = Field(
        default_factory=lambda: [
            "invoice", "pricing", "quote", "order",
            "support", "help", "urgent", "payment"
        ]
    )
    webhook_rate_limit_per_minute: int = 100
    webhook_response_timeout_ms: int = 500
    dry_run: bool = False


def load_whatsapp_config() -> WhatsAppConfig:
    """Load WhatsApp config from watcher_config.yaml."""
    config_path = Path("config/watcher_config.yaml")

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            whatsapp_data = config_data.get("whatsapp", {})
            return WhatsAppConfig(**whatsapp_data)

    return WhatsAppConfig()


# =============================================================================
# Rate Limiting
# =============================================================================


class RateLimiter:
    """In-memory rate limiter with sliding window.

    Implements FR-035: max 100 requests/minute per IP.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str) -> bool:
        """Check if request from IP is allowed.

        Args:
            client_ip: Client IP address

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        window_start = now - self.window_seconds

        async with self._lock:
            # Clean old entries
            self._requests[client_ip] = [
                ts for ts in self._requests[client_ip]
                if ts > window_start
            ]

            # Check if under limit
            if len(self._requests[client_ip]) >= self.max_requests:
                return False

            # Record this request
            self._requests[client_ip].append(now)
            return True

    async def cleanup(self) -> int:
        """Remove expired entries. Returns count of removed IPs."""
        now = time.time()
        window_start = now - self.window_seconds
        removed = 0

        async with self._lock:
            empty_ips = [
                ip for ip, timestamps in self._requests.items()
                if all(ts <= window_start for ts in timestamps)
            ]
            for ip in empty_ips:
                del self._requests[ip]
                removed += 1

        return removed


# =============================================================================
# Pydantic Models for Meta Webhook Payload
# =============================================================================


class WhatsAppMessageText(BaseModel):
    """Text content of a WhatsApp message."""
    body: str


class WhatsAppMessage(BaseModel):
    """Individual WhatsApp message from webhook payload."""
    from_number: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: WhatsAppMessageText | None = None


class WhatsAppMetadata(BaseModel):
    """Metadata about the WhatsApp Business account."""
    display_phone_number: str | None = None
    phone_number_id: str | None = None


class WhatsAppValue(BaseModel):
    """Value object containing messages and metadata."""
    messaging_product: str | None = None
    metadata: WhatsAppMetadata | None = None
    messages: list[WhatsAppMessage] = Field(default_factory=list)
    contacts: list[dict[str, Any]] = Field(default_factory=list)
    statuses: list[dict[str, Any]] = Field(default_factory=list)


class WhatsAppChange(BaseModel):
    """A change object from the webhook."""
    value: WhatsAppValue
    field: str | None = None


class WhatsAppEntry(BaseModel):
    """Entry object containing changes."""
    id: str
    changes: list[WhatsAppChange] = Field(default_factory=list)


class WhatsAppWebhookPayload(BaseModel):
    """Complete webhook payload from Meta."""
    object: str
    entry: list[WhatsAppEntry] = Field(default_factory=list)


# =============================================================================
# Signature Validation
# =============================================================================


def validate_signature(
    payload: bytes,
    signature_header: str,
    app_secret: str
) -> bool:
    """Validate X-Hub-Signature-256 header.

    Args:
        payload: Raw request body
        signature_header: Value of X-Hub-Signature-256 header
        app_secret: WhatsApp app secret from .env

    Returns:
        True if signature is valid, False otherwise

    Reference:
        https://developers.facebook.com/docs/graph-api/webhooks/getting-started#verification-requests
    """
    if not signature_header:
        return False

    # Header format: "sha256=<signature>"
    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]  # Remove "sha256=" prefix

    # Compute HMAC-SHA256
    computed = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed, expected_signature)


def generate_message_id(sender: str, content: str, timestamp: str) -> str:
    """Generate idempotency ID for a message using SHA-256.

    Args:
        sender: Sender phone number
        content: Message content
        timestamp: Message timestamp

    Returns:
        SHA-256 hash of combined components
    """
    combined = f"{sender}:{content}:{timestamp}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:32]


# =============================================================================
# Action File Creator
# =============================================================================


def create_action_file_content(
    sender: str,
    message_content: str,
    message_id: str,
    timestamp: datetime,
    matched_keywords: list[str]
) -> str:
    """Create Markdown action file content with YAML frontmatter.

    Args:
        sender: Sender phone number
        message_content: Message text
        message_id: Unique message ID for idempotency
        timestamp: Message timestamp
        matched_keywords: Keywords that triggered this action

    Returns:
        Markdown content with YAML frontmatter
    """
    created = timestamp.isoformat()
    preview = message_content[:100] + "..." if len(message_content) > 100 else message_content

    content = f"""---
type: whatsapp
source: "{sender}"
subject: "WhatsApp message from {sender}"
content: |
  {message_content}
priority: normal
timestamp: "{created}"
status: pending
message_id: "{message_id}"
matched_keywords: {matched_keywords}
---

## WhatsApp Message from {sender}

**Received**: {timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

**Matched Keywords**: {", ".join(matched_keywords)}

### Message Content

{message_content}

---

*This action file was automatically created by the WhatsApp webhook handler.*
*Review the message and take appropriate action.*
"""
    return content


# =============================================================================
# FastAPI Application
# =============================================================================

# Initialize components
config = load_whatsapp_config()
rate_limiter = RateLimiter(
    max_requests=config.webhook_rate_limit_per_minute,
    window_seconds=60
)

# Check for dry-run mode from environment variable
DRY_RUN = config.dry_run or os.environ.get("DRY_RUN", "").lower() == "true"

# Create FastAPI app
app = FastAPI(
    title="WhatsApp Webhook Handler",
    description="Receives WhatsApp Business API webhooks for AI Employee Silver Tier",
    version="1.0.0"
)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For first (for reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host
    return "unknown"


def match_keywords(text: str, keywords: list[str]) -> list[str]:
    """Find which keywords are present in the text.

    Args:
        text: Message text to search
        keywords: Keywords to look for (case-insensitive)

    Returns:
        List of matched keywords
    """
    text_lower = text.lower()
    matched = []

    for keyword in keywords:
        # Use word boundary matching for more accurate detection
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, text_lower):
            matched.append(keyword)

    return matched


async def process_message_async(
    message: WhatsAppMessage,
    sender: str,
    keywords: list[str]
) -> dict[str, Any]:
    """Process a single WhatsApp message asynchronously.

    This runs in the background after returning HTTP 200 to Meta.

    Args:
        message: Parsed WhatsApp message
        sender: Sender phone number
        keywords: Keywords to filter on

    Returns:
        Processing result dictionary
    """
    try:
        # Extract text content
        text_content = message.text.body if message.text else ""

        if not text_content:
            logger.debug(f"Skipping non-text message type: {message.type}")
            return {"status": "skipped", "reason": "non-text message"}

        # Check for keyword matches
        matched = match_keywords(text_content, keywords)
        if not matched:
            logger.debug(f"No keyword matches in message from {sender}")
            return {"status": "skipped", "reason": "no keyword match"}

        # Generate idempotency ID
        message_id = generate_message_id(sender, text_content, message.timestamp)

        # Check idempotency
        db = get_idempotency_db()
        if db.is_processed(message_id, "whatsapp"):
            logger.info(f"Duplicate message detected: {message_id}")
            return {"status": "skipped", "reason": "duplicate"}

        # Parse timestamp
        try:
            ts = datetime.fromtimestamp(int(message.timestamp), tz=timezone.utc)
        except ValueError:
            ts = datetime.now(timezone.utc)

        # Create action file content
        file_content = create_action_file_content(
            sender=sender,
            message_content=text_content,
            message_id=message_id,
            timestamp=ts,
            matched_keywords=matched
        )

        # Write to vault (or simulate in dry-run mode)
        vault = get_vault()
        filename = f"whatsapp-{message_id[:12]}.md"

        if DRY_RUN:
            logger.info(f"[DRY-RUN] Would create action file: {filename}")
            logger.info(f"[DRY-RUN] Message from {sender}: {text_content[:100]}...")
            logger.info(f"[DRY-RUN] Matched keywords: {matched}")
            return {
                "status": "dry_run",
                "message_id": message_id,
                "would_create_file": filename,
                "matched_keywords": matched
            }

        try:
            file_path = vault.write_file(
                folder_key="needs_action",
                filename=filename,
                content=file_content,
                overwrite=False
            )
            logger.info(f"Created action file: {file_path}")
        except FileExistsError:
            logger.warning(f"Action file already exists: {filename}")
            return {"status": "skipped", "reason": "file exists"}

        # Mark as processed in idempotency DB
        db.mark_processed(
            message_id=message_id,
            source="whatsapp",
            sender=sender,
            subject=text_content[:50]
        )

        # Log to audit trail
        audit = get_audit_logger()
        audit.log_detection(
            component="whatsapp_webhook",
            action_type="message_received",
            target=sender,
            parameters={
                "message_id": message_id,
                "matched_keywords": matched,
                "preview": text_content[:100]
            }
        )

        return {
            "status": "processed",
            "message_id": message_id,
            "action_file": str(file_path),
            "matched_keywords": matched
        }

    except Exception as e:
        logger.exception(f"Error processing message: {e}")
        audit = get_audit_logger()
        audit.log_error(
            component="whatsapp_webhook",
            action_type="message_processing",
            error=e,
            target=sender
        )
        return {"status": "error", "error": str(e)}


@app.get("/webhooks/whatsapp")
async def verify_webhook(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None
):
    """Handle Meta webhook verification request.

    Meta sends a GET request with hub.* query params to verify the endpoint.

    Reference:
        https://developers.facebook.com/docs/graph-api/webhooks/getting-started#verification-requests
    """
    # Get verify token from environment
    expected_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")

    # Handle URL-encoded parameter names (hub.mode -> hub_mode)
    # Note: FastAPI automatically handles dot-to-underscore conversion

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Webhook verification successful")
        return PlainTextResponse(content=hub_challenge)

    logger.warning(f"Webhook verification failed: mode={hub_mode}")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhooks/whatsapp")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256")
):
    """Receive and process WhatsApp webhook events.

    Must respond with HTTP 200 within 500ms or Meta will retry.

    Security:
        - Validates X-Hub-Signature-256 header using app secret
        - Rate limits to 100 requests/minute per IP
    """
    client_ip = get_client_ip(request)

    # Check rate limit first (fast operation)
    if not await rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        audit = get_audit_logger()
        audit.log_security_event(
            component="whatsapp_webhook",
            action_type="rate_limit_exceeded",
            target=client_ip,
            reason="Too many requests"
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Get raw body for signature validation
    body = await request.body()

    # Validate signature
    app_secret = os.environ.get("WHATSAPP_APP_SECRET", "")
    if app_secret and not validate_signature(body, x_hub_signature_256, app_secret):
        logger.warning(f"Invalid webhook signature from IP: {client_ip}")
        audit = get_audit_logger()
        audit.log_security_event(
            component="whatsapp_webhook",
            action_type="invalid_signature",
            target=client_ip,
            reason="X-Hub-Signature-256 validation failed"
        )
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = WhatsAppWebhookPayload.model_validate_json(body)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        # Still return 200 to prevent retries for malformed payloads
        return JSONResponse(content={"status": "error", "message": "Invalid payload"})

    # Quick validation - must be whatsapp_business_account
    if payload.object != "whatsapp_business_account":
        logger.debug(f"Ignoring non-whatsapp object: {payload.object}")
        return JSONResponse(content={"status": "ignored"})

    # Extract messages and schedule for background processing
    messages_count = 0
    for entry in payload.entry:
        for change in entry.changes:
            for message in change.value.messages:
                if message.type == "text" and message.text:
                    messages_count += 1
                    # Schedule async processing after HTTP response
                    background_tasks.add_task(
                        process_message_async,
                        message=message,
                        sender=message.from_number,
                        keywords=config.keywords
                    )

    logger.info(f"Received webhook with {messages_count} text message(s)")

    # Return 200 immediately (within 500ms)
    return JSONResponse(content={
        "status": "received",
        "messages_queued": messages_count
    })


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={
        "status": "healthy",
        "service": "whatsapp-webhook",
        "enabled": config.enabled,
        "dry_run": DRY_RUN,
        "rate_limit": f"{config.webhook_rate_limit_per_minute}/min"
    })


@app.get("/stats")
async def get_stats():
    """Get webhook handler statistics."""
    db = get_idempotency_db()
    vault = get_vault()

    return JSONResponse(content={
        "service": "whatsapp-webhook",
        "config": {
            "enabled": config.enabled,
            "keywords": config.keywords,
            "rate_limit": config.webhook_rate_limit_per_minute
        },
        "idempotency": {
            "processed_messages": db.get_processed_count("whatsapp")
        },
        "vault": {
            "needs_action_files": len(vault.list_files("needs_action", "whatsapp-*.md"))
        }
    })


# =============================================================================
# Server Watcher Integration
# =============================================================================


class WhatsAppWebhookHandler(ServerWatcher):
    """WhatsApp webhook handler as a ServerWatcher.

    Allows integration with the watcher management system.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        config: WhatsAppConfig | None = None
    ):
        """Initialize WhatsApp webhook handler.

        Args:
            host: Host to bind to
            port: Port to listen on
            config: WhatsApp configuration
        """
        self._config = config or load_whatsapp_config()

        super().__init__(
            name="whatsapp_webhook",
            priority=WatcherPriority.MEDIUM,
            memory_limit_mb=self._config.memory_limit_mb,
            host=host,
            port=port,
            config=self._config
        )

    async def _run_server(self) -> None:
        """Run the FastAPI server."""
        import uvicorn

        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def process_event(self, event: Any) -> None:
        """Process is handled by FastAPI routes, not this method."""
        pass


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Get configuration
    host = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.environ.get("WEBHOOK_PORT", "8000"))

    logger.info(f"Starting WhatsApp webhook handler on {host}:{port}")

    uvicorn.run(
        "src.watchers.whatsapp_webhook:app",
        host=host,
        port=port,
        reload=False
    )
