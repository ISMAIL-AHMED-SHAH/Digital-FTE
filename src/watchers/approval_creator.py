"""Approval File Creator for Silver Tier.

Creates approval request files in /Pending_Approval with:
- YAML frontmatter containing action details and integrity hash
- Markdown body explaining the action for human review

Implements FR-006, FR-007, FR-020 from spec.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.common.audit_logger import get_audit_logger
from src.common.integrity import generate_hash
from src.common.vault import get_vault
from src.watchers.models import ActionType, ApprovalRequest, ApprovalStatus

logger = logging.getLogger(__name__)


class ApprovalCreationError(Exception):
    """Error creating approval file."""
    pass


def _sanitize_filename(text: str, max_length: int = 50) -> str:
    """Create a safe filename from text.

    Args:
        text: Text to convert to filename
        max_length: Maximum length of the result

    Returns:
        Safe filename string
    """
    # Remove or replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', text)
    safe = re.sub(r'\s+', '_', safe)
    safe = re.sub(r'[^\w\-_.]', '', safe)

    # Truncate and clean up
    if len(safe) > max_length:
        safe = safe[:max_length]

    return safe.strip('_.')


def _generate_approval_filename(
    action_type: str,
    target: str | None = None,
    timestamp: datetime | None = None
) -> str:
    """Generate a unique filename for the approval file.

    Format: YYYY-MM-DD_HHMMSS_{action_type}_{target}.md

    Args:
        action_type: Type of action (email_send, linkedin_post)
        target: Optional target identifier (email, visibility)
        timestamp: Timestamp for the file (default: now)

    Returns:
        Filename string
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    date_str = timestamp.strftime("%Y-%m-%d_%H%M%S")
    action_safe = _sanitize_filename(action_type, 20)

    if target:
        target_safe = _sanitize_filename(target, 30)
        return f"{date_str}_{action_safe}_{target_safe}.md"

    return f"{date_str}_{action_safe}.md"


def _format_parameters_for_display(parameters: dict[str, Any]) -> str:
    """Format parameters as readable markdown for human review.

    Args:
        parameters: Action parameters

    Returns:
        Markdown-formatted string
    """
    lines = []

    for key, value in parameters.items():
        display_key = key.replace("_", " ").title()

        if isinstance(value, list):
            if value:
                lines.append(f"- **{display_key}**: {', '.join(str(v) for v in value)}")
            else:
                lines.append(f"- **{display_key}**: (none)")
        elif isinstance(value, str) and len(value) > 100:
            # Multi-line content
            lines.append(f"- **{display_key}**:")
            lines.append("  ```")
            lines.append(f"  {value[:500]}{'...' if len(value) > 500 else ''}")
            lines.append("  ```")
        else:
            lines.append(f"- **{display_key}**: {value}")

    return "\n".join(lines)


def _get_action_description(action_type: str) -> str:
    """Get human-readable description for an action type."""
    descriptions = {
        "email_send": "Send Email",
        "linkedin_post": "Publish LinkedIn Post",
        "whatsapp_send": "Send WhatsApp Message",
        "file_operation": "File Operation",
    }
    return descriptions.get(action_type, action_type.replace("_", " ").title())


def _generate_markdown_body(request: ApprovalRequest) -> str:
    """Generate the markdown body for the approval file.

    Args:
        request: The approval request

    Returns:
        Markdown content for human review
    """
    action_desc = _get_action_description(
        request.action_type if isinstance(request.action_type, str) else request.action_type.value
    )

    # Get target from parameters
    target = request.parameters.get("to") or request.parameters.get("visibility") or "N/A"

    body = f"""## Approval Required: {action_desc}

**Requested by**: {request.approval_requested_by}
**Created**: {request.created_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Expires**: {request.expires_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

### Reason

{request.reason}

### Action Details

**Type**: {action_desc}
**Target**: {target}

### Parameters

{_format_parameters_for_display(request.parameters)}

---

## How to Approve or Reject

- **To APPROVE**: Move this file to the `Approved` folder
- **To REJECT**: Move this file to the `Rejected` folder
- **If you do nothing**: This request will automatically expire

### Security Notice

This file contains an integrity hash to prevent tampering.
If you modify the parameters above, the action will be **rejected**
when processed because the hash will no longer match.

**Integrity Hash**: `{request.integrity_hash[:16]}...`

---

*This approval request was generated automatically by the AI Employee system.*
"""

    return body


