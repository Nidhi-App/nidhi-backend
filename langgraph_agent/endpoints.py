"""
FastAPI Endpoints for LangGraph Autonomous Agent

New endpoints that use the autonomous agent instead of the linear pipeline.
"""

import logging
import time
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from .graph import run_agent
from .state import IntentType

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/agent", tags=["Agent Chatbot"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AgentChatRequest(BaseModel):
    """Request model for agent chat"""
    user_id: str = Field(..., description="User UUID from Supabase Auth")
    query: str = Field(..., description="Natural language query", max_length=500)
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID")


class AgentChatResponse(BaseModel):
    """Response model for agent chat"""
    success: bool
    user_query: str
    response: str

    # Intent classification
    intent: str
    intent_confidence: float

    # SQL execution (if applicable)
    sql_queries: Optional[List[str]] = None
    results: Optional[List[dict]] = None
    row_count: int = 0

    # Metadata
    execution_time: float = 0
    retry_count: int = 0
    cache_hit: bool = False
    errors: Optional[List[str]] = None

    # Conversation
    conversation_id: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    Autonomous AI Agent Chatbot Endpoint

    This endpoint uses a true AI agent with:
    - Intent classification
    - Autonomous routing
    - Multi-step reasoning
    - Error recovery
    - Result validation

    Args:
        request: AgentChatRequest with user_id, query, and optional conversation_id

    Returns:
        AgentChatResponse with intent, response, and metadata
    """
    start_time = time.time()

    try:
        logger.info(f"🤖 [AGENT] Query from user {request.user_id}: '{request.query}'")

        # Run the autonomous agent
        final_state = run_agent(
            user_query=request.query,
            user_id=request.user_id,
            conversation_id=request.conversation_id
        )

        execution_time = time.time() - start_time

        # Format results
        results_list = []
        if final_state.get("query_results"):
            results_list = final_state["query_results"]

        # Build response
        response = AgentChatResponse(
            success=len(final_state.get("errors", [])) == 0,
            user_query=request.query,
            response=final_state.get("response", "I couldn't process your request."),

            # Intent
            intent=final_state.get("intent", IntentType.UNKNOWN).value,
            intent_confidence=final_state.get("intent_confidence", 0.0),

            # SQL (if applicable)
            sql_queries=final_state.get("sql_queries"),
            results=results_list,
            row_count=final_state.get("rows_affected", 0),

            # Metadata
            execution_time=execution_time,
            retry_count=final_state.get("retry_count", 0),
            cache_hit=final_state.get("cache_hit", False),
            errors=final_state.get("errors") if final_state.get("errors") else None,

            # Conversation
            conversation_id=request.conversation_id
        )

        logger.info(f"✅ [AGENT] Response generated in {execution_time:.2f}s")
        logger.info(f"   Intent: {response.intent} (confidence: {response.intent_confidence:.2f})")
        logger.info(f"   Retries: {response.retry_count}")

        return response

    except Exception as e:
        logger.error(f"❌ [AGENT] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {str(e)}"
        )


@router.get("/health")
async def agent_health():
    """
    Health check for agent

    Returns:
        Status message
    """
    return {
        "status": "healthy",
        "agent_type": "langgraph_autonomous",
        "capabilities": [
            "intent_classification",
            "autonomous_routing",
            "multi_step_reasoning",
            "error_recovery",
            "result_validation"
        ]
    }
