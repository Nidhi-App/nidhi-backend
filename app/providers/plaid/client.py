"""
Plaid API client wrapper.

This module provides a wrapper around the Plaid Python SDK for interacting
with the Plaid API. It handles authentication, error handling, and provides
typed methods for all Plaid API operations needed for the integration.
"""

import asyncio
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.exceptions import ApiException

from typing import Optional, List, Dict, Any
from app.config import settings
from app.utils.logger import logger
from app.utils.retry import retry_plaid_api


class PlaidClientError(Exception):
    """Base exception for Plaid client errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, plaid_error: Optional[Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.plaid_error = plaid_error


class PlaidClient:
    """
    Plaid API client wrapper.

    Provides methods for interacting with Plaid API including:
    - Link token management
    - Public token exchange
    - Account fetching
    - Transaction syncing
    - Item management
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        secret: Optional[str] = None,
        environment: Optional[str] = None
    ):
        """
        Initialize Plaid client.

        Args:
            client_id: Plaid client ID (defaults to settings.PLAID_CLIENT_ID)
            secret: Plaid secret (defaults to settings.PLAID_SECRET)
            environment: Plaid environment - sandbox, development, production
                        (defaults to settings.PLAID_ENV)
        """
        self.client_id = client_id or settings.PLAID_CLIENT_ID
        self.secret = secret or settings.PLAID_SECRET
        self.environment = environment or settings.PLAID_ENV

        # Map environment string to Plaid Environment enum
        env_map = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Sandbox,  # Use Sandbox for development
            "production": plaid.Environment.Production
        }

        if self.environment not in env_map:
            raise ValueError(
                f"Invalid Plaid environment: {self.environment}. "
                f"Must be one of: {list(env_map.keys())}"
            )

        # Initialize Plaid configuration
        configuration = plaid.Configuration(
            host=env_map[self.environment],
            api_key={
                'clientId': self.client_id,
                'secret': self.secret,
            }
        )

        # Create API client
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

        logger.info(f"Plaid client initialized with environment: {self.environment}")

    async def create_link_token(
        self,
        user_id: str,
        products: List[str] = None,
        redirect_uri: Optional[str] = None,
        webhook_url: Optional[str] = None,
        country_codes: Optional[List[str]] = None,
        language: str = "en",
        client_name: str = "Nidhi Expense App"
    ) -> Dict[str, Any]:
        """
        Create a link token for Plaid Link.

        The link token is used to initialize Plaid Link on the frontend.
        It's a short-lived token that expires after 4 hours.

        Args:
            user_id: Unique user identifier
            products: List of Plaid products to enable (e.g., ['transactions'])
            redirect_uri: OAuth redirect URI for OAuth institutions
            webhook_url: Webhook URL for receiving Plaid events
            country_codes: List of country codes (defaults to ['US'])
            language: Language for Plaid Link (defaults to 'en')
            client_name: Name displayed in Plaid Link (defaults to 'Nidhi Expense App')

        Returns:
            dict: Response containing link_token, expiration, and request_id
                {
                    "link_token": "link-sandbox-xxx...",
                    "expiration": "2025-01-20T14:30:00Z",
                    "request_id": "abc123"
                }

        Raises:
            PlaidClientError: If link token creation fails
        """
        try:
            # Default to transactions product if not specified
            if products is None:
                products = ["transactions"]

            # Convert product strings to Products enum
            product_enums = [Products(p) for p in products]

            # Default to US if no country codes specified
            if country_codes is None:
                country_codes = ["US"]

            # Convert country codes to CountryCode enum
            country_code_enums = [CountryCode(cc) for cc in country_codes]

            # Use webhook URL from settings if not provided
            if webhook_url is None:
                webhook_url = settings.PLAID_WEBHOOK_URL

            # Create user object
            user = LinkTokenCreateRequestUser(client_user_id=user_id)

            # Build request kwargs
            request_kwargs = {
                "user": user,
                "client_name": client_name,
                "products": product_enums,
                "country_codes": country_code_enums,
                "language": language,
            }

            # Only add optional fields if they are not None
            if webhook_url:
                request_kwargs["webhook"] = webhook_url
            if redirect_uri:
                request_kwargs["redirect_uri"] = redirect_uri

            request = LinkTokenCreateRequest(**request_kwargs)

            # Call Plaid API (synchronous SDK call wrapped in thread)
            logger.info(f"Creating link token for user: {self._hash_user_id(user_id)}")
            response = await asyncio.to_thread(self.client.link_token_create, request)

            logger.info(f"Link token created successfully for user: {self._hash_user_id(user_id)}")

            return {
                "link_token": response.link_token,
                "expiration": response.expiration.isoformat(),
                "request_id": response.request_id
            }

        except ApiException as e:
            logger.error(f"Failed to create link token: {e}")
            raise PlaidClientError(
                f"Failed to create link token: {e}",
                error_code=getattr(e, 'code', None),
                plaid_error=e
            )

    async def exchange_public_token(self, public_token: str) -> Dict[str, Any]:
        """
        Exchange a public token for an access token.

        This is called after the user successfully completes Plaid Link.
        The public token is a short-lived token that must be exchanged
        for a permanent access token.

        Args:
            public_token: Public token received from Plaid Link

        Returns:
            dict: Response containing access_token and item_id
                {
                    "access_token": "access-sandbox-xxx...",
                    "item_id": "abc123...",
                    "request_id": "xyz789"
                }

        Raises:
            PlaidClientError: If token exchange fails
        """
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)

            logger.info("Exchanging public token for access token")
            response = await asyncio.to_thread(self.client.item_public_token_exchange, request)

            logger.info(f"Token exchanged successfully, item_id: {response.item_id}")

            return {
                "access_token": response.access_token,
                "item_id": response.item_id,
                "request_id": response.request_id
            }

        except ApiException as e:
            logger.error(f"Failed to exchange public token: {e}")
            raise PlaidClientError(
                f"Failed to exchange public token: {e}",
                error_code=getattr(e, 'code', None),
                plaid_error=e
            )

    @retry_plaid_api
    async def get_accounts(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch accounts for an item.

        Retrieves all accounts associated with the access token,
        including current balance information.

        Args:
            access_token: Access token for the item

        Returns:
            dict: Response containing accounts, item, and request_id
                {
                    "accounts": [...],
                    "item": {...},
                    "request_id": "abc123"
                }

        Raises:
            PlaidClientError: If account fetch fails
        """
        try:
            request = AccountsGetRequest(access_token=access_token)

            logger.info(f"Fetching accounts for access token: {self._mask_token(access_token)}")
            response = await asyncio.to_thread(self.client.accounts_get, request)

            logger.info(f"Fetched {len(response.accounts)} accounts")

            return {
                "accounts": [acc.to_dict() for acc in response.accounts],
                "item": response.item.to_dict(),
                "request_id": response.request_id
            }

        except ApiException as e:
            logger.error(f"Failed to fetch accounts: {e}")
            self._handle_plaid_error(e)

    @retry_plaid_api
    async def sync_transactions(
        self,
        access_token: str,
        cursor: Optional[str] = None,
        count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync transactions using the /transactions/sync endpoint.

        This endpoint supports incremental updates using a cursor.
        On first call (no cursor), it returns all available transactions.
        On subsequent calls, it returns only changes since the last cursor.

        Args:
            access_token: Access token for the item
            cursor: Cursor from previous sync (None for initial sync)
            count: Maximum number of transactions to fetch per request

        Returns:
            dict: Response containing added, modified, removed transactions and next_cursor
                {
                    "added": [...],
                    "modified": [...],
                    "removed": [...],
                    "next_cursor": "cursor_string",
                    "has_more": false,
                    "request_id": "abc123"
                }

        Raises:
            PlaidClientError: If transaction sync fails
        """
        try:
            # Build request kwargs
            request_kwargs = {"access_token": access_token}

            # Only add optional fields if they are not None
            if cursor:
                request_kwargs["cursor"] = cursor
            if count:
                request_kwargs["count"] = count

            request = TransactionsSyncRequest(**request_kwargs)

            sync_type = "initial" if cursor is None else "incremental"
            logger.info(f"Syncing transactions ({sync_type}): {self._mask_token(access_token)}")

            response = await asyncio.to_thread(self.client.transactions_sync, request)

            logger.info(
                f"Transaction sync complete: "
                f"added={len(response.added)}, "
                f"modified={len(response.modified)}, "
                f"removed={len(response.removed)}, "
                f"has_more={response.has_more}"
            )

            return {
                "added": [txn.to_dict() for txn in response.added],
                "modified": [txn.to_dict() for txn in response.modified],
                "removed": [txn.to_dict() for txn in response.removed],
                "next_cursor": response.next_cursor,
                "has_more": response.has_more,
                "request_id": response.request_id
            }

        except ApiException as e:
            logger.error(f"Failed to sync transactions: {e}")
            self._handle_plaid_error(e)

    @retry_plaid_api
    async def get_item(self, access_token: str) -> Dict[str, Any]:
        """
        Get item details.

        Retrieves information about an item including status, products,
        and webhook configuration.

        Args:
            access_token: Access token for the item

        Returns:
            dict: Response containing item details
                {
                    "item": {
                        "item_id": "...",
                        "institution_id": "...",
                        "webhook": "...",
                        "products": [...],
                        "billed_products": [...],
                        "available_products": [...],
                        ...
                    },
                    "status": {...},
                    "request_id": "abc123"
                }

        Raises:
            PlaidClientError: If item fetch fails
        """
        try:
            request = ItemGetRequest(access_token=access_token)

            logger.info(f"Fetching item details: {self._mask_token(access_token)}")
            response = await asyncio.to_thread(self.client.item_get, request)

            logger.info(f"Item details fetched: item_id={response.item.item_id}")

            return {
                "item": response.item.to_dict(),
                "status": response.status.to_dict() if response.status else None,
                "request_id": response.request_id
            }

        except ApiException as e:
            logger.error(f"Failed to fetch item: {e}")
            self._handle_plaid_error(e)

    async def remove_item(self, access_token: str) -> Dict[str, Any]:
        """
        Remove (disconnect) an item.

        This invalidates the access token and removes the item from Plaid.
        This should be called when a user disconnects a bank connection.

        Args:
            access_token: Access token for the item

        Returns:
            dict: Response confirming removal
                {
                    "request_id": "abc123"
                }

        Raises:
            PlaidClientError: If item removal fails
        """
        try:
            request = ItemRemoveRequest(access_token=access_token)

            logger.info(f"Removing item: {self._mask_token(access_token)}")
            response = await asyncio.to_thread(self.client.item_remove, request)

            logger.info("Item removed successfully")

            return {
                "request_id": response.request_id
            }

        except ApiException as e:
            logger.error(f"Failed to remove item: {e}")
            self._handle_plaid_error(e)

    def _handle_plaid_error(self, error: ApiException) -> None:
        """
        Handle Plaid API errors with specific error codes.

        Args:
            error: Plaid API exception

        Raises:
            PlaidClientError: Wrapped Plaid error with additional context
        """
        error_code = getattr(error, 'code', None)
        error_message = str(error)

        # Map common Plaid errors to user-friendly messages
        error_messages = {
            "ITEM_LOGIN_REQUIRED": "Bank login credentials need to be updated. Please reconnect your bank.",
            "RATE_LIMIT_EXCEEDED": "Too many requests. Please try again later.",
            "INVALID_ACCESS_TOKEN": "Bank connection is invalid. Please reconnect your bank.",
            "ITEM_LOCKED": "Bank connection is locked. Please contact support.",
            "PRODUCTS_NOT_READY": "Bank data is not ready yet. Please try again in a few moments.",
            "INSTITUTION_DOWN": "The bank is currently unavailable. Please try again later.",
            "INSTITUTION_NOT_RESPONDING": "The bank is not responding. Please try again later.",
        }

        user_message = error_messages.get(error_code, f"Plaid API error: {error_message}")

        raise PlaidClientError(
            user_message,
            error_code=error_code,
            plaid_error=error
        )

    def _mask_token(self, token: str) -> str:
        """
        Mask access token for logging (show first 8 chars).

        Args:
            token: Access token to mask

        Returns:
            Masked token string
        """
        if not token or len(token) <= 12:
            return "***"
        return f"{token[:8]}...{token[-4:]}"

    def _hash_user_id(self, user_id: str) -> str:
        """
        Hash user ID for logging (privacy).

        Args:
            user_id: User ID to hash

        Returns:
            Hashed user ID or original if no logging secret configured
        """
        if not settings.LOGGING_SECRET:
            # In development, just truncate
            if len(user_id) > 8:
                return f"{user_id[:4]}...{user_id[-4:]}"
            return user_id

        import hashlib
        hashed = hashlib.sha256(
            f"{settings.LOGGING_SECRET}:{user_id}".encode()
        ).hexdigest()
        return hashed[:12]


# Global Plaid client instance
plaid_client = PlaidClient()
