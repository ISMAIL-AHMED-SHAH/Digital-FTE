"""Integrity Hash Module for Silver Tier.

Provides SHA-256 hash generation and validation for approval files
to prevent tampering with action parameters.

Implements FR-020 from spec.
"""

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class IntegrityError(Exception):
    """Base exception for integrity operations."""
    pass


class HashMismatchError(IntegrityError):
    """Hash validation failed - file may have been tampered with."""
    pass


def _normalize_value(value: Any) -> str:
    """Normalize a value for consistent hashing.

    Handles different types to ensure consistent hash regardless of
    how the data was serialized/deserialized.
    """
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return value
    elif isinstance(value, (list, tuple)):
        return "[" + ",".join(_normalize_value(v) for v in value) + "]"
    elif isinstance(value, dict):
        # Sort keys for consistent ordering
        sorted_items = sorted(value.items())
        return "{" + ",".join(f"{k}:{_normalize_value(v)}" for k, v in sorted_items) + "}"
    else:
        return str(value)


def _serialize_for_hash(
    action_type: str,
    parameters: dict[str, Any],
    created_timestamp: str
) -> str:
    """Serialize fields into a consistent string for hashing.

    The serialization must be deterministic - same inputs always produce
    same output regardless of dict ordering or whitespace.
    """
    # Normalize parameters
    normalized_params = _normalize_value(parameters)

    # Concatenate fields with delimiter
    serialized = f"{action_type}|{normalized_params}|{created_timestamp}"

    return serialized


def generate_hash(
    action_type: str,
    parameters: dict[str, Any],
    created_timestamp: str
) -> str:
    """Generate SHA-256 hash of approval request critical fields.

    This hash is embedded in the approval file's YAML frontmatter and
    verified before executing the action to detect tampering.

    Args:
        action_type: Type of action (email_send, linkedin_post, etc.)
        parameters: Action parameters (to, subject, body, etc.)
        created_timestamp: ISO 8601 timestamp when approval was created

    Returns:
        Hex-encoded SHA-256 hash string (64 characters)

    Example:
        >>> hash = generate_hash(
        ...     action_type="email_send",
        ...     parameters={"to": "user@example.com", "subject": "Hello"},
        ...     created_timestamp="2026-01-25T10:00:00Z"
        ... )
        >>> len(hash)
        64
    """
    serialized = _serialize_for_hash(action_type, parameters, created_timestamp)

    # Generate SHA-256 hash
    hash_bytes = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    logger.debug(f"Generated hash for {action_type}: {hash_bytes[:16]}...")
    return hash_bytes


def validate_hash(
    action_type: str,
    parameters: dict[str, Any],
    created_timestamp: str,
    expected_hash: str
) -> bool:
    """Validate that the hash matches the expected value.

    Args:
        action_type: Type of action
        parameters: Action parameters
        created_timestamp: Creation timestamp
        expected_hash: Hash to validate against

    Returns:
        True if hash matches, False otherwise
    """
    computed_hash = generate_hash(action_type, parameters, created_timestamp)
    is_valid = computed_hash == expected_hash

    if not is_valid:
        logger.warning(
            f"Hash mismatch for {action_type}: "
            f"expected {expected_hash[:16]}..., got {computed_hash[:16]}..."
        )

    return is_valid


def validate_hash_strict(
    action_type: str,
    parameters: dict[str, Any],
    created_timestamp: str,
    expected_hash: str
) -> None:
    """Validate hash and raise exception on mismatch.

    Args:
        action_type: Type of action
        parameters: Action parameters
        created_timestamp: Creation timestamp
        expected_hash: Hash to validate against

    Raises:
        HashMismatchError: If hash doesn't match (possible tampering)
    """
    if not validate_hash(action_type, parameters, created_timestamp, expected_hash):
        raise HashMismatchError(
            f"Integrity check failed for {action_type}. "
            f"The approval file may have been tampered with."
        )


def generate_action_id(
    content: str,
    recipient: str | None = None,
    timestamp_minute: str | None = None
) -> str:
    """Generate a unique action ID for idempotency checking.

    Used to create stable identifiers for actions that don't have
    natural IDs (like LinkedIn posts).

    Args:
        content: Main content of the action
        recipient: Optional recipient (email, visibility)
        timestamp_minute: Optional timestamp rounded to minute for uniqueness window

    Returns:
        SHA-256 hash of the combined fields
    """
    parts = [content]
    if recipient:
        parts.append(recipient)
    if timestamp_minute:
        parts.append(timestamp_minute)

    combined = "|".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def generate_message_hash(content: str, sender: str | None = None) -> str:
    """Generate a hash for message deduplication.

    Used for WhatsApp messages that don't have Message-ID headers.

    Args:
        content: Message content
        sender: Optional sender identifier

    Returns:
        SHA-256 hash of the message
    """
    parts = [content]
    if sender:
        parts.append(sender)

    combined = "|".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


# Convenience aliases
hash_action = generate_hash
verify_hash = validate_hash
