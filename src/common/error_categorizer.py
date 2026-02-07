"""Error Categorization for Gold Tier (FR-025).

Provides consistent error classification across all components:
- Transient: Temporary failures, should retry with backoff
- Auth: Authentication/authorization failures, pause and alert
- Logic: Business logic errors, needs human review
- Data: Data validation/corruption errors, quarantine file
- System: System-level errors, auto-restart via watchdog

Each category has an associated recovery strategy.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error category enum."""
    TRANSIENT = "transient"  # Retry with backoff
    AUTH = "auth"            # Pause component + alert user
    LOGIC = "logic"          # Human review required
    DATA = "data"            # Quarantine file + alert
    SYSTEM = "system"        # Auto-restart via watchdog
    UNKNOWN = "unknown"      # Fallback category


class RecoveryStrategy(str, Enum):
    """Recovery strategy enum."""
    RETRY = "retry"                     # Retry with exponential backoff
    PAUSE_AND_ALERT = "pause_and_alert" # Stop component, notify user
    HUMAN_REVIEW = "human_review"       # Queue for human intervention
    QUARANTINE = "quarantine"           # Move to quarantine folder
    AUTO_RESTART = "auto_restart"       # Watchdog will restart
    QUEUE = "queue"                     # Queue for later processing
    SKIP = "skip"                       # Skip this item, continue


@dataclass
class CategorizedError:
    """Result of error categorization.

    Attributes:
        category: Error category
        strategy: Recommended recovery strategy
        retryable: Whether the error can be retried
        original_error: Original exception or error message
        error_code: Extracted error code if any
        service: Service that generated the error
        context: Additional context info
        suggested_action: Human-readable suggestion
    """
    category: ErrorCategory
    strategy: RecoveryStrategy
    retryable: bool
    original_error: str
    error_code: str | None = None
    service: str | None = None
    context: dict[str, Any] | None = None
    suggested_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "strategy": self.strategy.value,
            "retryable": self.retryable,
            "original_error": self.original_error,
            "error_code": self.error_code,
            "service": self.service,
            "context": self.context,
            "suggested_action": self.suggested_action
        }


