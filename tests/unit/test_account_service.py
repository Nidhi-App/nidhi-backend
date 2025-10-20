"""Unit tests for account_service."""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.services.account_service import AccountService
from app.models.account import UnifiedAccount
from app.models.enums import AccountType, AccountSubtype, AccountStatus


@pytest.mark.asyncio
class TestAccountService:
    """Test cases for AccountService."""

    async def test_create_account(self, mock_supabase_client, sample_user_id, sample_account_data):
        """Test creating a new account."""
        # Arrange
        mock_supabase_client.table("accounts").execute.return_value.data = [sample_account_data]
        account = UnifiedAccount(**sample_account_data)

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.create_account(account)

        # Assert
        assert isinstance(result, UnifiedAccount)
        assert result.account_id == 1
        assert result.name == "Chase Checking"
        mock_supabase_client.table.assert_called_with("accounts")

    async def test_get_account(self, mock_supabase_client, sample_account_data):
        """Test fetching an account by ID."""
        # Arrange
        mock_supabase_client.table("accounts").execute.return_value.data = [sample_account_data]

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.get_account(1)

        # Assert
        assert isinstance(result, UnifiedAccount)
        assert result.account_id == 1
        assert result.account_type == AccountType.DEPOSITORY

    async def test_get_account_not_found(self, mock_supabase_client):
        """Test fetching non-existent account returns None."""
        # Arrange
        mock_supabase_client.table("accounts").execute.return_value.data = []

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.get_account(999)

        # Assert
        assert result is None

    async def test_get_user_accounts(self, mock_supabase_client, sample_user_id, sample_account_data):
        """Test fetching all accounts for a user."""
        # Arrange
        mock_supabase_client.table("accounts").execute.return_value.data = [
            sample_account_data,
            {**sample_account_data, "account_id": 2, "name": "Chase Savings"}
        ]

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.get_user_accounts(sample_user_id)

        # Assert
        assert len(result) == 2
        assert all(isinstance(acc, UnifiedAccount) for acc in result)

    async def test_get_accounts_by_connection(self, mock_supabase_client, sample_account_data):
        """Test fetching accounts for a connection."""
        # Arrange
        mock_supabase_client.table("accounts").execute.return_value.data = [sample_account_data]

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.get_accounts_by_connection(1)

        # Assert
        assert len(result) == 1
        assert result[0].connection_id == 1

    async def test_update_account(self, mock_supabase_client, sample_account_data):
        """Test updating an account."""
        # Arrange
        updated_data = {**sample_account_data, "current_balance": 2000.00}
        mock_supabase_client.table("accounts").execute.return_value.data = [updated_data]

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.update_account(
                1,
                {"current_balance": 2000.00}
            )

        # Assert
        assert result.current_balance == Decimal("2000.00")

    async def test_update_account_balance(self, mock_supabase_client, sample_account_data):
        """Test updating account balances."""
        # Arrange
        updated_data = {
            **sample_account_data,
            "current_balance": 1800.00,
            "available_balance": 1700.00
        }
        mock_supabase_client.table("accounts").execute.return_value.data = [updated_data]

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.update_account_balance(
                1,
                current_balance=1800.00,
                available_balance=1700.00
            )

        # Assert
        assert result.current_balance == Decimal("1800.00")
        assert result.available_balance == Decimal("1700.00")

    async def test_upsert_account_creates_new(self, mock_supabase_client, sample_user_id, sample_account_data):
        """Test upsert creates account when it doesn't exist."""
        # Arrange
        account = UnifiedAccount(**sample_account_data)

        # Mock SELECT operation (returns empty - account doesn't exist)
        select_result = MagicMock()
        select_result.data = []

        # Mock INSERT operation (returns new account)
        insert_result = MagicMock()
        insert_result.data = [sample_account_data]

        # Create table mock that supports both select and insert operations
        table_mock = MagicMock()

        # Configure select chain
        select_eq_chain = MagicMock()
        select_eq_chain.execute.return_value = select_result
        select_chain = MagicMock()
        select_chain.eq.return_value = select_eq_chain
        table_mock.select.return_value = select_chain

        # Configure insert chain
        insert_chain = MagicMock()
        insert_chain.execute.return_value = insert_result
        table_mock.insert.return_value = insert_chain

        # Mock table() to return the table_mock
        mock_supabase_client.table.return_value = table_mock

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.upsert_account(account)

        # Assert
        assert isinstance(result, UnifiedAccount)
        assert result.external_account_id == "acc_123abc"
        # Verify insert was called (not update)
        table_mock.insert.assert_called_once()
        # Verify update was NOT called
        if hasattr(table_mock, 'update'):
            assert not table_mock.update.called

    async def test_upsert_account_updates_existing(self, mock_supabase_client, sample_account_data):
        """Test upsert updates account when it exists."""
        # Arrange
        account = UnifiedAccount(**{**sample_account_data, "current_balance": 2500.00})
        updated_data = {**sample_account_data, "current_balance": 2500.00}

        # Mock SELECT operation (returns existing account)
        select_result = MagicMock()
        select_result.data = [{"account_id": 1}]

        # Mock UPDATE operation (returns updated account)
        update_result = MagicMock()
        update_result.data = [updated_data]

        # Create table mock that supports both select and update operations
        table_mock = MagicMock()

        # Configure select chain
        select_eq_chain = MagicMock()
        select_eq_chain.execute.return_value = select_result
        select_chain = MagicMock()
        select_chain.eq.return_value = select_eq_chain
        table_mock.select.return_value = select_chain

        # Configure update chain
        update_eq_chain = MagicMock()
        update_eq_chain.execute.return_value = update_result
        update_chain = MagicMock()
        update_chain.eq.return_value = update_eq_chain
        table_mock.update.return_value = update_chain

        # Mock table() to return the table_mock
        mock_supabase_client.table.return_value = table_mock

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.upsert_account(account)

        # Assert
        assert result.current_balance == Decimal("2500.00")
        # Verify update was called (not insert)
        table_mock.update.assert_called_once()
        # Verify insert was NOT called
        if hasattr(table_mock, 'insert'):
            assert not table_mock.insert.called

        # Verify immutable fields were NOT in the update payload
        update_call_args = table_mock.update.call_args
        update_payload = update_call_args[0][0]
        assert "user_id" not in update_payload
        assert "connection_id" not in update_payload
        assert "external_account_id" not in update_payload
        assert "created_at" not in update_payload

    async def test_upsert_accounts_bulk(self, mock_supabase_client, sample_user_id, sample_account_data):
        """Test bulk upsert of accounts."""
        # Arrange
        accounts = [
            UnifiedAccount(**sample_account_data),
            UnifiedAccount(**{**sample_account_data, "external_account_id": "acc_456def"})
        ]

        # Mock upsert_account for each call
        with patch.object(
            AccountService,
            "upsert_account",
            side_effect=[accounts[0], accounts[1]]
        ):
            # Act
            result = await AccountService.upsert_accounts(accounts)

            # Assert
            assert len(result) == 2

    async def test_delete_account(self, mock_supabase_client):
        """Test deleting an account."""
        # Arrange
        mock_supabase_client.table("accounts").execute.return_value = MagicMock()

        # Act
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            result = await AccountService.delete_account(1)

        # Assert
        assert result is True
        mock_supabase_client.table("accounts").delete.assert_called_once()
