"""Unit tests for Connection model security features."""
import pytest
from uuid import UUID
from pydantic import SecretStr

from app.models.connection import Connection
from app.models.enums import ConnectionStatus


class TestConnectionModelSecurity:
    """Test cases for Connection model sensitive data protection."""

    def test_access_token_excluded_from_serialization(self):
        """Test that access_token is excluded from model serialization."""
        # Arrange
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            access_token=SecretStr("access-sandbox-123abc"),
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        serialized = connection.model_dump()

        # Assert
        assert "access_token" not in serialized
        assert connection.access_token is not None

    def test_link_token_excluded_from_serialization(self):
        """Test that link_token is excluded from model serialization."""
        # Arrange
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            link_token=SecretStr("link-sandbox-abc123"),
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        serialized = connection.model_dump()

        # Assert
        assert "link_token" not in serialized
        assert connection.link_token is not None

    def test_access_token_not_in_string_representation(self):
        """Test that access_token value doesn't appear in string representation."""
        # Arrange
        sensitive_value = "access-sandbox-123abc"
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            access_token=SecretStr(sensitive_value),
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        string_repr = str(connection)
        json_repr = connection.model_dump_json()

        # Assert
        assert sensitive_value not in string_repr
        assert sensitive_value not in json_repr
        assert "**********" in string_repr or "SecretStr" in string_repr

    def test_link_token_not_in_string_representation(self):
        """Test that link_token value doesn't appear in string representation."""
        # Arrange
        sensitive_value = "link-sandbox-abc123"
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            link_token=SecretStr(sensitive_value),
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        string_repr = str(connection)
        json_repr = connection.model_dump_json()

        # Assert
        assert sensitive_value not in string_repr
        assert sensitive_value not in json_repr

    def test_get_access_token_returns_raw_value(self):
        """Test that get_access_token() returns the raw token value."""
        # Arrange
        expected_token = "access-sandbox-123abc"
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            access_token=SecretStr(expected_token),
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        raw_token = connection.get_access_token()

        # Assert
        assert raw_token == expected_token
        assert isinstance(raw_token, str)

    def test_get_link_token_returns_raw_value(self):
        """Test that get_link_token() returns the raw token value."""
        # Arrange
        expected_token = "link-sandbox-abc123"
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            link_token=SecretStr(expected_token),
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        raw_token = connection.get_link_token()

        # Assert
        assert raw_token == expected_token
        assert isinstance(raw_token, str)

    def test_get_access_token_returns_none_when_not_set(self):
        """Test that get_access_token() returns None when token is not set."""
        # Arrange
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        raw_token = connection.get_access_token()

        # Assert
        assert raw_token is None

    def test_get_link_token_returns_none_when_not_set(self):
        """Test that get_link_token() returns None when token is not set."""
        # Arrange
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        raw_token = connection.get_link_token()

        # Assert
        assert raw_token is None

    def test_artifact_accepts_non_sensitive_data(self):
        """Test that artifact field accepts non-sensitive metadata."""
        # Arrange
        artifact_data = {
            "transactions_cursor": "cursor_abc123",
            "last_sync_status": "success",
            "items_synced": 150,
            "sync_metadata": {
                "duration_ms": 1234,
                "errors": []
            }
        }

        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            artifact=artifact_data,
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        serialized = connection.model_dump()

        # Assert
        assert "artifact" in serialized
        assert serialized["artifact"] == artifact_data
        assert serialized["artifact"]["transactions_cursor"] == "cursor_abc123"

    def test_both_tokens_excluded_together(self):
        """Test that both access_token and link_token are excluded when both are set."""
        # Arrange
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            access_token=SecretStr("access-sandbox-123abc"),
            link_token=SecretStr("link-sandbox-abc123"),
            connection_status=ConnectionStatus.ACTIVE
        )

        # Act
        serialized = connection.model_dump()
        json_output = connection.model_dump_json()

        # Assert
        assert "access_token" not in serialized
        assert "link_token" not in serialized
        assert "access-sandbox-123abc" not in json_output
        assert "link-sandbox-abc123" not in json_output

    def test_model_example_excludes_sensitive_fields(self):
        """Test that the model's example schema doesn't include sensitive fields."""
        # Act
        example = Connection.Config.json_schema_extra["example"]

        # Assert
        assert "access_token" not in example
        assert "link_token" not in example
        assert "artifact" in example
        # Ensure artifact example doesn't contain sensitive data
        assert "access_token" not in str(example["artifact"])
        assert "link_token" not in str(example["artifact"])

    def test_artifact_field_description_warns_against_sensitive_data(self):
        """Test that artifact field has proper security warnings in description."""
        # Act
        artifact_field = Connection.model_fields["artifact"]

        # Assert
        description = artifact_field.description
        assert "Non-sensitive" in description or "non-sensitive" in description.lower()
        assert "Do NOT store" in description or "do not store" in description.lower()
        assert "sensitive" in description.lower()
        assert "token" in description.lower()
