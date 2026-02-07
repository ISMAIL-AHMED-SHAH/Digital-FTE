"""Retry Handler with Exponential Backoff (FR-026).

Provides configurable retry logic with exponential backoff for transient errors.

Configuration (per spec clarification):
- Initial delay: 1 second
- Max delay: 60 seconds
- Max attempts: 5
- Backoff multiplier: 2

Integrates with error_categorizer to only retry retryable errors.
"""

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar, ParamSpec

from .error_categorizer import categorize_error, is_retryable, ErrorCategory

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (including initial)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_multiplier: Multiplier for each subsequent delay
        jitter: Add random jitter to prevent thundering herd
        jitter_factor: Jitter range as fraction of delay (0.0 to 1.0)
        retry_on_categories: Error categories to retry (None = use is_retryable)
        service: Service name for error categorization
    """
    max_attempts: int = 5
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retry_on_categories: list[ErrorCategory] | None = None
    service: str | None = None


# Default config per spec clarification
DEFAULT_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=60.0,
    backoff_multiplier=2.0
)


@dataclass
class RetryResult:
    """Result of a retry operation.

    Attributes:
        success: Whether operation eventually succeeded
        result: Return value if successful
        attempts: Number of attempts made
        total_delay: Total time spent in delays
        final_error: Last error if failed
        errors: List of all errors encountered
    """
    success: bool
    result: Any = None
    attempts: int = 0
    total_delay: float = 0.0
    final_error: Exception | None = None
    errors: list[Exception] | None = None


def calculate_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """Calculate delay for a given attempt.

    Args:
        attempt: Attempt number (1-based)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Exponential backoff
    delay = config.initial_delay * (config.backoff_multiplier ** (attempt - 1))

    # Cap at max delay
    delay = min(delay, config.max_delay)

    # Add jitter
    if config.jitter:
        jitter_range = delay * config.jitter_factor
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def should_retry(
    error: Exception,
    config: RetryConfig
) -> bool:
    """Determine if an error should be retried.

    Args:
        error: The exception that occurred
        config: Retry configuration

    Returns:
        True if should retry
    """
    categorized = categorize_error(error, service=config.service)

    # Check custom categories if specified
    if config.retry_on_categories:
        return categorized.category in config.retry_on_categories

    # Default to categorizer's determination
    return categorized.retryable


def retry_sync(
    func: Callable[P, T],
    *args: P.args,
    config: RetryConfig | None = None,
    **kwargs: P.kwargs
) -> RetryResult:
    """Execute a function with retry logic (synchronous).

    Args:
        func: Function to execute
        *args: Positional arguments
        config: Retry configuration (uses DEFAULT_CONFIG if None)
        **kwargs: Keyword arguments

    Returns:
        RetryResult with success status and result/error
    """
    if config is None:
        config = DEFAULT_CONFIG

    errors: list[Exception] = []
    total_delay = 0.0

    for attempt in range(1, config.max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            return RetryResult(
                success=True,
                result=result,
                attempts=attempt,
                total_delay=total_delay,
                errors=errors if errors else None
            )
        except Exception as e:
            errors.append(e)
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed: {e}"
            )

            # Check if we should retry
            if attempt < config.max_attempts and should_retry(e, config):
                delay = calculate_delay(attempt, config)
                total_delay += delay
                logger.info(f"Retrying in {delay:.2f}s...")
                time.sleep(delay)
            else:
                # Max attempts reached or non-retryable error
                break

    return RetryResult(
        success=False,
        attempts=len(errors),
        total_delay=total_delay,
        final_error=errors[-1] if errors else None,
        errors=errors
    )


