"""Account service - CRUD operations for accounts."""
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.account import UnifiedAccount
from app.models.enums import AccountStatus
from app.utils.logger import logger
from app.utils.logging_security import hash_account_id, hash_user_id


class AccountService:
    """Service for managing accounts."""

    @staticmethod
    def _prepare_account_data(
        account: UnifiedAccount,
        include_created_at: bool = True,
        include_updated_at: bool = True
    ) -> dict:
        """Prepare account data dict for database operations.

        This helper centralizes the account data preparation logic to avoid
        duplication between create_account and upsert_account methods.

        Args:
            account: UnifiedAccount object to convert to dict
            include_created_at: Whether to include created_at timestamp (for INSERT)
            include_updated_at: Whether to include updated_at timestamp

        Returns:
            Dictionary with account data ready for database insertion/update
        """
        account_data = {
            "user_id": str(account.user_id),
            "connection_id": account.connection_id,
            "external_account_id": account.external_account_id,
            "name": account.name,
            "official_name": account.official_name,
            "account_type": account.account_type.value,
            "account_subtype": account.account_subtype.value if account.account_subtype else None,
            "currency": account.currency,
            "mask": account.mask,
            "current_balance": float(account.current_balance) if account.current_balance else None,
            "available_balance": float(account.available_balance) if account.available_balance else None,
            "credit_limit": float(account.credit_limit) if account.credit_limit else None,
            "institution_name": account.institution_name,
            "verification_status": account.verification_status,
            "holder_category": account.holder_category.value if account.holder_category else None,
            "provider_metadata": account.provider_metadata,
            "account_status": account.account_status.value,
            "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Add timestamps based on parameters
        if include_created_at:
            account_data["created_at"] = datetime.now(timezone.utc).isoformat()
        if include_updated_at:
            account_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        return account_data

    @staticmethod
    async def create_account(account: UnifiedAccount) -> UnifiedAccount:
        """Create a new account record."""
        try:
            db = get_db()
            account_data = AccountService._prepare_account_data(
                account,
                include_created_at=True,
                include_updated_at=True
            )

            result = await db.table("accounts").insert(account_data).execute()

            if result.data:
                # Log with hashed identifier for correlation without exposing PII
                logger.info(f"Account created [{hash_account_id(account.external_account_id)}]")
                return UnifiedAccount(**result.data[0])
            raise Exception("Failed to create account")

        except Exception as e:
            logger.error(f"Error creating account: {e}")
            raise

    @staticmethod
    async def get_account(account_id: int) -> Optional[UnifiedAccount]:
        """Get account by ID."""
        try:
            db = get_db()
            result = await db.table("accounts").select("*").eq("account_id", account_id).execute()

            if result.data:
                return UnifiedAccount(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error fetching account: {e}")
            raise

    @staticmethod
    async def get_account_by_external_id(external_account_id: str) -> Optional[UnifiedAccount]:
        """Get account by external account ID."""
        try:
            db = get_db()
            result = await db.table("accounts").select("*").eq("external_account_id", external_account_id).execute()

            if result.data:
                return UnifiedAccount(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error fetching account by external ID: {e}")
            raise

    @staticmethod
    async def get_user_accounts(user_id: UUID) -> List[UnifiedAccount]:
        """Get all accounts for a user."""
        try:
            db = get_db()
            result = await db.table("accounts").select("*").eq("user_id", str(user_id)).execute()
            return [UnifiedAccount(**acc) for acc in result.data]

        except Exception as e:
            logger.error(f"Error fetching user accounts: {e}")
            raise

    @staticmethod
    async def get_accounts_by_connection(connection_id: int) -> List[UnifiedAccount]:
        """Get all accounts for a connection."""
        try:
            db = get_db()
            result = await db.table("accounts").select("*").eq("connection_id", connection_id).execute()
            return [UnifiedAccount(**acc) for acc in result.data]

        except Exception as e:
            logger.error(f"Error fetching accounts by connection: {e}")
            raise

    @staticmethod
    async def update_account(account_id: int, updates: dict) -> UnifiedAccount:
        """Update account record."""
        try:
            db = get_db()

            # Fetch account to get external_account_id for consistent logging
            account_lookup = await db.table("accounts").select("external_account_id").eq("account_id", account_id).execute()
            if not account_lookup.data:
                raise Exception("Account not found")

            external_account_id = account_lookup.data[0]["external_account_id"]

            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Convert Decimal to float for JSON serialization
            if "current_balance" in updates and updates["current_balance"] is not None:
                updates["current_balance"] = float(updates["current_balance"])
            if "available_balance" in updates and updates["available_balance"] is not None:
                updates["available_balance"] = float(updates["available_balance"])
            if "credit_limit" in updates and updates["credit_limit"] is not None:
                updates["credit_limit"] = float(updates["credit_limit"])

            result = await db.table("accounts").update(updates).eq("account_id", account_id).execute()

            if result.data:
                logger.info(f"Account updated [{hash_account_id(external_account_id)}]")
                return UnifiedAccount(**result.data[0])
            raise Exception("Account not found")

        except Exception as e:
            logger.error(f"Error updating account: {e}")
            raise

    @staticmethod
    async def update_account_balance(
        account_id: int,
        current_balance: Optional[float] = None,
        available_balance: Optional[float] = None
    ) -> UnifiedAccount:
        """Update account balances."""
        updates = {"last_refreshed_at": datetime.now(timezone.utc).isoformat()}

        if current_balance is not None:
            updates["current_balance"] = current_balance
        if available_balance is not None:
            updates["available_balance"] = available_balance

        return await AccountService.update_account(account_id, updates)

    @staticmethod
    async def upsert_account(account: UnifiedAccount) -> UnifiedAccount:
        """Upsert account atomically - update if exists, create if not.

        Uses check-then-act pattern to ensure immutable fields are never updated:
        - Identity fields (user_id, connection_id, external_account_id) are immutable
        - created_at timestamp is preserved on updates (only set on INSERT)

        Updates all provider-sourced fields that may change over time, including:
        - Account metadata (name, official_name, institution_name, mask)
        - Account classification (account_type, account_subtype, currency)
        - Balances and limits (current_balance, available_balance, credit_limit)
        - Status fields (verification_status, holder_category, account_status)
        - Provider-specific metadata
        - updated_at timestamp (always updated)

        Implementation:
        - Checks if account exists by external_account_id
        - If exists: UPDATE with mutable fields only (excludes created_at and identity fields)
        - If not exists: INSERT with all fields (includes created_at and identity fields)

        Note: This replaces the previous database-level UPSERT which would incorrectly
        overwrite created_at on updates. The check-then-act pattern ensures proper
        timestamp preservation.
        """
        try:
            db = get_db()

            # Prepare complete account data for INSERT (includes all fields)
            # This payload is used ONLY when creating new accounts
            insert_data = AccountService._prepare_account_data(
                account,
                include_created_at=True,  # Set creation timestamp for new records
                include_updated_at=True
            )

            # Prepare UPDATE data (excludes immutable identity fields)
            # This payload is used ONLY when updating existing accounts
            # created_at is excluded to preserve the original creation timestamp
            update_data = AccountService._prepare_account_data(
                account,
                include_created_at=False,  # Never overwrite original created_at
                include_updated_at=True   # Always update the updated_at timestamp
            )
            # Remove immutable identity fields from update payload
            # These fields define the record's identity and must never change
            for field in ["user_id", "connection_id", "external_account_id"]:
                update_data.pop(field, None)

            # Check if account exists
            existing = db.table("accounts").select("account_id").eq(
                "external_account_id", account.external_account_id
            ).execute()

            if existing.data and len(existing.data) > 0:
                # Account exists - UPDATE only mutable fields
                result = db.table("accounts").update(update_data).eq(
                    "external_account_id", account.external_account_id
                ).execute()

                if result.data:
                    logger.info(
                        f"Account updated [{hash_account_id(account.external_account_id)}] "
                        f"for user [{hash_user_id(str(account.user_id))}]"
                    )
                    return UnifiedAccount(**result.data[0])
            else:
                # Account doesn't exist - INSERT with all fields
                result = db.table("accounts").insert(insert_data).execute()

                if result.data:
                    logger.info(
                        f"Account created [{hash_account_id(account.external_account_id)}] "
                        f"for user [{hash_user_id(str(account.user_id))}]"
                    )
                    return UnifiedAccount(**result.data[0])

            raise Exception("Upsert returned no data")

        except Exception as e:
            logger.error(
                f"Error upserting account [{hash_account_id(account.external_account_id)}]: {e}",
                exc_info=True
            )
            raise

    @staticmethod
    async def upsert_accounts(accounts: List[UnifiedAccount]) -> List[UnifiedAccount]:
        """Bulk upsert accounts concurrently with partial failure handling.

        Uses asyncio.gather with return_exceptions=True to process multiple account
        upserts in parallel. If some accounts fail, successful upserts are still returned.

        Args:
            accounts: List of UnifiedAccount objects to upsert

        Returns:
            List of successfully upserted UnifiedAccount objects (order preserved for successes)

        Raises:
            Exception: If ALL accounts fail to upsert (with details of all failures)

        Note:
            Partial failures are logged but don't stop the batch. Check logs for failed accounts.
        """
        if not accounts:
            return []

        tasks = [AccountService.upsert_account(account) for account in accounts]

        # return_exceptions=True prevents one failure from canceling the entire batch
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successes from failures (preserve order)
        successes = []
        failures = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Failure - log with context
                account = accounts[i]
                error_context = {
                    "external_account_id": account.external_account_id,
                    "account_name": account.name,
                    "error": str(result)
                }
                failures.append(error_context)
                logger.error(
                    f"Failed to upsert account in batch "
                    f"[{hash_account_id(account.external_account_id)}]: {result}",
                    exc_info=(type(result), result, result.__traceback__)
                )
            else:
                # Success
                successes.append(result)

        # Log summary
        total = len(accounts)
        success_count = len(successes)
        failure_count = len(failures)

        if failure_count > 0:
            logger.warning(
                f"Batch upsert completed with partial failures: "
                f"{success_count}/{total} succeeded, {failure_count}/{total} failed"
            )

        # If ALL failed, raise an exception with details
        if failure_count == total:
            error_summary = "; ".join(
                f"{f['external_account_id']}: {f['error']}"
                for f in failures[:5]  # Limit to first 5 for brevity
            )
            if failure_count > 5:
                error_summary += f" (and {failure_count - 5} more)"

            raise Exception(
                f"All {total} accounts failed to upsert. Errors: {error_summary}"
            )

        # Return successful upserts (order matches successful accounts)
        logger.info(f"Batch upsert completed: {success_count}/{total} accounts upserted successfully")
        return successes

    @staticmethod
    async def delete_account(account_id: int) -> bool:
        """Delete account record.

        Args:
            account_id: Account ID to delete

        Returns:
            True if account was deleted, False if account didn't exist

        Raises:
            Exception: If deletion fails due to database error
        """
        try:
            db = get_db()

            # Fetch account to get external_account_id for consistent logging
            account_lookup = await db.table("accounts").select("external_account_id").eq("account_id", account_id).execute()
            if not account_lookup.data:
                logger.warning(f"Account not found for deletion [account_id:{account_id}]")
                return False

            external_account_id = account_lookup.data[0]["external_account_id"]

            result = await db.table("accounts").delete().eq("account_id", account_id).execute()

            # Check if any rows were actually deleted
            if result.data and len(result.data) > 0:
                logger.info(f"Account deleted [{hash_account_id(external_account_id)}]")
                return True
            else:
                logger.warning(f"Account not found for deletion [{hash_account_id(external_account_id)}]")
                return False

        except Exception as e:
            logger.error(f"Error deleting account: {e}", exc_info=True)
            raise


# Singleton instance
account_service = AccountService()
