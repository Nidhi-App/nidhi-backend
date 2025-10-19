"""Transaction API schemas - request/response models."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import TransactionDirection


class TransactionResponse(BaseModel):
    """Transaction response schema."""

    txn_id: int
    account_id: int
    external_txn_id: str
    txn_date: datetime
    posted_at: Optional[datetime]
    authorized_date: Optional[datetime]
    amount: Decimal
    currency: str
    txn_direction: TransactionDirection
    description_raw: str
    merchant_name_raw: Optional[str]
    merchant_logo_url: Optional[str]
    merchant_website: Optional[str]
    pending: bool
    category: Optional[str]
    personal_finance_category: Optional[dict]
    payment_channel: Optional[str]
    counterparties: Optional[list]
    location: Optional[dict]
    check_number: Optional[str]
    running_balance: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """List of transactions response."""

    transactions: list[TransactionResponse]
    total: int
    limit: int
    offset: int


class TransactionFilters(BaseModel):
    """Transaction filter parameters."""

    account_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    txn_direction: Optional[TransactionDirection] = None
    pending: Optional[bool] = None
    category: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
