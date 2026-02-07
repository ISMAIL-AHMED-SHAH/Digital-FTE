# Silver Tier Data Models

This document defines the Pydantic models and data structures used throughout the AI Employee Silver Tier implementation.

## Table of Contents

1. [Action File Models](#action-file-models)
2. [Watcher Models](#watcher-models)
3. [MCP Models](#mcp-models)
4. [Configuration Models](#configuration-models)
5. [Database Models](#database-models)

---

## Action File Models

### ActionFile

Base model for action files created by watchers and processed by the approval workflow.

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

class ActionType(str, Enum):
    """Types of actions that can be created."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    LINKEDIN = "linkedin"
    FILE_DROP = "file_drop"

class ActionStatus(str, Enum):
    """Status of an action in the workflow."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    DONE = "done"

class ActionPriority(str, Enum):
    """Priority levels for actions."""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

class ActionFile(BaseModel):
    """
    Represents an action file in the vault.

    These files are created by watchers in /Needs_Action and move
    through the approval workflow.
    """
    type: ActionType
    source: str = Field(description="Source identifier (email, phone, etc.)")
    subject: str = Field(description="Action subject/title")
    content: str = Field(description="Action content/body")
    priority: ActionPriority = ActionPriority.NORMAL
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: ActionStatus = ActionStatus.PENDING
    message_id: str = Field(description="Unique ID for idempotency")

    # Optional metadata
    matched_keywords: Optional[List[str]] = None
    integrity_hash: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
```

### EmailActionFile

Specialized action file for email-related actions.

```python
class EmailActionFile(ActionFile):
    """Action file for email operations."""
    type: ActionType = ActionType.EMAIL

    # Email-specific fields
    sender: str = Field(description="Sender email address")
    recipients: List[str] = Field(description="Recipient email addresses")
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    thread_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    html_body: Optional[str] = None
    attachments: Optional[List[str]] = None
```

### WhatsAppActionFile

Specialized action file for WhatsApp messages.

```python
class WhatsAppActionFile(ActionFile):
    """Action file for WhatsApp messages."""
    type: ActionType = ActionType.WHATSAPP

    # WhatsApp-specific fields
    phone_number: str = Field(description="Sender phone number")
    wa_message_id: str = Field(description="WhatsApp message ID")
    contact_name: Optional[str] = None
```

### LinkedInActionFile

Specialized action file for LinkedIn posts.

```python
class Visibility(str, Enum):
    """LinkedIn post visibility options."""
    PUBLIC = "PUBLIC"
    CONNECTIONS = "CONNECTIONS"

class LinkedInActionFile(ActionFile):
    """Action file for LinkedIn posts."""
    type: ActionType = ActionType.LINKEDIN

    # LinkedIn-specific fields
    visibility: Visibility = Visibility.PUBLIC
    media_urls: Optional[List[str]] = None
```

---

## Watcher Models

### WatcherStatus

```python
class WatcherStatus(str, Enum):
    """Watcher lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

class WatcherPriority(int, Enum):
    """Watcher priority levels for graceful degradation."""
    HIGH = 1      # Gmail - critical business communication
    MEDIUM = 2    # WhatsApp - important but secondary
    LOW = 3       # LinkedIn - can be paused first
```

### WatcherStats

```python
class WatcherStats(BaseModel):
    """Statistics for a watcher instance."""
    name: str
    status: WatcherStatus
    priority: WatcherPriority
    memory_usage_mb: float
    memory_limit_mb: int
    events_processed: int
    errors_count: int
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    dry_run: bool = False
```

### ResourceMetrics

```python
class ResourceState(str, Enum):
    """Resource monitor states."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    DEGRADED = "degraded"

class ProcessMemory(BaseModel):
    """Memory usage for a single process."""
    name: str
    pid: Optional[int] = None
    memory_mb: float
    paused: bool = False

class ResourceMetrics(BaseModel):
    """Snapshot of resource usage."""
    timestamp: datetime
    state: ResourceState
    total_memory_mb: float
    budget_mb: int
    usage_percent: float
    alert_threshold_mb: float
    recovery_threshold_mb: float
    processes: List[ProcessMemory]
```

---

## MCP Models

### Gmail MCP Models

```python
class SendEmailInput(BaseModel):
    """Input schema for send_email MCP tool."""
    to: str = Field(description="Recipient email address")
    subject: str = Field(min_length=1, max_length=998)
    body: str = Field(min_length=1)
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    html: bool = False
    reply_to_message_id: Optional[str] = None

class SendEmailOutput(BaseModel):
    """Output schema for send_email MCP tool."""
    success: bool
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    error: Optional[str] = None
    rate_limit: Optional[dict] = None
```

### LinkedIn MCP Models

```python
class CreatePostInput(BaseModel):
    """Input schema for create_post MCP tool."""
    content: str = Field(min_length=1, max_length=3000)
    visibility: Visibility = Visibility.PUBLIC
    media: Optional[List[str]] = None
    dry_run: bool = False

class CreatePostOutput(BaseModel):
    """Output schema for create_post MCP tool."""
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    rate_limit: Optional[dict] = None
```

---

## Configuration Models

### WatcherConfig

```python
class GlobalConfig(BaseModel):
    """Global configuration settings."""
    total_memory_budget_mb: int = 500
    memory_alert_threshold_percent: int = 80
    memory_recovery_threshold_percent: int = 70
    resource_check_interval_seconds: int = 60
    idempotency_retention_days: int = 7
    approval_expiration_hours: int = 24

class GmailConfig(BaseModel):
    """Gmail watcher configuration."""
    enabled: bool = True
    priority: int = 1
    memory_limit_mb: int = 100
    poll_interval_seconds: int = 120
    keywords: List[str] = ["urgent", "important", "invoice"]
    labels: List[str] = ["INBOX", "IMPORTANT"]
    max_emails_per_poll: int = 10
    send_rate_limit_per_day: int = 50

class WhatsAppConfig(BaseModel):
    """WhatsApp watcher configuration."""
    enabled: bool = True
    priority: int = 2
    memory_limit_mb: int = 100
    keywords: List[str] = ["invoice", "pricing", "support"]
    webhook_rate_limit_per_minute: int = 100
    webhook_response_timeout_ms: int = 500

class LinkedInConfig(BaseModel):
    """LinkedIn MCP configuration."""
    enabled: bool = True
    priority: int = 3
    memory_limit_mb: int = 100
    post_rate_limit_per_day: int = 10
    max_post_length: int = 3000
    default_visibility: str = "PUBLIC"

class WatcherConfigFile(BaseModel):
    """Complete watcher configuration file."""
    global_: GlobalConfig = Field(alias="global")
    gmail: GmailConfig = GmailConfig()
    whatsapp: WhatsAppConfig = WhatsAppConfig()
    linkedin: LinkedInConfig = LinkedInConfig()
```

### SchedulerConfig

```python
class ScheduledTask(BaseModel):
    """Configuration for a scheduled task."""
    module: str = Field(description="Python module path")
    function: str = "run"
    schedule: Optional[str] = Field(description="Cron expression")
    description: str = ""
    enabled: bool = True
    parameters: dict = Field(default_factory=dict)

class SchedulerConfig(BaseModel):
    """Scheduler configuration file."""
    tasks: dict[str, ScheduledTask]
    settings: dict = Field(default_factory=dict)
```

---

## Database Models

### Idempotency Models

```python
class ProcessedMessage(BaseModel):
    """Record of a processed message in the idempotency database."""
    message_id: str = Field(description="SHA-256 hash or Message-ID")
    source: str = Field(description="Source watcher")
    processed_at: datetime
    expires_at: datetime
    sender: Optional[str] = None
    subject: Optional[str] = None

class SentAction(BaseModel):
    """Record of a sent action in the idempotency database."""
    action_id: str = Field(description="Idempotency key")
    action_type: str
    recipient: Optional[str] = None
    sent_at: datetime
    expires_at: datetime
    result_status: str  # 'success' or 'failed'
    error_message: Optional[str] = None
    external_id: Optional[str] = None

class RateLimitRecord(BaseModel):
    """Rate limit counter record."""
    action_type: str
    limit_date: str  # YYYY-MM-DD
    current_count: int
    max_count: int
    updated_at: datetime
```

### Audit Log Models

```python
class AuditLogEntry(BaseModel):
    """
    Structured audit log entry.

    Written to /Vault/Logs/YYYY-MM-DD.json as JSON-lines.
    """
    timestamp: datetime
    level: str = "INFO"
    component: str
    action_type: str
    actor: Optional[str] = None
    target: Optional[str] = None
    parameters: Optional[dict] = None
    approval_status: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
```

---

## OAuth Token Models

```python
class GmailToken(BaseModel):
    """Gmail OAuth token structure."""
    access_token: str
    refresh_token: str
    client_id: str
    client_secret: str
    expires_at: Optional[datetime] = None

class LinkedInToken(BaseModel):
    """LinkedIn OAuth token structure."""
    access_token: str
    refresh_token: Optional[str] = None
    client_id: str
    client_secret: str
    expires_at: Optional[datetime] = None
```

---

## Webhook Models

### WhatsApp Webhook Payload

```python
class WhatsAppMessageText(BaseModel):
    """Text content of a WhatsApp message."""
    body: str

class WhatsAppMessage(BaseModel):
    """Individual WhatsApp message from webhook."""
    from_number: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: Optional[WhatsAppMessageText] = None

class WhatsAppMetadata(BaseModel):
    """Metadata about the WhatsApp Business account."""
    display_phone_number: Optional[str] = None
    phone_number_id: Optional[str] = None

class WhatsAppValue(BaseModel):
    """Value object containing messages."""
    messaging_product: Optional[str] = None
    metadata: Optional[WhatsAppMetadata] = None
    messages: List[WhatsAppMessage] = []
    contacts: List[dict] = []
    statuses: List[dict] = []

class WhatsAppChange(BaseModel):
    """Change object from webhook."""
    value: WhatsAppValue
    field: Optional[str] = None

class WhatsAppEntry(BaseModel):
    """Entry containing changes."""
    id: str
    changes: List[WhatsAppChange] = []

class WhatsAppWebhookPayload(BaseModel):
    """Complete webhook payload from Meta."""
    object: str
    entry: List[WhatsAppEntry] = []
```

---

## File Integrity Models

```python
class IntegrityBlock(BaseModel):
    """
    Integrity information embedded in action files.

    Stored in YAML frontmatter for tamper detection.
    """
    hash: str = Field(description="SHA-256 hash of content")
    algorithm: str = "sha256"
    created_at: datetime

class IntegrityValidationResult(BaseModel):
    """Result of integrity validation."""
    valid: bool
    expected_hash: str
    actual_hash: str
    file_path: str
    error: Optional[str] = None
```

---

## Notes

- All datetime fields use UTC timezone
- Pydantic v2 syntax is used throughout
- Models are designed for serialization to/from YAML frontmatter
- Idempotency keys use SHA-256 truncated to 32 hex characters
