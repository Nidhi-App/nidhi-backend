"""
Plaid provider package.

This package contains all Plaid-specific implementation including:
- PlaidClient: API client wrapper for Plaid SDK
- Normalizers: Convert Plaid data to unified models
- Models: Plaid-specific Pydantic models
"""

from app.providers.plaid.client import PlaidClient, PlaidClientError, plaid_client
from app.providers.plaid.normalizer import (
    PlaidItemNormalizer,
    PlaidAccountNormalizer,
    PlaidTransactionNormalizer
)
from app.providers.plaid.models import (
    PlaidAccount,
    PlaidTransaction,
    PlaidBalance,
    PlaidItem,
    PlaidLinkTokenResponse,
    PlaidTokenExchangeResponse,
    PlaidWebhookPayload,
    PlaidInstitution,
    PlaidPersonalFinanceCategory,
    PlaidCounterparty,
    PlaidLocation
)

__all__ = [
    # Client
    "PlaidClient",
    "PlaidClientError",
    "plaid_client",

    # Normalizers
    "PlaidItemNormalizer",
    "PlaidAccountNormalizer",
    "PlaidTransactionNormalizer",

    # Models
    "PlaidAccount",
    "PlaidTransaction",
    "PlaidBalance",
    "PlaidItem",
    "PlaidLinkTokenResponse",
    "PlaidTokenExchangeResponse",
    "PlaidWebhookPayload",
    "PlaidInstitution",
    "PlaidPersonalFinanceCategory",
    "PlaidCounterparty",
    "PlaidLocation",
]