# Error patterns for categorization
# Each pattern is (regex, category, strategy, retryable, suggestion)
ERROR_PATTERNS = [
    # ==========================================================================
    # Transient Errors (retry with backoff)
    # ==========================================================================
    (
        r"(connection|connect).*?(timeout|timed out|refused|reset)",
        ErrorCategory.TRANSIENT,
        RecoveryStrategy.RETRY,
        True,
        "Network issue - will retry automatically"
    ),
    (
        r"(rate.?limit|too many requests|429|throttl)",
        ErrorCategory.TRANSIENT,
        RecoveryStrategy.RETRY,
        True,
        "Rate limited - will retry after cooldown"
    ),
    (
        r"(503|502|504|service unavailable|bad gateway|gateway timeout)",
        ErrorCategory.TRANSIENT,
        RecoveryStrategy.RETRY,
        True,
        "Service temporarily unavailable - will retry"
    ),
    (
        r"(temporary|transient|intermittent|try again)",
        ErrorCategory.TRANSIENT,
        RecoveryStrategy.RETRY,
        True,
        "Temporary issue - will retry automatically"
    ),
    (
        r"(network|dns|socket|ssl|tls).*(error|fail)",
        ErrorCategory.TRANSIENT,
        RecoveryStrategy.RETRY,
        True,
        "Network error - will retry"
    ),

    # ==========================================================================
    # Authentication Errors (pause + alert)
    # ==========================================================================
    (
        r"(401|403|unauthorized|forbidden|access denied)",
        ErrorCategory.AUTH,
        RecoveryStrategy.PAUSE_AND_ALERT,
        False,
        "Authentication failed - check credentials"
    ),
    (
        r"(token|oauth).*(expired|invalid|revoked)",
        ErrorCategory.AUTH,
        RecoveryStrategy.PAUSE_AND_ALERT,
        False,
        "Token expired - refresh required"
    ),
    (
        r"(api.?key|credential|password|secret).*(invalid|incorrect|wrong)",
        ErrorCategory.AUTH,
        RecoveryStrategy.PAUSE_AND_ALERT,
        False,
        "Invalid credentials - update in settings"
    ),
    (
        r"(permission|scope|grant).*denied",
        ErrorCategory.AUTH,
        RecoveryStrategy.PAUSE_AND_ALERT,
        False,
        "Missing permissions - reauthorize the app"
    ),

    # ==========================================================================
    # Logic Errors (human review)
    # ==========================================================================
    (
        r"(validation|constraint|integrity).*(error|fail|violation)",
        ErrorCategory.LOGIC,
        RecoveryStrategy.HUMAN_REVIEW,
        False,
        "Business rule violation - needs review"
    ),
    (
        r"(duplicate|already exists|conflict)",
        ErrorCategory.LOGIC,
        RecoveryStrategy.HUMAN_REVIEW,
        False,
        "Duplicate detected - review and resolve"
    ),
    (
        r"(not found|does not exist|404|missing)",
        ErrorCategory.LOGIC,
        RecoveryStrategy.HUMAN_REVIEW,
        False,
        "Resource not found - verify target exists"
    ),
    (
        r"(invalid|illegal|unexpected).*(value|parameter|argument|input)",
        ErrorCategory.LOGIC,
        RecoveryStrategy.HUMAN_REVIEW,
        False,
        "Invalid input - correct and retry"
    ),

    # ==========================================================================
    # Data Errors (quarantine)
    # ==========================================================================
    (
        r"(json|yaml|xml|csv).*(parse|decode|syntax|format).*(error|fail)",
        ErrorCategory.DATA,
        RecoveryStrategy.QUARANTINE,
        False,
        "File format error - moved to quarantine"
    ),
    (
        r"(corrupt|malformed|truncated|incomplete)",
        ErrorCategory.DATA,
        RecoveryStrategy.QUARANTINE,
        False,
        "Corrupted data - moved to quarantine"
    ),
    (
        r"(encoding|decode|utf|unicode|character).*(error|fail)",
        ErrorCategory.DATA,
        RecoveryStrategy.QUARANTINE,
        False,
        "Encoding error - check file encoding"
    ),
    (
        r"(schema|type).*(mismatch|violation|invalid)",
        ErrorCategory.DATA,
        RecoveryStrategy.QUARANTINE,
        False,
        "Schema validation failed - check data format"
    ),

    # ==========================================================================
    # System Errors (auto-restart)
    # ==========================================================================
    (
        r"(out of memory|oom|memory.*(error|exhaust))",
        ErrorCategory.SYSTEM,
        RecoveryStrategy.AUTO_RESTART,
        False,
        "Memory exhausted - restarting process"
    ),
    (
        r"(segfault|segmentation fault|signal \d+)",
        ErrorCategory.SYSTEM,
        RecoveryStrategy.AUTO_RESTART,
        False,
        "Process crashed - restarting"
    ),
    (
        r"(disk|storage).*(full|space|quota)",
        ErrorCategory.SYSTEM,
        RecoveryStrategy.PAUSE_AND_ALERT,
        False,
        "Disk space issue - free up space"
    ),
    (
        r"(process|pid|fork|exec).*(fail|error|die)",
        ErrorCategory.SYSTEM,
        RecoveryStrategy.AUTO_RESTART,
        False,
        "Process error - restarting"
    ),
]


# Service-specific error patterns
SERVICE_PATTERNS: dict[str, list[tuple]] = {
    "odoo": [
        (r"-32097", ErrorCategory.AUTH, RecoveryStrategy.PAUSE_AND_ALERT, False, "Odoo access denied"),
        (r"-32098", ErrorCategory.LOGIC, RecoveryStrategy.HUMAN_REVIEW, False, "Odoo validation error"),
        (r"-32500", ErrorCategory.TRANSIENT, RecoveryStrategy.RETRY, True, "Odoo server error"),
    ],
    "facebook": [
        (r"OAuthException", ErrorCategory.AUTH, RecoveryStrategy.PAUSE_AND_ALERT, False, "Facebook OAuth error"),
        (r"#200", ErrorCategory.AUTH, RecoveryStrategy.PAUSE_AND_ALERT, False, "Facebook permission error"),
        (r"#32", ErrorCategory.TRANSIENT, RecoveryStrategy.RETRY, True, "Facebook rate limit"),
    ],
    "instagram": [
        (r"OAuthException", ErrorCategory.AUTH, RecoveryStrategy.PAUSE_AND_ALERT, False, "Instagram OAuth error"),
        (r"INVALID_ASPEC_RATIO|36003", ErrorCategory.DATA, RecoveryStrategy.HUMAN_REVIEW, False, "Instagram media format error"),
        (r"2207051", ErrorCategory.TRANSIENT, RecoveryStrategy.RETRY, True, "Instagram rate limit"),
    ],
    "twitter": [
        (r"code.*89|invalid.*token", ErrorCategory.AUTH, RecoveryStrategy.PAUSE_AND_ALERT, False, "Twitter auth error"),
        (r"code.*88|rate.?limit", ErrorCategory.TRANSIENT, RecoveryStrategy.RETRY, True, "Twitter rate limit"),
        (r"code.*187|duplicate", ErrorCategory.LOGIC, RecoveryStrategy.SKIP, False, "Twitter duplicate tweet"),
        (r"code.*186|character", ErrorCategory.LOGIC, RecoveryStrategy.HUMAN_REVIEW, False, "Twitter character limit exceeded"),
    ],
    "gmail": [
        (r"invalid_grant|token.*revoked", ErrorCategory.AUTH, RecoveryStrategy.PAUSE_AND_ALERT, False, "Gmail auth error"),
        (r"quotaExceeded|userRateLimitExceeded", ErrorCategory.TRANSIENT, RecoveryStrategy.RETRY, True, "Gmail quota exceeded"),
    ],
}


