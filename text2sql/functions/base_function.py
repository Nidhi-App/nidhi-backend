"""
Base function class for all functions in the text2sql system
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..core.exceptions import Text2SQLException

logger = logging.getLogger(__name__)

class BaseFunction(ABC):
    """
    Abstract base class for all functions in the text2sql system

    Functions are atomic operations that perform specific tasks.
    They are orchestrated by agents to complete complex workflows.
    """

    def __init__(self, name: str, description: str = "", required_inputs: Optional[List[str]] = None, optional_inputs: Optional[List[str]] = None):
        """
        Initialize the base function

        Args:
            name: Name of the function
            description: Description of what the function does
            required_inputs: List of required input parameter names
            optional_inputs: List of optional input parameter names
        """
        self.name = name
        self.description = description
        self.required_inputs = required_inputs or []
        self.optional_inputs = optional_inputs or []
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = None
        self.error_count = 0

    @abstractmethod
    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute the function's main functionality

        Args:
            input_data: Input data for the function
            **kwargs: Additional keyword arguments

        Returns:
            Dict containing the execution results with 'success' key

        Raises:
            Text2SQLException: If execution fails
        """
        pass

    def run(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Run the function with validation, timing, and error handling

        Args:
            input_data: Input data for the function
            **kwargs: Additional keyword arguments

        Returns:
            Dict containing the execution results
        """
        start_time = time.time()

        try:
            # Validate input data
            self.validate_inputs(input_data)

            # Execute the function
            self.logger.info(f"Executing function {self.name}")
            result = self.execute(input_data, **kwargs)

            # Ensure result has 'success' key
            if 'success' not in result:
                result['success'] = True

            # Update statistics
            execution_time = time.time() - start_time
            self._update_stats(execution_time, success=True)

            # Add execution time to result
            result['execution_time'] = execution_time

            self.logger.info(f"Function {self.name} executed successfully in {execution_time:.3f} seconds")

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(execution_time, success=False)

            self.logger.error(f"Function {self.name} failed: {e}")

            # Convert to Text2SQLException for better error handling
            if not isinstance(e, Text2SQLException):
                e = Text2SQLException(f"Function {self.name} failed: {str(e)}")

            # return error result instead of raising exception (for better error handling by agents)
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'function': self.name,
                'execution_time': execution_time
            }

    def validate_inputs(self, input_data: Dict[str, Any]) -> None:
        """
        Validate input data

        Args:
            input_data: Input data to validate

        Raises:
            Text2SQLException: If validation fails
        """
        if not isinstance(input_data, dict):
            raise Text2SQLException(f"Function {self.name} requires input_data to be a dictionary")

        # Check required inputs
        missing_inputs = []
        for required_input in self.required_inputs:
            if required_input not in input_data:
                missing_inputs.append(required_input)

        if missing_inputs:
            raise Text2SQLException(f"Function {self.name} requires the following inputs: {missing_inputs}")

        # Check for unexpected inputs (optional validation)
        allowed_inputs = set(self.required_inputs + self.optional_inputs)
        if allowed_inputs:  # Only validate if there are allowed inputs
            unexpected_inputs = set(input_data.keys()) - allowed_inputs
            if unexpected_inputs:
                self.logger.warning(
                    f"Function {self.name} received unexpected inputs: {list(unexpected_inputs)}"
                )

    def get_input_schema(self) -> Dict[str, Any]:
        """
        Get the input schema for this function

        Returns:
            Dictionary describing the input schema
        """
        return {
            'name': self.name,
            'description': self.description,
            'required_inputs': self.required_inputs,
            'optional_inputs': self.optional_inputs
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this function

        Returns:
            Dictionary with execution statistics
        """
        avg_time = (
            self.total_execution_time / self.execution_count if self.execution_count > 0 else 0.0
        )

        success_rate = (
            (self.execution_count - self.error_count) / self.execution_count if self.execution_count > 0 else 0.0
        )

        return {
            'execution_count': self.execution_count,
            'error_count': self.error_count,
            'success_rate': success_rate,
            'average_execution_time': avg_time,
            'total_execution_time': self.total_execution_time,
            'last_execution_time': self.last_execution_time
        }

    def reset_stats(self) -> None:
        """Reset execution statistics"""
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = None
        self.error_count = 0
        self.logger.info(f"Reset execution statistics for function {self.name}")

    def _update_stats(self, execution_time: float, success: bool) -> None:
        """Update execution statistics"""
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.last_execution_time = time.time()

        if not success:
            self.error_count += 1

    def __str__(self) -> str:
        """String representation of the function"""
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __repr__(self) -> str:
        """Detailed representation of the function"""
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"description='{self.description}', "
            f"required_inputs={self.required_inputs}, "
            f"optional_inputs={self.optional_inputs}"
            f")"
        )
