"""Common utilities shared across watchers and MCP servers.

This package provides:
- Credential management (OS keychain integration)
- Idempotency database (SQLite)
- Integrity hashing (SHA-256)
- Audit logging (JSON-lines)
- Retry logic (exponential backoff)

Gold Tier additions:
- Error categorization (classify errors for recovery strategies)
- Retry handler (exponential backoff with error-aware retries)
"""

__version__ = "0.1.0"

# Gold Tier exports
from .error_categorizer import (
    ErrorCategory,
    RecoveryStrategy,
    CategorizedError,
    categorize_error,
    is_retryable,
    get_recovery_strategy,
    ErrorCategorizer,
)

from .retry_handler import (
    RetryConfig,
    RetryResult,
    retry_sync,
    retry_async,
    with_retry,
    RetryHandler,
    DEFAULT_CONFIG,
)

__all__ = [
    # Error categorization
    "ErrorCategory",
    "RecoveryStrategy",
    "CategorizedError",
    "categorize_error",
    "is_retryable",
    "get_recovery_strategy",
    "ErrorCategorizer",
    # Retry handling
    "RetryConfig",
    "RetryResult",
    "retry_sync",
    "retry_async",
    "with_retry",
    "RetryHandler",
    "DEFAULT_CONFIG",
]
