"""Unit tests for PlaidClient."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from plaid.exceptions import ApiException

from app.providers.plaid.client import PlaidClient, PlaidClientError
from app.config import settings


class TestPlaidClient:
    """Test suite for PlaidClient."""

    @pytest.fixture
    def plaid_client(self):
        """Create PlaidClient instance for testing."""
        return PlaidClient(
            client_id="test_client_id",
            secret="test_secret",
            environment="sandbox"
        )

    @pytest.fixture
    def mock_plaid_api(self):
        """Mock Plaid API client."""
        with patch('app.providers.plaid.client.plaid_api.PlaidApi') as mock:
            yield mock

    def test_client_initialization(self, plaid_client):
        """Test PlaidClient initializes correctly."""
        assert plaid_client.client_id == "test_client_id"
        assert plaid_client.secret == "test_secret"
        assert plaid_client.environment == "sandbox"
        assert plaid_client.client is not None

    def test_client_initialization_invalid_environment(self):
        """Test PlaidClient raises error for invalid environment."""
        with pytest.raises(ValueError, match="Invalid Plaid environment"):
            PlaidClient(
                client_id="test",
                secret="test",
                environment="invalid"
            )

    @pytest.mark.asyncio
    async def test_create_link_token_success(self, plaid_client):
        """Test successful link token creation."""
        # Mock response
        mock_response = Mock()
        mock_response.link_token = "link-sandbox-test-token"
        mock_response.expiration = datetime(2025, 1, 20, 14, 30, 0)
        mock_response.request_id = "test-request-id"

        # Mock the API call
        with patch.object(plaid_client.client, 'link_token_create', return_value=mock_response):
            result = await plaid_client.create_link_token(
                user_id="test-user-123",
                products=["transactions"]
            )

            assert result["link_token"] == "link-sandbox-test-token"
            assert result["request_id"] == "test-request-id"
            assert "expiration" in result

    @pytest.mark.asyncio
    async def test_create_link_token_api_error(self, plaid_client):
        """Test link token creation handles API errors."""
        # Mock API exception
        with patch.object(plaid_client.client, 'link_token_create', side_effect=ApiException("API Error")):
            with pytest.raises(PlaidClientError, match="Failed to create link token"):
                await plaid_client.create_link_token(user_id="test-user-123")

    @pytest.mark.asyncio
    async def test_exchange_public_token_success(self, plaid_client):
        """Test successful public token exchange."""
        # Mock response
        mock_response = Mock()
        mock_response.access_token = "access-sandbox-test-token"
        mock_response.item_id = "test-item-id"
        mock_response.request_id = "test-request-id"

        # Mock the API call
        with patch.object(plaid_client.client, 'item_public_token_exchange', return_value=mock_response):
            result = await plaid_client.exchange_public_token(
                public_token="public-sandbox-test-token"
            )

            assert result["access_token"] == "access-sandbox-test-token"
            assert result["item_id"] == "test-item-id"
            assert result["request_id"] == "test-request-id"

    @pytest.mark.asyncio
    async def test_exchange_public_token_api_error(self, plaid_client):
        """Test public token exchange handles API errors."""
        with patch.object(plaid_client.client, 'item_public_token_exchange', side_effect=ApiException("API Error")):
            with pytest.raises(PlaidClientError, match="Failed to exchange public token"):
                await plaid_client.exchange_public_token(public_token="invalid-token")

    @pytest.mark.asyncio
    async def test_get_accounts_success(self, plaid_client):
        """Test successful account fetch."""
        # Mock account
        mock_account = Mock()
        mock_account.to_dict.return_value = {
            "account_id": "test-account-id",
            "name": "Test Checking"
        }

        # Mock item
        mock_item = Mock()
        mock_item.to_dict.return_value = {
            "item_id": "test-item-id"
        }

        # Mock response
        mock_response = Mock()
        mock_response.accounts = [mock_account]
        mock_response.item = mock_item
        mock_response.request_id = "test-request-id"

        # Mock the API call
        with patch.object(plaid_client.client, 'accounts_get', return_value=mock_response):
            result = await plaid_client.get_accounts(access_token="test-access-token")

            assert len(result["accounts"]) == 1
            assert result["accounts"][0]["account_id"] == "test-account-id"
            assert result["item"]["item_id"] == "test-item-id"
            assert result["request_id"] == "test-request-id"

    @pytest.mark.asyncio
    async def test_sync_transactions_success(self, plaid_client):
        """Test successful transaction sync."""
        # Mock transaction
        mock_txn = Mock()
        mock_txn.to_dict.return_value = {
            "transaction_id": "test-txn-id",
            "amount": 25.00
        }

        # Mock response
        mock_response = Mock()
        mock_response.added = [mock_txn]
        mock_response.modified = []
        mock_response.removed = []
        mock_response.next_cursor = "next-cursor-token"
        mock_response.has_more = False
        mock_response.request_id = "test-request-id"

        # Mock the API call
        with patch.object(plaid_client.client, 'transactions_sync', return_value=mock_response):
            result = await plaid_client.sync_transactions(
                access_token="test-access-token",
                cursor=None
            )

            assert len(result["added"]) == 1
            assert result["added"][0]["transaction_id"] == "test-txn-id"
            assert result["next_cursor"] == "next-cursor-token"
            assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_sync_transactions_incremental(self, plaid_client):
        """Test incremental transaction sync with cursor."""
        # Mock response
        mock_response = Mock()
        mock_response.added = []
        mock_response.modified = []
        mock_response.removed = []
        mock_response.next_cursor = "new-cursor-token"
        mock_response.has_more = False
        mock_response.request_id = "test-request-id"

        # Mock the API call
        with patch.object(plaid_client.client, 'transactions_sync', return_value=mock_response):
            result = await plaid_client.sync_transactions(
                access_token="test-access-token",
                cursor="previous-cursor-token"
            )

            assert result["next_cursor"] == "new-cursor-token"

    @pytest.mark.asyncio
    async def test_get_item_success(self, plaid_client):
        """Test successful item fetch."""
        # Mock item
        mock_item = Mock()
        mock_item.to_dict.return_value = {
            "item_id": "test-item-id",
            "institution_id": "ins_123"
        }

        # Mock status
        mock_status = Mock()
        mock_status.to_dict.return_value = {}

        # Mock response
        mock_response = Mock()
        mock_response.item = mock_item
        mock_response.status = mock_status
        mock_response.request_id = "test-request-id"

        # Mock the API call
        with patch.object(plaid_client.client, 'item_get', return_value=mock_response):
            result = await plaid_client.get_item(access_token="test-access-token")

            assert result["item"]["item_id"] == "test-item-id"
            assert result["request_id"] == "test-request-id"

    @pytest.mark.asyncio
    async def test_remove_item_success(self, plaid_client):
        """Test successful item removal."""
        # Mock response
        mock_response = Mock()
        mock_response.request_id = "test-request-id"

        # Mock the API call
        with patch.object(plaid_client.client, 'item_remove', return_value=mock_response):
            result = await plaid_client.remove_item(access_token="test-access-token")

            assert result["request_id"] == "test-request-id"

    @pytest.mark.asyncio
    async def test_handle_plaid_error_item_login_required(self, plaid_client):
        """Test handling of ITEM_LOGIN_REQUIRED error."""
        error = ApiException("Login required")
        error.code = "ITEM_LOGIN_REQUIRED"

        with pytest.raises(PlaidClientError, match="Bank login credentials need to be updated"):
            plaid_client._handle_plaid_error(error)

    @pytest.mark.asyncio
    async def test_handle_plaid_error_rate_limit(self, plaid_client):
        """Test handling of RATE_LIMIT_EXCEEDED error."""
        error = ApiException("Rate limit")
        error.code = "RATE_LIMIT_EXCEEDED"

        with pytest.raises(PlaidClientError, match="Too many requests"):
            plaid_client._handle_plaid_error(error)

    def test_mask_token(self, plaid_client):
        """Test token masking for logging."""
        token = "access-sandbox-1234567890abcdef"
        masked = plaid_client._mask_token(token)

        assert masked == "access-s...cdef"
        assert "1234567890" not in masked

    def test_mask_token_short(self, plaid_client):
        """Test token masking for short tokens."""
        token = "short"
        masked = plaid_client._mask_token(token)

        assert masked == "***"

    def test_hash_user_id_no_secret(self, plaid_client):
        """Test user ID hashing when no logging secret is configured."""
        with patch.object(settings, 'LOGGING_SECRET', None):
            user_id = "user-1234567890"
            hashed = plaid_client._hash_user_id(user_id)

            # Should truncate instead of hash
            assert "user" in hashed or "..." in hashed

    def test_hash_user_id_with_secret(self, plaid_client):
        """Test user ID hashing with logging secret."""
        with patch.object(settings, 'LOGGING_SECRET', "test-secret"):
            user_id = "user-1234567890"
            hashed = plaid_client._hash_user_id(user_id)

            # Should be hashed (12 chars)
            assert len(hashed) == 12
            assert hashed != user_id
