"""
Main pipeline orchestrator for the text2sql system
"""

import logging
from typing import Dict, Any, Optional
from ..agents.llm_agent import LLMAgent
from ..core.exceptions import Text2SQLException

logger = logging.getLogger(__name__)


class Text2SQLPipeline:
    """
    Main pipeline class that provides a simple interface to the text2sql system
    
    This replaces the monolithic application entry points
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the Text2SQL Pipeline
        
        Args:
            openai_api_key: OpenAI API key (uses config if not provided)
        """
        self.agent = LLMAgent(openai_api_key)
        
        logger.info("✅ Text2SQL Pipeline initialized")
    
    def process_query(
        self, 
        user_query: str, 
        user_id: str,
        context: str = "",
        skip_validation: bool = False,
        skip_response_generation: bool = False
    ) -> Dict[str, Any]:
        """
        Process a natural language query through the complete pipeline
        
        Args:
            user_query: Natural language query
            user_id: User ID for data isolation
            context: Additional context for the query
            skip_validation: Skip SQL validation step
            skip_response_generation: Skip natural language response generation
            
        Returns:
            Complete pipeline result
        """
        input_data = {
            'user_query': user_query,
            'user_id': user_id,
            'context': context,
            'skip_validation': skip_validation,
            'skip_response_generation': skip_response_generation
        }
        
        return self.agent.execute(input_data)
    
    def process_query_simple(self, user_query: str, user_id: str) -> str:
        """
        Process a query and return just the natural language response
        
        Args:
            user_query: Natural language query
            user_id: User ID for data isolation
            
        Returns:
            Natural language response string
        """
        result = self.process_query(user_query, user_id)
        
        if result['success']:
            return result.get('response', 'Query processed successfully but no response generated.')
        else:
            return f"Sorry, I encountered an error: {result.get('error', 'Unknown error')}"
    
    def get_sql_only(self, user_query: str, user_id: str) -> Dict[str, Any]:
        """
        Generate and execute SQL without validation or response generation
        
        Args:
            user_query: Natural language query
            user_id: User ID for data isolation
            
        Returns:
            SQL generation and execution result
        """
        result = self.process_query(
            user_query, 
            user_id, 
            skip_validation=True, 
            skip_response_generation=True
        )
        
        if result['success']:
            return {
                'success': True,
                'sql': result['sql'],
                'params': result['params'],
                'rows': result['query_result']['rows'],
                'columns': result['query_result']['columns'],
                'row_count': result['query_result']['row_count']
            }
        else:
            return {
                'success': False,
                'error': result['error']
            }
    
    def test_system(self) -> Dict[str, Any]:
        """
        Test all components of the system
        
        Returns:
            Test results for all components
        """
        logger.info("🧪 Testing Text2SQL system...")
        
        # Test all functions
        function_tests = self.agent.test_all_functions()
        
        # Test with a simple query
        integration_test = False
        integration_error = None
        
        try:
            test_result = self.process_query(
                "Show me a test query", 
                user_id="test-user-id",
                skip_validation=True,
                skip_response_generation=True
            )
            integration_test = test_result.get('success', False)
            if not integration_test:
                integration_error = test_result.get('error')
        except Exception as e:
            integration_error = str(e)
        
        results = {
            'function_tests': function_tests,
            'integration_test': integration_test,
            'integration_error': integration_error,
            'overall_status': all(function_tests.values()) and integration_test
        }
        
        if results['overall_status']:
            logger.info("✅ All system tests passed")
        else:
            logger.error("❌ Some system tests failed")
        
        return results
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics
        
        Returns:
            System statistics
        """
        return self.agent.get_pipeline_stats()
    
    def reset_stats(self) -> None:
        """Reset all system statistics"""
        self.agent.reset_stats()
        for func_name in self.agent.list_functions():
            func = self.agent.get_function(func_name)
            if hasattr(func, 'reset_stats'):
                func.reset_stats()
        
        logger.info("🔄 System statistics reset")


# Global pipeline instance
_pipeline = None


def get_pipeline(openai_api_key: Optional[str] = None) -> Text2SQLPipeline:
    """
    Get the global pipeline instance
    
    Args:
        openai_api_key: OpenAI API key (uses config if not provided)
        
    Returns:
        Text2SQL Pipeline instance
    """
    global _pipeline
    if _pipeline is None:
        _pipeline = Text2SQLPipeline(openai_api_key)
    return _pipeline


def process_query(user_query: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to process a query using the global pipeline
    
    Args:
        user_query: Natural language query
        user_id: User ID for data isolation
        **kwargs: Additional arguments for process_query
        
    Returns:
        Pipeline result
    """
    pipeline = get_pipeline()
    return pipeline.process_query(user_query, user_id, **kwargs)


def process_query_simple(user_query: str, user_id: str) -> str:
    """
    Convenience function to get a simple response using the global pipeline
    
    Args:
        user_query: Natural language query
        user_id: User ID for data isolation
        
    Returns:
        Natural language response string
    """
    pipeline = get_pipeline()
    return pipeline.process_query_simple(user_query, user_id)
