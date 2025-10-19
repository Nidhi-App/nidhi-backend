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

        # Mock: account doesn't exist
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            with patch.object(
                AccountService,
                "get_account_by_external_id",
                return_value=None
            ):
                mock_supabase_client.table("accounts").execute.return_value.data = [sample_account_data]

                # Act
                result = await AccountService.upsert_account(account)

                # Assert
                assert isinstance(result, UnifiedAccount)
                assert result.external_account_id == "acc_123abc"

    async def test_upsert_account_updates_existing(self, mock_supabase_client, sample_account_data):
        """Test upsert updates account when it exists."""
        # Arrange
        account = UnifiedAccount(**{**sample_account_data, "current_balance": 2500.00})
        existing_account = UnifiedAccount(**sample_account_data)
        updated_data = {**sample_account_data, "current_balance": 2500.00}

        # Mock: account exists
        with patch("app.services.account_service.get_db", return_value=mock_supabase_client):
            with patch.object(
                AccountService,
                "get_account_by_external_id",
                return_value=existing_account
            ):
                mock_supabase_client.table("accounts").execute.return_value.data = [updated_data]

                # Act
                result = await AccountService.upsert_account(account)

                # Assert
                assert result.current_balance == Decimal("2500.00")

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
