"""
Base agent class for all agents for text2sql system
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from ..core.exceptions import Text2SQLException

# Avoid circular imports by importing only for type checking
if TYPE_CHECKING:
    from ..functions.base_function import BaseFunction

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the text2sql system
    
    Agents are responsible for orchestrating functions to complete tasks.
    They define the high-level workflow and coordinate between different functions.
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize the base agent
        
        Args:
            name: Name of the agent
            description: Description of what the agent does
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.functions = {}  # Registry of available functions
        self.execution_history = []  # History of function calls

    @abstractmethod
    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute the agent's main functionality
        
        Args:
            input_data: Input data for the agent
            **kwargs: Additional keyword arguments
            
        Returns:
            Dict containing the execution results
            
        Raises:
            Text2SQLException: If execution fails
        """
        pass

    def register_function(self, function: 'BaseFunction') -> None:
        """
        Register a function with this agent
        
        Args:
            function: Function instance to register
        """
        self.functions[function.name] = function
        self.logger.info(f"Registered function: {function.name}")

    def get_function(self, function_name: str) -> Optional['BaseFunction']:
        """
        Get a registered function by name
        
        Args:
            function_name: Name of the function to retrieve
            
        Returns:
            Function instance or None if not found
        """
        return self.functions.get(function_name)
    
    def list_functions(self) -> List[str]:
        """
        Get list of registered function names
        
        Returns:
            List of function names
        """
        return list(self.functions.keys())
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before execution
        
        Args:
            input_data: Input data to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Base validation - subclasses can override
        return isinstance(input_data, dict)
    
    def log_execution(self, input_data: Dict[str, Any], result: Dict[str, Any], duration: float) -> None:
        """
        Log execution details for monitoring and debugging
        
        Args:
            input_data: Original input data
            result: Execution result
            duration: Execution duration in seconds
        """
        execution_record = {
            'timestamp': self._get_timestamp(),
            'agent': self.name,
            'input_data': input_data,
            'result': result,
            'duration': duration,
            'success': result.get('success', False)
        }

        self.execution_history.append(execution_record)

        # Keep only the last 100 executions to prevent memory issues
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

        self.logger.info(
            f"Agent {self.name} executed in {duration:.3f}s - "
            f"Success: {execution_record['success']}"
        )

    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics for this agent
        
        Returns:
            Dictionary with execution statistics
        """
        if not self.execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'average_duration': 0.0,
                'last_execution': None
            }
        
        total = len(self.execution_history)
        successful = sum(1 for record in self.execution_history if record['success'])
        durations = [record['duration'] for record in self.execution_history]
        
        return {
            'total_executions': total,
            'success_rate': successful / total if total > 0 else 0.0,
            'average_duration': sum(durations) / len(durations) if durations else 0.0,
            'last_execution': self.execution_history[-1]['timestamp'] if self.execution_history else None
        }
    
    def reset_stats(self) -> None:
        """Reset execution history and statistics"""
        self.execution_history = []
        self.logger.info(f"Reset execution statistics for agent {self.name}")
    
    def _get_timestamp(self) -> float:
        """Get current timestamp"""
        import time
        return time.time()
    
    def __str__(self) -> str:
        """String representation of the agent"""
        return f"{self.__class__.__name__}(name='{self.name}', functions={len(self.functions)})"
    
    def __repr__(self) -> str:
        """Detailed representation of the agent"""
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"description='{self.description}', "
            f"functions={list(self.functions.keys())}"
            f")"
        )
