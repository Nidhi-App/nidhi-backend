"""
Plaid-specific Pydantic models.

These models represent the data structures returned by Plaid API.
They are used for validation and type checking before normalization
to our unified data models.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PlaidBalance(BaseModel):
    """Plaid account balance information."""

    available: Optional[float] = Field(
        None,
        description="Amount of funds available for use (may be null for some account types)"
    )
    current: float = Field(
        ...,
        description="Current balance of the account"
    )
    limit: Optional[float] = Field(
        None,
        description="Credit limit for credit-type accounts"
    )
    iso_currency_code: Optional[str] = Field(
        None,
        description="ISO-4217 currency code (e.g., USD, EUR)"
    )
    unofficial_currency_code: Optional[str] = Field(
        None,
        description="Unofficial currency code for non-standard currencies"
    )
    last_updated_datetime: Optional[datetime] = Field(
        None,
        description="Timestamp of last balance update"
    )


class PlaidAccount(BaseModel):
    """Plaid account information."""

    account_id: str = Field(
        ...,
        description="Plaid's unique identifier for the account"
    )
    balances: PlaidBalance = Field(
        ...,
        description="Balance information for the account"
    )
    mask: Optional[str] = Field(
        None,
        description="Last 2-4 digits of the account number"
    )
    name: str = Field(
        ...,
        description="Name of the account as given by the institution"
    )
    official_name: Optional[str] = Field(
        None,
        description="Official account name from the institution"
    )
    type: str = Field(
        ...,
        description="Account type (depository, credit, loan, investment, other)"
    )
    subtype: Optional[str] = Field(
        None,
        description="Account subtype (checking, savings, credit card, etc.)"
    )
    verification_status: Optional[str] = Field(
        None,
        description="Verification status of the account"
    )
    persistent_account_id: Optional[str] = Field(
        None,
        description="Persistent identifier that remains constant across updates"
    )
    holder_category: Optional[str] = Field(
        None,
        description="Holder category (personal, business, etc.)"
    )


class PlaidPersonalFinanceCategory(BaseModel):
    """Plaid personal finance category."""

    primary: str = Field(
        ...,
        description="Primary category (e.g., FOOD_AND_DRINK)"
    )
    detailed: str = Field(
        ...,
        description="Detailed category (e.g., FOOD_AND_DRINK_COFFEE)"
    )
    confidence_level: Optional[str] = Field(
        None,
        description="Confidence level of categorization (VERY_HIGH, HIGH, MEDIUM, LOW)"
    )


class PlaidCounterparty(BaseModel):
    """Plaid counterparty information."""

    name: str = Field(
        ...,
        description="Name of the counterparty"
    )
    type: Optional[str] = Field(
        None,
        description="Type of counterparty (merchant, financial_institution, etc.)"
    )
    logo_url: Optional[str] = Field(
        None,
        description="URL of the counterparty's logo"
    )
    website: Optional[str] = Field(
        None,
        description="Website of the counterparty"
    )
    entity_id: Optional[str] = Field(
        None,
        description="Plaid's unique identifier for the entity"
    )
    confidence_level: Optional[str] = Field(
        None,
        description="Confidence level of counterparty identification"
    )


class PlaidLocation(BaseModel):
    """Plaid location information."""

    address: Optional[str] = Field(
        None,
        description="Street address"
    )
    city: Optional[str] = Field(
        None,
        description="City"
    )
    region: Optional[str] = Field(
        None,
        description="Region/State"
    )
    postal_code: Optional[str] = Field(
        None,
        description="Postal code"
    )
    country: Optional[str] = Field(
        None,
        description="Country code"
    )
    lat: Optional[float] = Field(
        None,
        description="Latitude"
    )
    lon: Optional[float] = Field(
        None,
        description="Longitude"
    )
    store_number: Optional[str] = Field(
        None,
        description="Store number"
    )


class PlaidTransaction(BaseModel):
    """Plaid transaction information."""

    transaction_id: str = Field(
        ...,
        description="Plaid's unique identifier for the transaction"
    )
    account_id: str = Field(
        ...,
        description="Account ID that this transaction belongs to"
    )
    amount: float = Field(
        ...,
        description="Transaction amount (positive = money out, negative = money in)"
    )
    iso_currency_code: Optional[str] = Field(
        None,
        description="ISO-4217 currency code"
    )
    unofficial_currency_code: Optional[str] = Field(
        None,
        description="Unofficial currency code for non-standard currencies"
    )
    category: Optional[List[str]] = Field(
        None,
        description="Hierarchical category (e.g., ['Food and Drink', 'Restaurants'])"
    )
    category_id: Optional[str] = Field(
        None,
        description="Plaid's category ID"
    )
    date: str = Field(
        ...,
        description="Posted date (YYYY-MM-DD format)"
    )
    authorized_date: Optional[str] = Field(
        None,
        description="Authorized date (YYYY-MM-DD format)"
    )
    authorized_datetime: Optional[datetime] = Field(
        None,
        description="Authorized datetime with timezone"
    )
    posted_datetime: Optional[datetime] = Field(
        None,
        description="Posted datetime with timezone",
        alias="datetime"
    )
    name: str = Field(
        ...,
        description="Merchant or description of the transaction"
    )
    merchant_name: Optional[str] = Field(
        None,
        description="Cleaned merchant name"
    )
    merchant_entity_id: Optional[str] = Field(
        None,
        description="Plaid's unique identifier for the merchant"
    )
    logo_url: Optional[str] = Field(
        None,
        description="URL of merchant logo"
    )
    website: Optional[str] = Field(
        None,
        description="Merchant website"
    )
    payment_channel: str = Field(
        ...,
        description="Payment channel (online, in store, other)"
    )
    pending: bool = Field(
        ...,
        description="Whether the transaction is pending"
    )
    pending_transaction_id: Optional[str] = Field(
        None,
        description="ID of pending transaction that this replaces"
    )
    personal_finance_category: Optional[PlaidPersonalFinanceCategory] = Field(
        None,
        description="Personal finance category with confidence level"
    )
    counterparties: Optional[List[PlaidCounterparty]] = Field(
        None,
        description="List of counterparties involved in the transaction"
    )
    location: Optional[PlaidLocation] = Field(
        None,
        description="Location where the transaction occurred"
    )
    payment_meta: Optional[Dict[str, Any]] = Field(
        None,
        description="Payment metadata"
    )
    transaction_type: Optional[str] = Field(
        None,
        description="Transaction type (special, place, etc.)"
    )
    transaction_code: Optional[str] = Field(
        None,
        description="Transaction code from the institution"
    )
    check_number: Optional[str] = Field(
        None,
        description="Check number (if applicable)"
    )


class PlaidItem(BaseModel):
    """Plaid item information."""

    item_id: str = Field(
        ...,
        description="Plaid's unique identifier for the item"
    )
    institution_id: Optional[str] = Field(
        None,
        description="Institution ID"
    )
    webhook: Optional[str] = Field(
        None,
        description="Webhook URL configured for this item"
    )
    error: Optional[Dict[str, Any]] = Field(
        None,
        description="Error information if item is in error state"
    )
    available_products: List[str] = Field(
        default_factory=list,
        description="Products available but not yet enabled"
    )
    billed_products: List[str] = Field(
        default_factory=list,
        description="Products that are billed"
    )
    products: List[str] = Field(
        default_factory=list,
        description="Products currently enabled"
    )
    consented_products: Optional[List[str]] = Field(
        None,
        description="Products that user has consented to"
    )
    consent_expiration_time: Optional[datetime] = Field(
        None,
        description="Timestamp when consent expires"
    )
    update_type: str = Field(
        default="background",
        description="Update type (background or user_present_required)"
    )


class PlaidLinkTokenResponse(BaseModel):
    """Response from link token creation."""

    link_token: str = Field(
        ...,
        description="Link token for initializing Plaid Link"
    )
    expiration: datetime = Field(
        ...,
        description="Expiration time of the link token"
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier"
    )


class PlaidTokenExchangeResponse(BaseModel):
    """Response from public token exchange."""

    access_token: str = Field(
        ...,
        description="Access token for accessing item data"
    )
    item_id: str = Field(
        ...,
        description="Plaid item ID"
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier"
    )


class PlaidWebhookPayload(BaseModel):
    """Plaid webhook payload."""

    webhook_type: str = Field(
        ...,
        description="Type of webhook (TRANSACTIONS, ITEM, etc.)"
    )
    webhook_code: str = Field(
        ...,
        description="Specific webhook code (DEFAULT_UPDATE, ERROR, etc.)"
    )
    item_id: str = Field(
        ...,
        description="Item ID that triggered the webhook"
    )
    error: Optional[Dict[str, Any]] = Field(
        None,
        description="Error information if webhook is error-related"
    )
    new_transactions: Optional[int] = Field(
        None,
        description="Number of new transactions (for TRANSACTIONS webhooks)"
    )
    removed_transactions: Optional[List[str]] = Field(
        None,
        description="List of removed transaction IDs"
    )
    consent_expiration_time: Optional[datetime] = Field(
        None,
        description="Consent expiration time (for consent-related webhooks)"
    )


class PlaidInstitution(BaseModel):
    """Plaid institution information."""

    institution_id: str = Field(
        ...,
        description="Plaid institution ID"
    )
    name: str = Field(
        ...,
        description="Institution name"
    )
    products: List[str] = Field(
        default_factory=list,
        description="Products supported by this institution"
    )
    country_codes: List[str] = Field(
        default_factory=list,
        description="Country codes where institution operates"
    )
    url: Optional[str] = Field(
        None,
        description="Institution website URL"
    )
    primary_color: Optional[str] = Field(
        None,
        description="Primary brand color (hex code)"
    )
    logo: Optional[str] = Field(
        None,
        description="Base64-encoded logo"
    )
    routing_numbers: Optional[List[str]] = Field(
        None,
        description="Routing numbers for the institution"
    )
    oauth: bool = Field(
        default=False,
        description="Whether institution supports OAuth"
    )
