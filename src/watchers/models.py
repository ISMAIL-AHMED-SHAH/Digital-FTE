"""Pydantic Models for Silver Tier Watchers.

Defines data models for action files, approval requests, and
related entities with validation and serialization support.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ActionType(str, Enum):
    """Types of actions that can be requested."""
    EMAIL_SEND = "email_send"
    LINKEDIN_POST = "linkedin_post"
    WHATSAPP_SEND = "whatsapp_send"
    FILE_OPERATION = "file_operation"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionPriority(str, Enum):
    """Priority level for actions."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class ActionFileMetadata(BaseModel):
    """Metadata for incoming action files from watchers.

    These files are created in /Needs_Action when events are detected.
    """
    type: str = Field(..., description="Event type: email, whatsapp, file_drop")
    source: str = Field(..., description="Source identifier (email address, phone, path)")
    subject: str = Field(..., description="Subject or preview text")
    content: str = Field(..., description="Full content or file metadata")
    priority: ActionPriority = Field(default=ActionPriority.NORMAL)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: str = Field(..., description="Unique message ID for idempotency")
    status: str = Field(default="pending")

    class Config:
        use_enum_values = True


class ApprovalRequest(BaseModel):
    """Approval request model for human-in-the-loop workflow.

    Created when Claude identifies a sensitive action requiring approval.
    Written to /Pending_Approval with YAML frontmatter.

    The integrity_hash provides tamper detection - if any critical field
    is modified after creation, the hash will not match and the action
    will be rejected.

    Implements FR-006, FR-007, FR-020 from spec.
    """
    action_type: ActionType = Field(
        ...,
        description="Type of action to execute"
    )
    parameters: dict[str, Any] = Field(
        ...,
        description="Action parameters (to, subject, body, etc.)"
    )
    reason: str = Field(
        ...,
        description="Why this action is needed (context for human reviewer)"
    )
    created_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the approval request was created"
    )
    expires_timestamp: datetime = Field(
        default=None,
        description="When the request expires (created + 24h by default)"
    )
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Current status of the request"
    )
    integrity_hash: str = Field(
        default="",
        description="SHA-256 hash of action_type + parameters + created_timestamp"
    )
    approval_requested_by: str = Field(
        default="claude-code",
        description="System that requested the approval"
    )
    original_action_file: str | None = Field(
        default=None,
        description="Path to the original action file that triggered this request"
    )

    class Config:
        use_enum_values = True

    @model_validator(mode="after")
    def set_defaults(self) -> "ApprovalRequest":
        """Set computed defaults after model creation."""
        # Set expiration to 24 hours from creation if not set
        if self.expires_timestamp is None:
            self.expires_timestamp = self.created_timestamp + timedelta(hours=24)

        # Generate integrity hash if not set
        if not self.integrity_hash:
            from src.common.integrity import generate_hash
            self.integrity_hash = generate_hash(
                action_type=self.action_type if isinstance(self.action_type, str) else self.action_type.value,
                parameters=self.parameters,
                created_timestamp=self.created_timestamp.isoformat()
            )

        return self

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v: dict[str, Any], info) -> dict[str, Any]:
        """Validate that required parameters are present based on action type."""
        # This is called before action_type is available in info.data for some Pydantic versions
        # Full validation should be done at the service layer
        if not isinstance(v, dict):
            raise ValueError("parameters must be a dictionary")
        return v

    def is_expired(self) -> bool:
        """Check if the approval request has expired."""
        return datetime.now(timezone.utc) >= self.expires_timestamp

    def validate_integrity(self) -> bool:
        """Validate that the integrity hash matches the current values.

        Returns:
            True if hash matches (not tampered), False otherwise
        """
        from src.common.integrity import validate_hash
        return validate_hash(
            action_type=self.action_type if isinstance(self.action_type, str) else self.action_type.value,
            parameters=self.parameters,
            created_timestamp=self.created_timestamp.isoformat(),
            expected_hash=self.integrity_hash
        )

    def to_yaml_frontmatter(self) -> str:
        """Generate YAML frontmatter for the approval file."""
        import yaml

        data = {
            "action_type": self.action_type if isinstance(self.action_type, str) else self.action_type.value,
            "parameters": self.parameters,
            "reason": self.reason,
            "created_timestamp": self.created_timestamp.isoformat(),
            "expires_timestamp": self.expires_timestamp.isoformat(),
            "status": self.status if isinstance(self.status, str) else self.status.value,
            "integrity_hash": self.integrity_hash,
            "approval_requested_by": self.approval_requested_by,
        }

        if self.original_action_file:
            data["original_action_file"] = self.original_action_file

        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @classmethod
    def from_yaml_frontmatter(cls, yaml_content: str) -> "ApprovalRequest":
        """Parse an ApprovalRequest from YAML frontmatter."""
        import yaml

        data = yaml.safe_load(yaml_content)

        # Parse timestamps
        if isinstance(data.get("created_timestamp"), str):
            data["created_timestamp"] = datetime.fromisoformat(
                data["created_timestamp"].replace("Z", "+00:00")
            )
        if isinstance(data.get("expires_timestamp"), str):
            data["expires_timestamp"] = datetime.fromisoformat(
                data["expires_timestamp"].replace("Z", "+00:00")
            )

        return cls(**data)


class ApprovalResult(BaseModel):
    """Result of processing an approved or rejected action."""
    request: ApprovalRequest
    status: ApprovalStatus
    executed: bool = False
    result: str | None = None
    error: str | None = None
    external_id: str | None = None
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmailParameters(BaseModel):
    """Parameters for email_send action type."""
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body (plain text or HTML)")
    cc: list[str] = Field(default_factory=list, description="CC recipients")
    bcc: list[str] = Field(default_factory=list, description="BCC recipients")
    attachments: list[str] = Field(default_factory=list, description="File paths to attach")
    reply_to: str | None = Field(default=None, description="Reply-to address")


class LinkedInPostParameters(BaseModel):
    """Parameters for linkedin_post action type."""
    content: str = Field(..., max_length=3000, description="Post content")
    visibility: str = Field(default="PUBLIC", description="PUBLIC or CONNECTIONS")
    media: list[str] = Field(default_factory=list, description="Media file paths")


class WhatsAppParameters(BaseModel):
    """Parameters for whatsapp_send action type."""
    to: str = Field(..., description="Recipient phone number")
    message: str = Field(..., description="Message content")
    media_url: str | None = Field(default=None, description="Optional media URL")
