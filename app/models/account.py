"""Account model - unified account representation."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AccountType, AccountSubtype, AccountStatus, HolderCategory


class UnifiedAccount(BaseModel):
    """Unified account model - provider-agnostic representation."""

    account_id: Optional[int] = None
    user_id: UUID
    connection_id: Optional[int] = None
    external_account_id: str = Field(..., description="Provider's account ID")
    name: str = Field(..., description="Account name (e.g., 'Chase Checking')")
    official_name: Optional[str] = Field(None, description="Official bank account name")
    account_type: AccountType
    account_subtype: Optional[AccountSubtype] = None
    currency: str = Field(default="USD", description="ISO currency code")
    mask: Optional[str] = Field(None, description="Last 4 digits of account number")
    current_balance: Optional[Decimal] = Field(None, description="Current balance")
    available_balance: Optional[Decimal] = Field(None, description="Available balance")
    credit_limit: Optional[Decimal] = Field(None, description="Credit limit (for credit accounts)")
    institution_name: Optional[str] = Field(None, description="Bank/institution name")
    verification_status: Optional[str] = Field(None, description="Verification status")
    holder_category: Optional[HolderCategory] = Field(None, description="Account holder category (personal, business, or unrecognized)")
    provider_metadata: dict = Field(
        default_factory=dict,
        description="Provider-specific metadata (e.g., persistent_account_id for Plaid)"
    )
    account_status: AccountStatus = AccountStatus.ACTIVE
    last_refreshed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "connection_id": 1,
                "external_account_id": "blgvvBlXw3cq5GMPwqB6s6q4dLKB9WcVqGDGo",
                "name": "Chase Checking",
                "official_name": "Chase Premier Plus Checking",
                "account_type": "depository",
                "account_subtype": "checking",
                "currency": "USD",
                "mask": "0000",
                "current_balance": 1500.50,
                "available_balance": 1500.50,
                "institution_name": "Chase",
                "verification_status": "automatically_verified",
                "holder_category": "personal",
                "provider_metadata": {
                    "persistent_account_id": "persistent_id_123"
                },
                "account_status": "Active"
            }
        }
