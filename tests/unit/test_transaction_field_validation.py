"""Tests for transaction model field validation."""

import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError

from app.models.transaction import UnifiedTransaction
from app.models.enums import TransactionDirection


class TestTransactionRequiredFieldValidation:
    """Test suite for non-empty validation of required transaction fields."""

    def test_valid_transaction_accepted(self):
        """Test that a valid transaction is accepted."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="txn_123abc",
            txn_date=datetime(2025, 1, 15),
            amount=Decimal("25.00"),
            currency="USD",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Starbucks Coffee"
        )

        assert txn.external_txn_id == "txn_123abc"
        assert txn.description_raw == "Starbucks Coffee"

    def test_external_txn_id_strips_whitespace(self):
        """Test that external_txn_id strips leading/trailing whitespace."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="  txn_123abc  ",  # Whitespace around ID
            txn_date=datetime(2025, 1, 15),
            amount=Decimal("25.00"),
            currency="USD",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Test"
        )

        # Should be stripped
        assert txn.external_txn_id == "txn_123abc"

    def test_description_raw_strips_whitespace(self):
        """Test that description_raw strips leading/trailing whitespace."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="txn_123",
            txn_date=datetime(2025, 1, 15),
            amount=Decimal("25.00"),
            currency="USD",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="  Starbucks Coffee  "  # Whitespace around description
        )

        # Should be stripped
        assert txn.description_raw == "Starbucks Coffee"

    def test_external_txn_id_empty_string_rejected(self):
        """Test that empty external_txn_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="",  # Empty string
                txn_date=datetime(2025, 1, 15),
                amount=Decimal("25.00"),
                currency="USD",
                txn_direction=TransactionDirection.DEBIT,
                description_raw="Test"
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        # Check for either min_length constraint or custom validator error
        error_msg = str(errors[0])
        assert "external_txn_id" in error_msg.lower()

    def test_external_txn_id_whitespace_only_rejected(self):
        """Test that whitespace-only external_txn_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="   ",  # Only whitespace
                txn_date=datetime(2025, 1, 15),
                amount=Decimal("25.00"),
                currency="USD",
                txn_direction=TransactionDirection.DEBIT,
                description_raw="Test"
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        error = errors[0]
        # Should fail custom validator with helpful message
        assert "external_txn_id cannot be empty" in str(error)

    def test_description_raw_empty_string_rejected(self):
        """Test that empty description_raw is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="txn_123",
                txn_date=datetime(2025, 1, 15),
                amount=Decimal("25.00"),
                currency="USD",
                txn_direction=TransactionDirection.DEBIT,
                description_raw=""  # Empty string
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        error_msg = str(errors[0])
        assert "description_raw" in error_msg.lower()

    def test_description_raw_whitespace_only_rejected(self):
        """Test that whitespace-only description_raw is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="txn_123",
                txn_date=datetime(2025, 1, 15),
                amount=Decimal("25.00"),
                currency="USD",
                txn_direction=TransactionDirection.DEBIT,
                description_raw="   "  # Only whitespace
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        error = errors[0]
        # Should fail custom validator with helpful message
        assert "description_raw cannot be empty" in str(error)

    def test_validation_error_messages_are_helpful(self):
        """Test that validation error messages provide clear guidance."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="  ",
                txn_date=datetime(2025, 1, 15),
                amount=Decimal("25.00"),
                currency="USD",
                txn_direction=TransactionDirection.DEBIT,
                description_raw="Valid description"
            )

        errors = exc_info.value.errors()
        error = errors[0]
        error_msg = str(error['msg'])

        # Check error message is helpful
        assert "data integrity" in error_msg.lower() or "cannot be empty" in error_msg.lower()

    def test_description_validation_error_message_is_helpful(self):
        """Test that description validation error message is helpful."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedTransaction(
                account_id=1,
                external_txn_id="txn_123",
                txn_date=datetime(2025, 1, 15),
                amount=Decimal("25.00"),
                currency="USD",
                txn_direction=TransactionDirection.DEBIT,
                description_raw="  "
            )

        errors = exc_info.value.errors()
        error = errors[0]
        error_msg = str(error['msg'])

        # Check error message is helpful
        assert "user display" in error_msg.lower() or "categorization" in error_msg.lower()

    def test_valid_transaction_with_minimal_fields(self):
        """Test that transaction with only required fields is valid."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="minimal_txn_id",
            txn_date=datetime(2025, 1, 15),
            amount=Decimal("10.00"),
            currency="USD",
            txn_direction=TransactionDirection.CREDIT,
            description_raw="Minimal transaction"
        )

        assert txn.external_txn_id == "minimal_txn_id"
        assert txn.description_raw == "Minimal transaction"
        assert txn.merchant_name_raw is None  # Optional field

    def test_single_character_values_accepted(self):
        """Test that single-character values are accepted (min_length=1)."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="x",  # Single character
            txn_date=datetime(2025, 1, 15),
            amount=Decimal("1.00"),
            currency="USD",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Y"  # Single character
        )

        assert txn.external_txn_id == "x"
        assert txn.description_raw == "Y"

    def test_special_characters_in_fields_accepted(self):
        """Test that special characters in transaction fields are accepted."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="txn-123_abc.xyz",  # With special chars
            txn_date=datetime(2025, 1, 15),
            amount=Decimal("25.00"),
            currency="USD",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Coffee @ Starbucks #1234"  # With special chars
        )

        assert txn.external_txn_id == "txn-123_abc.xyz"
        assert txn.description_raw == "Coffee @ Starbucks #1234"

    def test_unicode_characters_in_description_accepted(self):
        """Test that unicode characters in description are accepted."""
        txn = UnifiedTransaction(
            account_id=1,
            external_txn_id="txn_123",
            txn_date=datetime(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="EUR",
            txn_direction=TransactionDirection.DEBIT,
            description_raw="Café Français € 50"  # Unicode characters
        )

        assert txn.description_raw == "Café Français € 50"
