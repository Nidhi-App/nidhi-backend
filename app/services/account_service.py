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
    async def create_account(account: UnifiedAccount) -> UnifiedAccount:
        """Create a new account record."""
        try:
            db = get_db()
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
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

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
        """Upsert account - update if exists, create if not.

        Updates all provider-sourced fields that may change over time, including:
        - Account metadata (name, official_name, institution_name, mask)
        - Account classification (account_type, account_subtype, currency)
        - Balances and limits (current_balance, available_balance, credit_limit)
        - Status fields (verification_status, holder_category, account_status)
        - Provider-specific metadata

        Note: user_id, connection_id, and external_account_id are immutable after creation.
        """
        try:
            existing = await AccountService.get_account_by_external_id(account.external_account_id)

            if existing:
                # Update existing account with all provider-sourced fields
                updates = {
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
                    "last_refreshed_at": datetime.now(timezone.utc).isoformat()
                }
                return await AccountService.update_account(existing.account_id, updates)
            else:
                # Create new account
                return await AccountService.create_account(account)

        except Exception as e:
            logger.error(f"Error upserting account: {e}")
            raise

    @staticmethod
    async def upsert_accounts(accounts: List[UnifiedAccount]) -> List[UnifiedAccount]:
        """Bulk upsert accounts concurrently for better performance.

        Uses asyncio.gather to process multiple account upserts in parallel,
        significantly improving performance when syncing large numbers of accounts.

        Args:
            accounts: List of UnifiedAccount objects to upsert

        Returns:
            List of upserted UnifiedAccount objects in the same order as input
        """
        tasks = [AccountService.upsert_account(account) for account in accounts]
        results = await asyncio.gather(*tasks)
        return list(results)

    @staticmethod
    async def delete_account(account_id: int) -> bool:
        """Delete account record."""
        try:
            db = get_db()

            # Fetch account to get external_account_id for consistent logging
            account_lookup = await db.table("accounts").select("external_account_id").eq("account_id", account_id).execute()
            if not account_lookup.data:
                raise Exception("Account not found")

            external_account_id = account_lookup.data[0]["external_account_id"]

            await db.table("accounts").delete().eq("account_id", account_id).execute()
            logger.info(f"Account deleted [{hash_account_id(external_account_id)}]")
            return True

        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            raise


# Singleton instance
account_service = AccountService()
