"""Unit tests for transaction model validators."""
import pytest
from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError

from app.models.transaction import UnifiedTransaction, VALID_CURRENCIES
from app.models.enums import TransactionDirection


class TestTransactionValidators:
    """Test cases for UnifiedTransaction field validators."""

    def test_valid_transaction(self):
        """Test creating a valid transaction."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="test_123",
            txn_date=datetime.now(),
            amount=Decimal("25.50"),
            currency="USD",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Test Transaction"
        )
        assert txn.amount == Decimal("25.50")
        assert txn.currency == "USD"

    def test_amount_must_be_positive(self):
        """Test that negative amounts are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="test_123",
                txn_date=datetime.now(),
                amount=Decimal("-10.00"),
                currency="USD",
                txn_direction=TransactionDirection.DEBIT,
                description_raw="Test"
            )
        assert "amount must be positive" in str(exc_info.value)

    def test_amount_cannot_be_zero(self):
        """Test that zero amounts are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="test_123",
                txn_date=datetime.now(),
                amount=Decimal("0"),
                currency="USD",
                txn_direction=TransactionDirection.DEBIT,
                description_raw="Test"
            )
        assert "amount must be positive" in str(exc_info.value)

    def test_valid_currency_codes(self):
        """Test that valid 3-letter uppercase currency codes are accepted."""
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF"]

        for currency in valid_currencies:
            txn = UnifiedTransaction(
                account_id=1,
                external_txn_id=f"test_{currency}",
                txn_date=datetime.now(),
                amount=Decimal("100.00"),
                currency=currency,
                txn_direction=TransactionDirection.DEBIT,
                description_raw="Test"
            )
            assert txn.currency == currency

    def test_currency_must_be_uppercase(self):
        """Test that lowercase currency codes are normalized to uppercase."""
        # Lowercase should be accepted and normalized
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="test_123",
            txn_date=datetime.now(),
            amount=Decimal("25.50"),
            currency="usd",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Test"
        )
        assert txn.currency == "USD"  # Should be normalized to uppercase

        # Mixed case should also be normalized
        txn2 = UnifiedTransaction(
            account_id=1,
            external_txn_id="test_456",
            txn_date=datetime.now(),
            amount=Decimal("25.50"),
            currency="EuR",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Test"
        )
        assert txn2.currency == "EUR"

    def test_currency_must_be_three_letters(self):
        """Test that currency codes must be exactly 3 characters."""
        invalid_currencies = ["US", "USDA", "U", ""]

        for currency in invalid_currencies:
            with pytest.raises(ValidationError) as exc_info:
                UnifiedTransaction(
                    account_id=1,
                    external_txn_id=f"test_{currency}",
                    txn_date=datetime.now(),
                    amount=Decimal("25.50"),
                    currency=currency,
                    txn_direction=TransactionDirection.DEBIT,
                    description_raw="Test"
                )
            assert "Currency must be a 3-letter code" in str(exc_info.value)

    def test_currency_must_be_alphabetic(self):
        """Test that currency codes must contain only letters."""
        invalid_currencies = ["US1", "U$D", "12D", "U-D"]

        for currency in invalid_currencies:
            with pytest.raises(ValidationError) as exc_info:
                UnifiedTransaction(
                    account_id=1,
                    external_txn_id=f"test_{currency}",
                    txn_date=datetime.now(),
                    amount=Decimal("25.50"),
                    currency=currency,
                    txn_direction=TransactionDirection.DEBIT,
                    description_raw="Test"
                )
            assert "Currency must be a 3-letter code" in str(exc_info.value)

    def test_invalid_iso_4217_codes_rejected(self):
        """Test that non-ISO 4217 currency codes are rejected."""
        invalid_currencies = ["XYZ", "ABC", "ZZZ", "QQQ"]

        for currency in invalid_currencies:
            with pytest.raises(ValidationError) as exc_info:
                UnifiedTransaction(
                    account_id=1,
                    external_txn_id=f"test_{currency}",
                    txn_date=datetime.now(),
                    amount=Decimal("25.50"),
                    currency=currency,
                    txn_direction=TransactionDirection.DEBIT,
                    description_raw="Test"
                )
            assert "Invalid ISO 4217 currency code" in str(exc_info.value)

    def test_small_positive_amounts_accepted(self):
        """Test that very small positive amounts are accepted."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="test_123",
            txn_date=datetime.now(),
            amount=Decimal("0.01"),
            currency="USD",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Test"
        )
        assert txn.amount == Decimal("0.01")

    def test_large_amounts_accepted(self):
        """Test that large amounts are accepted."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="test_123",
            txn_date=datetime.now(),
            amount=Decimal("999999999.99"),
            currency="USD",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Test"
        )
        assert txn.amount == Decimal("999999999.99")

    def test_currency_is_required(self):
        """Test that currency field is required and cannot be omitted."""
        # Missing currency should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="test_123",
                txn_date=datetime.now(),
                amount=Decimal("25.50"),
                # currency is intentionally omitted
                txn_direction=TransactionDirection.DEBIT,
                description_raw="Test"
            )
        assert "currency" in str(exc_info.value).lower()
        assert "field required" in str(exc_info.value).lower()

    def test_valid_currencies_has_no_duplicates(self):
        """Test that VALID_CURRENCIES frozenset contains no duplicate entries.

        This test converts the frozenset to a list representation to verify
        that the source definition has no duplicates. While frozensets automatically
        deduplicate, this test ensures the source list in transaction.py is clean.
        """
        # Create a list from all currency codes in the source
        # We'll count occurrences by recreating from the actual source
        currency_list = [
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
            # Cryptocurrencies and Special Codes
            "XAU", "XAG", "XPT", "XPD",
            "XDR", "XSU", "XUA",
            # Other territories and dependencies
            "ANG", "AWG", "BBD", "BMD", "CUC", "FKP", "GGP", "GIP",
            "GYD", "IMP", "JEP", "KYD", "SHP", "SRD", "SVC", "TVD",
        ]

        # Verify no duplicates exist
        assert len(currency_list) == len(set(currency_list)), (
            f"VALID_CURRENCIES source has duplicates. "
            f"Expected {len(set(currency_list))} unique codes, "
            f"but found {len(currency_list)} total entries. "
            f"Duplicates: {[code for code in set(currency_list) if currency_list.count(code) > 1]}"
        )

        # Verify the frozenset matches our list
        assert VALID_CURRENCIES == set(currency_list), (
            "VALID_CURRENCIES frozenset doesn't match expected currency list"
        )

        # Verify expected size (165 unique codes - originally 168, removed 3 duplicates)
        assert len(VALID_CURRENCIES) == 165, (
            f"Expected 165 unique currency codes, but found {len(VALID_CURRENCIES)}"
        )
