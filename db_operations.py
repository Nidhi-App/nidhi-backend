"""
Database operations for Supabase
Handles all CRUD operations for providers, connections, accounts, and transactions
"""

import os
from typing import List, Dict, Any, Optional
from uuid import UUID
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

    def create_accounts_batch(self, accounts_data: List[Dict[str, Any]]) -> List[UUID]:
        """
        Batch insert accounts

        Args:
            accounts_data: List of account data dictionaries

        Returns:
            List of account UUIDs
        """
        response = self.supabase.table("accounts").insert(accounts_data).execute()

        if response.data:
            return [UUID(str(account["account_id"])) for account in response.data]

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

    def get_account_by_id(self, account_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get account by ID

        Args:
            account_id: Account UUID

        Returns:
            Account data or None
        """
        response = self.supabase.table("accounts").select("*").eq("account_id", str(account_id)).execute()

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

    def verify_accounts_ownership(self, account_ids: List[UUID], user_id: str) -> bool:
        """
        Verify that all accounts belong to a user

        Args:
            account_ids: List of account UUIDs
            user_id: User UUID

        Returns:
            True if all accounts belong to user, False otherwise
        """
        # Convert UUIDs to strings for Supabase query
        account_id_strings = [str(aid) for aid in account_ids]

        response = (
            self.supabase.table("accounts")
            .select("account_id")
            .in_("account_id", account_id_strings)
            .eq("user_id", user_id)
            .execute()
        )

        return response.data is not None and len(response.data) == len(account_ids)

    # ========================================================================
    # Conversation Operations
    # ========================================================================

    def create_conversation(
        self, user_id: str, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation for a user

        Args:
            user_id: User UUID
            title: Conversation title (optional, can be generated later)
            metadata: Additional metadata (optional)

        Returns:
            Conversation data including conversation_id
        """
        conversation_data = {
            "user_id": user_id,
            "title": title,
            "metadata": metadata or {},
        }

        response = self.supabase.table("conversations").insert(conversation_data).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]

        raise Exception("Failed to create conversation")

    def get_user_conversations(
        self, user_id: str, include_archived: bool = False, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get conversations for a user with pagination

        Args:
            user_id: User UUID
            include_archived: Whether to include archived conversations
            limit: Maximum number of conversations to return
            offset: Offset for pagination

        Returns:
            List of conversations ordered by last_message_at DESC
        """
        query = (
            self.supabase.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_deleted", False)
        )

        if not include_archived:
            query = query.eq("is_archived", False)

        response = (
            query.order("last_message_at", desc=True)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return response.data if response.data else []

    def get_conversation_by_id(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific conversation by ID with ownership verification

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID (for ownership verification)

        Returns:
            Conversation data or None if not found/not authorized
        """
        response = (
            self.supabase.table("conversations")
            .select("*")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .eq("is_deleted", False)
            .execute()
        )

        if response.data and len(response.data) > 0:
            return response.data[0]

        return None

    def update_conversation_title(self, conversation_id: str, user_id: str, title: str) -> bool:
        """
        Update conversation title

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID (for ownership verification)
            title: New title

        Returns:
            True if updated successfully
        """
        response = (
            self.supabase.table("conversations")
            .update({"title": title})
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )

        return response.data is not None and len(response.data) > 0

    def archive_conversation(self, conversation_id: str, user_id: str, archived: bool = True) -> bool:
        """
        Archive or unarchive a conversation

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID (for ownership verification)
            archived: True to archive, False to unarchive

        Returns:
            True if updated successfully
        """
        response = (
            self.supabase.table("conversations")
            .update({"is_archived": archived})
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )

        return response.data is not None and len(response.data) > 0

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        Soft delete a conversation (sets is_deleted = True)

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID (for ownership verification)

        Returns:
            True if deleted successfully
        """
        response = (
            self.supabase.table("conversations")
            .update({"is_deleted": True})
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )

        return response.data is not None and len(response.data) > 0

    # ========================================================================
    # Message Operations
    # ========================================================================

    def add_message(
        self,
        conversation_id: str,
        role: str,  # 'user', 'assistant', 'system'
        content: str,
        sql_query: Optional[str] = None,
        sql_params: Optional[List[Any]] = None,
        query_results_summary: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
        error: Optional[str] = None,
        model_version: Optional[str] = None,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation

        Args:
            conversation_id: Conversation UUID
            role: Message role ('user', 'assistant', 'system')
            content: Message content (max 10,000 chars)
            sql_query: Generated SQL query (for assistant messages)
            sql_params: SQL parameters
            query_results_summary: Summary of query results {row_count, sample_rows}
            execution_time: Execution time in seconds
            error: Error message if any
            model_version: Model version used (e.g., 'gpt-4')
            token_count: Token count for cost tracking
            metadata: Additional metadata (cache_hit, etc.)

        Returns:
            Message data including message_id
        """
        # Truncate content if too long
        if len(content) > 10000:
            content = content[:10000]

        message_data = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sql_query": sql_query,
            "sql_params": sql_params,
            "query_results_summary": query_results_summary,
            "execution_time": execution_time,
            "error": error,
            "model_version": model_version,
            "token_count": token_count,
            "metadata": metadata or {},
        }

        response = self.supabase.table("messages").insert(message_data).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]

        raise Exception("Failed to add message")

    def get_conversation_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        order_desc: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation with pagination

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID (for ownership verification)
            limit: Maximum number of messages to return
            offset: Offset for pagination
            order_desc: If True, order by created_at DESC, else ASC

        Returns:
            List of messages
        """
        # First verify conversation ownership
        conversation = self.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            return []

        query = (
            self.supabase.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
        )

        if order_desc:
            query = query.order("created_at", desc=True)
        else:
            query = query.order("created_at", desc=False)

        response = query.range(offset, offset + limit - 1).execute()

        return response.data if response.data else []

    def get_last_n_messages(
        self, conversation_id: str, user_id: str, n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get last N messages for context (ordered chronologically)

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID (for ownership verification)
            n: Number of messages to retrieve

        Returns:
            List of last N messages in chronological order (oldest first)
        """
        # Get messages in DESC order (newest first)
        messages_desc = self.get_conversation_messages(
            conversation_id, user_id, limit=n, offset=0, order_desc=True
        )

        # Reverse to get chronological order (oldest first)
        return list(reversed(messages_desc))

    def get_conversation_message_count(self, conversation_id: str, user_id: str) -> int:
        """
        Get total message count for a conversation

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID (for ownership verification)

        Returns:
            Total number of messages
        """
        # First verify conversation ownership
        conversation = self.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            return 0

        response = (
            self.supabase.table("messages")
            .select("message_id", count="exact")
            .eq("conversation_id", conversation_id)
            .execute()
        )

        return response.count if response.count else 0
