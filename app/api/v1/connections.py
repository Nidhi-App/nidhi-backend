"""
Plaid connections API endpoints.

This module handles Plaid Link flow:
1. Creating link tokens for frontend integration
2. Exchanging public tokens for access tokens
3. Managing connections (get, list, disconnect)
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from loguru import logger

from app.schemas.connection import (
    LinkTokenResponse,
    ExchangeTokenRequest,
    ConnectionResponse,
    ConnectionListResponse
)
from app.services.connection_service import connection_service
from app.services.sync_service import sync_service
from app.providers.plaid.client import plaid_client, PlaidClientError
from app.providers.plaid.normalizer import PlaidItemNormalizer
from app.models.enums import ConnectionStatus
from app.core.database import get_db


router = APIRouter(prefix="/connections", tags=["connections"])


# TODO Phase 4: Implement proper authentication
# For now, using a simple header-based auth for development
async def get_current_user_id(x_user_id: str = Header(..., description="User ID (temporary auth)")):
    """
    Temporary authentication dependency.

    In production, this will be replaced with proper JWT-based authentication.
    For Phase 4 development, we accept user_id via header.

    Args:
        x_user_id: User ID from X-User-Id header

    Returns:
        UUID: Validated user ID

    Raises:
        HTTPException: If user ID is invalid
    """
    try:
        return UUID(x_user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format. Must be a valid UUID."
        )


async def get_plaid_provider_id() -> int:
    """
    Get Plaid provider ID from database.

    Returns:
        int: Plaid provider ID

    Raises:
        HTTPException: If Plaid provider not found
    """
    try:
        db = get_db()
        result = db.table("providers").select("provider_id").eq("name", "Plaid").execute()

        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Plaid provider not configured in database"
            )

        return result.data[0]["provider_id"]
    except Exception as e:
        logger.error(f"Failed to fetch Plaid provider ID: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch provider configuration"
        )


@router.post("/plaid/link/token", response_model=LinkTokenResponse)
async def create_plaid_link_token(
    user_id: UUID = Header(..., alias="X-User-Id")
):
    """
    Create a Plaid link token for frontend Plaid Link integration.

    **Flow:**
    1. Create initial connection record (status: Initializing)
    2. Call Plaid API to create link_token
    3. Store link_token in connection artifact
    4. Return link_token to frontend

    **Frontend Usage:**
    ```javascript
    const response = await fetch('/api/v1/connections/plaid/link/token', {
        headers: {'X-User-Id': userId}
    });
    const {link_token, connection_id} = await response.json();

    // Initialize Plaid Link with link_token
    const plaidHandler = Plaid.create({
        token: link_token,
        onSuccess: (public_token, metadata) => {
            // Exchange public token
        }
    });
    ```

    Args:
        user_id: User ID from header (temporary auth)

    Returns:
        LinkTokenResponse: Contains link_token, expiration, and connection_id

    Raises:
        HTTPException: If link token creation fails
    """
    try:
        # Get Plaid provider ID
        provider_id = await get_plaid_provider_id()

        # Create initial connection record
        logger.info(f"Creating connection for user: {user_id}")
        connection = await connection_service.create_connection(
            user_id=user_id,
            provider_id=provider_id,
            status=ConnectionStatus.INITIALIZING
        )

        # Create Plaid link token
        logger.info(f"Creating Plaid link token for connection: {connection.connection_id}")
        link_token_response = await plaid_client.create_link_token(
            user_id=str(user_id),
            products=["transactions"],
        )

        # Store link token in connection artifact
        await connection_service.update_artifact(
            connection.connection_id,
            {
                "link_token": link_token_response["link_token"],
                "link_token_expiration": link_token_response["expiration"]
            }
        )

        logger.info(f"Link token created successfully for connection: {connection.connection_id}")

        return LinkTokenResponse(
            link_token=link_token_response["link_token"],
            expiration=link_token_response["expiration"],
            connection_id=connection.connection_id
        )

    except PlaidClientError as e:
        logger.error(f"Plaid API error creating link token: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create link token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating link token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error creating link token"
        )


@router.post("/plaid/exchange-token", response_model=ConnectionResponse)
async def exchange_plaid_public_token(
    request: ExchangeTokenRequest,
    background_tasks: BackgroundTasks,
    user_id: UUID = Header(..., alias="X-User-Id")
):
    """
    Exchange public token for access token and complete Plaid connection.

    **Flow:**
    1. Call Plaid API to exchange public_token for access_token
    2. Update connection with access_token, external_item_id, institution info
    3. Update status to Pending
    4. Trigger background job to fetch accounts (Phase 5)
    5. Return connection details

    **Frontend Usage:**
    ```javascript
    const plaidHandler = Plaid.create({
        token: link_token,
        onSuccess: async (public_token, metadata) => {
            await fetch('/api/v1/connections/plaid/exchange-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-Id': userId
                },
                body: JSON.stringify({
                    public_token,
                    metadata
                })
            });
        }
    });
    ```

    Args:
        request: Exchange token request with public_token and metadata
        background_tasks: FastAPI background tasks for async sync
        user_id: User ID from header (temporary auth)

    Returns:
        ConnectionResponse: Complete connection details

    Raises:
        HTTPException: If token exchange fails
    """
    try:
        # Exchange public token for access token
        logger.info("Exchanging public token for access token")
        exchange_response = await plaid_client.exchange_public_token(
            request.public_token
        )

        # Extract institution info from metadata (if available)
        institution_id = None
        institution_name = None
        if request.metadata:
            institution = request.metadata.get("institution")
            if institution:
                institution_id = institution.get("institution_id")
                institution_name = institution.get("name")

        # Find the connection for this user (get most recent Initializing connection)
        connections = await connection_service.get_user_connections(user_id)
        initializing_connections = [
            c for c in connections
            if c.connection_status == ConnectionStatus.INITIALIZING
        ]

        if not initializing_connections:
            raise HTTPException(
                status_code=400,
                detail="No initializing connection found. Please create a link token first."
            )

        # Use the most recent one
        connection = sorted(
            initializing_connections,
            key=lambda c: c.created_at,
            reverse=True
        )[0]

        # Update connection with access token and item info
        logger.info(f"Updating connection {connection.connection_id} with access token")
        updated_connection = await connection_service.update_connection(
            connection.connection_id,
            {
                "external_item_id": exchange_response["item_id"],
                "access_token": exchange_response["access_token"],
                "institution_id": institution_id,
                "institution_name": institution_name,
                "connection_status": ConnectionStatus.PENDING.value
            }
        )

        # Trigger background sync (accounts + transactions)
        logger.info(f"Triggering background sync for connection: {connection.connection_id}")
        background_tasks.add_task(sync_service.sync_connection, connection.connection_id)

        logger.info(
            f"Token exchanged successfully for connection: {connection.connection_id}, "
            f"item_id: {exchange_response['item_id']}"
        )

        return ConnectionResponse.model_validate(updated_connection)

    except PlaidClientError as e:
        logger.error(f"Plaid API error exchanging token: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange token: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error exchanging token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error exchanging token"
        )


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: UUID,
    user_id: UUID = Header(..., alias="X-User-Id")
):
    """
    Get connection details by ID.

    Args:
        connection_id: Connection ID
        user_id: User ID from header (temporary auth)

    Returns:
        ConnectionResponse: Connection details

    Raises:
        HTTPException: If connection not found or user unauthorized
    """
    try:
        connection = await connection_service.get_connection(connection_id)

        if not connection:
            raise HTTPException(
                status_code=404,
                detail=f"Connection {connection_id} not found"
            )

        # Verify user owns this connection
        if connection.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this connection"
            )

        return ConnectionResponse.model_validate(connection)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching connection {connection_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error fetching connection"
        )


@router.get("", response_model=ConnectionListResponse)
async def list_connections(
    user_id: UUID = Header(..., alias="X-User-Id")
):
    """
    List all connections for the current user.

    Args:
        user_id: User ID from header (temporary auth)

    Returns:
        ConnectionListResponse: List of user connections
    """
    try:
        connections = await connection_service.get_user_connections(user_id)

        return ConnectionListResponse(
            connections=[
                ConnectionResponse.model_validate(conn)
                for conn in connections
            ],
            total=len(connections)
        )

    except Exception as e:
        logger.error(f"Error listing connections: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error listing connections"
        )


@router.delete("/{connection_id}")
async def disconnect_plaid_connection(
    connection_id: UUID,
    user_id: UUID = Header(..., alias="X-User-Id")
):
    """
    Disconnect a Plaid connection (remove item).

    **Flow:**
    1. Verify user owns connection
    2. Call Plaid API to remove item (invalidate access_token)
    3. Update connection status to Revoked
    4. Optionally: soft-delete accounts & transactions (Phase 5)

    Args:
        connection_id: Connection ID to disconnect
        user_id: User ID from header (temporary auth)

    Returns:
        dict: Success message

    Raises:
        HTTPException: If disconnection fails
    """
    try:
        # Get connection
        connection = await connection_service.get_connection(connection_id)

        if not connection:
            raise HTTPException(
                status_code=404,
                detail=f"Connection {connection_id} not found"
            )

        # Verify user owns this connection
        if connection.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to disconnect this connection"
            )

        # Call Plaid to remove item (if access_token exists)
        if connection.access_token:
            try:
                logger.info(f"Removing Plaid item for connection: {connection_id}")
                await plaid_client.remove_item(connection.access_token.get_secret_value())
                logger.info(f"Plaid item removed successfully for connection: {connection_id}")
            except PlaidClientError as e:
                # Log error but continue (connection might already be invalid)
                logger.warning(f"Failed to remove Plaid item (continuing): {e}")

        # Update connection status to Revoked
        await connection_service.update_connection(
            connection_id,
            {"connection_status": ConnectionStatus.REVOKED.value}
        )

        # TODO Phase 5: Optionally soft-delete accounts & transactions
        # await account_service.soft_delete_by_connection(connection_id)
        # await transaction_service.soft_delete_by_connection(connection_id)

        logger.info(f"Connection disconnected successfully: {connection_id}")

        return {
            "message": "Connection disconnected successfully",
            "connection_id": connection_id
        }

    except HTTPException:
        raise
    except PlaidClientError as e:
        logger.error(f"Plaid API error disconnecting: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to disconnect from Plaid: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error disconnecting connection {connection_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error disconnecting connection"
        )


@router.post("/{connection_id}/sync")
async def trigger_manual_sync(
    connection_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: UUID = Header(..., alias="X-User-Id")
):
    """
    Trigger a manual sync for a connection (user-initiated refresh).

    **Flow:**
    1. Verify connection exists and user owns it
    2. Verify connection is in Active or Pending state
    3. Trigger background sync (accounts + transactions)

    **Background Sync:**
    - Fetches latest accounts from Plaid
    - Syncs transactions (initial if first time, incremental otherwise)
    - Updates connection status to Active
    - Handles errors gracefully (marks as needs_reauth if auth fails)

    Args:
        connection_id: Connection ID to sync
        background_tasks: FastAPI background tasks
        user_id: User ID from header (temporary auth)

    Returns:
        dict: Sync started message with connection_id

    Raises:
        HTTPException: If sync trigger fails (404, 403, 400)
    """
    try:
        # Get connection
        connection = await connection_service.get_connection(connection_id)

        if not connection:
            raise HTTPException(
                status_code=404,
                detail=f"Connection {connection_id} not found"
            )

        # Verify user owns this connection
        if connection.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to sync this connection"
            )

        # Verify connection is in syncable state
        if connection.connection_status not in [ConnectionStatus.ACTIVE, ConnectionStatus.PENDING]:
            raise HTTPException(
                status_code=400,
                detail=f"Connection is {connection.connection_status.value}. Cannot sync."
            )

        # Trigger complete sync in background
        logger.info(f"Manual sync triggered for connection: {connection_id}")
        background_tasks.add_task(sync_service.sync_connection, connection_id)

        return {
            "message": "Sync started in background",
            "connection_id": str(connection_id),
            "status": "processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering sync for connection {connection_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error triggering sync"
        )