def create_approval_file(
    action_type: ActionType | str,
    parameters: dict[str, Any],
    reason: str,
    original_action_file: str | None = None,
    vault_path: str | Path | None = None,
    dry_run: bool = False
) -> tuple[ApprovalRequest, Path | None]:
    """Create an approval request file in /Pending_Approval.

    This function:
    1. Creates an ApprovalRequest with computed integrity hash
    2. Generates YAML frontmatter + Markdown body
    3. Writes to /Pending_Approval folder
    4. Logs the creation for audit trail

    Args:
        action_type: Type of action (email_send, linkedin_post, etc.)
        parameters: Action parameters (to, subject, body, etc.)
        reason: Why this action is needed (context for reviewer)
        original_action_file: Path to the original action file
        vault_path: Override vault path (default: from env)
        dry_run: If True, don't write file, just return the request

    Returns:
        Tuple of (ApprovalRequest, Path to created file or None if dry_run)

    Raises:
        ApprovalCreationError: If file creation fails
    """
    # Convert action_type to string if enum
    action_type_str = action_type if isinstance(action_type, str) else action_type.value

    # Create the approval request
    created_at = datetime.now(timezone.utc)

    # Generate integrity hash
    integrity_hash = generate_hash(
        action_type=action_type_str,
        parameters=parameters,
        created_timestamp=created_at.isoformat()
    )

    request = ApprovalRequest(
        action_type=action_type_str,
        parameters=parameters,
        reason=reason,
        created_timestamp=created_at,
        integrity_hash=integrity_hash,
        original_action_file=original_action_file
    )

    # Log for audit
    audit = get_audit_logger()

    if dry_run:
        logger.info(f"[DRY-RUN] Would create approval file for {action_type_str}")
        audit.log(
            component="approval_creator",
            action_type="approval_request_created",
            target=parameters.get("to") or parameters.get("visibility") or "unknown",
            parameters={"action_type": action_type_str, "dry_run": True},
            result="dry_run_skipped"
        )
        return request, None

    # Generate file content
    yaml_frontmatter = request.to_yaml_frontmatter()
    markdown_body = _generate_markdown_body(request)
    file_content = f"---\n{yaml_frontmatter}---\n\n{markdown_body}"

    # Generate filename
    target = parameters.get("to") or parameters.get("visibility")
    filename = _generate_approval_filename(action_type_str, target, created_at)

    # Write to vault
    try:
        vault = get_vault(vault_path)
        file_path = vault.write_file("pending_approval", filename, file_content)

        logger.info(f"Created approval file: {file_path}")

        audit.log_approval(
            component="approval_creator",
            action_type=action_type_str,
            target=parameters.get("to") or parameters.get("visibility") or "unknown",
            approval_status="pending",
            parameters={
                "filename": filename,
                "integrity_hash": integrity_hash[:16] + "...",
                "expires_at": request.expires_timestamp.isoformat()
            }
        )

        return request, file_path

    except Exception as e:
        logger.exception(f"Failed to create approval file: {e}")
        audit.log_error(
            component="approval_creator",
            action_type="approval_file_creation",
            error=e,
            target=action_type_str
        )
        raise ApprovalCreationError(f"Failed to create approval file: {e}") from e


def create_email_approval(
    to: str,
    subject: str,
    body: str,
    reason: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    attachments: list[str] | None = None,
    **kwargs
) -> tuple[ApprovalRequest, Path | None]:
    """Convenience function to create email send approval.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        reason: Why this email should be sent
        cc: CC recipients
        bcc: BCC recipients
        attachments: File paths to attach
        **kwargs: Additional arguments for create_approval_file

    Returns:
        Tuple of (ApprovalRequest, Path)
    """
    parameters = {
        "to": to,
        "subject": subject,
        "body": body,
        "cc": cc or [],
        "bcc": bcc or [],
        "attachments": attachments or []
    }

    return create_approval_file(
        action_type=ActionType.EMAIL_SEND,
        parameters=parameters,
        reason=reason,
        **kwargs
    )


def create_linkedin_approval(
    content: str,
    reason: str,
    visibility: str = "PUBLIC",
    media: list[str] | None = None,
    **kwargs
) -> tuple[ApprovalRequest, Path | None]:
    """Convenience function to create LinkedIn post approval.

    Args:
        content: Post content (max 3000 chars)
        reason: Why this post should be published
        visibility: PUBLIC or CONNECTIONS
        media: Media file paths
        **kwargs: Additional arguments for create_approval_file

    Returns:
        Tuple of (ApprovalRequest, Path)
    """
    parameters = {
        "content": content,
        "visibility": visibility,
        "media": media or []
    }

    return create_approval_file(
        action_type=ActionType.LINKEDIN_POST,
        parameters=parameters,
        reason=reason,
        **kwargs
    )
