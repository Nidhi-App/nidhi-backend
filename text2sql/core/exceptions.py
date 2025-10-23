"""
Custom exceptions for the text2sql system
"""

from typing import Optional, Dict, Any


class Text2SQLException(Exception):
    """Base exception for all text2sql related errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context
        }


class ConfigurationError(Text2SQLException):
    """Raised when there are configuration-related issues"""
    pass


class DatabaseConnectionError(Text2SQLException):
    """Raised when database connection fails"""

    def __init__(self, message: str, db_config: Optional[Dict[str, Any]] = None):
        context = {'db_config': db_config} if db_config else {}
        super().__init__(message, error_code="DB_CONNECTION_FAILED", context=context)


class DatabaseExecutionError(Text2SQLException):
    """Raised when SQL execution fails"""

    def __init__(self, message: str, sql: Optional[str] = None, params: Optional[tuple] = None):
        context = {}
        if sql:
            context['sql'] = sql
        if params:
            context['params'] = params
        super().__init__(message, error_code="SQL_EXECUTION_FAILED", context=context)


class OpenAIConnectionError(Text2SQLException):
    """Raised when OpenAI API connection fails"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        context = {'status_code': status_code} if status_code else {}
        super().__init__(message, error_code="OPENAI_CONNECTION_FAILED", context=context)


class OpenAIAPIError(Text2SQLException):
    """Raised when OpenAI API returns an error"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        context = {}
        if status_code:
            context['status_code'] = status_code
        if response_data:
            context['response_data'] = response_data
        super().__init__(message, error_code="OPENAI_API_ERROR", context=context)


class SQLGenerationError(Text2SQLException):
    """Raised when SQL generation fails"""

    def __init__(self, message: str, user_query: Optional[str] = None):
        context = {'user_query': user_query} if user_query else {}
        super().__init__(message, error_code="SQL_GENERATION_FAILED", context=context)


class SQLValidationError(Text2SQLException):
    """Raised when SQL validation fails"""

    def __init__(
        self,
        message: str,
        sql: Optional[str] = None,
        validation_details: Optional[Dict[str, Any]] = None
    ):
        context = {}
        if sql:
            context['sql'] = sql
        if validation_details:
            context['validation_details'] = validation_details
        super().__init__(message, error_code="SQL_VALIDATION_FAILED", context=context)


class ResponseGenerationError(Text2SQLException):
    """Raised when natural language response generation fails"""

    def __init__(
        self,
        message: str,
        user_query: Optional[str] = None,
        query_result: Optional[Dict[str, Any]] = None
    ):
        context = {}
        if user_query:
            context['user_query'] = user_query
        if query_result:
            context['query_result'] = query_result
        super().__init__(message, error_code="RESPONSE_GENERATION_FAILED", context=context)


class ValidationError(Text2SQLException):
    """Raised when input validation fails"""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None
    ):
        context = {}
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = str(field_value)
        super().__init__(message, error_code="VALIDATION_ERROR", context=context)


# Exception mapping for HTTP status codes (useful for API layer)
EXCEPTION_STATUS_MAPPING = {
    Text2SQLException: 500,
    ConfigurationError: 500,
    DatabaseConnectionError: 503,
    DatabaseExecutionError: 422,
    OpenAIConnectionError: 503,
    OpenAIAPIError: 502,
    SQLGenerationError: 422,
    SQLValidationError: 422,
    ResponseGenerationError: 500,
    ValidationError: 400,
}


def get_http_status_for_exception(exception: Exception) -> int:
    """Get appropriate HTTP status code for an exception"""
    for exc_type, status_code in EXCEPTION_STATUS_MAPPING.items():
        if isinstance(exception, exc_type):
            return status_code
    return 500  # Default to 500 for unknown exceptions
