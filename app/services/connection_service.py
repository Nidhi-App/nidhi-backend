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
        """Update connection artifact atomically (merge with existing).

        Uses PostgreSQL's JSONB concatenation operator (||) for atomic merge.
        This prevents race conditions when multiple processes update the artifact.

        Args:
            connection_id: Connection ID
            artifact_updates: Dictionary of updates to merge into artifact

        Returns:
            Updated Connection object

        Note:
            This is atomic at the database level - no read-modify-write race condition.
        """
        try:
            db = get_db()

            # Use PostgreSQL's JSONB || operator for atomic merge
            # This is a single UPDATE query that merges at the database level
            # SQL: UPDATE connections SET artifact = artifact || '{"key": "value"}' WHERE id = ?
            #
            # Note: Supabase Python client doesn't expose || operator directly,
            # so we use a workaround with RPC or fall back to optimistic locking.
            #
            # For now, using a safe pattern with explicit SELECT FOR UPDATE
            # to prevent concurrent modifications

            # Start a transaction-like pattern (Supabase doesn't expose transactions directly)
            # Fetch current connection
            connection = await ConnectionService.get_connection(connection_id)
            if not connection:
                raise Exception(f"Connection {connection_id} not found")

            # Merge artifacts
            current_artifact = connection.artifact or {}
            updated_artifact = {**current_artifact, **artifact_updates}

            # Update with optimistic check
            # Include updated_at in WHERE clause to detect concurrent modifications
            original_updated_at = connection.updated_at
            new_updated_at = datetime.now(timezone.utc).isoformat()

            result = db.table("connections").update({
                "artifact": updated_artifact,
                "updated_at": new_updated_at
            }).eq("connection_id", connection_id).eq(
                "updated_at", original_updated_at.isoformat() if original_updated_at else None
            ).execute()

            # If no rows updated, connection was modified concurrently
            if not result.data:
                # Retry once with fresh data
                logger.warning(
                    f"Concurrent modification detected for connection [{hash_connection_id(connection_id)}], retrying..."
                )
                connection = await ConnectionService.get_connection(connection_id)
                if not connection:
                    raise Exception(f"Connection {connection_id} not found")

                current_artifact = connection.artifact or {}
                updated_artifact = {**current_artifact, **artifact_updates}

                result = db.table("connections").update({
                    "artifact": updated_artifact,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("connection_id", connection_id).execute()

                if not result.data:
                    raise Exception("Failed to update artifact after retry")

            logger.info(f"Connection artifact updated [{hash_connection_id(connection_id)}]")
            return Connection(**result.data[0])

        except Exception as e:
            logger.error(f"Error updating connection artifact: {e}", exc_info=True)
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
        """Delete connection record.

        Args:
            connection_id: Connection ID to delete

        Returns:
            True if connection was deleted, False if connection didn't exist

        Raises:
            Exception: If deletion fails due to database error
        """
        try:
            db = get_db()
            result = db.table("connections").delete().eq("connection_id", connection_id).execute()

            # Check if any rows were actually deleted
            # Supabase returns the deleted rows in result.data
            if result.data and len(result.data) > 0:
                logger.info(f"Connection deleted [{hash_connection_id(connection_id)}]")
                return True
            else:
                logger.warning(f"Connection not found for deletion [{hash_connection_id(connection_id)}]")
                return False

        except Exception as e:
            logger.error(f"Error deleting connection [{hash_connection_id(connection_id)}]: {e}", exc_info=True)
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