async def retry_async(
    func: Callable[P, T],
    *args: P.args,
    config: RetryConfig | None = None,
    **kwargs: P.kwargs
) -> RetryResult:
    """Execute an async function with retry logic.

    Args:
        func: Async function to execute
        *args: Positional arguments
        config: Retry configuration (uses DEFAULT_CONFIG if None)
        **kwargs: Keyword arguments

    Returns:
        RetryResult with success status and result/error
    """
    if config is None:
        config = DEFAULT_CONFIG

    errors: list[Exception] = []
    total_delay = 0.0

    for attempt in range(1, config.max_attempts + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            return RetryResult(
                success=True,
                result=result,
                attempts=attempt,
                total_delay=total_delay,
                errors=errors if errors else None
            )
        except Exception as e:
            errors.append(e)
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed: {e}"
            )

            # Check if we should retry
            if attempt < config.max_attempts and should_retry(e, config):
                delay = calculate_delay(attempt, config)
                total_delay += delay
                logger.info(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
            else:
                break

    return RetryResult(
        success=False,
        attempts=len(errors),
        total_delay=total_delay,
        final_error=errors[-1] if errors else None,
        errors=errors
    )


def with_retry(
    config: RetryConfig | None = None,
    service: str | None = None,
    max_attempts: int | None = None,
    initial_delay: float | None = None,
    max_delay: float | None = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to add retry logic to a function.

    Args:
        config: Full retry configuration
        service: Service name for error categorization
        max_attempts: Override max attempts
        initial_delay: Override initial delay
        max_delay: Override max delay

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(service="odoo", max_attempts=3)
        def call_odoo_api(data):
            return odoo_client.execute(data)
    """
    # Build config from params
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts or DEFAULT_CONFIG.max_attempts,
            initial_delay=initial_delay or DEFAULT_CONFIG.initial_delay,
            max_delay=max_delay or DEFAULT_CONFIG.max_delay,
            service=service
        )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = retry_sync(func, *args, config=config, **kwargs)
            if result.success:
                return result.result
            raise result.final_error

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = await retry_async(func, *args, config=config, **kwargs)
            if result.success:
                return result.result
            raise result.final_error

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class RetryHandler:
    """Stateful retry handler with metrics tracking.

    Useful for monitoring retry patterns across a service.
    """

    def __init__(self, config: RetryConfig | None = None):
        """Initialize handler.

        Args:
            config: Default retry configuration
        """
        self.config = config or DEFAULT_CONFIG
        self._total_attempts = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_delay = 0.0

    def execute(
        self,
        func: Callable[P, T],
        *args: P.args,
        config: RetryConfig | None = None,
        **kwargs: P.kwargs
    ) -> RetryResult:
        """Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            config: Override configuration
            **kwargs: Keyword arguments

        Returns:
            RetryResult
        """
        cfg = config or self.config
        result = retry_sync(func, *args, config=cfg, **kwargs)

        # Update metrics
        self._total_attempts += result.attempts
        self._total_delay += result.total_delay
        if result.success:
            self._total_successes += 1
        else:
            self._total_failures += 1

        return result

    async def execute_async(
        self,
        func: Callable[P, T],
        *args: P.args,
        config: RetryConfig | None = None,
        **kwargs: P.kwargs
    ) -> RetryResult:
        """Execute an async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            config: Override configuration
            **kwargs: Keyword arguments

        Returns:
            RetryResult
        """
        cfg = config or self.config
        result = await retry_async(func, *args, config=cfg, **kwargs)

        # Update metrics
        self._total_attempts += result.attempts
        self._total_delay += result.total_delay
        if result.success:
            self._total_successes += 1
        else:
            self._total_failures += 1

        return result

    def get_metrics(self) -> dict[str, Any]:
        """Get retry metrics.

        Returns:
            Dict with total attempts, successes, failures, delay
        """
        total = self._total_successes + self._total_failures
        return {
            "total_operations": total,
            "total_attempts": self._total_attempts,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "success_rate": self._total_successes / total if total > 0 else 0,
            "average_attempts": self._total_attempts / total if total > 0 else 0,
            "total_delay_seconds": self._total_delay,
            "average_delay_seconds": self._total_delay / total if total > 0 else 0
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._total_attempts = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_delay = 0.0

    async def execute_with_retry(
        self,
        func: Callable[P, T],
        *args: P.args,
        on_retry: Callable[[int, Exception, float], None] | None = None,
        error_context: dict | None = None,
        **kwargs: P.kwargs
    ) -> "RetryResult":
        """Execute an async function with retry logic (alternative interface).

        This method provides a more convenient interface that matches
        common retry patterns.

        Args:
            func: Async function to execute
            on_retry: Optional callback called on each retry
            error_context: Context for error categorization
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            RetryResult with success status and result/error
        """
        cfg = self.config
        errors: list[Exception] = []
        total_delay = 0.0

        for attempt in range(1, cfg.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Update metrics
                self._total_attempts += attempt
                self._total_successes += 1
                self._total_delay += total_delay

                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt,
                    total_delay=total_delay,
                    errors=errors if errors else None
                )
            except Exception as e:
                errors.append(e)
                logger.warning(
                    f"Attempt {attempt}/{cfg.max_attempts} failed: {e}"
                )

                # Check if we should retry
                ctx = error_context or {}
                if hasattr(e, 'status_code'):
                    ctx['status_code'] = e.status_code

                should_try_again = should_retry(e, cfg)

                # For auth errors (401), don't retry
                if ctx.get('status_code') == 401:
                    should_try_again = False

                if attempt < cfg.max_attempts and should_try_again:
                    delay = calculate_delay(attempt, cfg)
                    total_delay += delay

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e, delay)

                    logger.info(f"Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    break

        # Update metrics
        self._total_attempts += len(errors)
        self._total_failures += 1
        self._total_delay += total_delay

        return RetryResult(
            success=False,
            attempts=len(errors),
            total_delay=total_delay,
            final_error=errors[-1] if errors else None,
            errors=errors
        )


# Compatibility alias
RetryResult.value = property(lambda self: self.result)
RetryResult.error = property(lambda self: self.final_error)
