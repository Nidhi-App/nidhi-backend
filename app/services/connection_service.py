"""Connection service - CRUD operations for connections."""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.connection import Connection
from app.models.enums import ConnectionStatus
from app.utils.logger import logger
from app.utils.logging_security import hash_connection_id, hash_user_id


class ConnectionService:
    """Service for managing provider connections."""

    @staticmethod
    async def create_connection(
        user_id: UUID,
        provider_id: int,
        status: ConnectionStatus = ConnectionStatus.INITIALIZING
    ) -> Connection:
        """Create a new connection record."""
        try:
            db = get_db()
            connection_data = {
                "user_id": str(user_id),
                "provider_id": provider_id,
                "connection_status": status.value,
                "artifact": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = db.table("connections").insert(connection_data).execute()

            if result.data:
                logger.info(f"Connection created [{hash_user_id(user_id)}]")
                return Connection(**result.data[0])
            raise Exception("Failed to create connection")

        except Exception as e:
            logger.error(f"Error creating connection: {e}")
            raise

    @staticmethod
    async def get_connection(connection_id: int) -> Optional[Connection]:
        """Get connection by ID."""
        try:
            db = get_db()
            result = db.table("connections").select("*").eq("connection_id", connection_id).execute()

            if result.data:
                return Connection(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error fetching connection: {e}")
            raise

    @staticmethod
    async def get_connection_by_item_id(external_item_id: str) -> Optional[Connection]:
        """Get connection by external item ID (e.g., Plaid item_id)."""
        try:
            db = get_db()
            result = db.table("connections").select("*").eq("external_item_id", external_item_id).execute()

            if result.data:
                return Connection(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error fetching connection by item ID: {e}")
            raise

    @staticmethod
    async def get_user_connections(user_id: UUID, provider_id: Optional[int] = None) -> List[Connection]:
        """Get all connections for a user."""
        try:
            db = get_db()
            query = db.table("connections").select("*").eq("user_id", str(user_id))

            if provider_id:
                query = query.eq("provider_id", provider_id)

            result = query.execute()
            return [Connection(**conn) for conn in result.data]

        except Exception as e:
            logger.error(f"Error fetching user connections: {e}")
            raise

    @staticmethod
    async def update_connection(connection_id: int, updates: dict) -> Connection:
        """Update connection record."""
        try:
            db = get_db()
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = db.table("connections").update(updates).eq("connection_id", connection_id).execute()

            if result.data:
                logger.info(f"Connection updated [{hash_connection_id(connection_id)}]")
                return Connection(**result.data[0])
            raise Exception("Connection not found")

        except Exception as e:
            logger.error(f"Error updating connection: {e}")
            raise

    @staticmethod
    async def update_connection_status(connection_id: int, status: ConnectionStatus) -> Connection:
        """Update connection status."""
        return await ConnectionService.update_connection(
            connection_id,
            {"connection_status": status.value}
        )

    @staticmethod
    async def update_artifact(connection_id: int, artifact_updates: dict) -> Connection:
        """Update connection artifact (merge with existing)."""
        try:
            connection = await ConnectionService.get_connection(connection_id)
            if not connection:
                raise Exception(f"Connection {connection_id} not found")

            current_artifact = connection.artifact or {}
            updated_artifact = {**current_artifact, **artifact_updates}

            return await ConnectionService.update_connection(
                connection_id,
                {"artifact": updated_artifact}
            )

        except Exception as e:
            logger.error(f"Error updating connection artifact: {e}")
            raise

    @staticmethod
    async def mark_needs_reauth(connection_id: int) -> Connection:
        """Mark connection as needing reauthorization."""
        return await ConnectionService.update_connection(
            connection_id,
            {"connection_status": ConnectionStatus.NEEDS_REAUTH.value}
        )

    @staticmethod
    async def update_last_synced(connection_id: int) -> Connection:
        """Update last_synced_at timestamp."""
        return await ConnectionService.update_connection(
            connection_id,
            {"last_synced_at": datetime.now(timezone.utc).isoformat()}
        )

    @staticmethod
    async def delete_connection(connection_id: int) -> bool:
        """Delete connection record."""
        try:
            db = get_db()
            db.table("connections").delete().eq("connection_id", connection_id).execute()
            logger.info(f"Connection deleted [{hash_connection_id(connection_id)}]")
            return True

        except Exception as e:
            logger.error(f"Error deleting connection: {e}")
            raise

    @staticmethod
    async def get_active_connections(provider_id: Optional[int] = None) -> List[Connection]:
        """Get all active connections, optionally filtered by provider."""
        try:
            db = get_db()
            query = db.table("connections").select("*").eq("connection_status", ConnectionStatus.ACTIVE.value)

            if provider_id:
                query = query.eq("provider_id", provider_id)

            result = query.execute()
            return [Connection(**conn) for conn in result.data]

        except Exception as e:
            logger.error(f"Error fetching active connections: {e}")
            raise


# Singleton instance
connection_service = ConnectionService()
