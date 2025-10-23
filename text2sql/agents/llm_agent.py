"""
LLM Agent that orchestrates the complete text2sql pipeline
"""

import logging
import time
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from ..functions.sql_generator import SQLGenerator
from ..functions.sql_executor import SQLExecutor
from ..functions.sql_validator import SQLValidator
from ..functions.response_generator import ResponseGenerator
from ..core.exceptions import Text2SQLException, ValidationError

logger = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    """
    Main agent that orchestrates the complete text2sql pipeline
    
    Replaces the monolithic Text2SQLWithValidation class
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize LLM Agent
        
        Args:
            openai_api_key: OpenAI API key for GPT functions
        """
        super().__init__(
            name="llm_agent",
            description="Orchestrates the complete text2sql pipeline with validation and NL responses"
        )
        
        # Initialize and register all functions
        self.register_function(SQLGenerator(openai_api_key))
        self.register_function(SQLExecutor())
        self.register_function(SQLValidator(openai_api_key))
        self.register_function(ResponseGenerator(openai_api_key))
        
        logger.info("✅ LLM Agent initialized with all text2sql functions")
    
    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute the complete text2sql pipeline
        
        Args:
            input_data: Must contain 'user_query' and 'user_id'
                       Optional: 'context', 'skip_validation', 'skip_response_generation'
            
        Returns:
            Complete pipeline result with all intermediate steps
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data):
                return {
                    'success': False,
                    'error': 'Invalid input data',
                    'execution_time': time.time() - start_time
                }
            
            user_query = input_data['user_query']
            user_id = input_data['user_id']
            context = input_data.get('context', '')
            skip_validation = input_data.get('skip_validation', False)
            skip_response_generation = input_data.get('skip_response_generation', False)
            
            logger.info(f"🔄 Processing query: '{user_query}' for user {user_id}")
            
            # Step 1: Generate SQL
            logger.info("🤖 Step 1: Generating SQL...")
            sql_input = {
                'user_query': user_query,
                'user_id': user_id,
                'context': context
            }
            sql_result = self.get_function("sql_generator").run(sql_input)
            
            if not sql_result['success']:
                return self._create_error_result(
                    "SQL generation failed", 
                    sql_result.get('error', 'Unknown error'),
                    start_time,
                    sql_result=sql_result
                )
            
            # Step 2: Execute SQL
            logger.info("⚡ Step 2: Executing SQL...")
            execution_input = {
                'sql': sql_result['sql'],
                'params': sql_result['params'],
                'user_id': user_id
            }
            execution_result = self.get_function("sql_executor").run(execution_input)
            
            if not execution_result['success']:
                return self._create_error_result(
                    "SQL execution failed",
                    execution_result.get('error', 'Unknown error'),
                    start_time,
                    sql_result=sql_result,
                    execution_result=execution_result
                )
            
            # Step 3: Validate results (optional)
            validation_result = None
            if not skip_validation:
                logger.info("🔍 Step 3: Validating query...")
                validation_input = {
                    'user_query': user_query,
                    'generated_sql': sql_result['sql'],
                    'query_result': execution_result,
                    'context': context
                }
                validation_result = self.get_function("sql_validator").run(validation_input)
                
                if not validation_result['success']:
                    logger.warning(f"⚠️  Validation failed: {validation_result.get('error')}")
                    # Continue even if validation fails
            
            # Step 4: Generate natural language response (optional)
            response_result = None
            if not skip_response_generation:
                logger.info("📝 Step 4: Generating response...")
                response_input = {
                    'user_query': user_query,
                    'query_result': execution_result,
                    'validation_result': validation_result,
                    'context': context
                }
                response_result = self.get_function("response_generator").run(response_input)
                
                if not response_result['success']:
                    logger.warning(f"⚠️  Response generation failed: {response_result.get('error')}")
                    # Continue even if response generation fails
            
            # Combine all results
            total_time = time.time() - start_time

            final_result = {
                'success': True,
                'user_query': user_query,
                'user_id': user_id,
                'sql': sql_result['sql'],
                'params': sql_result['params'],
                'query_result': execution_result,
                'validation': validation_result,
                'response': response_result.get('response') if response_result else None,
                'total_time': total_time,
                'timing': {
                    'sql_generation': sql_result.get('execution_time', 0),
                    'sql_execution': execution_result.get('execution_time', 0),
                    'validation': validation_result.get('execution_time', 0) if validation_result else 0,
                    'response_generation': response_result.get('execution_time', 0) if response_result else 0,
                    'total': total_time
                },
                'metadata': {
                    'model_used': sql_result.get('model_used'),
                    'validation_method': validation_result.get('validation_method') if validation_result else None,
                    'response_method': response_result.get('generation_method') if response_result else None
                }
            }
            
            # Log execution
            self.log_execution(input_data, final_result, total_time)
            
            logger.info(f"✅ Pipeline completed successfully in {total_time:.3f}s")
            
            return final_result
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ Pipeline execution failed: {e}")
            
            error_result = self._create_error_result(
                "Pipeline execution failed",
                str(e),
                start_time
            )
            
            self.log_execution(input_data, error_result, total_time)
            return error_result
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for the pipeline
        
        Args:
            input_data: Input data to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not super().validate_input(input_data):
            return False
        
        required_fields = ['user_query', 'user_id']
        for field in required_fields:
            if field not in input_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        if not isinstance(input_data['user_query'], str) or not input_data['user_query'].strip():
            logger.error("user_query must be a non-empty string")
            return False
        
        if not isinstance(input_data['user_id'], str) or not input_data['user_id'].strip():
            logger.error("user_id must be a non-empty string")
            return False
        
        return True
    
    def _create_error_result(
        self, 
        error_type: str, 
        error_message: str, 
        start_time: float,
        **additional_data
    ) -> Dict[str, Any]:
        """
        Create standardized error result
        
        Args:
            error_type: Type of error
            error_message: Error message
            start_time: Pipeline start time
            **additional_data: Additional result data
            
        Returns:
            Error result dictionary
        """
        result = {
            'success': False,
            'error_type': error_type,
            'error': error_message,
            'total_time': time.time() - start_time
        }
        result.update(additional_data)
        return result
    
    def test_all_functions(self) -> Dict[str, bool]:
        """
        Test all registered functions
        
        Returns:
            Dictionary with test results for each function
        """
        logger.info("🧪 Testing all functions...")
        
        results = {}
        
        # Test SQL Generator
        sql_gen = self.get_function("sql_generator")
        if hasattr(sql_gen, 'test_connection'):
            results['sql_generator'] = sql_gen.test_connection()
        else:
            results['sql_generator'] = True
        
        # Test SQL Executor
        sql_exec = self.get_function("sql_executor")
        if hasattr(sql_exec, 'test_connection'):
            results['sql_executor'] = sql_exec.test_connection()
        else:
            results['sql_executor'] = True
        
        # SQL Validator and Response Generator don't have separate test methods
        # They use the same OpenAI connection as SQL Generator
        results['sql_validator'] = results['sql_generator']
        results['response_generator'] = results['sql_generator']
        
        all_passed = all(results.values())
        
        if all_passed:
            logger.info("✅ All function tests passed")
        else:
            failed_functions = [name for name, passed in results.items() if not passed]
            logger.error(f"❌ Function tests failed: {failed_functions}")
        
        return results
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for the entire pipeline
        
        Returns:
            Pipeline statistics dictionary
        """
        agent_stats = self.get_execution_stats()
        
        function_stats = {}
        for func_name in self.list_functions():
            func = self.get_function(func_name)
            if hasattr(func, 'get_stats'):
                function_stats[func_name] = func.get_stats()
        
        return {
            'agent_stats': agent_stats,
            'function_stats': function_stats,
            'registered_functions': self.list_functions()
        }
