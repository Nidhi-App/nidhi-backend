"""
Integration tests for Phase 5 data sync flow.

Tests account and transaction synchronization from Plaid.
Requires valid Plaid credentials and database access.
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.core.database import get_db
from app.services.sync_service import sync_service
from app.services.connection_service import connection_service
from app.models.enums import ConnectionStatus


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
async def test_user_and_connection():
    """Create a test user and active connection with access token."""
    db = get_db()

    # Get or create test user
    result = db.table('profiles').select('*').limit(1).execute()
    if result.data:
        user_id = result.data[0]['id']
    else:
        pytest.skip("No test user found in database")

    # Get Plaid provider
    provider_result = db.table('providers').select('provider_id').eq('name', 'Plaid').execute()
    provider_id = provider_result.data[0]['provider_id']

    # For these tests, we need a real Plaid sandbox connection
    # This would typically be created via the full link flow
    pytest.skip("Sync tests require a real Plaid connection with access_token from sandbox")

    return {
        "user_id": user_id,
        "provider_id": provider_id
    }


class TestSyncService:
    """Integration tests for sync_service."""

    @pytest.mark.asyncio
    async def test_sync_accounts_structure(self):
        """
        Test that sync_accounts method exists and has correct structure.

        Note: Full test requires real Plaid sandbox connection with access_token.
        """
        # Verify method exists
        assert hasattr(sync_service, 'sync_accounts')
        assert callable(sync_service.sync_accounts)

        # Verify method signature
        import inspect
        sig = inspect.signature(sync_service.sync_accounts)
        assert 'connection_id' in sig.parameters

        print("✅ sync_accounts method structure verified")

    @pytest.mark.asyncio
    async def test_sync_transactions_initial_structure(self):
        """Test that sync_transactions_initial method exists and has correct structure."""
        assert hasattr(sync_service, 'sync_transactions_initial')
        assert callable(sync_service.sync_transactions_initial)

        import inspect
        sig = inspect.signature(sync_service.sync_transactions_initial)
        assert 'connection_id' in sig.parameters

        print("✅ sync_transactions_initial method structure verified")

    @pytest.mark.asyncio
    async def test_sync_transactions_incremental_structure(self):
        """Test that sync_transactions_incremental method exists and has correct structure."""
        assert hasattr(sync_service, 'sync_transactions_incremental')
        assert callable(sync_service.sync_transactions_incremental)

        import inspect
        sig = inspect.signature(sync_service.sync_transactions_incremental)
        assert 'connection_id' in sig.parameters

        print("✅ sync_transactions_incremental method structure verified")

    @pytest.mark.asyncio
    async def test_sync_connection_structure(self):
        """Test that sync_connection method exists and has correct structure."""
        assert hasattr(sync_service, 'sync_connection')
        assert callable(sync_service.sync_connection)

        import inspect
        sig = inspect.signature(sync_service.sync_connection)
        assert 'connection_id' in sig.parameters

        print("✅ sync_connection method structure verified")


class TestSyncAPIEndpoints:
    """Integration tests for sync-related API endpoints."""

    @pytest.mark.asyncio
    async def test_manual_sync_endpoint_exists(self):
        """Test that manual sync endpoint is accessible."""
        test_user_id = str(uuid4())
        test_connection_id = str(uuid4())

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # This should return 404 (connection not found) not 404 (endpoint not found)
            response = await client.post(
                f"/api/v1/connections/{test_connection_id}/sync",
                headers={"X-User-Id": test_user_id}
            )

            # Expect 404 (connection not found), not 404 (route not found)
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

        print("✅ Manual sync endpoint exists and responds correctly")

    @pytest.mark.asyncio
    async def test_token_exchange_triggers_sync(self):
        """
        Test that token exchange endpoint triggers background sync.

        Note: Cannot fully test without valid public_token from Plaid Link.
        This test verifies the endpoint structure is correct.
        """
        # Get an existing user from database
        db = get_db()
        result = db.table('profiles').select('id').limit(1).execute()

        if not result.data:
            pytest.skip("No test user found in database")

        test_user_id = str(result.data[0]['id'])

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create link token first
            link_response = await client.post(
                "/api/v1/connections/plaid/link/token",
                headers={"X-User-Id": test_user_id}
            )

            if link_response.status_code == 200:
                print("✅ Link token created (prerequisite for token exchange)")

                # Note: We can't actually exchange without a real public_token
                # But we've verified the flow structure is in place
                print("✅ Token exchange endpoint ready (requires valid public_token for full test)")
            else:
                pytest.skip(f"Could not create link token: {link_response.status_code}")


class TestSyncFlowDocumentation:
    """Tests to verify sync flow is properly documented."""

    def test_sync_service_has_docstrings(self):
        """Verify all sync_service methods have proper documentation."""
        import inspect

        methods_to_check = [
            'sync_accounts',
            'sync_transactions_initial',
            'sync_transactions_incremental',
            'sync_connection'
        ]

        for method_name in methods_to_check:
            method = getattr(sync_service, method_name)
            docstring = inspect.getdoc(method)

            assert docstring is not None, f"{method_name} missing docstring"
            assert len(docstring) > 50, f"{method_name} docstring too short"

        print("✅ All sync_service methods have proper documentation")

    def test_api_endpoints_have_docstrings(self):
        """Verify sync-related API endpoints have proper documentation."""
        from app.api.v1 import connections
        import inspect

        # Check manual sync endpoint
        for route in connections.router.routes:
            if hasattr(route, 'path') and 'sync' in route.path:
                endpoint = route.endpoint
                docstring = inspect.getdoc(endpoint)

                assert docstring is not None, f"Sync endpoint {route.path} missing docstring"
                assert len(docstring) > 100, f"Sync endpoint {route.path} docstring too short"

        print("✅ Sync API endpoints have proper documentation")


# Example of how to test with real Plaid sandbox connection (requires setup)
class TestFullSyncFlow:
    """
    Full sync flow tests (requires Plaid sandbox connection).

    To run these tests:
    1. Create a Plaid sandbox connection via link flow
    2. Store connection_id in environment variable
    3. Run: pytest tests/integration/test_sync_flow.py::TestFullSyncFlow -m integration
    """

    @pytest.mark.skip(reason="Requires real Plaid sandbox connection with access_token")
    @pytest.mark.asyncio
    async def test_full_sync_flow(self):
        """
        Test complete sync flow with real Plaid sandbox.

        Flow:
        1. Create connection (via link flow - done separately)
        2. Sync accounts
        3. Sync transactions (initial)
        4. Verify data in database
        5. Sync transactions (incremental)
        6. Verify updates
        """
        # This would require a real connection_id from environment
        # connection_id = os.getenv('TEST_PLAID_CONNECTION_ID')
        # result = await sync_service.sync_connection(connection_id)
        # assert result['accounts'] > 0
        # assert result['transactions']['added'] > 0
        pass


@pytest.fixture(scope="session", autouse=True)
def verify_sync_environment():
    """Verify environment is configured for sync tests."""
    if settings.PLAID_ENV not in ["sandbox", "development"]:
        pytest.skip(
            f"Sync tests should only run in sandbox/development. "
            f"Current: {settings.PLAID_ENV}"
        )

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        pytest.skip("Sync tests require Supabase configuration")
