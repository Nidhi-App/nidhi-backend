"""
SQL Execution function for the text2sql system
"""

import logging
from typing import Dict, Any, Optional, Tuple
from .base_function import BaseFunction
from ..database import get_db_manager
from ..core.exceptions import DatabaseExecutionError, ValidationError

logger = logging.getLogger(__name__)


class SQLExecutor(BaseFunction):
    """
    Function that safely executes SQL queries against the database
    
    Extracts the SQL execution logic from the monolithic GPT5Text2SQL class
    """
    
    def __init__(self, db_manager=None):
        """
        Initialize SQL Executor
        
        Args:
            db_manager: Database manager instance (uses global if not provided)
        """
        super().__init__(
            name="sql_executor",
            description="Executes SQL queries safely against the database",
            required_inputs=["sql", "params"],
            optional_inputs=["user_id", "timeout", "fetch_results"]
        )
        
        self.db_manager = db_manager or get_db_manager()
        
    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute SQL query safely
        
        Args:
            input_data: Must contain 'sql' and 'params'
                       Optional: 'user_id', 'timeout', 'fetch_results'
            
        Returns:
            Dict with 'success', 'rows', 'columns', 'row_count', and metadata
        """
        sql = input_data["sql"]
        params = input_data["params"]
        user_id = input_data.get("user_id")
        fetch_results = input_data.get("fetch_results", True)
        
        # Validate inputs
        self._validate_sql_input(sql, params, user_id)
        
        try:
            logger.info(f"🔄 Executing SQL query")
            logger.debug(f"SQL: {sql}")
            logger.debug(f"Params: {params}")
            
            # Execute query using database manager
            result = self.db_manager.execute_raw_sql(
                sql=sql,
                params=params,
                fetch_results=fetch_results
            )
            
            # Add additional metadata
            result.update({
                'user_id': user_id,
                'query_type': self._get_query_type(sql),
                'parameter_count': len(params) if params else 0
            })
            
            logger.info(f"✅ SQL executed successfully - {result['row_count']} rows affected")
            
            return result
            
        except DatabaseExecutionError:
            # Re-raise database errors as-is
            raise
        except Exception as e:
            logger.error(f"❌ SQL execution failed: {e}")
            raise DatabaseExecutionError(
                f"Failed to execute SQL: {str(e)}",
                sql=sql,
                params=params
            )
    
    def _validate_sql_input(self, sql: str, params: Tuple, user_id: Optional[str]) -> None:
        """
        Validate SQL query input for security and correctness
        
        Args:
            sql: SQL query string
            params: Query parameters
            user_id: User ID (optional)
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(sql, str) or not sql.strip():
            raise ValidationError("SQL query must be a non-empty string", field_name="sql")
        
        if not isinstance(params, (tuple, list)):
            raise ValidationError("Parameters must be a tuple or list", field_name="params")
        
        # Basic SQL injection protection
        sql_upper = sql.upper().strip()
        
        # Check for dangerous SQL patterns
        dangerous_patterns = [
            "DROP TABLE", "DROP DATABASE", "DELETE FROM", "TRUNCATE",
            "ALTER TABLE", "CREATE TABLE", "INSERT INTO", "UPDATE SET"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in sql_upper and not self._is_safe_operation(sql_upper, pattern):
                raise ValidationError(
                    f"Potentially dangerous SQL operation detected: {pattern}",
                    field_name="sql",
                    field_value=sql
                )
        
        # Ensure user_id filtering for SELECT statements
        if sql_upper.startswith("SELECT") and user_id is not None:
            # Check if query has user_id filtering (in WHERE clause)
            if "USER_ID" not in sql_upper or "WHERE" not in sql_upper:
                logger.warning("⚠️  SELECT query does not filter by user_id - potential data leak risk")
        
        # Validate parameter count
        param_placeholders = sql.count("%s")
        param_count = len(params) if params else 0
        
        if param_placeholders != param_count:
            raise ValidationError(
                f"Parameter count mismatch: query has {param_placeholders} placeholders but {param_count} parameters provided",
                field_name="params"
            )
    
    def _is_safe_operation(self, sql_upper: str, pattern: str) -> bool:
        """
        Check if a potentially dangerous operation is actually safe
        
        Args:
            sql_upper: Uppercase SQL query
            pattern: Dangerous pattern detected
            
        Returns:
            True if operation is safe, False otherwise
        """
        # Allow certain patterns in specific contexts
        if pattern == "DELETE FROM" and "WHERE user_id" in sql_upper:
            return True  # User-scoped deletes might be OK
        
        if pattern == "UPDATE SET" and "WHERE user_id" in sql_upper:
            return True  # User-scoped updates might be OK
        
        # For now, block all other dangerous operations
        return False
    
    def _get_query_type(self, sql: str) -> str:
        """
        Determine the type of SQL query
        
        Args:
            sql: SQL query string
            
        Returns:
            Query type string
        """
        sql_upper = sql.upper().strip()
        
        if sql_upper.startswith("SELECT"):
            return "SELECT"
        elif sql_upper.startswith("INSERT"):
            return "INSERT"
        elif sql_upper.startswith("UPDATE"):
            return "UPDATE"
        elif sql_upper.startswith("DELETE"):
            return "DELETE"
        elif sql_upper.startswith("CREATE"):
            return "CREATE"
        elif sql_upper.startswith("ALTER"):
            return "ALTER"
        elif sql_upper.startswith("DROP"):
            return "DROP"
        else:
            return "OTHER"
    
    def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("🧪 Testing database connection...")
            return self.db_manager.test_connection()
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False
