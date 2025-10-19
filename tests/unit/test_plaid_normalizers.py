"""Unit tests for Plaid normalizers."""

import pytest
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import SecretStr

from app.providers.plaid.normalizer import (
    PlaidItemNormalizer,
    PlaidAccountNormalizer,
    PlaidTransactionNormalizer
)
from app.models.enums import (
    AccountType,
    AccountSubtype,
    TransactionDirection,
    AccountStatus,
    HolderCategory,
    ConnectionStatus
)
from app.models.connection import Connection


class TestPlaidItemNormalizer:
    """Test suite for PlaidItemNormalizer."""

    def test_normalize_from_exchange(self):
        """Test creating connection from token exchange."""
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        provider_id = 8
        access_token = "access-sandbox-test-token"
        item_id = "item_123abc"

        result = PlaidItemNormalizer.normalize_from_exchange(
            user_id=user_id,
            provider_id=provider_id,
            access_token=access_token,
            item_id=item_id,
            institution_id="ins_3",
            institution_name="Chase"
        )

        assert result.user_id == user_id
        assert result.provider_id == provider_id
        assert result.external_item_id == item_id
        assert result.get_access_token() == access_token
        assert result.connection_status == ConnectionStatus.PENDING
        assert result.institution_id == "ins_3"
        assert result.institution_name == "Chase"
        assert result.created_at is not None
        assert result.updated_at is not None

    def test_normalize_from_exchange_with_metadata(self):
        """Test creating connection with metadata from Plaid Link."""
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        metadata = {
            "institution": {
                "name": "Bank of America",
                "institution_id": "ins_4"
            },
            "link_session_id": "session_123"
        }

        result = PlaidItemNormalizer.normalize_from_exchange(
            user_id=user_id,
            provider_id=8,
            access_token="access-token",
            item_id="item_id",
            metadata=metadata
        )

        # Should extract from metadata
        assert result.institution_id == "ins_4"
        assert result.institution_name == "Bank of America"

    def test_normalize_from_item_get(self):
        """Test updating connection from Plaid item data."""
        # Create initial connection
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            external_item_id="item_123",
            access_token=SecretStr("access-token"),
            connection_status=ConnectionStatus.PENDING
        )

        # Mock Plaid item data
        plaid_item = {
            "item_id": "item_123",
            "institution_id": "ins_3",
            "products": ["transactions", "auth"],
            "billed_products": ["transactions"],
            "available_products": ["identity", "balance"],
            "consent_expiration_time": "2025-12-31T23:59:59Z",
            "update_type": "background"
        }

        result = PlaidItemNormalizer.normalize_from_item_get(plaid_item, connection)

        assert result.products == ["transactions", "auth"]
        assert result.available_products == ["identity", "balance"]
        assert result.consent_expiration_time is not None
        assert result.update_type == "background"
        assert result.connection_status == ConnectionStatus.ACTIVE  # Updated from PENDING

    def test_normalize_from_item_get_with_error(self):
        """Test updating connection with item error."""
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            external_item_id="item_123",
            access_token=SecretStr("access-token"),
            connection_status=ConnectionStatus.ACTIVE
        )

        # Item with login required error
        plaid_item = {
            "item_id": "item_123",
            "products": ["transactions"],
            "error": {
                "error_code": "ITEM_LOGIN_REQUIRED",
                "error_message": "User needs to re-authenticate"
            }
        }

        result = PlaidItemNormalizer.normalize_from_item_get(plaid_item, connection)

        assert result.connection_status == ConnectionStatus.NEEDS_REAUTH

    def test_normalize_from_item_get_item_locked(self):
        """Test updating connection with ITEM_LOCKED error."""
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            external_item_id="item_123",
            access_token=SecretStr("access-token"),
            connection_status=ConnectionStatus.ACTIVE
        )

        plaid_item = {
            "item_id": "item_123",
            "products": ["transactions"],
            "error": {
                "error_code": "ITEM_LOCKED",
                "error_message": "Item is locked"
            }
        }

        result = PlaidItemNormalizer.normalize_from_item_get(plaid_item, connection)

        assert result.connection_status == ConnectionStatus.ERROR

    def test_update_institution_info(self):
        """Test updating institution information."""
        connection = Connection(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            external_item_id="item_123",
            access_token=SecretStr("access-token"),
            connection_status=ConnectionStatus.PENDING
        )

        result = PlaidItemNormalizer.update_institution_info(
            connection,
            institution_id="ins_5",
            institution_name="Wells Fargo"
        )

        assert result.institution_id == "ins_5"
        assert result.institution_name == "Wells Fargo"
        assert result.updated_at is not None

    def test_mark_needs_reauth(self):
        """Test marking connection as needs reauth."""
        connection = Connection(
            connection_id=1,
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            external_item_id="item_123",
            access_token=SecretStr("access-token"),
            connection_status=ConnectionStatus.ACTIVE
        )

        result = PlaidItemNormalizer.mark_needs_reauth(
            connection,
            error_message="Credentials expired"
        )

        assert result.connection_status == ConnectionStatus.NEEDS_REAUTH
        assert result.updated_at is not None

    def test_mark_revoked(self):
        """Test marking connection as revoked."""
        connection = Connection(
            connection_id=1,
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            provider_id=8,
            external_item_id="item_123",
            access_token=SecretStr("access-token"),
            connection_status=ConnectionStatus.ACTIVE
        )

        result = PlaidItemNormalizer.mark_revoked(
            connection,
            reason="User disconnected bank"
        )

        assert result.connection_status == ConnectionStatus.REVOKED
        assert result.updated_at is not None


