"""Retry Logic Module for Silver Tier.

Provides exponential backoff retry decorator and utilities for
handling transient API failures.

Implements FR-013 from spec.
"""

import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, Type, TypeVar

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar("T")

# Default retry configuration
DEFAULT_INITIAL_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 60.0  # seconds
DEFAULT_MAX_RETRIES = 5
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_JITTER = 0.1  # 10% jitter


class RetryError(Exception):
    """All retry attempts failed."""

    def __init__(self, message: str, last_exception: Exception | None = None, attempts: int = 0):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
        jitter: float = DEFAULT_JITTER,
        retryable_exceptions: tuple[Type[Exception], ...] | None = None,
        on_retry: Callable[[Exception, int], None] | None = None
    ):
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay before first retry (seconds)
            max_delay: Maximum delay between retries (seconds)
            backoff_multiplier: Multiplier for exponential backoff
            jitter: Random jitter factor (0.0 to 1.0) to prevent thundering herd
            retryable_exceptions: Tuple of exception types to retry on (default: all)
            on_retry: Optional callback called before each retry with (exception, attempt)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (Exception,)
        self.on_retry = on_retry

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.initial_delay * (self.backoff_multiplier ** attempt)

        # Cap at max delay
        delay = min(delay, self.max_delay)

        # Add jitter
        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay = delay + random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if we should retry after this exception.

        Args:
            exception: The exception that was raised
            attempt: Current attempt number (0-based)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False

        return isinstance(exception, self.retryable_exceptions)


# Default configuration instance
default_config = RetryConfig()


def exponential_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    jitter: float = DEFAULT_JITTER,
    retryable_exceptions: tuple[Type[Exception], ...] | None = None,
    on_retry: Callable[[Exception, int], None] | None = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for adding exponential backoff retry logic to a function.

    Usage:
        @exponential_backoff(max_retries=3)
        def call_api():
            return requests.get("https://api.example.com")

        # With specific exceptions
        @exponential_backoff(
            max_retries=5,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )
        def fetch_data():
            ...

    Args:
        max_retries: Maximum retry attempts (default: 5)
        initial_delay: Initial delay in seconds (default: 1)
        max_delay: Maximum delay in seconds (default: 60)
        backoff_multiplier: Delay multiplier (default: 2)
        jitter: Random jitter factor (default: 0.1)
        retryable_exceptions: Exceptions to retry on (default: all)
        on_retry: Callback before each retry

    Returns:
        Decorated function with retry logic
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        on_retry=on_retry
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not config.should_retry(e, attempt):
                        raise

                    delay = config.calculate_delay(attempt)

                    logger.warning(
                        f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                        f"after {delay:.2f}s due to: {e}"
                    )

                    if config.on_retry:
                        config.on_retry(e, attempt)

                    time.sleep(delay)

            # Should not reach here, but just in case
            raise RetryError(
                f"All {config.max_retries} retry attempts failed for {func.__name__}",
                last_exception=last_exception,
                attempts=config.max_retries
            )

        return wrapper

    return decorator


def async_exponential_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    jitter: float = DEFAULT_JITTER,
    retryable_exceptions: tuple[Type[Exception], ...] | None = None,
    on_retry: Callable[[Exception, int], None] | None = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Async version of exponential_backoff decorator.

    Usage:
        @async_exponential_backoff(max_retries=3)
        async def call_api():
            async with aiohttp.ClientSession() as session:
                return await session.get("https://api.example.com")
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        on_retry=on_retry
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not config.should_retry(e, attempt):
                        raise

                    delay = config.calculate_delay(attempt)

                    logger.warning(
                        f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                        f"after {delay:.2f}s due to: {e}"
                    )

                    if config.on_retry:
                        config.on_retry(e, attempt)

                    await asyncio.sleep(delay)

            raise RetryError(
                f"All {config.max_retries} retry attempts failed for {func.__name__}",
                last_exception=last_exception,
                attempts=config.max_retries
            )

        return wrapper

    return decorator


def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any
) -> T:
    """Execute a function with retry logic (non-decorator version).

    Usage:
        result = retry_with_backoff(
            requests.get,
            "https://api.example.com",
            config=RetryConfig(max_retries=3)
        )

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        config: Retry configuration (uses default if None)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function

    Raises:
        RetryError: If all retry attempts fail
    """
    config = config or default_config
    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            if not config.should_retry(e, attempt):
                raise

            delay = config.calculate_delay(attempt)

            logger.warning(
                f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                f"after {delay:.2f}s due to: {e}"
            )

            if config.on_retry:
                config.on_retry(e, attempt)

            time.sleep(delay)

    raise RetryError(
        f"All {config.max_retries} retry attempts failed for {func.__name__}",
        last_exception=last_exception,
        attempts=config.max_retries
    )


# Common retry configurations for different use cases
API_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    initial_delay=1.0,
    max_delay=60.0,
    retryable_exceptions=(ConnectionError, TimeoutError, OSError)
)

OAUTH_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=2.0,
    max_delay=30.0
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=0.5,
    max_delay=5.0
)
