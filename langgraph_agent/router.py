"""
LangGraph Agent Routing Logic

Conditional edges that determine which node to execute next.
This is the "brain" that makes the agent autonomous.
"""

import logging
from typing import Literal

from .state import AgentState, IntentType

logger = logging.getLogger(__name__)


class AgentRouter:
    """Routing logic for the autonomous agent"""

    @staticmethod
    def route_after_intent(
        state: AgentState
    ) -> Literal["chat", "plan_sql", "error", "end"]:
        """
        Route based on classified intent

        This is the first major decision point that routes queries
        to appropriate handlers.

        Returns:
            - "chat": Normal conversation (no SQL needed)
            - "plan_sql": SQL query needed (accounts/transactions)
            - "error": Restricted or invalid query
            - "end": Unknown or empty query
        """
        intent = state["intent"]
        logger.info(f"🧭 [ROUTER] Intent routing: {intent.value}")

        if intent == IntentType.NORMAL_CONVERSATION:
            logger.info("   → Routing to CHAT (no SQL needed)")
            return "chat"

        elif intent == IntentType.RESTRICTED:
            logger.info("   → Routing to ERROR (restricted query)")
            return "error"

        elif intent in [
            IntentType.ACCOUNTS_QUERY,
            IntentType.TRANSACTIONS_QUERY,
            IntentType.ACCOUNTS_AND_TRANSACTIONS
        ]:
            logger.info("   → Routing to PLAN_SQL (database query needed)")
            return "plan_sql"

        elif intent == IntentType.USER_METADATA:
            logger.info("   → Routing to ERROR (metadata not implemented yet)")
            return "error"

        else:  # UNKNOWN
            logger.warning("   → Routing to CHAT (intent unclear, treating as conversation)")
            return "chat"

    @staticmethod
    def route_after_planning(
        state: AgentState
    ) -> Literal["ask_clarification", "generate_sql"]:
        """
        Route after query planning

        Determines if we need clarification before generating SQL

        Returns:
            - "ask_clarification": Need to ask user for more info
            - "generate_sql": Ready to generate SQL
        """
        logger.info(f"🧭 [ROUTER] Planning routing")

        if state.get("requires_clarification", False):
            logger.info("   → Need CLARIFICATION from user")
            return "ask_clarification"
        else:
            logger.info("   → Ready to GENERATE_SQL")
            return "generate_sql"

    @staticmethod
    def route_after_validation(
        state: AgentState
    ) -> Literal["execute", "retry", "error"]:
        """
        Route after SQL validation

        Determines if SQL is safe to execute or needs retry

        Returns:
            - "execute": SQL is valid, execute it
            - "retry": SQL is invalid, retry generation
            - "error": Max retries exceeded
        """
        logger.info(f"🧭 [ROUTER] Validation routing")

        sql_valid = state.get("sql_valid", False)
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        if sql_valid:
            logger.info("   → SQL is VALID, routing to EXECUTE")
            return "execute"

        elif retry_count < max_retries:
            logger.info(f"   → SQL INVALID, routing to RETRY (attempt {retry_count + 1}/{max_retries})")
            return "retry"

        else:
            logger.error(f"   → Max retries reached, routing to ERROR")
            return "error"

    @staticmethod
    def route_after_execution(
        state: AgentState
    ) -> Literal["check_results", "error"]:
        """
        Route after SQL execution

        Returns:
            - "check_results": Execution successful, check results
            - "error": Execution failed
        """
        logger.info(f"🧭 [ROUTER] Execution routing")

        if state.get("execution_errors"):
            logger.error("   → Execution FAILED, routing to ERROR")
            return "error"
        else:
            logger.info("   → Execution SUCCESS, routing to CHECK_RESULTS")
            return "check_results"

    @staticmethod
    def route_after_check(
        state: AgentState
    ) -> Literal["generate_response", "retry", "ask_clarification"]:
        """
        Route after checking results

        Determines if results are satisfactory or need retry

        Returns:
            - "generate_response": Results good, generate response
            - "retry": Results unsatisfactory, retry with different SQL
            - "ask_clarification": Need user input
        """
        logger.info(f"🧭 [ROUTER] Result check routing")

        satisfactory = state.get("results_satisfactory", False)
        needs_retry = state.get("needs_retry", False)
        requires_clarification = state.get("requires_clarification", False)
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        if satisfactory:
            logger.info("   → Results SATISFACTORY, routing to GENERATE_RESPONSE")
            return "generate_response"

        elif requires_clarification and retry_count < max_retries:
            logger.info("   → Need CLARIFICATION from user")
            return "ask_clarification"

        elif needs_retry and retry_count < max_retries:
            logger.info(f"   → Results UNSATISFACTORY, routing to RETRY")
            return "retry"

        else:
            # Give up and generate response with what we have
            logger.warning("   → Max retries reached, generating response anyway")
            return "generate_response"

    @staticmethod
    def should_continue_after_chat(
        state: AgentState
    ) -> Literal["end"]:
        """
        After chat, we're done

        Returns:
            - "end": Conversation finished
        """
        logger.info(f"🧭 [ROUTER] Chat complete, routing to END")
        return "end"

    @staticmethod
    def should_continue_after_response(
        state: AgentState
    ) -> Literal["end"]:
        """
        After generating response, we're done

        Returns:
            - "end": Agent finished
        """
        logger.info(f"🧭 [ROUTER] Response generated, routing to END")
        return "end"

    @staticmethod
    def should_continue_after_error(
        state: AgentState
    ) -> Literal["end"]:
        """
        After error handling, we're done

        Returns:
            - "end": Agent finished with error
        """
        logger.info(f"🧭 [ROUTER] Error handled, routing to END")
        return "end"

    @staticmethod
    def route_after_retry(
        state: AgentState
    ) -> Literal["validate", "error"]:
        """
        Route after retry

        Goes back to validation with new SQL

        Returns:
            - "validate": Retry generated new SQL, validate it
            - "error": Retry failed
        """
        logger.info(f"🧭 [ROUTER] Retry routing")

        if state.get("sql_queries") and len(state["sql_queries"]) > state.get("current_sql_index", 0):
            logger.info("   → Retry successful, routing to VALIDATE")
            return "validate"
        else:
            logger.error("   → Retry FAILED, routing to ERROR")
            return "error"
