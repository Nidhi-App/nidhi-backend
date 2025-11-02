"""
LangGraph Autonomous AI Agent for Text2SQL

A truly autonomous agent that:
- Classifies user intent before processing
- Dynamically routes queries to appropriate handlers
- Retries on failures with different approaches
- Handles multi-step SQL queries
- Asks clarifying questions when needed
- Validates results before responding

This replaces the linear pipeline with an autonomous agent architecture.
"""

from .state import AgentState, IntentType, QueryComplexity, create_initial_state
from .nodes import AgentNodes
from .router import AgentRouter
from .graph import create_agent_graph, run_agent, visualize_graph

__all__ = [
    # State
    "AgentState",
    "IntentType",
    "QueryComplexity",
    "create_initial_state",

    # Core components
    "AgentNodes",
    "AgentRouter",

    # Main functions
    "create_agent_graph",
    "run_agent",
    "visualize_graph",
]

__version__ = "1.0.0"
