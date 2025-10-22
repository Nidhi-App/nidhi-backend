"""
Database operations for Supabase
Handles all CRUD operations for providers, connections, accounts, and transactions
"""

import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseOperations:
    """Handle database operations with Supabase"""

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

        self.supabase: Client = create_client(supabase_url, supabase_key)

    # Provider Operations
    def create_or_get_provider(self, name: str = "Fake Bank Provider") -> int:
        """
        Create or retrieve fake bank provider

        Args:
            name: Provider name

        Returns:
            Provider ID
        """
        # Check if provider exists
        response = self.supabase.table("providers").select("provider_id").eq("name", name).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]["provider_id"]

        # Create new provider
        provider_data = {
            "name": name,
            "is_aa_aggregator": False,
            "website": "https://nidhi-fi.app",
        }

        response = self.supabase.table("providers").insert(provider_data).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]["provider_id"]

        raise Exception("Failed to create provider")

    # Connection Operations
    def create_connection(self, connection_data: Dict[str, Any]) -> int:
        """
        Create connection between user and institution

        Args:
            connection_data: Connection data dictionary

        Returns:
            Connection ID
        """
        response = self.supabase.table("connections").insert(connection_data).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]["connection_id"]

        raise Exception("Failed to create connection")

    def get_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all connections for a user

        Args:
            user_id: User UUID

        Returns:
            List of connections
        """
        response = self.supabase.table("connections").select("*").eq("user_id", user_id).execute()

        return response.data if response.data else []

    # Account Operations
    def create_account(self, account_data: Dict[str, Any]) -> int:
        """
        Insert account into accounts table

        Args:
            account_data: Account data dictionary

        Returns:
            Account ID
        """
        response = self.supabase.table("accounts").insert(account_data).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]["account_id"]

        raise Exception("Failed to create account")

    def create_accounts_batch(self, accounts_data: List[Dict[str, Any]]) -> List[int]:
        """
        Batch insert accounts

        Args:
            accounts_data: List of account data dictionaries

        Returns:
            List of account IDs
        """
        response = self.supabase.table("accounts").insert(accounts_data).execute()

        if response.data:
            return [account["account_id"] for account in response.data]

        raise Exception("Failed to create accounts")

    def get_user_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all accounts for a user

        Args:
            user_id: User UUID

        Returns:
            List of accounts
        """
        response = (
            self.supabase.table("accounts")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return response.data if response.data else []

    def get_account_by_id(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        Get account by ID

        Args:
            account_id: Account ID

        Returns:
            Account data or None
        """
        response = self.supabase.table("accounts").select("*").eq("account_id", account_id).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]

        return None

    def update_account_balance(self, account_id: int, new_balance: float) -> bool:
        """
        Update account current_balance

        Args:
            account_id: Account ID
            new_balance: New balance value

        Returns:
            Success status
        """
        response = (
            self.supabase.table("accounts")
            .update({"current_balance": new_balance})
            .eq("account_id", account_id)
            .execute()
        )

        return response.data is not None

    # Transaction Operations
    def create_transaction(self, transaction_data: Dict[str, Any]) -> int:
        """
        Insert single transaction

        Args:
            transaction_data: Transaction data dictionary

        Returns:
            Transaction ID
        """
        response = self.supabase.table("transactions").insert(transaction_data).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]["transaction_id"]

        raise Exception("Failed to create transaction")

    def bulk_create_transactions(self, transactions_data: List[Dict[str, Any]]) -> int:
        """
        Batch insert transactions (use batching for performance)

        Args:
            transactions_data: List of transaction data dictionaries

        Returns:
            Number of transactions created
        """
        # Supabase has a limit on batch insert size, so we'll batch in chunks
        batch_size = 500
        total_created = 0

        for i in range(0, len(transactions_data), batch_size):
            batch = transactions_data[i : i + batch_size]

            try:
                response = self.supabase.table("transactions").insert(batch).execute()

                if response.data:
                    total_created += len(response.data)
            except Exception as e:
                print(f"Error inserting batch {i // batch_size + 1}: {str(e)}")
                # Continue with next batch even if one fails
                continue

        return total_created

    def get_account_transactions(
        self, account_id: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for an account

        Args:
            account_id: Account ID
            limit: Maximum number of transactions to retrieve

        Returns:
            List of transactions
        """
        response = (
            self.supabase.table("transactions")
            .select("*")
            .eq("account_id", account_id)
            .order("txn_date", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data if response.data else []

    def get_transaction_count_for_account(self, account_id: int) -> int:
        """
        Get count of transactions for an account

        Args:
            account_id: Account ID

        Returns:
            Transaction count
        """
        response = (
            self.supabase.table("transactions")
            .select("transaction_id", count="exact")
            .eq("account_id", account_id)
            .execute()
        )

        return response.count if response.count else 0

    # Summary Operations
    def get_user_accounts_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get summary of user's accounts with transaction counts

        Args:
            user_id: User UUID

        Returns:
            Summary data
        """
        accounts = self.get_user_accounts(user_id)

        accounts_with_counts = []
        total_balance = 0.0

        for account in accounts:
            account_id = account["account_id"]
            transaction_count = self.get_transaction_count_for_account(account_id)

            accounts_with_counts.append(
                {
                    "account_id": account_id,
                    "name": account["name"],
                    "mask": account.get("mask"),
                    "account_type": account["account_type"],
                    "account_subtype": account.get("account_subtype"),
                    "current_balance": account["current_balance"],
                    "currency": account.get("currency", "USD"),
                    "institution_name": account.get("institution_name"),
                    "transaction_count": transaction_count,
                }
            )

            # Sum balances (only for depository accounts)
            if account["account_type"] == "depository":
                total_balance += float(account["current_balance"])

        return {
            "total_accounts": len(accounts),
            "total_balance": round(total_balance, 2),
            "accounts": accounts_with_counts,
        }

    # Validation Operations
    def verify_account_ownership(self, account_id: int, user_id: str) -> bool:
        """
        Verify that an account belongs to a user

        Args:
            account_id: Account ID
            user_id: User UUID

        Returns:
            True if account belongs to user, False otherwise
        """
        response = (
            self.supabase.table("accounts")
            .select("account_id")
            .eq("account_id", account_id)
            .eq("user_id", user_id)
            .execute()
        )

        return response.data is not None and len(response.data) > 0

    def verify_accounts_ownership(self, account_ids: List[int], user_id: str) -> bool:
        """
        Verify that all accounts belong to a user

        Args:
            account_ids: List of account IDs
            user_id: User UUID

        Returns:
            True if all accounts belong to user, False otherwise
        """
        response = (
            self.supabase.table("accounts")
            .select("account_id")
            .in_("account_id", account_ids)
            .eq("user_id", user_id)
            .execute()
        )

        return response.data is not None and len(response.data) == len(account_ids)
