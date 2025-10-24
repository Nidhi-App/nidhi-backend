"""
Natural Language Response Generation function for the text2sql system
"""

import logging
import requests
from typing import Dict, Any, Optional
from .base_function import BaseFunction
from ..config import Text2SQLConfig
from ..core.exceptions import ResponseGenerationError, OpenAIConnectionError, OpenAIAPIError
from ..cache import get_cache_manager

logger = logging.getLogger(__name__)


class ResponseGenerator(BaseFunction):
    """
    Function that generates natural language responses from SQL query results

    Extracts the response generation logic from the monolithic NaturalLanguageGenerator class
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize Response Generator

        Args:
            openai_api_key: OpenAI API key (uses config if not provided)
        """
        super().__init__(
            name="response_generator",
            description="Generates natural language responses from query results",
            required_inputs=["user_query", "query_result"],
            optional_inputs=["validation_result", "context"]
        )

        self.config = Text2SQLConfig()
        self.openai_api_key = openai_api_key or self.config.OPENAI_API_KEY
        self.cache_manager = get_cache_manager()

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute natural language response generation

        Args:
            input_data: Must contain 'user_query' and 'query_result'
                       Optional: 'validation_result', 'context'

        Returns:
            Dict with 'success', 'response', and metadata
        """
        user_query = input_data["user_query"]
        query_result = input_data["query_result"]
        validation_result = input_data.get("validation_result")
        context = input_data.get("context", "")

        try:
            logger.info(f"📝 Generating response for query: '{user_query}'")

            if not self.openai_api_key:
                # Use fallback response if no API key
                response_text = self._fallback_response(user_query, query_result)
                method = 'fallback'
            else:
                # Generate using GPT
                response_text = self._generate_with_gpt(
                    user_query, query_result, validation_result, context
                )
                method = 'gpt'

            logger.info(f"✅ Response generated using {method} method")

            return {
                'success': True,
                'response': response_text,
                'generation_method': method,
                'user_query': user_query,
                'has_validation': validation_result is not None
            }

        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            raise ResponseGenerationError(
                f"Failed to generate response: {str(e)}",
                user_query=user_query,
                query_result=query_result
            )

    def _generate_with_gpt(
        self,
        user_query: str,
        query_result: Dict[str, Any],
        validation_result: Optional[Dict[str, Any]] = None,
        context: str = ""
    ) -> str:
        """
        Generate response using GPT model

        Args:
            user_query: Original user query
            query_result: Query execution result
            validation_result: Query validation result
            context: Additional context

        Returns:
            Generated natural language response
        """
        try:
            # Get user_id from query_result if available
            user_id = query_result.get("user_id", "unknown")

            # Create cache key for response generation
            # Use row count and column structure as part of cache key
            result_summary = f"rows:{query_result.get('row_count', 0)}_cols:{len(query_result.get('columns', []))}"
            cache_key = self.cache_manager.create_cache_key(
                "response_gen",
                user_id,
                user_query,
                result=result_summary,
                context=context
            )

            # Check cache first
            cached_response = self.cache_manager.get(cache_key)
            if cached_response:
                logger.info(f"✅ Cache HIT for response generation")
                return cached_response

            logger.info(f"❌ Cache MISS for response generation")

            # Prepare response generation prompt
            response_prompt = self._create_response_prompt(
                user_query, query_result, validation_result, context
            )

            # Make request to OpenAI
            response = self._make_openai_request(response_prompt)

            # Extract response text
            response_text = self._extract_text_from_response(response)
            if not response_text:
                raise ResponseGenerationError("No response text received from OpenAI")

            response_text = response_text.strip()

            # Cache the generated response
            self.cache_manager.set(
                cache_key,
                response_text,
                ttl=self.cache_manager.config.LLM_RESPONSE_TTL
            )
            logger.info(f"📦 Cached response generation result")

            return response_text

        except Exception as e:
            logger.error(f"GPT response generation failed: {e}")
            return self._fallback_response(user_query, query_result)

    def _create_response_prompt(
        self,
        user_query: str,
        query_result: Dict[str, Any],
        validation_result: Optional[Dict[str, Any]] = None,
        context: str = ""
    ) -> str:
        """
        Create response generation prompt for GPT

        Args:
            user_query: Original user query
            query_result: Query execution result
            validation_result: Query validation result
            context: Additional context

        Returns:
            Formatted response prompt
        """
        result_summary = self._format_result_for_response(query_result)
        validation_info = ""

        if validation_result:
            validation_info = f"\nQuery Validation: {validation_result}"

        prompt = f"""
You are a helpful financial assistant. Convert the SQL query results into a natural, conversational response for the user.

User's Question: "{user_query}"
Query Results: {result_summary}
{validation_info}
{f"Context: {context}" if context else ""}

Guidelines:
1. Provide a clear, conversational response
2. Include specific numbers and data from the results
3. If there are many results, summarize the key insights
4. If the query failed or returned no results, explain this helpfully
5. If validation shows issues, mention them appropriately
6. Use currency formatting where appropriate
7. Make the response engaging and easy to understand

Respond naturally as if talking to the user directly. Do not mention SQL or technical details unless necessary.
"""
        return prompt

    def _format_result_for_response(self, query_result: Dict[str, Any]) -> str:
        """
        Format query result for response generation

        Args:
            query_result: Query execution result

        Returns:
            Formatted result string
        """
        if not query_result.get('success'):
            return f"Query failed with error: {query_result.get('error', 'Unknown error')}"

        rows = query_result.get('rows', [])
        columns = query_result.get('columns', [])

        if not rows:
            return "Query executed successfully but returned no results."

        # Format results for natural language generation
        result_str = f"Found {len(rows)} results:\n"
        for i, row in enumerate(rows[:10]):  # Show first 10 rows
            result_str += f"- {dict(zip(columns, row))}\n"

        if len(rows) > 10:
            result_str += f"... and {len(rows) - 10} more results"

        return result_str

    def _fallback_response(self, user_query: str, query_result: Dict[str, Any]) -> str:
        """
        Generate a simple fallback response when GPT is not available

        Args:
            user_query: Original user query
            query_result: Query execution result

        Returns:
            Simple fallback response
        """
        if not query_result.get('success'):
            return f"I encountered an error while processing your request: {query_result.get('error', 'Unknown error')}"

        rows = query_result.get('rows', [])
        columns = query_result.get('columns', [])

        if not rows:
            return "I didn't find any results for your query."

        if len(rows) == 1:
            result_dict = dict(zip(columns, rows[0]))
            return f"Here's what I found: {result_dict}"
        else:
            return f"I found {len(rows)} results. Here are the first few: {[dict(zip(columns, row)) for row in rows[:3]]}"

    def _make_openai_request(self, prompt: str) -> Dict[str, Any]:
        """
        Make request to OpenAI API

        Args:
            prompt: Response generation prompt

        Returns:
            API response as dictionary
        """
        try:
            url = f"{self.config.OPENAI_BASE_URL}/responses"
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                "model": self.config.OPENAI_MODEL,
                "input": prompt,
                "reasoning": {"effort": "low"},
                "text": {"verbosity": "low"}
            }

            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=self.config.OPENAI_TIMEOUT
            )
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

    def _extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text from OpenAI API response

        Args:
            response: OpenAI API response

        Returns:
            Extracted text
        """
        if 'output' in response and isinstance(response['output'], list):
            for output_item in response['output']:
                if output_item.get('type') == 'message' and 'content' in output_item:
                    for content_item in output_item['content']:
                        if content_item.get('type') == 'output_text' and 'text' in content_item:
                            return content_item['text']
        return None
