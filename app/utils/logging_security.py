"""Secure logging utilities for anonymizing sensitive identifiers in logs.

This module provides utilities to safely log sensitive identifiers (like user IDs,
external account IDs, etc.) by hashing them with HMAC-SHA256. This allows correlation
in logs while preventing exposure of actual PII.

Security Notes:
    - Uses HMAC-SHA256 for deterministic, secure hashing
    - Secret key must be configured via LOGGING_SECRET environment variable
    - Hashes are truncated to 8 characters for readability
    - Same identifier always produces same hash (for log correlation)
    - Hash cannot be reversed to obtain original identifier
"""
import hashlib
import hmac
from typing import Optional, Union
from uuid import UUID

from app.config import settings
from app.utils.logger import logger


def hash_identifier(identifier: Union[str, int, UUID, None], prefix: str = "id") -> str:
    """Hash a sensitive identifier for safe logging.

    Creates a deterministic HMAC-SHA256 hash of the identifier using a secret key
    from configuration. The hash is truncated to 8 characters for log readability
    while maintaining sufficient uniqueness for correlation.

    Args:
        identifier: The sensitive identifier to hash (user_id, account_id, etc.)
        prefix: A prefix to add to the hash for context (e.g., "user", "acct", "txn")

    Returns:
        A safe log string in format: "{prefix}:hash_XXXXXXXX"
        Returns "{prefix}:none" if identifier is None
        Returns "{prefix}:error" if hashing fails

    Examples:
        >>> hash_identifier("acc_123abc", "acct")
        "acct:hash_a1b2c3d4"

        >>> hash_identifier(UUID("123e4567-e89b-12d3-a456-426614174000"), "user")
        "user:hash_f9e8d7c6"

        >>> hash_identifier(12345, "id")
        "id:hash_b4c5d6e7"

    Security:
        - Uses HMAC-SHA256 with secret key from LOGGING_SECRET env var
        - Truncated to 8 hex characters (32 bits of entropy)
        - Sufficient for log correlation, prevents identifier exposure
        - Falls back to generic placeholder if secret is not configured
    """
    if identifier is None:
        return f"{prefix}:none"

    try:
        # Get the secret key from configuration
        secret = settings.LOGGING_SECRET
        if not secret:
            logger.warning(
                "LOGGING_SECRET not configured. Using generic identifier in logs. "
                "Set LOGGING_SECRET environment variable for secure identifier hashing."
            )
            return f"{prefix}:unconfigured"

        # Convert identifier to string
        id_str = str(identifier)

        # Create HMAC-SHA256 hash
        hash_obj = hmac.new(
            secret.encode('utf-8'),
            id_str.encode('utf-8'),
            hashlib.sha256
        )

        # Get hex digest and truncate to 8 characters
        hash_digest = hash_obj.hexdigest()[:8]

        return f"{prefix}:hash_{hash_digest}"

    except Exception as e:
        logger.error(f"Error hashing identifier for logging: {e}")
        return f"{prefix}:error"


def hash_user_id(user_id: Union[str, UUID, None]) -> str:
    """Hash a user ID for safe logging.

    Args:
        user_id: The user ID to hash (UUID or string)

    Returns:
        Hashed identifier with "user" prefix

    Example:
        >>> hash_user_id(UUID("123e4567-e89b-12d3-a456-426614174000"))
        "user:hash_f9e8d7c6"
    """
    return hash_identifier(user_id, prefix="user")


def hash_account_id(account_id: Union[str, int, None]) -> str:
    """Hash an account ID for safe logging.

    Args:
        account_id: The account ID to hash (internal ID or external ID)

    Returns:
        Hashed identifier with "acct" prefix

    Example:
        >>> hash_account_id("acc_123abc")
        "acct:hash_a1b2c3d4"
    """
    return hash_identifier(account_id, prefix="acct")


def hash_connection_id(connection_id: Union[str, int, None]) -> str:
    """Hash a connection ID for safe logging.

    Args:
        connection_id: The connection ID to hash (internal ID or external item ID)

    Returns:
        Hashed identifier with "conn" prefix

    Example:
        >>> hash_connection_id("item_123abc")
        "conn:hash_b2c3d4e5"
    """
    return hash_identifier(connection_id, prefix="conn")


def hash_transaction_id(transaction_id: Union[str, int, None]) -> str:
    """Hash a transaction ID for safe logging.

    Args:
        transaction_id: The transaction ID to hash (internal ID or external ID)

    Returns:
        Hashed identifier with "txn" prefix

    Example:
        >>> hash_transaction_id("txn_abc123")
        "txn:hash_c3d4e5f6"
    """
    return hash_identifier(transaction_id, prefix="txn")
