"""
Plaid normalization layer.

This module provides normalization functions to convert Plaid-specific
data structures to our unified data models. This abstraction layer allows
us to work with provider-agnostic models throughout the application.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import SecretStr

from app.models.account import UnifiedAccount
from app.models.transaction import UnifiedTransaction
from app.models.connection import Connection
from app.models.enums import AccountType, AccountSubtype, TransactionDirection, AccountStatus, HolderCategory, ConnectionStatus
from app.utils.logger import logger


class PlaidItemNormalizer:
    """Normalizer for converting Plaid Item to Connection model."""

    @staticmethod
    def normalize_from_exchange(
        user_id: UUID,
        provider_id: int,
        access_token: str,
        item_id: str,
        institution_id: Optional[str] = None,
        institution_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Connection:
        """
        Create Connection from public token exchange response.

        This is called right after the user completes Plaid Link and we
        exchange the public_token for an access_token.

        Args:
            user_id: User UUID
            provider_id: Provider ID (from providers table)
            access_token: Plaid access token (long-lived)
            item_id: Plaid item ID
            institution_id: Institution ID (from Plaid Link metadata)
            institution_name: Institution name (from Plaid Link metadata)
            metadata: Additional metadata from Plaid Link (optional)

        Returns:
            Connection: Normalized connection model

        Example metadata from Plaid Link:
            {
                "institution": {
                    "name": "Chase",
                    "institution_id": "ins_3"
                },
                "accounts": [...],
                "link_session_id": "...",
                "public_token": "..."
            }
        """
        # Extract institution info from metadata if provided
        if metadata and "institution" in metadata:
            institution_data = metadata["institution"]
            institution_id = institution_id or institution_data.get("institution_id")
            institution_name = institution_name or institution_data.get("name")

        return Connection(
            user_id=user_id,
            provider_id=provider_id,
            external_item_id=item_id,
            access_token=SecretStr(access_token),
            connection_status=ConnectionStatus.PENDING,  # Pending until accounts are fetched
            institution_id=institution_id,
            institution_name=institution_name,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    @staticmethod
    def normalize_from_item_get(
        plaid_item: Dict[str, Any],
        connection: Connection
    ) -> Connection:
        """
        Update Connection with data from Plaid /item/get response.

        This is called when we fetch item details to update the connection
        with the latest information about products, consent, etc.

        Args:
            plaid_item: Raw Plaid item data from /item/get
            connection: Existing connection to update

        Returns:
            Connection: Updated connection model

        Example Plaid Item:
            {
                "item_id": "abc123",
                "institution_id": "ins_3",
                "webhook": "https://api.example.com/webhooks/plaid",
                "products": ["transactions"],
                "billed_products": ["transactions"],
                "available_products": ["auth", "identity"],
                "consented_products": ["transactions", "auth"],
                "consent_expiration_time": "2025-12-31T23:59:59Z",
                "update_type": "background",
                "error": null
            }
        """
        # Update products
        connection.products = plaid_item.get("products", [])
        connection.available_products = plaid_item.get("available_products", [])

        # Update consent information
        if plaid_item.get("consent_expiration_time"):
            connection.consent_expiration_time = datetime.fromisoformat(
                plaid_item["consent_expiration_time"].replace('Z', '+00:00')
            )

        # Update type (background or user_present_required)
        connection.update_type = plaid_item.get("update_type")

        # Handle error state
        if plaid_item.get("error"):
            error_code = plaid_item["error"].get("error_code")
            if error_code == "ITEM_LOGIN_REQUIRED":
                connection.connection_status = ConnectionStatus.NEEDS_REAUTH
            elif error_code in ["ITEM_LOCKED", "ITEM_NOT_FOUND"]:
                connection.connection_status = ConnectionStatus.ERROR
        else:
            # No error, connection is active
            if connection.connection_status in [ConnectionStatus.PENDING, ConnectionStatus.ERROR]:
                connection.connection_status = ConnectionStatus.ACTIVE

        connection.updated_at = datetime.now(timezone.utc)

        logger.debug(
            f"Updated connection from Plaid item: {plaid_item.get('item_id')} -> "
            f"status={connection.connection_status.value}, products={connection.products}"
        )

        return connection

    @staticmethod
    def update_institution_info(
        connection: Connection,
        institution_id: str,
        institution_name: str
    ) -> Connection:
        """
        Update connection with institution information.

        Args:
            connection: Existing connection
            institution_id: Plaid institution ID
            institution_name: Institution name

        Returns:
            Connection: Updated connection
        """
        connection.institution_id = institution_id
        connection.institution_name = institution_name
        connection.updated_at = datetime.now(timezone.utc)
        return connection

    @staticmethod
    def mark_needs_reauth(connection: Connection, error_message: Optional[str] = None) -> Connection:
        """
        Mark connection as needing re-authentication.

        Args:
            connection: Connection to update
            error_message: Optional error message

        Returns:
            Connection: Updated connection
        """
        connection.connection_status = ConnectionStatus.NEEDS_REAUTH
        connection.updated_at = datetime.now(timezone.utc)

        logger.warning(
            f"Connection {connection.connection_id} marked as needs reauth: {error_message}"
        )

        return connection

    @staticmethod
    def mark_revoked(connection: Connection, reason: Optional[str] = None) -> Connection:
        """
        Mark connection as revoked (user disconnected).

        Args:
            connection: Connection to update
            reason: Optional reason for revocation

        Returns:
            Connection: Updated connection
        """
        connection.connection_status = ConnectionStatus.REVOKED
        connection.updated_at = datetime.now(timezone.utc)

        logger.info(
            f"Connection {connection.connection_id} revoked: {reason or 'User initiated'}"
        )

        return connection


class PlaidAccountNormalizer:
    """Normalizer for converting Plaid accounts to UnifiedAccount model."""

    @staticmethod
    def normalize(
        plaid_account: Dict[str, Any],
        user_id: UUID,
        connection_id: int,
        institution_name: Optional[str] = None
    ) -> UnifiedAccount:
        """
        Convert Plaid account to UnifiedAccount model.

        Args:
            plaid_account: Raw Plaid account data (dict)
            user_id: User UUID
            connection_id: Connection ID
            institution_name: Institution name (from connection)

        Returns:
            UnifiedAccount: Normalized account model

        Example Plaid Account Structure:
            {
                "account_id": "blgvvBlXw3cq5GMPwqB6s6q4dLKB9WcVqGDGo",
                "balances": {
                    "available": 100.00,
                    "current": 110.00,
                    "limit": null,
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
        """
        try:
            balances = plaid_account.get("balances", {})

            # Extract account type and subtype
            account_type_raw = plaid_account.get("type", "").lower()
            account_subtype_raw = plaid_account.get("subtype", "").lower() if plaid_account.get("subtype") else None

            # Map Plaid account type to our enum
            account_type = PlaidAccountNormalizer._map_account_type(account_type_raw)

            # Map Plaid account subtype to our enum
            account_subtype = PlaidAccountNormalizer._map_account_subtype(account_subtype_raw) if account_subtype_raw else None

            # Extract currency (default to USD if not provided)
            currency = balances.get("iso_currency_code") or balances.get("unofficial_currency_code") or "USD"

            # Extract balances (convert to Decimal for precision)
            current_balance = Decimal(str(balances.get("current"))) if balances.get("current") is not None else None
            available_balance = Decimal(str(balances.get("available"))) if balances.get("available") is not None else None
            credit_limit = Decimal(str(balances.get("limit"))) if balances.get("limit") is not None else None

            # Map holder category
            holder_category_raw = plaid_account.get("holder_category")
            holder_category = PlaidAccountNormalizer._map_holder_category(holder_category_raw) if holder_category_raw else None

            # Build provider metadata
            provider_metadata = {
                "plaid": {
                    "persistent_account_id": plaid_account.get("persistent_account_id"),
                    "last_updated_datetime": balances.get("last_updated_datetime"),
                    "original_type": account_type_raw,
                    "original_subtype": account_subtype_raw
                }
            }

            # Create UnifiedAccount
            unified_account = UnifiedAccount(
                user_id=user_id,
                connection_id=connection_id,
                external_account_id=plaid_account["account_id"],
                name=plaid_account.get("name", "Unknown Account"),
                official_name=plaid_account.get("official_name"),
                account_type=account_type,
                account_subtype=account_subtype,
                currency=currency,
                mask=plaid_account.get("mask"),
                current_balance=current_balance,
                available_balance=available_balance,
                credit_limit=credit_limit,
                institution_name=institution_name,
                verification_status=plaid_account.get("verification_status"),
                holder_category=holder_category,
                provider_metadata=provider_metadata,
                account_status=AccountStatus.ACTIVE,
                last_refreshed_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            logger.debug(
                f"Normalized Plaid account: {plaid_account['account_id']} -> "
                f"{account_type.value}/{account_subtype.value if account_subtype else 'none'}"
            )

            return unified_account

        except Exception as e:
            logger.error(f"Failed to normalize Plaid account: {e}")
            logger.error(f"Plaid account data: {plaid_account}")
            raise

    @staticmethod
    def _map_account_type(plaid_type: str) -> AccountType:
        """
        Map Plaid account type to AccountType enum.

        Args:
            plaid_type: Plaid account type (depository, credit, loan, investment, other)

        Returns:
            AccountType enum value
        """
        mapping = {
            "depository": AccountType.DEPOSITORY,
            "credit": AccountType.CREDIT,
            "loan": AccountType.LOAN,
            "investment": AccountType.INVESTMENT,
            "other": AccountType.OTHER
        }
        return mapping.get(plaid_type.lower(), AccountType.OTHER)

    @staticmethod
    def _map_account_subtype(plaid_subtype: str) -> Optional[AccountSubtype]:
        """
        Map Plaid account subtype to AccountSubtype enum.

        Args:
            plaid_subtype: Plaid account subtype

        Returns:
            AccountSubtype enum value or None if not found
        """
        # Replace underscores with spaces to match enum format
        # (Plaid uses "credit_card", enum uses "credit card")
        normalized = plaid_subtype.lower().replace("_", " ")

        try:
            return AccountSubtype(normalized)
        except ValueError:
            logger.warning(f"Unknown Plaid account subtype: {plaid_subtype}, using None")
            return None

    @staticmethod
    def _map_holder_category(plaid_holder_category: str) -> Optional[HolderCategory]:
        """
        Map Plaid holder category to HolderCategory enum.

        Args:
            plaid_holder_category: Plaid holder category (personal, business)

        Returns:
            HolderCategory enum value
        """
        mapping = {
            "personal": HolderCategory.PERSONAL,
            "business": HolderCategory.BUSINESS,
        }
        result = mapping.get(plaid_holder_category.lower(), HolderCategory.UNRECOGNIZED)
        return result


class PlaidTransactionNormalizer:
    """Normalizer for converting Plaid transactions to UnifiedTransaction model."""

    @staticmethod
    def normalize(
        plaid_txn: Dict[str, Any],
        account_id: int
    ) -> UnifiedTransaction:
        """
        Convert Plaid transaction to UnifiedTransaction model.

        Args:
            plaid_txn: Raw Plaid transaction data (dict)
            account_id: Internal account ID (from accounts table)

        Returns:
            UnifiedTransaction: Normalized transaction model

        Example Plaid Transaction Structure:
            {
                "transaction_id": "yBVBEwrXdDf9gfXP4kcKFK6FjqqmRhQ4JqYnb",
                "account_id": "vzeNDwK7KQIm4yEog683uElbp9GRLEFXGK98D",
                "amount": 25.00,
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
                "pending": false,
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_COFFEE",
                    "confidence_level": "VERY_HIGH"
                },
                "counterparties": [...],
                "location": {...}
            }
        """
        try:
            # Extract amount and determine direction
            # Plaid convention: positive amount = money out (debit), negative = money in (credit)
            plaid_amount = plaid_txn.get("amount", 0)
            amount = Decimal(str(abs(plaid_amount)))
            txn_direction = TransactionDirection.DEBIT if plaid_amount > 0 else TransactionDirection.CREDIT

            # Handle zero amounts
            if plaid_amount == 0:
                txn_direction = TransactionDirection.UNKNOWN

            # Extract currency
            currency = plaid_txn.get("iso_currency_code") or plaid_txn.get("unofficial_currency_code") or "USD"

            # Parse dates
            txn_date = PlaidTransactionNormalizer._parse_date(plaid_txn.get("date"))
            posted_at = PlaidTransactionNormalizer._parse_datetime(plaid_txn.get("datetime")) or txn_date
            authorized_date = PlaidTransactionNormalizer._parse_date(plaid_txn.get("authorized_date"))

            # Extract category (join hierarchical category with " > ")
            category = None
            if plaid_txn.get("category"):
                category = " > ".join(plaid_txn["category"])

            # Extract personal finance category
            personal_finance_category = plaid_txn.get("personal_finance_category")
            if personal_finance_category:
                personal_finance_category = {
                    "primary": personal_finance_category.get("primary"),
                    "detailed": personal_finance_category.get("detailed"),
                    "confidence_level": personal_finance_category.get("confidence_level")
                }

            # Extract location
            location = plaid_txn.get("location")
            if location:
                location = {
                    "address": location.get("address"),
                    "city": location.get("city"),
                    "region": location.get("region"),
                    "postal_code": location.get("postal_code"),
                    "country": location.get("country"),
                    "lat": location.get("lat"),
                    "lon": location.get("lon"),
                    "store_number": location.get("store_number")
                }

            # Build provider metadata
            provider_metadata = {
                "plaid": {
                    "transaction_code": plaid_txn.get("transaction_code"),
                    "transaction_type": plaid_txn.get("transaction_type"),
                    "merchant_entity_id": plaid_txn.get("merchant_entity_id"),
                    "category_id": plaid_txn.get("category_id"),
                    "pending_transaction_id": plaid_txn.get("pending_transaction_id"),
                    "payment_meta": plaid_txn.get("payment_meta")
                }
            }

            # Create UnifiedTransaction
            unified_txn = UnifiedTransaction(
                account_id=account_id,
                external_txn_id=plaid_txn["transaction_id"],
                txn_date=txn_date,
                posted_at=posted_at,
                authorized_date=authorized_date,
                amount=amount,
                currency=currency,
                txn_direction=txn_direction,
                description_raw=plaid_txn.get("name", "Unknown Transaction"),
                merchant_name_raw=plaid_txn.get("merchant_name"),
                merchant_logo_url=plaid_txn.get("logo_url"),
                merchant_website=plaid_txn.get("website"),
                pending=plaid_txn.get("pending", False),
                category=category,
                personal_finance_category=personal_finance_category,
                payment_channel=plaid_txn.get("payment_channel"),
                counterparties=plaid_txn.get("counterparties", []),
                location=location,
                check_number=plaid_txn.get("check_number"),
                provider_metadata=provider_metadata,
                raw_payload=plaid_txn,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            logger.debug(
                f"Normalized Plaid transaction: {plaid_txn['transaction_id']} -> "
                f"{txn_direction.value} {amount} {currency}"
            )

            return unified_txn

        except Exception as e:
            logger.error(f"Failed to normalize Plaid transaction: {e}")
            logger.error(f"Plaid transaction data: {plaid_txn}")
            raise

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date string (YYYY-MM-DD) to datetime.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            datetime object or None
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None

    @staticmethod
    def _parse_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
        """
        Parse ISO datetime string to datetime.

        Args:
            datetime_str: ISO datetime string

        Returns:
            datetime object or None
        """
        if not datetime_str:
            return None

        try:
            # Handle ISO format with timezone
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
            return None
