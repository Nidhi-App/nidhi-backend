"""
LangGraph Agent State Schema

Defines the state structure that flows through the autonomous agent
"""

from typing import TypedDict, Literal, Optional, Any
from enum import Enum


class IntentType(str, Enum):
    """User query intent categories"""
    NORMAL_CONVERSATION = "NORMAL_CONVERSATION"
    ACCOUNTS_QUERY = "ACCOUNTS_QUERY"
    TRANSACTIONS_QUERY = "TRANSACTIONS_QUERY"
    ACCOUNTS_AND_TRANSACTIONS = "ACCOUNTS_AND_TRANSACTIONS"
    USER_METADATA = "USER_METADATA"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


class QueryComplexity(str, Enum):
    """SQL query complexity levels"""
    SIMPLE = "SIMPLE"  # Single SQL query
    MULTI_STEP = "MULTI_STEP"  # Multiple SQL queries needed
    AGGREGATION = "AGGREGATION"  # Needs complex aggregation
    UNKNOWN = "UNKNOWN"


class AgentState(TypedDict, total=False):
    """
    State that flows through the LangGraph agent

    This state is passed between nodes and updated at each step.
    The agent maintains this state throughout the conversation lifecycle.
    """

    # Input
    user_query: str  # Original user query
    user_id: str  # User ID for filtering
    conversation_id: Optional[str]  # Conversation context

    # Intent Classification
    intent: IntentType  # Classified intent
    intent_confidence: float  # Confidence score (0-1)

    # Query Planning
    query_plan: Optional[str]  # Plan for executing the query
    complexity: QueryComplexity  # Query complexity
    requires_clarification: bool  # Whether to ask user for clarification
    clarification_question: Optional[str]  # Question to ask user

    # SQL Generation
    sql_queries: list[str]  # List of SQL queries to execute (multi-step support)
    current_sql_index: int  # Current query being executed
    sql_params: list[tuple]  # Parameters for each SQL query

    # SQL Validation
    sql_valid: bool  # Whether SQL is valid
    validation_errors: list[str]  # Validation error messages
    validation_confidence: float  # Confidence in validation

    # SQL Execution
    query_results: list[Any]  # Results from SQL execution
    execution_errors: list[str]  # Execution error messages
    rows_affected: int  # Number of rows affected/returned

    # Result Evaluation
    results_satisfactory: bool  # Whether results meet expectations
    needs_retry: bool  # Whether to retry with different approach
    retry_count: int  # Number of retries attempted
    max_retries: int  # Maximum retries allowed

    # Response Generation
    response: Optional[str]  # Final natural language response
    response_metadata: Optional[dict]  # Additional response metadata

    # Error Tracking
    errors: list[str]  # All errors encountered
    current_node: str  # Current node being executed

    # Metadata
    model_used: str  # LLM model used
    execution_time: float  # Total execution time
    cache_hit: bool  # Whether cache was used

    # Routing Control
    next_action: Optional[str]  # Next action to take (for debugging)


# Default state values
def create_initial_state(
    user_query: str,
    user_id: str,
    conversation_id: Optional[str] = None
) -> AgentState:
    """
    Create initial agent state

    Args:
        user_query: User's natural language query
        user_id: User identifier
        conversation_id: Optional conversation ID for context

    Returns:
        Initialized AgentState
    """
    return AgentState(
        # Input
        user_query=user_query,
        user_id=user_id,
        conversation_id=conversation_id,

        # Intent Classification
        intent=IntentType.UNKNOWN,
        intent_confidence=0.0,

        # Query Planning
        query_plan=None,
        complexity=QueryComplexity.UNKNOWN,
        requires_clarification=False,
        clarification_question=None,

        # SQL Generation
        sql_queries=[],
        current_sql_index=0,
        sql_params=[],

        # SQL Validation
        sql_valid=False,
        validation_errors=[],
        validation_confidence=0.0,

        # SQL Execution
        query_results=[],
        execution_errors=[],
        rows_affected=0,

        # Result Evaluation
        results_satisfactory=False,
        needs_retry=False,
        retry_count=0,
        max_retries=3,

        # Response Generation
        response=None,
        response_metadata=None,

        # Error Tracking
        errors=[],
        current_node="start",

        # Metadata
        model_used="gpt-4",
        execution_time=0.0,
        cache_hit=False,

        # Routing Control
        next_action=None
    )
