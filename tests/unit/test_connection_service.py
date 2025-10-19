"""Unit tests for connection_service."""
import pytest
from unittest.mock import patch, MagicMock
from uuid import UUID

from app.services.connection_service import ConnectionService, connection_service
from app.models.connection import Connection
from app.models.enums import ConnectionStatus


@pytest.mark.asyncio
class TestConnectionService:
    """Test cases for ConnectionService."""

    async def test_create_connection(self, mock_supabase_client, sample_user_id, sample_connection_data):
        """Test creating a new connection."""
        # Arrange
        mock_supabase_client.table("connections").execute.return_value.data = [sample_connection_data]

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.create_connection(sample_user_id, 8)

        # Assert
        assert isinstance(result, Connection)
        assert result.user_id == sample_user_id
        assert result.provider_id == 8
        assert result.connection_status == ConnectionStatus.ACTIVE
        mock_supabase_client.table.assert_called_with("connections")

    async def test_get_connection(self, mock_supabase_client, sample_connection_data):
        """Test fetching a connection by ID."""
        # Arrange
        mock_supabase_client.table("connections").execute.return_value.data = [sample_connection_data]

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.get_connection(1)

        # Assert
        assert isinstance(result, Connection)
        assert result.connection_id == 1
        assert result.institution_name == "Chase"

    async def test_get_connection_not_found(self, mock_supabase_client):
        """Test fetching non-existent connection returns None."""
        # Arrange
        mock_supabase_client.table("connections").execute.return_value.data = []

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.get_connection(999)

        # Assert
        assert result is None

    async def test_get_user_connections(self, mock_supabase_client, sample_user_id, sample_connection_data):
        """Test fetching all connections for a user."""
        # Arrange
        mock_supabase_client.table("connections").execute.return_value.data = [
            sample_connection_data,
            {**sample_connection_data, "connection_id": 2}
        ]

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.get_user_connections(sample_user_id)

        # Assert
        assert len(result) == 2
        assert all(isinstance(conn, Connection) for conn in result)

    async def test_update_connection(self, mock_supabase_client, sample_connection_data):
        """Test updating a connection."""
        # Arrange
        updated_data = {**sample_connection_data, "institution_name": "Bank of America"}
        mock_supabase_client.table("connections").execute.return_value.data = [updated_data]

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.update_connection(
                1,
                {"institution_name": "Bank of America"}
            )

        # Assert
        assert result.institution_name == "Bank of America"

    async def test_update_connection_status(self, mock_supabase_client, sample_connection_data):
        """Test updating connection status."""
        # Arrange
        updated_data = {**sample_connection_data, "connection_status": "Needs_Reauth"}
        mock_supabase_client.table("connections").execute.return_value.data = [updated_data]

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.update_connection_status(
                1,
                ConnectionStatus.NEEDS_REAUTH
            )

        # Assert
        assert result.connection_status == ConnectionStatus.NEEDS_REAUTH

    async def test_update_artifact(self, mock_supabase_client, sample_connection_data):
        """Test updating connection artifact."""
        # Arrange
        connection_data = {**sample_connection_data}
        updated_artifact_data = {
            **connection_data,
            "artifact": {
                "transactions_cursor": "cursor_abc",
                "new_field": "new_value"
            }
        }

        # Mock get_connection and update_connection
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            with patch.object(
                ConnectionService,
                "get_connection",
                return_value=Connection(**connection_data)
            ):
                mock_supabase_client.table("connections").execute.return_value.data = [updated_artifact_data]

                # Act
                result = await ConnectionService.update_artifact(
                    1,
                    {"new_field": "new_value"}
                )

                # Assert
                assert result.artifact["new_field"] == "new_value"
                assert result.artifact["transactions_cursor"] == "cursor_abc"

    async def test_mark_needs_reauth(self, mock_supabase_client, sample_connection_data):
        """Test marking connection as needing reauth."""
        # Arrange
        updated_data = {**sample_connection_data, "connection_status": "Needs_Reauth"}
        mock_supabase_client.table("connections").execute.return_value.data = [updated_data]

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.mark_needs_reauth(1)

        # Assert
        assert result.connection_status == ConnectionStatus.NEEDS_REAUTH

    async def test_delete_connection(self, mock_supabase_client):
        """Test deleting a connection."""
        # Arrange
        mock_supabase_client.table("connections").execute.return_value = MagicMock()

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.delete_connection(1)

        # Assert
        assert result is True
        mock_supabase_client.table("connections").delete.assert_called_once()

    async def test_get_active_connections(self, mock_supabase_client, sample_connection_data):
        """Test fetching active connections."""
        # Arrange
        mock_supabase_client.table("connections").execute.return_value.data = [sample_connection_data]

        # Act
        with patch("app.services.connection_service.get_db", return_value=mock_supabase_client):
            result = await ConnectionService.get_active_connections()

        # Assert
        assert len(result) == 1
        assert result[0].connection_status == ConnectionStatus.ACTIVE
