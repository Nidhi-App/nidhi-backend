"""
SQL generator function for text2sql system using OpenAI's GPT-5
"""

import logging
import re
import requests
from typing import Dict, Any, Tuple, Optional
from .base_function import BaseFunction
from ..config import Text2SQLConfig, get_schema_info
from ..core.exceptions import SQLGenerationError, OpenAIAPIError, OpenAIConnectionError
from ..cache import get_cache_manager
from ..cache.normalization import normalize_query

logger = logging.getLogger(__name__)

class SQLGenerator(BaseFunction):
    """
    Function that converts natural language queries to SQL using OpenAI GPT-5 model

    Extracts the SQL generation logic from the monolithic GPT5Text2SQL class
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize SQL Generator

        Args:
            openai_api_key: OpenAI API key (uses config if not provided)
        """
        super().__init__(
            name="sql_generator",
            description="Generate SQL query from natural language",
            required_inputs=["user_query", "user_id"],
            optional_inputs=["context", "schema_info"]
        )
        self.config = Text2SQLConfig()
        self.openai_api_key = openai_api_key or self.config.OPENAI_API_KEY
        self.model = self.config.OPENAI_MODEL
        self.schema_info = get_schema_info()
        self.system_prompt = self._create_system_prompt()
        self.cache_manager = get_cache_manager()

        if not self.openai_api_key:
            logger.warning("⚠️  OpenAI API key not found - SQL generation will fail")
        elif len(self.openai_api_key) < 20:
            logger.error("❌ OpenAI API key appears to be truncated or invalid")
            logger.info("💡 Please check your .env file and ensure OPENAI_API_KEY is set correctly")
        else:
            logger.info("✅ OpenAI API key found")

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute SQL generation from natural language query

        Args:
            input_data: Must contain 'user_query' and 'user_id'

        Returns:
            Dict with 'success', 'sql', 'params', and metadata
        """
        user_query = input_data.get('user_query')
        user_id = input_data.get('user_id')
        context = input_data.get('context', '')

        if not self.openai_api_key:
            raise SQLGenerationError("OpenAI API key is required for SQL generation", user_query=user_query)

        try:
            logger.info(f"Generating SQL for user_query: '{user_query}' with user_id: {user_id}")

            # Generate the SQL query
            sql_query, params = self._generate_sql_query(user_query, user_id, context)

            logger.info(f"Generated SQL: {sql_query}")
            logger.info(f"With params: {params}")

            return {
                'success': True,
                'sql': sql_query,
                'params': params,
                'user_query': user_query,
                'user_id': user_id,
                'model_used': self.model,
            }
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise SQLGenerationError(f"Failed to generate SQL: {e}", user_query=user_query)

    def _generate_sql_query(self, user_query: str, user_id: str, context: str = "") -> Tuple[str, tuple]:
        """
        Generate SQL query using OpenAI GPT-5

        Args:
            user_query: Natural language query
            user_id: User ID
            context: Additional context
        Returns:
            Tuple of (sql_query, parameters)
        """
        try:
            # Normalize query for better cache hits
            normalized_query = normalize_query(user_query)
            logger.debug(f"Normalized query: '{user_query}' → '{normalized_query}'")

            # Create cache key for SQL generation using normalized query
            cache_key = self.cache_manager.create_cache_key(
                "sql_gen",
                user_id,
                normalized_query,  # Use normalized query instead of raw query
                context=context,
                model=self.model,
                schema=self.schema_info[:200]  # Use first 200 chars of schema for cache key
            )

            # Check cache first
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.info(f"✅ Cache HIT for SQL generation: {user_query}")
                logger.info(f"   Matched normalized query: {normalized_query}")
                return cached_result["sql"], cached_result["params"]

            logger.info(f"❌ Cache MISS for SQL generation: {user_query}")
            logger.info(f"   Normalized query: {normalized_query}")

            # Prepare the input for GPT-5 with user context
            full_context = f"{context}\n" if context else ""
            input_text = (
                f"{self.system_prompt}\n\n"
                f"{full_context}"
                f"User Query: '{user_query}'\n"
                f"User ID: {user_id}\n"
                f"Convert this query to SQL for user_id {user_id}:"
            )

            logger.info("🤖 Sending request to GPT-5...")

            # Make request to OpenAI API
            response = self._make_openai_request(input_text)

            # Extract the SQL query from the response
            sql_query = self._extract_sql_from_response(response)

            # Clean and validate the SQL query
            sql_query = self._clean_sql_query(sql_query)

            # Parameters (user_id is always the first parameter)
            params = (user_id,)

            # Cache the result
            cache_value = {
                "sql": sql_query,
                "params": params
            }
            self.cache_manager.set(
                cache_key,
                cache_value,
                ttl=self.cache_manager.config.LLM_SQL_GENERATION_TTL
            )
            logger.info(f"📦 Cached SQL generation result for: {user_query}")

            return sql_query, params

        except Exception as e:
            logger.error(f"Failed to generate SQL query: {e}")
            raise SQLGenerationError(f"Failed to generate SQL query: {e}", user_query=user_query)

    def _make_openai_request(self, input_text: str) -> Dict[str, Any]:
        """
        Make request to OpenAI API

        Args:
            input_text: Input text for the request

        Returns:
            Dictionary containing the response
        """
        try:
            url = f"{self.config.OPENAI_BASE_URL}/responses"
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                "model": self.model,
                "input": input_text,
                "reasoning": {"effort": "low"},
                "text": {"verbosity": "low"}
            }

            response = requests.post(url, json=data, headers=headers, timeout=self.config.OPENAI_TIMEOUT)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                raise OpenAIAPIError(
                    f"OpenAI API request failed: {str(e)}",
                    status_code=status_code
                )
            else:
                raise OpenAIConnectionError(f"Failed to connect to OpenAI API: {str(e)}")

    def _extract_sql_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract SQL query from OpenAI API response

        Args:
            response: OpenAI API response

        Returns:
            Extracted SQL query string
        """
        sql_query = None

        if 'output' in response and isinstance(response['output'], list):
            for output_item in response['output']:
                if output_item.get('type') == 'message' and 'content' in output_item:
                    for content_item in output_item['content']:
                        if content_item.get('type') == 'output_text' and 'text' in content_item:
                            sql_query = content_item['text']
                            break
                    if sql_query:
                        break

        if not sql_query:
            raise SQLGenerationError("No SQL query found in OpenAI API response")

        return sql_query.strip()

    def _clean_sql_query(self, sql_query: str) -> str:
        """
        Clean and normalize the SQL query

        Args:
            sql_query: SQL query to clean and validate

        Returns:
            Cleaned SQL query
        """
        # Remove markdown code blocks
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.startswith("```"):
            sql_query = sql_query[3:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]

        # Remove extra quotes if present
        if (sql_query.startswith('"') and sql_query.endswith('"')) or (sql_query.startswith("'") and sql_query.endswith("'")):
            sql_query = sql_query[1:-1]

        sql_query = sql_query.strip()

        # Convert PostgreSQL $1, $2, etc. to psycopg2 %s format
        sql_query = re.sub(r'\$(\d+)', '%s', sql_query)

        return sql_query


    def _create_system_prompt(self) -> str:
        """
        Create system prompt for GPT model

        Returns:
            System prompt string
        """
        return f"""
You are an expert SQL developer specializing in PostgreSQL queries for financial data.

{self.schema_info}

Rules:
1. Always use parameterized queries with %s placeholders
2. Always filter by user_id for data security - use the provided user_id context
3. Use proper JOINs when accessing both accounts and transactions
4. Return clean, executable SQL without explanations
5. Use meaningful column aliases
6. Handle date filtering properly with PostgreSQL functions
7. Use appropriate aggregation functions (SUM, COUNT, AVG, etc.)
8. Order results logically (by date DESC, amount DESC, etc.)
9. Generate only the SQL query, no explanations or markdown formatting
"""

    def test_connection(self) -> bool:
        """
        Test connection to OpenAI API

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            logger.info("🧪 Testing OpenAI API connection...")

            test_input = "Hello, are you working?"

            response = self._make_openai_request(test_input)

            logger.info("✅ OpenAI API connection successful!")
            logger.info(f"Test response: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to test connection to OpenAI API: {e}")
            return False