class TestPlaidAccountNormalizer:
    """Test suite for PlaidAccountNormalizer."""

    @pytest.fixture
    def sample_plaid_account(self):
        """Sample Plaid account data."""
        return {
            "account_id": "blgvvBlXw3cq5GMPwqB6s6q4dLKB9WcVqGDGo",
            "balances": {
                "available": 100.00,
                "current": 110.00,
                "limit": None,
                "iso_currency_code": "USD",
                "last_updated_datetime": "2024-01-15T14:30:00Z"
            },
            "mask": "0000",
            "name": "Plaid Checking",
            "official_name": "Plaid Gold Standard 0% Interest Checking",
            "type": "depository",
            "subtype": "checking",
            "verification_status": "automatically_verified",
            "persistent_account_id": "persistent_id_123",
            "holder_category": "personal"
        }

    @pytest.fixture
    def sample_credit_account(self):
        """Sample Plaid credit card account."""
        return {
            "account_id": "credit-card-account-id",
            "balances": {
                "available": 9000.00,
                "current": 1000.00,
                "limit": 10000.00,
                "iso_currency_code": "USD"
            },
            "mask": "1234",
            "name": "Chase Freedom",
            "official_name": "Chase Freedom Unlimited",
            "type": "credit",
            "subtype": "credit_card",
            "verification_status": "automatically_verified",
            "holder_category": "personal"
        }

    def test_normalize_depository_account(self, sample_plaid_account):
        """Test normalizing a depository account."""
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        connection_id = 1

        result = PlaidAccountNormalizer.normalize(
            sample_plaid_account,
            user_id,
            connection_id,
            institution_name="Plaid Bank"
        )

        assert result.user_id == user_id
        assert result.connection_id == connection_id
        assert result.external_account_id == "blgvvBlXw3cq5GMPwqB6s6q4dLKB9WcVqGDGo"
        assert result.name == "Plaid Checking"
        assert result.official_name == "Plaid Gold Standard 0% Interest Checking"
        assert result.account_type == AccountType.DEPOSITORY
        assert result.account_subtype == AccountSubtype.CHECKING
        assert result.currency == "USD"
        assert result.mask == "0000"
        assert result.current_balance == Decimal("110.00")
        assert result.available_balance == Decimal("100.00")
        assert result.credit_limit is None
        assert result.institution_name == "Plaid Bank"
        assert result.verification_status == "automatically_verified"
        assert result.holder_category == HolderCategory.PERSONAL
        assert result.account_status == AccountStatus.ACTIVE
        assert "plaid" in result.provider_metadata
        assert result.provider_metadata["plaid"]["persistent_account_id"] == "persistent_id_123"

    def test_normalize_credit_account(self, sample_credit_account):
        """Test normalizing a credit card account."""
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        connection_id = 2

        result = PlaidAccountNormalizer.normalize(
            sample_credit_account,
            user_id,
            connection_id,
            institution_name="Chase"
        )

        assert result.account_type == AccountType.CREDIT
        assert result.account_subtype == AccountSubtype.CREDIT_CARD
        assert result.current_balance == Decimal("1000.00")
        assert result.available_balance == Decimal("9000.00")
        assert result.credit_limit == Decimal("10000.00")
        assert result.institution_name == "Chase"

    def test_normalize_account_missing_currency(self, sample_plaid_account):
        """Test normalizing account without currency (should default to USD)."""
        sample_plaid_account["balances"]["iso_currency_code"] = None

        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        connection_id = 1

        result = PlaidAccountNormalizer.normalize(
            sample_plaid_account,
            user_id,
            connection_id
        )

        assert result.currency == "USD"

    def test_normalize_account_missing_optional_fields(self):
        """Test normalizing account with minimal fields."""
        minimal_account = {
            "account_id": "minimal-account-id",
            "balances": {
                "current": 50.00
            },
            "name": "Minimal Account",
            "type": "other"
        }

        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        connection_id = 1

        result = PlaidAccountNormalizer.normalize(
            minimal_account,
            user_id,
            connection_id
        )

        assert result.external_account_id == "minimal-account-id"
        assert result.name == "Minimal Account"
        assert result.account_type == AccountType.OTHER
        assert result.account_subtype is None
        assert result.official_name is None
        assert result.mask is None

    def test_map_account_type(self):
        """Test account type mapping."""
        assert PlaidAccountNormalizer._map_account_type("depository") == AccountType.DEPOSITORY
        assert PlaidAccountNormalizer._map_account_type("credit") == AccountType.CREDIT
        assert PlaidAccountNormalizer._map_account_type("loan") == AccountType.LOAN
        assert PlaidAccountNormalizer._map_account_type("investment") == AccountType.INVESTMENT
        assert PlaidAccountNormalizer._map_account_type("other") == AccountType.OTHER
        assert PlaidAccountNormalizer._map_account_type("unknown") == AccountType.OTHER

    def test_map_holder_category(self):
        """Test holder category mapping."""
        assert PlaidAccountNormalizer._map_holder_category("personal") == HolderCategory.PERSONAL
        assert PlaidAccountNormalizer._map_holder_category("business") == HolderCategory.BUSINESS
        assert PlaidAccountNormalizer._map_holder_category("unknown") == HolderCategory.UNRECOGNIZED


