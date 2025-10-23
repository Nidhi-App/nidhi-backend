"""
SQL Generator using OpenAI to convert natural language to SQL
"""

import logging
import re
import requests
from typing import Dict, Any, Tuple, Optional

from .config import config, get_schema_info

logger = logging.getLogger(__name__)


class SQLGenerator:
    """
    Converts natural language queries to SQL using OpenAI
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize SQL Generator

        Args:
            openai_api_key: OpenAI API key (uses config if not provided)
        """
        self.openai_api_key = openai_api_key or config.OPENAI_API_KEY
        self.model = config.OPENAI_MODEL
        self.schema_info = get_schema_info()
        self.system_prompt = self._create_system_prompt()

        if not self.openai_api_key:
            logger.warning("⚠️  OpenAI API key not found - SQL generation will fail")
        else:
            logger.info("✅ OpenAI API key configured")

    def _create_system_prompt(self) -> str:
        """Create the system prompt for SQL generation"""
        return f"""You are an expert SQL query generator for a financial database.

{self.schema_info}

Your task is to convert natural language queries into valid PostgreSQL SQL queries.

RULES:
1. ALWAYS filter by user_id for security
2. Use %s as placeholder for user_id parameter (NEVER hardcode the user_id value)
3. Return ONLY the SQL query, no explanations
4. Use proper JOINs when querying transactions
5. Handle date ranges intelligently (e.g., "this month", "last 30 days")
6. Return meaningful column aliases
7. Use appropriate aggregations (SUM, COUNT, AVG) when asked for totals or summaries

OUTPUT FORMAT:
Return ONLY the SQL query on a single line or multiple lines. No markdown, no code blocks, no explanations.
"""

    def generate_sql(
        self, user_query: str, user_id: str, context: str = ""
    ) -> Tuple[str, tuple]:
        """
        Generate SQL query from natural language

        Args:
            user_query: Natural language query
            user_id: User ID for filtering
            context: Additional context (optional)

        Returns:
            Tuple of (sql_query, parameters)
        """
        if not self.openai_api_key:
            raise Exception("OpenAI API key is required for SQL generation")

        try:
            logger.info(f"🤖 Generating SQL for query: '{user_query}'")
            logger.info(f"   User ID: {user_id}")

            # Prepare the input
            full_context = f"{context}\n" if context else ""
            input_text = (
                f"{self.system_prompt}\n\n"
                f"{full_context}"
                f"User Query: '{user_query}'\n"
                f"User ID (for filtering): {user_id}\n\n"
                f"Generate PostgreSQL SQL query with %s placeholder for user_id:"
            )

            # Call OpenAI API
            response = self._make_openai_request(input_text)

            # Extract SQL from response
            sql_query = self._extract_sql_from_response(response)

            # Clean the SQL
            sql_query = self._clean_sql_query(sql_query)

            # Parameters (user_id is the first parameter)
            params = (user_id,)

            logger.info(f"✅ Generated SQL: {sql_query}")
            logger.info(f"   Parameters: {params}")

            return sql_query, params

        except Exception as e:
            logger.error(f"❌ Failed to generate SQL: {e}")
            raise Exception(f"Failed to generate SQL query: {e}")

    def _make_openai_request(self, input_text: str) -> Dict[str, Any]:
        """
        Make request to OpenAI API using the /responses endpoint for gpt-5-nano

        Args:
            input_text: Input prompt

        Returns:
            Response dictionary from OpenAI
        """
        try:
            url = f"{config.OPENAI_BASE_URL}/responses"
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "input": input_text,
                "reasoning": {"effort": "low"},
                "text": {"verbosity": "low"}
            }

            logger.info(f"📡 Calling OpenAI API with model: {self.model}")

            response = requests.post(
                url, headers=headers, json=data, timeout=config.OPENAI_TIMEOUT
            )

            if response.status_code != 200:
                error_detail = response.text
                logger.error(
                    f"OpenAI API error {response.status_code}: {error_detail}"
                )
                raise Exception(f"OpenAI API error: {error_detail}")

            response_data = response.json()
            return response_data

        except requests.exceptions.Timeout:
            logger.error("OpenAI API request timed out")
            raise Exception("OpenAI API request timed out")
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise Exception(f"OpenAI API request failed: {e}")
        except Exception as e:
            logger.error(f"Failed to make OpenAI request: {e}")
            raise

    def _extract_sql_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract SQL query from OpenAI response (gpt-5-nano format)

        Args:
            response: Response dictionary from OpenAI

        Returns:
            Extracted SQL query
        """
        sql_text = None

        # Parse the gpt-5-nano response format
        if 'output' in response and isinstance(response['output'], list):
            for output_item in response['output']:
                if output_item.get('type') == 'message' and 'content' in output_item:
                    for content_item in output_item['content']:
                        if content_item.get('type') == 'output_text' and 'text' in content_item:
                            sql_text = content_item['text']
                            break
                    if sql_text:
                        break

        if not sql_text:
            raise Exception("No SQL query found in OpenAI API response")

        # Remove markdown code blocks if present
        sql_text = sql_text.strip()

        # Remove ```sql and ``` markers
        sql_text = re.sub(r"```sql\s*", "", sql_text)
        sql_text = re.sub(r"```\s*", "", sql_text)

        # Remove any explanatory text after the query
        lines = sql_text.split("\n")
        sql_lines = []

        for line in lines:
            # Skip comments and explanations
            if line.strip().startswith("--"):
                continue
            if line.strip().startswith("#"):
                continue
            if not line.strip():
                continue

            sql_lines.append(line)

            # Stop if we hit a clear explanation line
            if any(
                keyword in line.lower()
                for keyword in ["explanation:", "note:", "this query"]
            ):
                break

        sql_text = "\n".join(sql_lines)
        return sql_text.strip()

    def _clean_sql_query(self, sql: str) -> str:
        """
        Clean and validate SQL query

        Args:
            sql: Raw SQL query

        Returns:
            Cleaned SQL query
        """
        # Remove extra whitespace
        sql = " ".join(sql.split())

        # Ensure it ends with semicolon (optional but good practice)
        if not sql.endswith(";"):
            sql = sql + ";"

        # Basic validation - check for required elements
        sql_upper = sql.upper()

        if "SELECT" not in sql_upper:
            raise Exception("Generated SQL must be a SELECT query")

        # Check for user_id filtering (security requirement)
        if "%S" not in sql_upper and "USER_ID" not in sql_upper:
            logger.warning(
                "⚠️  Generated SQL may not filter by user_id - this is a security concern!"
            )

        return sql


# Global SQL generator instance
_sql_generator = None


def get_sql_generator() -> SQLGenerator:
    """Get the global SQL generator instance"""
    global _sql_generator
    if _sql_generator is None:
        _sql_generator = SQLGenerator()
    return _sql_generator
