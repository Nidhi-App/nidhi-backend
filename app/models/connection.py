"""Connection model - represents a provider connection (e.g., Plaid item)."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from app.models.enums import ConnectionStatus


class Connection(BaseModel):
    """Connection model matching database schema.

    Security Note:
        The access_token and link_token fields contain sensitive credentials and must NEVER be:
        - Included in API responses (excluded via Field(exclude=True))
        - Logged or printed (protected by SecretStr)
        - Committed to source control in examples or tests
        - Exposed in error messages or debugging output

        Use get_access_token() and get_link_token() methods to access these values only when needed.

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
        description="Provider access token (SENSITIVE - never log or expose)"
    )
    link_token: Optional[SecretStr] = Field(
        default=None,
        exclude=True,
        description="Plaid Link token for frontend initialization (SENSITIVE - short-lived, exclude from logs)"
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
        """Get the raw access token value (for internal use only).

        WARNING: This method exposes the sensitive access_token credential.
        Only use this method when making authenticated API calls to the provider.
        NEVER log, print, or include the returned value in API responses.

        Returns:
            The raw access token string, or None if not set.
        """
        return self.access_token.get_secret_value() if self.access_token else None

    def get_link_token(self) -> Optional[str]:
        """Get the raw link token value (for API responses only).

        WARNING: This method exposes the sensitive link_token credential.
        Only use this method when returning the link_token to the frontend for
        Plaid Link initialization. Link tokens are short-lived (typically 4 hours).
        NEVER log or persist the returned value.

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
