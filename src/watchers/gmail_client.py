"""Gmail API Client Wrapper for Silver Tier.

Provides a high-level interface for Gmail API operations:
- OAuth2 authentication and token management
- Fetching unread/important emails
- Reading message content
- Marking messages as read

Uses google-api-python-client for Gmail API access.
Implements FR-001 from spec.
"""

import base64
import logging
import re
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any

from src.common.credentials import get_credential_manager, TokenExpiredError
from src.common.retry import exponential_backoff, OAUTH_RETRY_CONFIG

logger = logging.getLogger(__name__)

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"
]

# Service name for credential storage
GMAIL_SERVICE = "gmail"


class GmailClientError(Exception):
    """Base exception for Gmail client operations."""
    pass


class GmailAuthError(GmailClientError):
    """Authentication/authorization error."""
    pass


class GmailAPIError(GmailClientError):
    """Gmail API call failed."""
    pass


class GmailClient:
    """Gmail API client with OAuth2 authentication.

    Usage:
        client = GmailClient()

        # Authenticate (uses stored credentials)
        client.authenticate()

        # List unread important emails
        emails = client.list_unread_important(max_results=10)

        # Get full message content
        for email in emails:
            content = client.get_message_content(email['id'])
            print(content['subject'], content['from'])

        # Mark as read
        client.mark_as_read(email['id'])
    """

    def __init__(self):
        """Initialize Gmail client."""
        self._service = None
        self._credentials = None
        self._cred_manager = get_credential_manager()

    def _get_google_credentials(self):
        """Get Google OAuth2 credentials from stored token."""
        from google.oauth2.credentials import Credentials

        token_data = self._cred_manager.get_token(GMAIL_SERVICE)
        if not token_data:
            raise GmailAuthError(
                "No Gmail credentials found. Run scripts/setup_gmail_oauth.py first."
            )

        # Build credentials object
        credentials = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=GMAIL_SCOPES
        )

        return credentials

    def _refresh_credentials(self, credentials) -> bool:
        """Refresh expired credentials.

        Returns:
            True if refresh succeeded, False otherwise
        """
        from google.auth.transport.requests import Request

        try:
            credentials.refresh(Request())

            # Store refreshed token
            self._cred_manager.store_token(GMAIL_SERVICE, {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
            })

            logger.info("Gmail credentials refreshed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh Gmail credentials: {e}")
            return False

    def authenticate(self) -> bool:
        """Authenticate with Gmail API using stored credentials.

        Returns:
            True if authentication succeeded

        Raises:
            GmailAuthError: If authentication fails
        """
        from googleapiclient.discovery import build

        try:
            credentials = self._get_google_credentials()

            # Check if credentials need refresh
            if credentials.expired and credentials.refresh_token:
                if not self._refresh_credentials(credentials):
                    raise GmailAuthError("Failed to refresh expired credentials")

            # Build Gmail service
            self._service = build("gmail", "v1", credentials=credentials)
            self._credentials = credentials

            # Verify by getting user profile
            profile = self._service.users().getProfile(userId="me").execute()
            logger.info(f"Authenticated as: {profile.get('emailAddress')}")

            return True

        except GmailAuthError:
            raise
        except Exception as e:
            raise GmailAuthError(f"Gmail authentication failed: {e}") from e

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._service is not None

    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated before API calls."""
        if not self.is_authenticated():
            self.authenticate()

    @exponential_backoff(max_retries=3, retryable_exceptions=(GmailAPIError,))
    def list_unread_important(
        self,
        max_results: int = 10,
        labels: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """List unread important emails.

        Args:
            max_results: Maximum number of emails to return
            labels: Labels to filter by (default: INBOX, IMPORTANT, UNREAD)

        Returns:
            List of email metadata dicts with id, threadId, snippet
        """
        self._ensure_authenticated()

        if labels is None:
            labels = ["INBOX", "IMPORTANT", "UNREAD"]

        try:
            # Build query
            query = "is:unread"

            results = self._service.users().messages().list(
                userId="me",
                labelIds=labels,
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            logger.debug(f"Found {len(messages)} unread important emails")

            return messages

        except Exception as e:
            logger.error(f"Failed to list emails: {e}")
            raise GmailAPIError(f"Failed to list emails: {e}") from e

    @exponential_backoff(max_retries=3, retryable_exceptions=(GmailAPIError,))
    def list_unread_with_keywords(
        self,
        keywords: list[str],
        max_results: int = 10
    ) -> list[dict[str, Any]]:
        """List unread emails containing specific keywords.

        Args:
            keywords: Keywords to search for
            max_results: Maximum number of emails to return

        Returns:
            List of email metadata dicts
        """
        self._ensure_authenticated()

        try:
            # Build query with keywords
            keyword_query = " OR ".join(f'"{kw}"' for kw in keywords)
            query = f"is:unread ({keyword_query})"

            results = self._service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            logger.debug(f"Found {len(messages)} emails matching keywords")

            return messages

        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            raise GmailAPIError(f"Failed to search emails: {e}") from e

    @exponential_backoff(max_retries=3, retryable_exceptions=(GmailAPIError,))
    def get_message_content(self, message_id: str) -> dict[str, Any]:
        """Get full message content.

        Args:
            message_id: Gmail message ID

        Returns:
            Dict with: id, threadId, from, to, subject, date, body, snippet, labels
        """
        self._ensure_authenticated()

        try:
            message = self._service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            # Parse headers
            headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}

            # Parse body
            body = self._extract_body(message.get("payload", {}))

            # Parse sender
            from_header = headers.get("from", "")
            sender_name, sender_email = parseaddr(from_header)

            return {
                "id": message["id"],
                "thread_id": message.get("threadId"),
                "message_id": headers.get("message-id", message["id"]),
                "from": from_header,
                "from_email": sender_email,
                "from_name": sender_name,
                "to": headers.get("to", ""),
                "cc": headers.get("cc", ""),
                "subject": headers.get("subject", "(no subject)"),
                "date": headers.get("date", ""),
                "body": body,
                "snippet": message.get("snippet", ""),
                "labels": message.get("labelIds", []),
                "internal_date": message.get("internalDate")
            }

        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise GmailAPIError(f"Failed to get message: {e}") from e

    def _extract_body(self, payload: dict) -> str:
        """Extract message body from payload.

        Handles both single-part and multipart messages.
        Prefers plain text over HTML.
        """
        body = ""

        if "body" in payload and payload["body"].get("data"):
            # Single part message
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            # Multipart message - look for text/plain first, then text/html
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")

                if mime_type == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    break
                elif mime_type == "text/html" and not body and part.get("body", {}).get("data"):
                    html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    # Simple HTML to text conversion
                    body = self._html_to_text(html)
                elif "parts" in part:
                    # Nested multipart
                    nested_body = self._extract_body(part)
                    if nested_body and not body:
                        body = nested_body

        return body.strip()

    def _html_to_text(self, html: str) -> str:
        """Simple HTML to text conversion."""
        # Remove script and style elements
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Replace common tags
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)

        # Remove all other tags
        text = re.sub(r'<[^>]+>', '', text)

        # Decode HTML entities
        import html
        text = html.unescape(text)

        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()

    @exponential_backoff(max_retries=3, retryable_exceptions=(GmailAPIError,))
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read.

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful
        """
        self._ensure_authenticated()

        try:
            self._service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()

            logger.debug(f"Marked message {message_id} as read")
            return True

        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            raise GmailAPIError(f"Failed to mark as read: {e}") from e

    @exponential_backoff(max_retries=3, retryable_exceptions=(GmailAPIError,))
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        html: bool = False
    ) -> dict[str, Any]:
        """Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            cc: CC recipients
            bcc: BCC recipients
            html: If True, body is HTML

        Returns:
            Dict with id, threadId of sent message
        """
        self._ensure_authenticated()

        import email.mime.text
        import email.mime.multipart

        try:
            # Create message
            if html:
                msg = email.mime.multipart.MIMEMultipart("alternative")
                msg.attach(email.mime.text.MIMEText(body, "html"))
            else:
                msg = email.mime.text.MIMEText(body)

            msg["To"] = to
            msg["Subject"] = subject

            if cc:
                msg["Cc"] = ", ".join(cc)
            if bcc:
                msg["Bcc"] = ", ".join(bcc)

            # Encode message
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

            # Send
            result = self._service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            logger.info(f"Sent email to {to}: {result.get('id')}")

            return {
                "id": result.get("id"),
                "thread_id": result.get("threadId"),
                "message_id": result.get("id")  # Gmail returns internal ID
            }

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise GmailAPIError(f"Failed to send email: {e}") from e

    def get_profile(self) -> dict[str, Any]:
        """Get authenticated user's profile.

        Returns:
            Dict with emailAddress, messagesTotal, threadsTotal, historyId
        """
        self._ensure_authenticated()

        try:
            return self._service.users().getProfile(userId="me").execute()
        except Exception as e:
            raise GmailAPIError(f"Failed to get profile: {e}") from e


# Module-level convenience instance
_default_client: GmailClient | None = None


def get_gmail_client() -> GmailClient:
    """Get the default Gmail client instance."""
    global _default_client
    if _default_client is None:
        _default_client = GmailClient()
    return _default_client