class TestPlaidTransactionNormalizer:
    """Test suite for PlaidTransactionNormalizer."""

    @pytest.fixture
    def sample_plaid_debit_txn(self):
        """Sample Plaid debit transaction."""
        return {
            "transaction_id": "yBVBEwrXdDf9gfXP4kcKFK6FjqqmRhQ4JqYnb",
            "account_id": "vzeNDwK7KQIm4yEog683uElbp9GRLEFXGK98D",
            "amount": 25.00,  # Positive = debit
            "iso_currency_code": "USD",
            "category": ["Food and Drink", "Restaurants"],
            "category_id": "13005000",
            "date": "2025-01-14",
            "authorized_date": "2025-01-14",
            "name": "Starbucks",
            "merchant_name": "Starbucks",
            "logo_url": "https://plaid-merchant-logos.plaid.com/starbucks_619.png",
            "website": "starbucks.com",
            "payment_channel": "in store",
            "pending": False,
            "personal_finance_category": {
                "primary": "FOOD_AND_DRINK",
                "detailed": "FOOD_AND_DRINK_COFFEE",
                "confidence_level": "VERY_HIGH"
            },
            "counterparties": [],
            "location": {
                "city": "San Francisco",
                "region": "CA",
                "country": "US",
                "lat": 37.7749,
                "lon": -122.4194
            }
        }

    @pytest.fixture
    def sample_plaid_credit_txn(self):
        """Sample Plaid credit transaction."""
        return {
            "transaction_id": "credit-txn-id",
            "account_id": "account-id",
            "amount": -1000.00,  # Negative = credit
            "iso_currency_code": "USD",
            "category": ["Transfer", "Payroll"],
            "date": "2025-01-15",
            "name": "Employer Inc",
            "payment_channel": "other",
            "pending": False
        }

    def test_normalize_debit_transaction(self, sample_plaid_debit_txn):
        """Test normalizing a debit transaction."""
        account_id = 1

        result = PlaidTransactionNormalizer.normalize(
            sample_plaid_debit_txn,
            account_id
        )

        assert result.account_id == account_id
        assert result.external_txn_id == "yBVBEwrXdDf9gfXP4kcKFK6FjqqmRhQ4JqYnb"
        assert result.amount == Decimal("25.00")  # Stored as positive
        assert result.currency == "USD"
        assert result.txn_direction == TransactionDirection.DEBIT
        assert result.description_raw == "Starbucks"
        assert result.merchant_name_raw == "Starbucks"
        assert result.merchant_logo_url == "https://plaid-merchant-logos.plaid.com/starbucks_619.png"
        assert result.merchant_website == "starbucks.com"
        assert result.pending is False
        assert result.category == "Food and Drink > Restaurants"
        assert result.personal_finance_category["primary"] == "FOOD_AND_DRINK"
        assert result.personal_finance_category["detailed"] == "FOOD_AND_DRINK_COFFEE"
        assert result.payment_channel == "in store"
        assert result.location["city"] == "San Francisco"

    def test_normalize_credit_transaction(self, sample_plaid_credit_txn):
        """Test normalizing a credit transaction."""
        account_id = 2

        result = PlaidTransactionNormalizer.normalize(
            sample_plaid_credit_txn,
            account_id
        )

        assert result.amount == Decimal("1000.00")  # Stored as positive
        assert result.txn_direction == TransactionDirection.CREDIT
        assert result.description_raw == "Employer Inc"
        assert result.category == "Transfer > Payroll"

    def test_normalize_zero_amount_transaction(self):
        """Test normalizing transaction with zero amount."""
        zero_txn = {
            "transaction_id": "zero-txn-id",
            "account_id": "account-id",
            "amount": 0.00,
            "date": "2025-01-14",
            "name": "Zero Amount",
            "payment_channel": "other",
            "pending": False
        }

        account_id = 1

        # Should raise validation error because amount must be positive
        with pytest.raises(Exception):  # Pydantic will raise validation error
            PlaidTransactionNormalizer.normalize(zero_txn, account_id)

    def test_normalize_pending_transaction(self):
        """Test normalizing a pending transaction."""
        pending_txn = {
            "transaction_id": "pending-txn-id",
            "account_id": "account-id",
            "amount": 50.00,
            "date": "2025-01-14",
            "name": "Pending Purchase",
            "payment_channel": "online",
            "pending": True
        }

        account_id = 1

        result = PlaidTransactionNormalizer.normalize(pending_txn, account_id)

        assert result.pending is True

    def test_normalize_transaction_missing_optional_fields(self):
        """Test normalizing transaction with minimal fields."""
        minimal_txn = {
            "transaction_id": "minimal-txn-id",
            "account_id": "account-id",
            "amount": 10.00,
            "date": "2025-01-14",
            "name": "Minimal Transaction",
            "payment_channel": "other",
            "pending": False
        }

        account_id = 1

        result = PlaidTransactionNormalizer.normalize(minimal_txn, account_id)

        assert result.external_txn_id == "minimal-txn-id"
        assert result.description_raw == "Minimal Transaction"
        assert result.merchant_name_raw is None
        assert result.category is None
        assert result.personal_finance_category is None
        assert result.currency == "USD"  # Default

    def test_normalize_transaction_with_check_number(self):
        """Test normalizing transaction with check number."""
        check_txn = {
            "transaction_id": "check-txn-id",
            "account_id": "account-id",
            "amount": 100.00,
            "date": "2025-01-14",
            "name": "Check #1234",
            "payment_channel": "other",
            "pending": False,
            "check_number": "1234"
        }

        account_id = 1

        result = PlaidTransactionNormalizer.normalize(check_txn, account_id)

        assert result.check_number == "1234"

    def test_parse_date_valid(self):
        """Test parsing valid date string."""
        date_str = "2025-01-14"
        result = PlaidTransactionNormalizer._parse_date(date_str)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 14

    def test_parse_date_invalid(self):
        """Test parsing invalid date string."""
        date_str = "invalid-date"
        result = PlaidTransactionNormalizer._parse_date(date_str)

        assert result is None

    def test_parse_date_none(self):
        """Test parsing None date."""
        result = PlaidTransactionNormalizer._parse_date(None)

        assert result is None

    def test_parse_datetime_valid(self):
        """Test parsing valid datetime string."""
        datetime_str = "2025-01-14T14:30:00Z"
        result = PlaidTransactionNormalizer._parse_datetime(datetime_str)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 14

    def test_parse_datetime_invalid(self):
        """Test parsing invalid datetime string."""
        datetime_str = "invalid-datetime"
        result = PlaidTransactionNormalizer._parse_datetime(datetime_str)

        assert result is None

    def test_normalize_transaction_provider_metadata(self, sample_plaid_debit_txn):
        """Test that provider metadata is correctly stored."""
        account_id = 1

        result = PlaidTransactionNormalizer.normalize(
            sample_plaid_debit_txn,
            account_id
        )

        assert "plaid" in result.provider_metadata
        assert result.provider_metadata["plaid"]["category_id"] == "13005000"
        assert result.raw_payload == sample_plaid_debit_txn
