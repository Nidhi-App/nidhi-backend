"""Connection model - represents a provider connection (e.g., Plaid item)."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from app.models.enums import ConnectionStatus


class Connection(BaseModel):
    """Connection model matching database schema.

    Security Note - Token Handling:
        This model contains two distinct types of sensitive tokens:

        1. access_token (NEVER expose to frontend):
           - Long-lived credential for backend-to-Plaid API calls
           - MUST NEVER be included in API responses
           - MUST NEVER be logged or printed
           - Only accessed via get_access_token() for internal Plaid API calls

        2. link_token (Safe to return to frontend):
           - Short-lived token (~4 hours) for Plaid Link initialization
           - DESIGNED to be returned to frontend via API responses
           - Should NOT be logged or persisted
           - Accessed via get_link_token() when initializing Plaid Link UI

        Both fields use SecretStr and Field(exclude=True) to prevent accidental exposure.
        Always use the getter methods to access token values intentionally.

        IMPORTANT: The artifact field is for NON-SENSITIVE metadata only. Never store tokens,
        passwords, or other credentials in artifact. Use dedicated SecretStr fields instead.
    """

    connection_id: Optional[int] = None
    user_id: UUID
    provider_id: int
    external_item_id: Optional[str] = None
    access_token: Optional[SecretStr] = Field(
        default=None,
        exclude=True,
        description="Long-lived Plaid access token for backend API calls (NEVER expose to frontend)"
    )
    link_token: Optional[SecretStr] = Field(
        default=None,
        exclude=True,
        description="Short-lived Plaid Link token for frontend initialization (safe to return in API responses)"
    )
    connection_status: ConnectionStatus = ConnectionStatus.INITIALIZING
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    products: Optional[List[str]] = Field(
        default=None,
        description="List of Plaid products enabled for this connection (e.g., 'transactions', 'auth')"
    )
    available_products: Optional[List[str]] = Field(
        default=None,
        description="List of Plaid products available but not yet enabled"
    )
    consent_expiration_time: Optional[datetime] = None
    update_type: Optional[str] = None
    scopes: Optional[dict] = None
    fip_ids: Optional[dict] = None
    artifact: dict = Field(
        default_factory=dict,
        description="Non-sensitive metadata (e.g., transaction cursor, sync state). "
                    "IMPORTANT: Do NOT store sensitive tokens here - use dedicated SecretStr fields."
    )
    last_synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_access_token(self) -> Optional[str]:
        """Get the raw access_token value (INTERNAL USE ONLY - NEVER expose to frontend).

        WARNING: This exposes the long-lived access_token credential used for Plaid API calls.
        - Only use when making authenticated backend-to-Plaid API requests
        - NEVER include in API responses to frontend
        - NEVER log, print, or expose in error messages

        Returns:
            The raw access token string, or None if not set.
        """
        return self.access_token.get_secret_value() if self.access_token else None

    def get_link_token(self) -> Optional[str]:
        """Get the raw link_token value (SAFE to return to frontend).

        This token is specifically designed to be sent to the frontend for Plaid Link
        initialization. Link tokens are short-lived (typically 4 hours) and have limited scope.

        Usage:
        - SAFE to include in API responses for Plaid Link initialization
        - Should NOT be logged or persisted in application logs
        - Automatically expires after ~4 hours

        Returns:
            The raw link token string, or None if not set.
        """
        return self.link_token.get_secret_value() if self.link_token else None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                # NOTE: This example intentionally excludes sensitive fields like access_token and link_token.
                # Never commit real credentials to source control.
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "provider_id": 8,
                "external_item_id": "item_123abc",
                "connection_status": "Active",
                "institution_id": "ins_3",
                "institution_name": "Chase",
                "products": ["transactions", "auth"],
                "available_products": ["balance", "identity"],
                "artifact": {
                    # NOTE: Only non-sensitive metadata should be stored in artifact
                    "transactions_cursor": "cursor_abc",
                    "last_sync_status": "success",
                    "items_synced": 150
                }
            }
        }
