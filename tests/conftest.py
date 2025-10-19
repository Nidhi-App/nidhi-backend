"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import Mock
from uuid import UUID
from datetime import datetime, timezone

from app.core.database import Database


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    client = Mock()

    # Mock table method that returns a query builder
    def mock_table(table_name):
        query_builder = Mock()
        query_builder.select = Mock(return_value=query_builder)
        query_builder.insert = Mock(return_value=query_builder)
        query_builder.update = Mock(return_value=query_builder)
        query_builder.delete = Mock(return_value=query_builder)
        query_builder.eq = Mock(return_value=query_builder)
        query_builder.order = Mock(return_value=query_builder)
        query_builder.range = Mock(return_value=query_builder)

        # Mock execute to return a result object immediately (not async)
        execute_result = Mock()
        execute_result.data = []
        query_builder.execute = Mock(return_value=execute_result)

        return query_builder

    client.table = mock_table
    return client


@pytest.fixture(autouse=True)
def reset_database_client():
    """Reset database client before each test."""
    Database.reset_client()
    yield
    Database.reset_client()


@pytest.fixture
def sample_user_id():
    """Sample UUID for testing."""
    return UUID("123e4567-e89b-12d3-a456-426614174000")


@pytest.fixture
def sample_connection_data(sample_user_id):
    """Sample connection data for testing.

    NOTE: This fixture intentionally excludes access_token and link_token
    because they should be excluded from API responses and database queries
    should not select them (they're marked with exclude=True).
    """
    return {
        "connection_id": 1,
        "user_id": str(sample_user_id),
        "provider_id": 8,
        "external_item_id": "item_123abc",
        # access_token and link_token intentionally excluded
        "connection_status": "Active",
        "institution_id": "ins_3",
        "institution_name": "Chase",
        "products": ["transactions", "auth"],
        "available_products": ["balance", "identity"],
        "artifact": {"transactions_cursor": "cursor_abc"},
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_account_data(sample_user_id):
    """Sample account data for testing."""
    return {
        "account_id": 1,
        "user_id": str(sample_user_id),
        "connection_id": 1,
        "external_account_id": "acc_123abc",
        "name": "Chase Checking",
        "official_name": "Chase Premier Plus Checking",
        "account_type": "depository",
        "account_subtype": "checking",
        "currency": "USD",
        "mask": "0000",
        "current_balance": 1500.50,
        "available_balance": 1500.50,
        "credit_limit": None,
        "institution_name": "Chase",
        "verification_status": "automatically_verified",
        "holder_category": "personal",
        "provider_metadata": {"persistent_account_id": "persistent_123"},
        "account_status": "Active",
        "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return {
        "txn_id": 1,
        "account_id": 1,
        "external_txn_id": "txn_123abc",
        "txn_date": datetime.now(timezone.utc).isoformat(),
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "authorized_date": datetime.now(timezone.utc).isoformat(),
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
            "detailed": "FOOD_AND_DRINK_COFFEE"
        },
        "payment_channel": "in store",
        "counterparties": [],
        "location": None,
        "check_number": None,
        "running_balance": None,
        "provider_metadata": {},
        "raw_payload": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
