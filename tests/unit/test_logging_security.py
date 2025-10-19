"""Unit tests for logging security utilities."""
import pytest
from unittest.mock import patch
from uuid import UUID

from app.utils.logging_security import (
    hash_identifier,
    hash_user_id,
    hash_account_id,
    hash_connection_id,
    hash_transaction_id
)


class TestLoggingSecurity:
    """Test cases for secure identifier hashing."""

    def test_hash_identifier_with_string(self):
        """Test hashing a string identifier."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        identifier = "acc_123abc"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result = hash_identifier(identifier, "acct")

        # Assert
        assert result.startswith("acct:hash_")
        assert len(result.split("hash_")[1]) == 8  # 8 hex characters

    def test_hash_identifier_with_int(self):
        """Test hashing an integer identifier."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        identifier = 12345

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result = hash_identifier(identifier, "id")

        # Assert
        assert result.startswith("id:hash_")
        assert len(result.split("hash_")[1]) == 8

    def test_hash_identifier_with_uuid(self):
        """Test hashing a UUID identifier."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        identifier = UUID("123e4567-e89b-12d3-a456-426614174000")

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result = hash_identifier(identifier, "user")

        # Assert
        assert result.startswith("user:hash_")
        assert len(result.split("hash_")[1]) == 8

    def test_hash_identifier_deterministic(self):
        """Test that same identifier always produces same hash."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        identifier = "acc_123abc"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result1 = hash_identifier(identifier, "acct")
            result2 = hash_identifier(identifier, "acct")

        # Assert
        assert result1 == result2

    def test_hash_identifier_different_secrets_different_hashes(self):
        """Test that different secrets produce different hashes."""
        # Arrange
        identifier = "acc_123abc"
        secret1 = "test-secret-key-1-min-32-characters"
        secret2 = "test-secret-key-2-min-32-characters"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', secret1):
            result1 = hash_identifier(identifier, "acct")
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', secret2):
            result2 = hash_identifier(identifier, "acct")

        # Assert
        assert result1 != result2
        assert result1.startswith("acct:hash_")
        assert result2.startswith("acct:hash_")

    def test_hash_identifier_different_identifiers_different_hashes(self):
        """Test that different identifiers produce different hashes."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        identifier1 = "acc_123abc"
        identifier2 = "acc_456def"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result1 = hash_identifier(identifier1, "acct")
            result2 = hash_identifier(identifier2, "acct")

        # Assert
        assert result1 != result2

    def test_hash_identifier_none_returns_none_suffix(self):
        """Test that None identifier returns safe placeholder."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result = hash_identifier(None, "acct")

        # Assert
        assert result == "acct:none"

    def test_hash_identifier_no_secret_configured(self):
        """Test fallback behavior when LOGGING_SECRET is not configured."""
        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', None):
            result = hash_identifier("acc_123", "acct")

        # Assert
        assert result == "acct:unconfigured"

    def test_hash_identifier_empty_secret(self):
        """Test fallback behavior when LOGGING_SECRET is empty string."""
        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', ""):
            result = hash_identifier("acc_123", "acct")

        # Assert
        assert result == "acct:unconfigured"

    def test_hash_user_id(self):
        """Test hash_user_id convenience function."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result = hash_user_id(user_id)

        # Assert
        assert result.startswith("user:hash_")

    def test_hash_account_id(self):
        """Test hash_account_id convenience function."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        account_id = "acc_123abc"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result = hash_account_id(account_id)

        # Assert
        assert result.startswith("acct:hash_")

    def test_hash_connection_id(self):
        """Test hash_connection_id convenience function."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        connection_id = "item_123abc"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result = hash_connection_id(connection_id)

        # Assert
        assert result.startswith("conn:hash_")

    def test_hash_transaction_id(self):
        """Test hash_transaction_id convenience function."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        transaction_id = "txn_abc123"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            result = hash_transaction_id(transaction_id)

        # Assert
        assert result.startswith("txn:hash_")

    def test_hash_cannot_be_reversed(self):
        """Test that the hash cannot be easily reversed to get original identifier."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        identifier = "acc_sensitive_123abc"

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            hashed = hash_identifier(identifier, "acct")

        # Assert
        # The hash should not contain the original identifier
        assert identifier not in hashed
        assert "sensitive" not in hashed
        assert "123abc" not in hashed

    def test_hash_provides_sufficient_uniqueness(self):
        """Test that 8 hex characters provide sufficient uniqueness for correlation."""
        # Arrange
        test_secret = "test-secret-key-min-32-characters-long"
        # Generate multiple different identifiers
        identifiers = [f"acc_{i}" for i in range(100)]

        # Act
        with patch('app.utils.logging_security.settings.LOGGING_SECRET', test_secret):
            hashes = [hash_identifier(id, "acct") for id in identifiers]

        # Assert
        # All hashes should be unique (collision probability is negligible with 8 hex chars)
        assert len(set(hashes)) == len(hashes)
