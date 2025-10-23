"""
Database connection management for Supabase PostgreSQL
"""

import logging
import psycopg2
from typing import Dict, Any, List, Tuple, Optional
from contextlib import contextmanager

from ..config import Text2SQLConfig

logger = logging.getLogger(__name__)


class SupabaseDatabaseManager:
    """
    Manages database connections to Supabase PostgreSQL using direct psycopg2 connection
    """

    def __init__(self):
        """Initialize the database manager"""
        self._connection = None
        self.config = Text2SQLConfig()
        logger.info("✅ Supabase database manager initialized")

    def connect(self) -> None:
        """Establish connection to Supabase PostgreSQL"""
        try:
            # Get Supabase PostgreSQL connection config
            db_config = self.config.get_supabase_db_config()

            logger.info(f"Connecting to Supabase PostgreSQL at {db_config['host']}...")

            self._connection = psycopg2.connect(**db_config)
            logger.info("✅ Connected to Supabase PostgreSQL")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase PostgreSQL: {e}")
            raise Exception(f"Failed to connect to Supabase PostgreSQL: {e}")

    def disconnect(self) -> None:
        """Close database connection"""
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                logger.info("✅ Database connection closed")
            except Exception as e:
                logger.error(f"❌ Failed to close database connection: {e}")

    def is_connected(self) -> bool:
        """Check if database connection is active"""
        if not self._connection:
            return False
        try:
            # Test connection with a simple query
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            return False

    def ensure_connection(self) -> None:
        """Ensure database connection is active, reconnect if needed"""
        if not self.is_connected():
            logger.info("Reconnecting to Supabase PostgreSQL...")
            self.connect()

    @contextmanager
    def get_cursor(self):
        """Get a database cursor with automatic cleanup"""
        self.ensure_connection()
        cursor = self._connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute_raw_sql(
        self, sql: str, params: Optional[Tuple] = None, fetch_results: bool = True
    ) -> Dict[str, Any]:
        """
        Execute SQL query using direct PostgreSQL connection

        Args:
            sql: SQL query string with %s placeholders
            params: Query parameters tuple (user_id)
            fetch_results: Whether to fetch results (default: True)

        Returns:
            Dict with query results and metadata
        """
        import time

        start_time = time.time()

        try:
            logger.info(f"📝 Executing SQL: {sql}")
            if params:
                logger.info(f"   With params: {params}")

            with self.get_cursor() as cursor:
                # Execute the query
                cursor.execute(sql, params or ())

                if fetch_results and sql.strip().upper().startswith('SELECT'):
                    # Fetch all results
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    row_count = len(rows)
                else:
                    rows = []
                    columns = []
                    row_count = cursor.rowcount
                    if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                        self._connection.commit()

                execution_time = time.time() - start_time
                logger.info(
                    f"✅ Query executed in {execution_time:.3f}s, returned {row_count} rows"
                )

                return {
                    "success": True,
                    "rows": rows,
                    "columns": columns,
                    "row_count": row_count,
                    "execution_time": execution_time,
                    "sql": sql,
                    "params": params,
                }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Database query failed: {e}")

            # Try to rollback the transaction
            try:
                if self._connection:
                    self._connection.rollback()
            except Exception:
                pass

            raise Exception(f"Failed to execute query: {e}")

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            result = self.execute_raw_sql("SELECT 1 as test")
            return result["success"] and result["rows"][0][0] == 1
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False

    def get_user_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user

        Args:
            user_id: User UUID

        Returns:
            List of account dictionaries
        """
        try:
            sql = "SELECT * FROM accounts WHERE user_id = %s"
            result = self.execute_raw_sql(sql, (user_id,))

            # Convert tuples to dicts
            accounts = []
            for row in result['rows']:
                account = {}
                for i, col in enumerate(result['columns']):
                    account[col] = row[i]
                accounts.append(account)

            return accounts
        except Exception as e:
            logger.error(f"Failed to get user accounts: {e}")
            return []

    def get_user_transactions(
        self, user_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent transactions for a user

        Args:
            user_id: User UUID
            limit: Maximum number of transactions to return

        Returns:
            List of transaction dictionaries
        """
        try:
            sql = """
                SELECT t.*
                FROM transactions t
                JOIN accounts a ON t.account_id = a.account_id
                WHERE a.user_id = %s
                ORDER BY t.txn_date DESC
                LIMIT %s
            """
            result = self.execute_raw_sql(sql, (user_id, limit))

            # Convert tuples to dicts
            transactions = []
            for row in result['rows']:
                transaction = {}
                for i, col in enumerate(result['columns']):
                    transaction[col] = row[i]
                transactions.append(transaction)

            return transactions
        except Exception as e:
            logger.error(f"Failed to get user transactions: {e}")
            return []

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Global database manager instance
_db_manager = None


def get_db_manager() -> SupabaseDatabaseManager:
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = SupabaseDatabaseManager()
    return _db_manager
