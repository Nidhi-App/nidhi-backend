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
                logger.info(f"Transaction updated [{hash_transaction_id(txn_id)}]")
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
        """Upsert transaction - update if exists, create if not."""
        try:
            existing = await TransactionService.get_transaction_by_external_id(transaction.external_txn_id)

            if existing:
                # Update existing transaction
                updates = {
                    "txn_date": transaction.txn_date.isoformat(),
                    "posted_at": transaction.posted_at.isoformat() if transaction.posted_at else None,
                    "authorized_date": transaction.authorized_date.isoformat() if transaction.authorized_date else None,
                    "amount": float(transaction.amount),
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
                    "raw_payload": transaction.raw_payload
                }
                return await TransactionService.update_transaction(existing.txn_id, updates)
            else:
                # Create new transaction
                return await TransactionService.create_transaction(transaction)

        except Exception as e:
            logger.error(f"Error upserting transaction: {e}")
            raise

    @staticmethod
    async def upsert_transactions(transactions: List[UnifiedTransaction]) -> List[UnifiedTransaction]:
        """Bulk upsert transactions."""
        results = []
        for transaction in transactions:
            result = await TransactionService.upsert_transaction(transaction)
            results.append(result)
        return results

    @staticmethod
    async def delete_transaction(txn_id: int) -> bool:
        """Delete transaction record."""
        try:
            db = get_db()
            db.table("transactions").delete().eq("txn_id", txn_id).execute()
            logger.info(f"Transaction deleted [{hash_transaction_id(txn_id)}]")
            return True

        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            raise

    @staticmethod
    async def delete_transaction_by_external_id(external_txn_id: str) -> bool:
        """Delete transaction by external ID."""
        try:
            db = get_db()
            db.table("transactions").delete().eq("external_txn_id", external_txn_id).execute()
            logger.info(f"Transaction deleted [{hash_transaction_id(external_txn_id)}]")
            return True

        except Exception as e:
            logger.error(f"Error deleting transaction by external ID: {e}")
            raise


# Singleton instance
transaction_service = TransactionService()