def categorize_error(
    error: str | Exception,
    service: str | None = None,
    context: dict[str, Any] | None = None
) -> CategorizedError:
    """Categorize an error and determine recovery strategy.

    Args:
        error: Error message or exception
        service: Service name (odoo, facebook, instagram, twitter, gmail)
        context: Additional context information

    Returns:
        CategorizedError with category, strategy, and suggestions
    """
    error_str = str(error).lower()

    # Extract error code if present
    error_code = None
    code_match = re.search(r"(code|error)[:\s]*['\"]?(\d+|[A-Z_]+)['\"]?", error_str, re.IGNORECASE)
    if code_match:
        error_code = code_match.group(2)

    # First check service-specific patterns
    if service and service.lower() in SERVICE_PATTERNS:
        for pattern, category, strategy, retryable, suggestion in SERVICE_PATTERNS[service.lower()]:
            if re.search(pattern, error_str, re.IGNORECASE):
                return CategorizedError(
                    category=category,
                    strategy=strategy,
                    retryable=retryable,
                    original_error=str(error),
                    error_code=error_code,
                    service=service,
                    context=context,
                    suggested_action=suggestion
                )

    # Check general patterns
    for pattern, category, strategy, retryable, suggestion in ERROR_PATTERNS:
        if re.search(pattern, error_str, re.IGNORECASE):
            return CategorizedError(
                category=category,
                strategy=strategy,
                retryable=retryable,
                original_error=str(error),
                error_code=error_code,
                service=service,
                context=context,
                suggested_action=suggestion
            )

    # Default to unknown/transient (safest default is to retry)
    return CategorizedError(
        category=ErrorCategory.UNKNOWN,
        strategy=RecoveryStrategy.RETRY,
        retryable=True,
        original_error=str(error),
        error_code=error_code,
        service=service,
        context=context,
        suggested_action="Unknown error - will attempt retry"
    )


def is_retryable(error: str | Exception, service: str | None = None) -> bool:
    """Quick check if an error is retryable.

    Args:
        error: Error message or exception
        service: Service name

    Returns:
        True if error should be retried
    """
    return categorize_error(error, service).retryable


def get_recovery_strategy(error: str | Exception, service: str | None = None) -> RecoveryStrategy:
    """Get the recommended recovery strategy for an error.

    Args:
        error: Error message or exception
        service: Service name

    Returns:
        RecoveryStrategy enum value
    """
    return categorize_error(error, service).strategy


class ErrorCategorizer:
    """Stateful error categorizer with history tracking.

    Useful for detecting patterns like repeated auth failures
    that might indicate a deeper issue.
    """

    def __init__(self, max_history: int = 100):
        """Initialize categorizer.

        Args:
            max_history: Maximum errors to keep in history
        """
        self.max_history = max_history
        self._history: list[CategorizedError] = []

    def categorize(
        self,
        error: str | Exception,
        service: str | None = None,
        context: dict[str, Any] | None = None
    ) -> CategorizedError:
        """Categorize an error and add to history."""
        result = categorize_error(error, service, context)
        self._history.append(result)

        # Trim history
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        return result

    def get_recent_by_category(self, category: ErrorCategory, limit: int = 10) -> list[CategorizedError]:
        """Get recent errors of a specific category."""
        return [e for e in reversed(self._history) if e.category == category][:limit]

    def get_error_rate(self, service: str | None = None, window: int = 10) -> float:
        """Get error rate in recent history.

        Args:
            service: Filter by service (None = all)
            window: Number of recent items to consider

        Returns:
            Error rate as decimal (0.0 to 1.0)
        """
        recent = self._history[-window:]
        if service:
            recent = [e for e in recent if e.service == service]

        if not recent:
            return 0.0

        non_retryable = sum(1 for e in recent if not e.retryable)
        return non_retryable / len(recent)

    def should_circuit_break(
        self,
        service: str,
        error_threshold: float = 0.5,
        window: int = 10
    ) -> bool:
        """Check if service should be circuit-broken.

        Args:
            service: Service name
            error_threshold: Error rate threshold (0.0 to 1.0)
            window: Window size for error rate calculation

        Returns:
            True if service should be temporarily disabled
        """
        return self.get_error_rate(service, window) >= error_threshold

    def clear_history(self) -> None:
        """Clear error history."""
        self._history = []
