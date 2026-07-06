"""
Wait / retry utilities for element operations.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, Type, Tuple

from autofw.core.constants import DEFAULT_POLL_INTERVAL_MS, DEFAULT_TIMEOUT_MS
from autofw.core.exceptions import TimeoutException

logger = logging.getLogger(__name__)


def wait_until(
    condition: Callable[[], Any],
    timeout: int = DEFAULT_TIMEOUT_MS,
    poll_interval: int = DEFAULT_POLL_INTERVAL_MS,
    description: str = "condition",
    raise_on_timeout: bool = True,
) -> Any:
    """
    Poll a condition function until it returns a truthy value or timeout.

    Args:
        condition: A callable that returns a truthy value on success
        timeout: Max time to wait in milliseconds
        poll_interval: Time between attempts in milliseconds
        description: Human-readable description for error messages
        raise_on_timeout: If True, raises TimeoutException; otherwise returns None

    Returns:
        The condition's return value if truthy, or None on timeout

    Raises:
        TimeoutException: If condition never becomes truthy and raise_on_timeout=True
    """
    deadline = time.monotonic() + (timeout / 1000)
    interval = poll_interval / 1000

    last_value = None
    while time.monotonic() < deadline:
        try:
            last_value = condition()
            if last_value:
                return last_value
        except Exception as e:
            logger.debug("wait_until(%s) failed: %s", description, e)
        time.sleep(interval)

    if raise_on_timeout:
        raise TimeoutException(
            f"Timed out after {timeout}ms waiting for: {description}"
        )
    return last_value


def retry_on_exception(
    fn: Callable[[], Any],
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    delay_ms: int = 1000,
    backoff: float = 2.0,
) -> Any:
    """
    Retry a function on specified exceptions with exponential backoff.

    Args:
        fn: Function to retry
        exceptions: Tuple of exception types to catch
        max_attempts: Maximum number of attempts
        delay_ms: Initial delay between retries in milliseconds
        backoff: Multiplier for delay after each attempt

    Returns:
        The function's return value on success

    Raises:
        The last exception caught if all attempts fail
    """
    delay = delay_ms / 1000
    last_exc = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except exceptions as e:
            last_exc = e
            if attempt < max_attempts:
                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                    attempt, max_attempts, e, delay,
                )
                time.sleep(delay)
                delay *= backoff

    raise last_exc  # type: ignore[misc]
