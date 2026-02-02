"""
LangGraph Agent Workflow

Builds the autonomous agent graph with conditional routing.
This is the complete agentic system that replaces the linear pipeline.
"""

import logging
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import AgentNodes
from .router import AgentRouter

logger = logging.getLogger(__name__)


def create_agent_graph():
    """
    Create and compile the LangGraph autonomous agent

    This graph represents a truly autonomous AI agent that:
    - Classifies intent before processing
    - Plans query execution dynamically
    - Retries on failures
    - Asks clarifying questions
    - Routes to different paths based on context

    Returns:
        Compiled LangGraph agent
    """
    logger.info("🏗️  Building LangGraph autonomous agent...")

    # Initialize nodes and router
    nodes = AgentNodes()
    router = AgentRouter()

    # Create state graph
    workflow = StateGraph(AgentState)

    # ========== ADD NODES ==========
    logger.info("   Adding nodes...")

    workflow.add_node("classify_intent", nodes.classify_intent)
    workflow.add_node("chat", nodes.handle_chat)
    workflow.add_node("plan_sql", nodes.plan_sql_query)
    workflow.add_node("generate_sql", nodes.generate_sql)
    workflow.add_node("validate", nodes.validate_sql)
    workflow.add_node("execute", nodes.execute_sql)
    workflow.add_node("check_results", nodes.check_results)
    workflow.add_node("generate_response", nodes.generate_response)
    workflow.add_node("retry", nodes.retry_sql)
    workflow.add_node("error", nodes.handle_error)

    # ========== SET ENTRY POINT ==========
    # Always start with intent classification
    workflow.set_entry_point("classify_intent")

    # ========== ADD CONDITIONAL EDGES ==========
    logger.info("   Adding conditional routing...")

    # After intent classification → route to chat, SQL, or error
    workflow.add_conditional_edges(
        "classify_intent",
        router.route_after_intent,
        {
            "chat": "chat",
            "plan_sql": "plan_sql",
            "error": "error",
            "end": END
        }
    )

    # After chat → end
    workflow.add_conditional_edges(
        "chat",
        router.should_continue_after_chat,
        {
            "end": END
        }
    )

    # After planning → ask clarification or generate SQL
    workflow.add_conditional_edges(
        "plan_sql",
        router.route_after_planning,
        {
            "ask_clarification": END,  # TODO: implement clarification loop
            "generate_sql": "generate_sql"
        }
    )

    # After SQL generation → validate
    workflow.add_edge("generate_sql", "validate")

    # After validation → execute, retry, or error
    workflow.add_conditional_edges(
        "validate",
        router.route_after_validation,
        {
            "execute": "execute",
            "retry": "retry",
            "error": "error"
        }
    )

    # After execution → check results or error
    workflow.add_conditional_edges(
        "execute",
        router.route_after_execution,
        {
            "check_results": "check_results",
            "error": "error"
        }
    )

    # After checking results → response, retry, or clarification
    workflow.add_conditional_edges(
        "check_results",
        router.route_after_check,
        {
            "generate_response": "generate_response",
            "retry": "retry",
            "ask_clarification": END  # TODO: implement clarification loop
        }
    )

    # After retry → back to validation or error
    workflow.add_conditional_edges(
        "retry",
        router.route_after_retry,
        {
            "validate": "validate",
            "error": "error"
        }
    )

    # After response → end
    workflow.add_conditional_edges(
        "generate_response",
        router.should_continue_after_response,
        {
            "end": END
        }
    )

    # After error → end
    workflow.add_conditional_edges(
        "error",
        router.should_continue_after_error,
        {
            "end": END
        }
    )

    # ========== COMPILE GRAPH ==========
    logger.info("   Compiling graph...")
    agent = workflow.compile()

    logger.info("✅ LangGraph agent compiled successfully!")
    logger.info("""
    🤖 Agent Capabilities:
       ✅ Intent classification
       ✅ Autonomous routing
       ✅ Multi-step reasoning
       ✅ Error recovery with retries
       ✅ Result validation
       ✅ Dynamic SQL generation
       ✅ Conversation handling
    """)

    return agent


# ========== CONVENIENCE FUNCTION ==========
def run_agent(user_query: str, user_id: str, conversation_id: str = None) -> AgentState:
    """
    Run the agent with a user query

    Args:
        user_query: User's natural language query
        user_id: User identifier
        conversation_id: Optional conversation ID

    Returns:
        Final agent state with response
    """
    from .state import create_initial_state

    logger.info(f"🚀 Running agent for query: '{user_query}'")

    # Create initial state
    initial_state = create_initial_state(
        user_query=user_query,
        user_id=user_id,
        conversation_id=conversation_id
    )

    # Create and run agent
    agent = create_agent_graph()
    final_state = agent.invoke(initial_state)

    logger.info(f"✅ Agent completed")
    logger.info(f"   Response: {final_state.get('response', 'No response')}")

    return final_state


# ========== GRAPH VISUALIZATION ==========
def visualize_graph(output_path: str = "agent_graph.png"):
    """
    Visualize the agent graph (requires graphviz)

    Args:
        output_path: Path to save the graph image
    """
    try:
        from langchain_core.runnables.graph import MermaidDrawMethod

        agent = create_agent_graph()
        graph_image = agent.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API
        )

        with open(output_path, "wb") as f:
            f.write(graph_image)

        logger.info(f"✅ Graph visualization saved to {output_path}")

    except Exception as e:
        logger.error(f"❌ Could not visualize graph: {e}")
        logger.info("💡 Install graphviz: brew install graphviz")


if __name__ == "__main__":
    # Test the agent
    logging.basicConfig(level=logging.INFO)

    # Example queries
    test_queries = [
        "Hello there!",
        "What's my account balance?",
        "Show me transactions from last week",
        "Which account did I spend the most from?"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")

        result = run_agent(
            user_query=query,
            user_id="test-user-123"
        )

        print(f"\nIntent: {result['intent'].value}")
        print(f"Response: {result['response']}")
