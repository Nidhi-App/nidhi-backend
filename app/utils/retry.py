"""
Retry utilities for handling transient failures.

This module provides retry decorators and utilities for handling
temporary failures when calling external APIs like Plaid.
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from plaid.exceptions import ApiException
from app.utils.logger import logger
import logging


def is_retryable_plaid_error(exception: Exception) -> bool:
    """
    Determine if a Plaid API error is retryable.

    Args:
        exception: Exception to check

    Returns:
        True if the error should be retried, False otherwise
    """
    if not isinstance(exception, ApiException):
        return False

    # Get error code from Plaid exception
    error_code = getattr(exception, 'code', None)

    # List of retryable error codes
    retryable_codes = {
        "RATE_LIMIT_EXCEEDED",  # Rate limit - retry with backoff
        "INSTITUTION_NOT_RESPONDING",  # Temporary institution issue
        "INSTITUTION_DOWN",  # Institution temporarily down
        "PRODUCTS_NOT_READY",  # Data not ready yet
        "INTERNAL_SERVER_ERROR",  # Plaid internal error
    }

    return error_code in retryable_codes


# Retry decorator for Plaid API calls
retry_plaid_api = retry(
    retry=retry_if_exception_type(ApiException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 10,
    multiplier: int = 1
):
    """
    Create a custom retry decorator with specific parameters.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Multiplier for exponential backoff

    Returns:
        Retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
