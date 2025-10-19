"""Transaction model - unified transaction representation."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import TransactionDirection


# ISO 4217 Currency Codes (Active as of 2025)
# Reference: https://www.iso.org/iso-4217-currency-codes.html
# Maintained by SIX Group on behalf of ISO
VALID_CURRENCIES = frozenset({
    # Major Currencies
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    # Americas
    "ARS", "BOB", "BRL", "BSD", "BZD", "CLP", "COP", "CRC", "CUP", "DOP",
    "GTQ", "HNL", "HTG", "JMD", "MXN", "NIO", "PAB", "PEN", "PYG", "TTD",
    "UYU", "VES", "XCD",
    # Europe
    "ALL", "BAM", "BGN", "BYN", "CZK", "DKK", "GEL", "HRK", "HUF", "ISK",
    "MDL", "MKD", "NOK", "PLN", "RON", "RSD", "RUB", "SEK", "TRY", "UAH",
    # Africa
    "AED", "AOA", "BWP", "CDF", "DJF", "DZD", "EGP", "ERN", "ETB", "GHS",
    "GMD", "GNF", "KES", "LRD", "LSL", "LYD", "MAD", "MGA", "MRU", "MUR",
    "MWK", "MZN", "NAD", "NGN", "RWF", "SCR", "SDG", "SLE", "SOS", "SSP",
    "STN", "SZL", "TND", "TZS", "UGX", "XAF", "XOF", "ZAR", "ZMW", "ZWL",
    # Middle East
    "BHD", "ILS", "IQD", "IRR", "JOD", "KWD", "LBP", "OMR", "QAR", "SAR",
    "SYP", "YER",
    # Asia
    "AFN", "AMD", "AZN", "BDT", "BTN", "BND", "CNY", "HKD", "IDR", "INR",
    "KGS", "KHR", "KPW", "KRW", "KZT", "LAK", "LKR", "MMK", "MNT", "MOP",
    "MVR", "MYR", "NPR", "PHP", "PKR", "SGD", "THB", "TJS", "TMT", "TWD",
    "UZS", "VND",
    # Pacific
    "FJD", "PGK", "SBD", "TOP", "VUV", "WST", "XPF",
    # Cryptocurrencies and Special Codes (for completeness)
    "XAU", "XAG", "XPT", "XPD",  # Precious metals
    "XDR", "XSU", "XUA",  # Special drawing rights and units
    # Other territories and dependencies
    "ANG", "AWG", "BBD", "BMD", "CUC", "FKP", "GGP", "GIP",
    "GYD", "IMP", "JEP", "KYD", "SHP", "SRD", "SVC", "TVD",
})



class UnifiedTransaction(BaseModel):
    """Unified transaction model - provider-agnostic representation."""

    txn_id: Optional[int] = None
    account_id: int = Field(..., description="Internal account_id from accounts table")
    external_txn_id: str = Field(..., description="Provider's transaction ID")
    txn_date: datetime = Field(..., description="Transaction date")
    posted_at: Optional[datetime] = Field(None, description="Posted/settled date")
    authorized_date: Optional[datetime] = Field(None, description="Authorization date (Plaid)")
    amount: Decimal = Field(..., description="Transaction amount (always positive)")
    currency: str = Field(..., description="ISO 4217 currency code (required, validated)")
    txn_direction: TransactionDirection = Field(..., description="Credit (in) or Debit (out)")
    description_raw: str = Field(..., description="Raw transaction description")
    merchant_name_raw: Optional[str] = Field(None, description="Merchant name")
    merchant_logo_url: Optional[str] = Field(None, description="Merchant logo URL (Plaid)")
    merchant_website: Optional[str] = Field(None, description="Merchant website (Plaid)")
    pending: bool = Field(default=False, description="Is transaction pending?")
    category: Optional[str] = Field(None, description="Simplified category string")
    personal_finance_category: Optional[dict] = Field(
        None,
        description="Plaid personal finance category (primary, detailed, confidence)"
    )
    payment_channel: Optional[str] = Field(None, description="Payment channel (in store, online, etc.)")
    counterparties: list = Field(default_factory=list, description="Plaid counterparties")
    location: Optional[dict] = Field(None, description="Transaction location (lat, lon, address)")
    check_number: Optional[str] = Field(None, description="Check number if applicable")
    running_balance: Optional[Decimal] = Field(None, description="Running balance after transaction")
    provider_metadata: dict = Field(
        default_factory=dict,
        description="Provider-specific metadata"
    )
    raw_payload: dict = Field(
        default_factory=dict,
        description="Full raw provider response"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate that amount is positive."""
        if v <= 0:
            raise ValueError('amount must be positive')
        return v

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate and normalize currency to uppercase ISO 4217 code.

        Args:
            v: Currency code (case-insensitive, will be normalized to uppercase)

        Returns:
            Uppercase 3-letter ISO 4217 currency code

        Raises:
            ValueError: If the currency code is not a valid ISO 4217 code

        Examples:
            >>> validate_currency("usd")  # Returns "USD"
            >>> validate_currency("EUR")  # Returns "EUR"
            >>> validate_currency("XYZ")  # Raises ValueError
        """
        # Normalize to uppercase
        normalized = v.strip().upper()

        # Validate format (3 letters)
        if not (len(normalized) == 3 and normalized.isalpha()):
            raise ValueError(
                f"Currency must be a 3-letter code, got: '{v}' (length: {len(v)})"
            )

        # Validate against ISO 4217 standard
        if normalized not in VALID_CURRENCIES:
            raise ValueError(
                f"Invalid ISO 4217 currency code: '{normalized}'. "
                f"Must be a valid 3-letter currency code (e.g., USD, EUR, GBP)"
            )

        return normalized

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "account_id": 1,
                "external_txn_id": "yBVBEwrXdDf9gfXP4kcKFK6FjqqmRhQ4JqYnb",
                "txn_date": "2025-01-14T00:00:00Z",
                "posted_at": "2025-01-14T00:00:00Z",
                "authorized_date": "2025-01-14T00:00:00Z",
                "amount": 25.00,
                "currency": "USD",
                "txn_direction": "Debit",
                "description_raw": "Starbucks",
                "merchant_name_raw": "Starbucks",
                "merchant_logo_url": "https://plaid-merchant-logos.plaid.com/starbucks_619.png",
                "merchant_website": "starbucks.com",
                "pending": False,
                "category": "Food and Drink > Restaurants",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_COFFEE",
                    "confidence_level": "VERY_HIGH"
                },
                "payment_channel": "in store",
                "provider_metadata": {
                    "transaction_code": "purchase",
                    "merchant_entity_id": "123"
                }
            }
        }
