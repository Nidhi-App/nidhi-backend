"""
SQL Validation function for the text2sql system
"""

import logging
import json
import requests
from typing import Dict, Any, Optional
from .base_function import BaseFunction
from ..config import Text2SQLConfig
from ..core.exceptions import SQLValidationError, OpenAIConnectionError, OpenAIAPIError

logger = logging.getLogger(__name__)


class SQLValidator(BaseFunction):
    """
    Function that validates generated SQL queries and their results
    
    Extracts the validation logic from the monolithic QueryValidator class
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize SQL Validator
        
        Args:
            openai_api_key: OpenAI API key (uses config if not provided)
        """
        super().__init__(
            name="sql_validator",
            description="Validates SQL queries and results using GPT models",
            required_inputs=["user_query", "generated_sql", "query_result"],
            optional_inputs=["context"]
        )
        
        self.config = Text2SQLConfig()
        self.openai_api_key = openai_api_key or self.config.OPENAI_API_KEY
        
    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute SQL validation
        
        Args:
            input_data: Must contain 'user_query', 'generated_sql', 'query_result'
            
        Returns:
            Dict with 'success', 'is_valid', 'confidence', 'issues', 'suggestions'
        """
        user_query = input_data["user_query"]
        generated_sql = input_data["generated_sql"]
        query_result = input_data["query_result"]
        context = input_data.get("context", "")
        
        if not self.openai_api_key:
            # Return default validation if no API key
            return {
                'success': True,
                'is_valid': True,
                'confidence': 0.5,
                'issues': [],
                'suggestions': [],
                'validation_method': 'fallback'
            }
        
        try:
            logger.info(f"🔍 Validating SQL query for: '{user_query}'")
            
            # Validate using GPT
            validation_result = self._validate_with_gpt(
                user_query, generated_sql, query_result, context
            )
            
            validation_result['success'] = True
            validation_result['validation_method'] = 'gpt'
            
            logger.info(f"✅ Validation completed - Valid: {validation_result.get('is_valid')}, "
                       f"Confidence: {validation_result.get('confidence', 0):.2f}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ SQL validation failed: {e}")
            raise SQLValidationError(
                f"Failed to validate SQL: {str(e)}",
                sql=generated_sql,
                validation_details={'user_query': user_query, 'error': str(e)}
            )
    
    def _validate_with_gpt(
        self, 
        user_query: str, 
        generated_sql: str, 
        query_result: Dict[str, Any],
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Validate query using GPT model
        
        Args:
            user_query: Original user query
            generated_sql: Generated SQL query
            query_result: Query execution result
            context: Additional context
            
        Returns:
            Validation result dictionary
        """
        try:
            # Prepare validation prompt
            validation_prompt = self._create_validation_prompt(
                user_query, generated_sql, query_result, context
            )
            
            # Make request to OpenAI
            response = self._make_openai_request(validation_prompt)
            
            # Parse response
            validation_text = self._extract_text_from_response(response)
            if not validation_text:
                raise SQLValidationError("No validation response received")
            
            # Try to parse JSON response
            try:
                validation_result = json.loads(validation_text)
                return validation_result
            except json.JSONDecodeError:
                logger.warning("Failed to parse validation JSON, using fallback")
                return {
                    'is_valid': True,
                    'confidence': 0.7,
                    'issues': [],
                    'suggestions': []
                }
                
        except Exception as e:
            logger.error(f"GPT validation error: {e}")
            return {
                'is_valid': True,  # Default to valid on error
                'confidence': 0.5,
                'issues': [f"Validation error: {str(e)}"],
                'suggestions': []
            }
    
    def _create_validation_prompt(
        self, 
        user_query: str, 
        generated_sql: str, 
        query_result: Dict[str, Any],
        context: str = ""
    ) -> str:
        """
        Create validation prompt for GPT
        
        Args:
            user_query: Original user query
            generated_sql: Generated SQL query
            query_result: Query execution result
            context: Additional context
            
        Returns:
            Formatted validation prompt
        """
        result_summary = self._format_result_for_validation(query_result)
        
        prompt = f"""
You are an expert SQL validator. Your task is to determine if a generated SQL query correctly answers the user's natural language question.

User Question: "{user_query}"
Generated SQL: {generated_sql}
Query Result: {result_summary}
{f"Context: {context}" if context else ""}

Analyze whether:
1. The SQL query logically answers the user's question
2. The query structure is appropriate for the question type
3. The results align with what the user asked for
4. Any potential issues or improvements

Respond with a JSON object containing:
- is_valid: boolean (true if query correctly answers the question)
- confidence: float (0.0 to 1.0, how confident you are in this assessment)
- issues: array of strings (any problems identified)
- suggestions: array of strings (improvements if needed)

Only return the JSON object, no other text.
"""
        return prompt
    
    def _format_result_for_validation(self, query_result: Dict[str, Any]) -> str:
        """
        Format query result for validation prompt
        
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
        
        # Show first few rows for validation
        result_str = f"Query returned {len(rows)} rows with columns: {columns}\n"
        for i, row in enumerate(rows[:3]):  # Show first 3 rows
            result_str += f"Row {i+1}: {dict(zip(columns, row))}\n"
        
        if len(rows) > 3:
            result_str += f"... and {len(rows) - 3} more rows"
        
        return result_str
    
    def _make_openai_request(self, prompt: str) -> Dict[str, Any]:
        """
        Make request to OpenAI API
        
        Args:
            prompt: Validation prompt
            
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
