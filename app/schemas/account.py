"""Account API schemas - request/response models."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AccountType, AccountSubtype, AccountStatus, HolderCategory


class AccountResponse(BaseModel):
    """Account response schema."""

    account_id: int
    user_id: UUID
    connection_id: Optional[int]
    external_account_id: str
    name: str
    official_name: Optional[str]
    account_type: AccountType
    account_subtype: Optional[AccountSubtype]
    currency: str
    mask: Optional[str]
    current_balance: Optional[Decimal]
    available_balance: Optional[Decimal]
    credit_limit: Optional[Decimal]
    institution_name: Optional[str]
    verification_status: Optional[str]
    holder_category: Optional[HolderCategory]
    account_status: AccountStatus
    last_refreshed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccountListResponse(BaseModel):
    """List of accounts response."""

    accounts: list[AccountResponse]
    total: int


class AccountBalanceUpdate(BaseModel):
    """Account balance update request."""

    current_balance: Optional[Decimal]
    available_balance: Optional[Decimal]
