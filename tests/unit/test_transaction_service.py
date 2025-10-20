"""Unit tests for transaction_service."""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.services.transaction_service import TransactionService
from app.models.transaction import UnifiedTransaction
from app.models.enums import TransactionDirection


@pytest.mark.asyncio
class TestTransactionService:
    """Test cases for TransactionService."""

    async def test_create_transaction(self, mock_supabase_client, sample_transaction_data):
        """Test creating a new transaction."""
        # Arrange
        mock_supabase_client.table("transactions").execute.return_value.data = [sample_transaction_data]
        transaction = UnifiedTransaction(**sample_transaction_data)

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.create_transaction(transaction)

        # Assert
        assert isinstance(result, UnifiedTransaction)
        assert result.txn_id == 1
        assert result.description_raw == "Starbucks"
        mock_supabase_client.table.assert_called_with("transactions")

    async def test_get_transaction(self, mock_supabase_client, sample_transaction_data):
        """Test fetching a transaction by ID."""
        # Arrange
        mock_supabase_client.table("transactions").execute.return_value.data = [sample_transaction_data]

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.get_transaction(1)

        # Assert
        assert isinstance(result, UnifiedTransaction)
        assert result.txn_id == 1
        assert result.txn_direction == TransactionDirection.DEBIT

    async def test_get_transaction_not_found(self, mock_supabase_client):
        """Test fetching non-existent transaction returns None."""
        # Arrange
        mock_supabase_client.table("transactions").execute.return_value.data = []

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.get_transaction(999)

        # Assert
        assert result is None

    async def test_get_transaction_by_external_id(self, mock_supabase_client, sample_transaction_data):
        """Test fetching transaction by external ID."""
        # Arrange
        mock_supabase_client.table("transactions").execute.return_value.data = [sample_transaction_data]

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.get_transaction_by_external_id("txn_123abc")

        # Assert
        assert isinstance(result, UnifiedTransaction)
        assert result.external_txn_id == "txn_123abc"

    async def test_get_account_transactions(self, mock_supabase_client, sample_transaction_data):
        """Test fetching transactions for an account."""
        # Arrange
        mock_supabase_client.table("transactions").execute.return_value.data = [
            sample_transaction_data,
            {**sample_transaction_data, "txn_id": 2}
        ]

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.get_account_transactions(1)

        # Assert
        assert len(result) == 2
        assert all(isinstance(txn, UnifiedTransaction) for txn in result)

    async def test_get_account_transactions_with_pagination(self, mock_supabase_client, sample_transaction_data):
        """Test fetching transactions with pagination."""
        # Arrange
        mock_supabase_client.table("transactions").execute.return_value.data = [sample_transaction_data]

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.get_account_transactions(
                1,
                limit=50,
                offset=10
            )

        # Assert
        mock_query_builder = mock_supabase_client.table("transactions")
        mock_query_builder.range.assert_called_once_with(10, 59)

    async def test_update_transaction(self, mock_supabase_client, sample_transaction_data):
        """Test updating a transaction."""
        # Arrange
        updated_data = {**sample_transaction_data, "amount": 30.00}
        mock_supabase_client.table("transactions").execute.return_value.data = [updated_data]

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.update_transaction(
                1,
                {"amount": 30.00}
            )

        # Assert
        assert result.amount == Decimal("30.00")

    async def test_update_transaction_by_external_id(self, mock_supabase_client, sample_transaction_data):
        """Test updating transaction by external ID."""
        # Arrange
        updated_data = {**sample_transaction_data, "pending": True}
        mock_supabase_client.table("transactions").execute.return_value.data = [updated_data]

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.update_transaction_by_external_id(
                "txn_123abc",
                {"pending": True}
            )

        # Assert
        assert result.pending is True

    async def test_upsert_transaction_creates_new(self, mock_supabase_client, sample_transaction_data):
        """Test upsert creates transaction when it doesn't exist."""
        # Arrange
        transaction = UnifiedTransaction(**sample_transaction_data)

        # Mock: transaction doesn't exist
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            with patch.object(
                TransactionService,
                "get_transaction_by_external_id",
                return_value=None
            ):
                mock_supabase_client.table("transactions").execute.return_value.data = [sample_transaction_data]

                # Act
                result = await TransactionService.upsert_transaction(transaction)

                # Assert
                assert isinstance(result, UnifiedTransaction)
                assert result.external_txn_id == "txn_123abc"

    async def test_upsert_transaction_updates_existing(self, mock_supabase_client, sample_transaction_data):
        """Test upsert updates transaction when it exists."""
        # Arrange
        transaction = UnifiedTransaction(**{**sample_transaction_data, "amount": 35.00})
        existing_transaction = UnifiedTransaction(**sample_transaction_data)
        updated_data = {**sample_transaction_data, "amount": 35.00}

        # Mock: transaction exists
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            with patch.object(
                TransactionService,
                "get_transaction_by_external_id",
                return_value=existing_transaction
            ):
                mock_supabase_client.table("transactions").execute.return_value.data = [updated_data]

                # Act
                result = await TransactionService.upsert_transaction(transaction)

                # Assert
                assert result.amount == Decimal("35.00")

    async def test_upsert_transactions_bulk(self, mock_supabase_client, sample_transaction_data):
        """Test bulk upsert of transactions using native bulk upsert."""
        # Arrange
        txn_data_1 = sample_transaction_data.copy()
        txn_data_2 = {**sample_transaction_data, "external_txn_id": "txn_456def", "txn_id": 2}

        transactions = [
            UnifiedTransaction(**txn_data_1),
            UnifiedTransaction(**txn_data_2)
        ]

        # Mock the bulk upsert response
        mock_supabase_client.table("transactions").execute.return_value.data = [
            txn_data_1,
            txn_data_2
        ]

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.upsert_transactions(transactions)

        # Assert
        assert len(result) == 2
        assert isinstance(result[0], UnifiedTransaction)
        assert isinstance(result[1], UnifiedTransaction)
        assert result[0].external_txn_id == "txn_123abc"
        assert result[1].external_txn_id == "txn_456def"

        # Verify upsert was called with a list of transaction dicts
        mock_supabase_client.table.assert_called_with("transactions")

    async def test_delete_transaction(self, mock_supabase_client):
        """Test deleting a transaction."""
        # Arrange
        mock_supabase_client.table("transactions").execute.return_value = MagicMock()

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.delete_transaction(1)

        # Assert
        assert result is True
        mock_supabase_client.table("transactions").delete.assert_called_once()

    async def test_delete_transaction_by_external_id(self, mock_supabase_client):
        """Test deleting transaction by external ID."""
        # Arrange
        mock_supabase_client.table("transactions").execute.return_value = MagicMock()

        # Act
        with patch("app.services.transaction_service.get_db", return_value=mock_supabase_client):
            result = await TransactionService.delete_transaction_by_external_id("txn_123abc")

        # Assert
        assert result is True
        mock_supabase_client.table("transactions").delete.assert_called_once()
