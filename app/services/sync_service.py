"""
Sync service - Orchestrates data synchronization from Plaid.

This service handles:
1. Account sync from Plaid
2. Initial transaction sync
3. Incremental transaction sync with cursor
4. Complete connection sync orchestration
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from app.models.enums import ConnectionStatus
from app.providers.plaid.client import plaid_client, PlaidClientError
from app.providers.plaid.normalizer import (
    PlaidAccountNormalizer,
    PlaidTransactionNormalizer,
    PlaidItemNormalizer
)
from app.services.connection_service import connection_service
from app.services.account_service import account_service
from app.services.transaction_service import transaction_service
from app.utils.logger import logger
from app.utils.logging_security import hash_connection_id


class SyncService:
    """Service for synchronizing data from Plaid to database."""

    async def sync_accounts(self, connection_id: UUID) -> int:
        """
        Sync accounts for a connection from Plaid.

        Flow:
        1. Get connection (access_token)
        2. Call Plaid /accounts/get
        3. Normalize accounts (Plaid → Unified)
        4. Upsert accounts to database
        5. Update connection with item info
        6. Update last_synced_at

        Args:
            connection_id: Connection ID to sync accounts for

        Returns:
            int: Number of accounts synced

        Raises:
            Exception: If sync fails
        """
        try:
            logger.info(f"Starting account sync for connection [{hash_connection_id(connection_id)}]")

            # Get connection
            connection = await connection_service.get_connection(connection_id)
            if not connection:
                raise Exception(f"Connection {connection_id} not found")

            if not connection.access_token:
                raise Exception(f"Connection {connection_id} has no access token")

            # Fetch accounts from Plaid
            logger.info(f"Fetching accounts from Plaid for connection [{hash_connection_id(connection_id)}]")
            plaid_response = await plaid_client.get_accounts(
                connection.access_token.get_secret_value()
            )

            # Normalize accounts
            accounts = []
            for plaid_account in plaid_response["accounts"]:
                try:
                    normalized = PlaidAccountNormalizer.normalize(
                        plaid_account,
                        connection.user_id,
                        connection_id
                    )
                    accounts.append(normalized)
                except Exception as e:
                    logger.error(
                        f"Failed to normalize account {plaid_account.get('account_id')}: {e}"
                    )
                    continue

            # Upsert accounts to database
            if accounts:
                logger.info(f"Upserting {len(accounts)} accounts to database")
                await account_service.upsert_accounts(accounts)
            else:
                logger.warning(f"No accounts to sync for connection [{hash_connection_id(connection_id)}]")

            # Update connection with item info
            item_info = plaid_response.get("item", {})
            updates = {
                "products": item_info.get("billed_products", []),
                "available_products": item_info.get("available_products", []),
                "last_synced_at": datetime.now(timezone.utc).isoformat()
            }

            # Only update status to Active if currently Pending
            if connection.connection_status == ConnectionStatus.PENDING:
                updates["connection_status"] = ConnectionStatus.ACTIVE.value

            await connection_service.update_connection(connection_id, updates)

            logger.info(
                f"Account sync completed for connection [{hash_connection_id(connection_id)}]: "
                f"{len(accounts)} accounts synced"
            )

            return len(accounts)

        except PlaidClientError as e:
            logger.error(f"Plaid error during account sync: {e}")
            # Check if this is an auth error
            if e.error_code in ["ITEM_LOGIN_REQUIRED", "INVALID_ACCESS_TOKEN"]:
                await connection_service.mark_needs_reauth(connection_id)
            raise
        except Exception as e:
            logger.error(f"Error syncing accounts for connection [{hash_connection_id(connection_id)}]: {e}")
            raise

    async def sync_transactions_initial(self, connection_id: UUID) -> Dict[str, int]:
        """
        Initial transaction sync (no cursor).

        Flow:
        1. Get connection & accounts
        2. Call Plaid /transactions/sync (no cursor)
        3. Normalize transactions
        4. Insert transactions to DB
        5. Store next_cursor in connection.artifact

        Args:
            connection_id: Connection ID to sync transactions for

        Returns:
            Dict with counts: {"added": N, "modified": 0, "removed": 0}

        Raises:
            Exception: If sync fails
        """
        try:
            logger.info(f"Starting initial transaction sync for connection [{hash_connection_id(connection_id)}]")

            # Get connection
            connection = await connection_service.get_connection(connection_id)
            if not connection:
                raise Exception(f"Connection {connection_id} not found")

            if not connection.access_token:
                raise Exception(f"Connection {connection_id} has no access token")

            # Get accounts for this connection
            accounts = await account_service.get_accounts_by_connection(connection_id)
            if not accounts:
                logger.warning(f"No accounts found for connection [{hash_connection_id(connection_id)}]")
                return {"added": 0, "modified": 0, "removed": 0}

            # Create account mapping (external_id → internal account object)
            account_map = {acc.external_account_id: acc for acc in accounts}

            # Fetch transactions from Plaid (initial sync, no cursor)
            logger.info(f"Fetching transactions from Plaid (initial) for connection [{hash_connection_id(connection_id)}]")
            plaid_response = await plaid_client.sync_transactions(
                access_token=connection.access_token.get_secret_value(),
                cursor=None  # Initial sync
            )

            # Process added transactions
            transactions = []
            for plaid_txn in plaid_response["added"]:
                plaid_account_id = plaid_txn.get("account_id")
                account = account_map.get(plaid_account_id)

                if not account:
                    logger.warning(
                        f"Transaction references unknown account: {plaid_account_id}"
                    )
                    continue

                try:
                    normalized = PlaidTransactionNormalizer.normalize(
                        plaid_txn,
                        account.account_id
                    )
                    transactions.append(normalized)
                except Exception as e:
                    logger.error(
                        f"Failed to normalize transaction {plaid_txn.get('transaction_id')}: {e}"
                    )
                    continue

            # Insert transactions to database
            if transactions:
                logger.info(f"Inserting {len(transactions)} transactions to database")
                await transaction_service.upsert_transactions(transactions)

            # Store cursor in connection artifact
            next_cursor = plaid_response.get("next_cursor")
            if next_cursor:
                await connection_service.update_artifact(
                    connection_id,
                    {"transactions_cursor": next_cursor}
                )

            # Update last_synced_at
            await connection_service.update_last_synced(connection_id)

            logger.info(
                f"Initial transaction sync completed for connection [{hash_connection_id(connection_id)}]: "
                f"{len(transactions)} transactions synced"
            )

            return {
                "added": len(transactions),
                "modified": 0,
                "removed": 0
            }

        except PlaidClientError as e:
            logger.error(f"Plaid error during initial transaction sync: {e}")
            if e.error_code in ["ITEM_LOGIN_REQUIRED", "INVALID_ACCESS_TOKEN"]:
                await connection_service.mark_needs_reauth(connection_id)
            raise
        except Exception as e:
            logger.error(
                f"Error during initial transaction sync for connection [{hash_connection_id(connection_id)}]: {e}"
            )
            raise

    async def sync_transactions_incremental(self, connection_id: UUID) -> Dict[str, int]:
        """
        Incremental transaction sync (with cursor).

        Handles:
        - added: New transactions → INSERT
        - modified: Updated transactions → UPDATE
        - removed: Deleted transactions → DELETE

        Args:
            connection_id: Connection ID to sync transactions for

        Returns:
            Dict with counts: {"added": N, "modified": M, "removed": R}

        Raises:
            Exception: If sync fails
        """
        try:
            logger.info(f"Starting incremental transaction sync for connection [{hash_connection_id(connection_id)}]")

            # Get connection
            connection = await connection_service.get_connection(connection_id)
            if not connection:
                raise Exception(f"Connection {connection_id} not found")

            if not connection.access_token:
                raise Exception(f"Connection {connection_id} has no access token")

            # Get cursor from artifact
            cursor = connection.artifact.get("transactions_cursor")
            if not cursor:
                raise Exception(
                    f"No cursor found for connection [{hash_connection_id(connection_id)}]. "
                    "Use sync_transactions_initial() first."
                )

            # Get accounts for this connection
            accounts = await account_service.get_accounts_by_connection(connection_id)
            account_map = {acc.external_account_id: acc for acc in accounts}

            # Fetch transactions from Plaid with cursor
            logger.info(f"Fetching transactions from Plaid (incremental) for connection [{hash_connection_id(connection_id)}]")
            plaid_response = await plaid_client.sync_transactions(
                access_token=connection.access_token.get_secret_value(),
                cursor=cursor
            )

            counts = {"added": 0, "modified": 0, "removed": 0}

            # Handle ADDED transactions
            for plaid_txn in plaid_response["added"]:
                plaid_account_id = plaid_txn.get("account_id")
                account = account_map.get(plaid_account_id)

                if not account:
                    logger.warning(f"Transaction references unknown account: {plaid_account_id}")
                    continue

                try:
                    normalized = PlaidTransactionNormalizer.normalize(plaid_txn, account.account_id)
                    await transaction_service.upsert_transaction(normalized)
                    counts["added"] += 1
                except Exception as e:
                    logger.error(f"Failed to add transaction {plaid_txn.get('transaction_id')}: {e}")

            # Handle MODIFIED transactions
            for plaid_txn in plaid_response["modified"]:
                plaid_account_id = plaid_txn.get("account_id")
                account = account_map.get(plaid_account_id)

                if not account:
                    logger.warning(f"Transaction references unknown account: {plaid_account_id}")
                    continue

                try:
                    normalized = PlaidTransactionNormalizer.normalize(plaid_txn, account.account_id)
                    # Upsert handles both insert and update
                    await transaction_service.upsert_transaction(normalized)
                    counts["modified"] += 1
                except Exception as e:
                    logger.error(f"Failed to update transaction {plaid_txn.get('transaction_id')}: {e}")

            # Handle REMOVED transactions
            for removed_txn in plaid_response["removed"]:
                external_txn_id = removed_txn.get("transaction_id")
                try:
                    deleted = await transaction_service.delete_transaction_by_external_id(external_txn_id)
                    if deleted:
                        counts["removed"] += 1
                except Exception as e:
                    logger.error(f"Failed to delete transaction {external_txn_id}: {e}")

            # Update cursor
            next_cursor = plaid_response.get("next_cursor")
            if next_cursor:
                await connection_service.update_artifact(
                    connection_id,
                    {"transactions_cursor": next_cursor}
                )

            # Update last_synced_at
            await connection_service.update_last_synced(connection_id)

            logger.info(
                f"Incremental transaction sync completed for connection [{hash_connection_id(connection_id)}]: "
                f"added={counts['added']}, modified={counts['modified']}, removed={counts['removed']}"
            )

            return counts

        except PlaidClientError as e:
            logger.error(f"Plaid error during incremental transaction sync: {e}")
            if e.error_code in ["ITEM_LOGIN_REQUIRED", "INVALID_ACCESS_TOKEN"]:
                await connection_service.mark_needs_reauth(connection_id)
            raise
        except Exception as e:
            logger.error(
                f"Error during incremental transaction sync for connection [{hash_connection_id(connection_id)}]: {e}"
            )
            raise

    async def sync_connection(self, connection_id: UUID) -> Dict[str, any]:
        """
        Complete sync for a connection.

        Flow:
        1. Sync accounts (always)
        2. Sync transactions (initial or incremental based on cursor)
        3. Update connection status to Active if successful

        Args:
            connection_id: Connection ID to sync

        Returns:
            Dict with sync results:
            {
                "accounts": int,
                "transactions": {"added": N, "modified": M, "removed": R}
            }

        Raises:
            Exception: If sync fails
        """
        try:
            logger.info(f"Starting complete sync for connection [{hash_connection_id(connection_id)}]")

            # Sync accounts first
            accounts_count = await self.sync_accounts(connection_id)

            # Check if we need initial or incremental transaction sync
            connection = await connection_service.get_connection(connection_id)
            cursor = connection.artifact.get("transactions_cursor")

            if cursor:
                # Incremental sync
                transaction_counts = await self.sync_transactions_incremental(connection_id)
            else:
                # Initial sync
                transaction_counts = await self.sync_transactions_initial(connection_id)

            logger.info(f"Complete sync finished for connection [{hash_connection_id(connection_id)}]")

            return {
                "accounts": accounts_count,
                "transactions": transaction_counts
            }

        except Exception as e:
            logger.error(f"Error during complete sync for connection [{hash_connection_id(connection_id)}]: {e}")
            # Update connection to error state
            await connection_service.update_connection(
                connection_id,
                {
                    "connection_status": ConnectionStatus.ERROR.value,
                    "error_message": str(e)[:500]  # Truncate long error messages
                }
            )
            raise


# Singleton instance
sync_service = SyncService()
