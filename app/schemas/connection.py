"""Connection API schemas - request/response models."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import ConnectionStatus


class ConnectionResponse(BaseModel):
    """Connection response schema."""

    connection_id: UUID
    user_id: UUID
    provider_id: int
    external_item_id: Optional[str]
    connection_status: ConnectionStatus
    institution_id: Optional[str]
    institution_name: Optional[str]
    products: Optional[List[str]]
    available_products: Optional[List[str]]
    consent_expiration_time: Optional[datetime]
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionListResponse(BaseModel):
    """List of connections response."""

    connections: list[ConnectionResponse]
    total: int


class LinkTokenResponse(BaseModel):
    """Plaid link token response."""

    link_token: str
    expiration: str
    connection_id: UUID


class ExchangeTokenRequest(BaseModel):
    """Public token exchange request."""

    public_token: str
    metadata: Optional[dict] = None


class ConnectionStatusUpdate(BaseModel):
    """Connection status update request."""

    status: ConnectionStatus
