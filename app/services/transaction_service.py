"""Transaction service - CRUD operations for transactions."""
from datetime import datetime, timezone
from typing import List, Optional

from app.core.database import get_db
from app.models.transaction import UnifiedTransaction
from app.utils.logger import logger
from app.utils.logging_security import hash_transaction_id


class TransactionService:
    """Service for managing transactions."""

    @staticmethod
    async def create_transaction(transaction: UnifiedTransaction) -> UnifiedTransaction:
        """Create a new transaction record."""
        try:
            db = get_db()
            txn_data = {
                "account_id": transaction.account_id,
                "external_txn_id": transaction.external_txn_id,
                "txn_date": transaction.txn_date.isoformat(),
                "posted_at": transaction.posted_at.isoformat() if transaction.posted_at else None,
                "authorized_date": transaction.authorized_date.isoformat() if transaction.authorized_date else None,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
                "txn_direction": transaction.txn_direction.value,
                "description_raw": transaction.description_raw,
                "merchant_name_raw": transaction.merchant_name_raw,
                "merchant_logo_url": transaction.merchant_logo_url,
                "merchant_website": transaction.merchant_website,
                "pending": transaction.pending,
                "category": transaction.category,
                "personal_finance_category": transaction.personal_finance_category,
                "payment_channel": transaction.payment_channel,
                "counterparties": transaction.counterparties,
                "location": transaction.location,
                "check_number": transaction.check_number,
                "running_balance": float(transaction.running_balance) if transaction.running_balance else None,
                "provider_metadata": transaction.provider_metadata,
                "raw_payload": transaction.raw_payload,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = db.table("transactions").insert(txn_data).execute()

            if result.data:
                logger.info(f"Transaction created [{hash_transaction_id(transaction.external_txn_id)}]")
                return UnifiedTransaction(**result.data[0])
            raise Exception("Failed to create transaction")

        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            raise

    @staticmethod
    async def get_transaction(txn_id: int) -> Optional[UnifiedTransaction]:
        """Get transaction by ID."""
        try:
            db = get_db()
            result = db.table("transactions").select("*").eq("txn_id", txn_id).execute()

            if result.data:
                return UnifiedTransaction(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error fetching transaction: {e}")
            raise

    @staticmethod
    async def get_transaction_by_external_id(external_txn_id: str) -> Optional[UnifiedTransaction]:
        """Get transaction by external transaction ID."""
        try:
            db = get_db()
            result = db.table("transactions").select("*").eq("external_txn_id", external_txn_id).execute()

            if result.data:
                return UnifiedTransaction(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error fetching transaction by external ID: {e}")
            raise

    @staticmethod
    async def get_account_transactions(
        account_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[UnifiedTransaction]:
        """Get transactions for an account."""
        try:
            db = get_db()
            result = (
                db.table("transactions")
                .select("*")
                .eq("account_id", account_id)
                .order("txn_date", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return [UnifiedTransaction(**txn) for txn in result.data]

        except Exception as e:
            logger.error(f"Error fetching account transactions: {e}")
            raise

    @staticmethod
    async def update_transaction(txn_id: int, updates: dict) -> UnifiedTransaction:
        """Update transaction record."""
        try:
            db = get_db()
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Convert Decimal to float for JSON serialization
            if "amount" in updates and updates["amount"] is not None:
                updates["amount"] = float(updates["amount"])
            if "running_balance" in updates and updates["running_balance"] is not None:
                updates["running_balance"] = float(updates["running_balance"])

            result = db.table("transactions").update(updates).eq("txn_id", txn_id).execute()

            if result.data:
                # Use external_txn_id from result for consistent logging
                external_txn_id = result.data[0].get("external_txn_id", str(txn_id))
                logger.info(f"Transaction updated [{hash_transaction_id(external_txn_id)}]")
                return UnifiedTransaction(**result.data[0])
            raise Exception("Transaction not found")

        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            raise

    @staticmethod
    async def update_transaction_by_external_id(
        external_txn_id: str,
        updates: dict
    ) -> UnifiedTransaction:
        """Update transaction by external ID."""
        try:
            db = get_db()
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Convert Decimal to float
            if "amount" in updates and updates["amount"] is not None:
                updates["amount"] = float(updates["amount"])
            if "running_balance" in updates and updates["running_balance"] is not None:
                updates["running_balance"] = float(updates["running_balance"])

            result = db.table("transactions").update(updates).eq("external_txn_id", external_txn_id).execute()

            if result.data:
                logger.info(f"Transaction updated [{hash_transaction_id(external_txn_id)}]")
                return UnifiedTransaction(**result.data[0])
            raise Exception("Transaction not found")

        except Exception as e:
            logger.error(f"Error updating transaction by external ID: {e}")
            raise

    @staticmethod
    async def upsert_transaction(transaction: UnifiedTransaction) -> UnifiedTransaction:
        """Upsert transaction atomically - update if exists, create if not.

        Uses native database UPSERT (ON CONFLICT) to avoid race conditions.
        This is atomic and safe for concurrent requests.

        Args:
            transaction: UnifiedTransaction object to upsert

        Returns:
            Upserted UnifiedTransaction object

        Note:
            This is atomic at the database level - no check-then-act race condition.
        """
        try:
            db = get_db()

            # Prepare complete transaction data for upsert
            txn_data = {
                "account_id": transaction.account_id,
                "external_txn_id": transaction.external_txn_id,
                "txn_date": transaction.txn_date.isoformat(),
                "posted_at": transaction.posted_at.isoformat() if transaction.posted_at else None,
                "authorized_date": transaction.authorized_date.isoformat() if transaction.authorized_date else None,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
                "txn_direction": transaction.txn_direction.value,
                "description_raw": transaction.description_raw,
                "merchant_name_raw": transaction.merchant_name_raw,
                "merchant_logo_url": transaction.merchant_logo_url,
                "merchant_website": transaction.merchant_website,
                "pending": transaction.pending,
                "category": transaction.category,
                "personal_finance_category": transaction.personal_finance_category,
                "payment_channel": transaction.payment_channel,
                "counterparties": transaction.counterparties,
                "location": transaction.location,
                "check_number": transaction.check_number,
                "running_balance": float(transaction.running_balance) if transaction.running_balance else None,
                "provider_metadata": transaction.provider_metadata,
                "raw_payload": transaction.raw_payload,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            # Only set created_at for new records
            txn_data["created_at"] = datetime.now(timezone.utc).isoformat()

            # Atomic upsert using Supabase's upsert() method
            # This uses PostgreSQL's ON CONFLICT internally
            result = db.table("transactions").upsert(
                txn_data,
                on_conflict="external_txn_id"
            ).execute()

            if result.data:
                logger.info(f"Transaction upserted [{hash_transaction_id(transaction.external_txn_id)}]")
                return UnifiedTransaction(**result.data[0])

            raise Exception("Upsert returned no data")

        except Exception as e:
            logger.error(f"Error upserting transaction: {e}", exc_info=True)
            raise

    @staticmethod
    async def upsert_transactions(transactions: List[UnifiedTransaction]) -> List[UnifiedTransaction]:
        """Bulk upsert transactions using native database bulk upsert.

        This method performs a single atomic bulk upsert operation instead of
        N sequential database round-trips, significantly improving performance
        for large transaction batches.

        Args:
            transactions: List of UnifiedTransaction objects to upsert

        Returns:
            List of upserted UnifiedTransaction objects with database-assigned IDs

        Note:
            - Uses PostgreSQL's ON CONFLICT via Supabase's native bulk upsert
            - All operations are atomic within a single database transaction
            - Conflict resolution is based on external_txn_id
        """
        if not transactions:
            return []

        try:
            db = get_db()

            # Build list of transaction dicts for bulk upsert
            txn_data_list = []
            for transaction in transactions:
                txn_data = {
                    "account_id": transaction.account_id,
                    "external_txn_id": transaction.external_txn_id,
                    "txn_date": transaction.txn_date.isoformat(),
                    "posted_at": transaction.posted_at.isoformat() if transaction.posted_at else None,
                    "authorized_date": transaction.authorized_date.isoformat() if transaction.authorized_date else None,
                    "amount": float(transaction.amount),
                    "currency": transaction.currency,
                    "txn_direction": transaction.txn_direction.value,
                    "description_raw": transaction.description_raw,
                    "merchant_name_raw": transaction.merchant_name_raw,
                    "merchant_logo_url": transaction.merchant_logo_url,
                    "merchant_website": transaction.merchant_website,
                    "pending": transaction.pending,
                    "category": transaction.category,
                    "personal_finance_category": transaction.personal_finance_category,
                    "payment_channel": transaction.payment_channel,
                    "counterparties": transaction.counterparties,
                    "location": transaction.location,
                    "check_number": transaction.check_number,
                    "running_balance": float(transaction.running_balance) if transaction.running_balance else None,
                    "provider_metadata": transaction.provider_metadata,
                    "raw_payload": transaction.raw_payload,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                txn_data_list.append(txn_data)

            # Perform atomic bulk upsert using Supabase's native method
            # This uses PostgreSQL's ON CONFLICT internally - single DB round-trip
            result = db.table("transactions").upsert(
                txn_data_list,
                on_conflict="external_txn_id"
            ).execute()

            if result.data:
                logger.info(f"Bulk upserted {len(result.data)} transactions")
                return [UnifiedTransaction(**txn) for txn in result.data]

            raise Exception("Bulk upsert returned no data")

        except Exception as e:
            logger.error(f"Error bulk upserting transactions: {e}", exc_info=True)
            raise

    @staticmethod
    async def delete_transaction(txn_id: int) -> bool:
        """Delete transaction record.

        Args:
            txn_id: Transaction ID to delete

        Returns:
            True if transaction was deleted, False if transaction didn't exist

        Raises:
            Exception: If deletion fails due to database error
        """
        try:
            db = get_db()
            result = db.table("transactions").delete().eq("txn_id", txn_id).execute()

            # Check if any rows were actually deleted
            if result.data and len(result.data) > 0:
                # Use external_txn_id from deleted row for consistent logging
                external_txn_id = result.data[0].get("external_txn_id", str(txn_id))
                logger.info(f"Transaction deleted [{hash_transaction_id(external_txn_id)}]")
                return True
            else:
                logger.warning(f"Transaction not found for deletion [txn_id:{txn_id}]")
                return False

        except Exception as e:
            logger.error(f"Error deleting transaction: {e}", exc_info=True)
            raise

    @staticmethod
    async def delete_transaction_by_external_id(external_txn_id: str) -> bool:
        """Delete transaction by external ID.

        Args:
            external_txn_id: External transaction ID to delete

        Returns:
            True if transaction was deleted, False if transaction didn't exist

        Raises:
            Exception: If deletion fails due to database error
        """
        try:
            db = get_db()
            result = db.table("transactions").delete().eq("external_txn_id", external_txn_id).execute()

            # Check if any rows were actually deleted
            if result.data and len(result.data) > 0:
                logger.info(f"Transaction deleted [{hash_transaction_id(external_txn_id)}]")
                return True
            else:
                logger.warning(f"Transaction not found for deletion [{hash_transaction_id(external_txn_id)}]")
                return False

        except Exception as e:
            logger.error(f"Error deleting transaction by external ID: {e}", exc_info=True)
            raise


# Singleton instance
transaction_service = TransactionService()
