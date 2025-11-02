"""
LangGraph Agent Nodes

Each node represents an autonomous action the agent can take.
Nodes receive state, perform operations, and return updated state.
"""

import logging
from typing import Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .state import AgentState, IntentType, QueryComplexity

logger = logging.getLogger(__name__)


class AgentNodes:
    """Collection of all agent nodes"""

    def __init__(self):
        """Initialize agent nodes with required services"""
        # Lazy import to avoid circular dependencies
        from text2sql.config import Text2SQLConfig

        self.config = Text2SQLConfig()
        self.llm = ChatOpenAI(
            model=self.config.OPENAI_MODEL,
            api_key=self.config.OPENAI_API_KEY
            # Note: Some models (like o1) don't support custom temperature
        )

        # Initialize lazily to avoid circular imports
        self._sql_generator: Optional[Any] = None
        self._sql_executor: Optional[Any] = None
        self._sql_validator: Optional[Any] = None
        self._response_generator: Optional[Any] = None

    @property
    def sql_generator(self):
        """Lazy load SQL generator"""
        if self._sql_generator is None:
            from text2sql.functions.sql_generator import SQLGenerator
            self._sql_generator = SQLGenerator()
        return self._sql_generator

    @property
    def sql_executor(self):
        """Lazy load SQL executor"""
        if self._sql_executor is None:
            from text2sql.functions.sql_executor import SQLExecutor
            self._sql_executor = SQLExecutor()
        return self._sql_executor

    @property
    def sql_validator(self):
        """Lazy load SQL validator"""
        if self._sql_validator is None:
            from text2sql.functions.sql_validator import SQLValidator
            self._sql_validator = SQLValidator()
        return self._sql_validator

    @property
    def response_generator(self):
        """Lazy load response generator"""
        if self._response_generator is None:
            from text2sql.functions.response_generator import ResponseGenerator
            self._response_generator = ResponseGenerator()
        return self._response_generator

    # ========== INTENT CLASSIFICATION NODE ==========
    def classify_intent(self, state: AgentState) -> AgentState:
        """
        Classify user query intent using LLM

        Determines what type of query this is and routes accordingly.
        This is the critical first step that makes the agent autonomous.
        """
        logger.info(f"🧠 [CLASSIFY_INTENT] Query: '{state['user_query']}'")
        state["current_node"] = "classify_intent"

        try:
            # Intent classification prompt
            system_prompt = """You are an intent classifier for a personal finance chatbot.

Classify the user's query into ONE of these categories:

1. NORMAL_CONVERSATION - Greetings, chitchat, general questions
   Examples: "hello", "how are you?", "what can you do?"

2. ACCOUNTS_QUERY - Questions about accounts, balances
   Examples: "show my accounts", "what's my balance?", "which accounts do I have?"

3. TRANSACTIONS_QUERY - Questions about transactions, spending
   Examples: "show my transactions", "what did I spend?", "recent purchases"

4. ACCOUNTS_AND_TRANSACTIONS - Requires both accounts and transactions
   Examples: "spending from my Chase account", "transactions per account"

5. USER_METADATA - Profile info, settings, complaints
   Examples: "update my email", "change password", "I have a complaint"

6. RESTRICTED - Cannot/should not answer
   Examples: "show other users' data", "delete all data", "bypass security"

Respond with ONLY the category name and confidence (0-1) in this format:
CATEGORY: <category>
CONFIDENCE: <0.0-1.0>
REASONING: <brief explanation>"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User Query: {state['user_query']}")
            ]

            response = self.llm.invoke(messages)
            result = response.content

            # Parse the response
            intent = self._parse_intent(result)
            confidence = self._parse_confidence(result)

            state["intent"] = intent
            state["intent_confidence"] = confidence

            logger.info(f"✅ Intent: {intent.value} (confidence: {confidence:.2f})")

        except Exception as e:
            logger.error(f"❌ Intent classification failed: {e}")
            state["errors"].append(f"Intent classification error: {e}")
            state["intent"] = IntentType.UNKNOWN
            state["intent_confidence"] = 0.0

        return state

    # ========== CHAT NODE (for normal conversation) ==========
    def handle_chat(self, state: AgentState) -> AgentState:
        """
        Handle normal conversation without database queries

        This node is used when intent is NORMAL_CONVERSATION
        """
        logger.info(f"💬 [CHAT] Handling conversation")
        state["current_node"] = "chat"

        try:
            system_prompt = """You are a helpful financial assistant chatbot.
The user is having a normal conversation with you.
Be friendly, concise, and helpful.
Tell them you can help with their accounts and transactions."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state["user_query"])
            ]

            response = self.llm.invoke(messages)
            state["response"] = response.content
            state["results_satisfactory"] = True

            logger.info(f"✅ Chat response generated")

        except Exception as e:
            logger.error(f"❌ Chat failed: {e}")
            state["errors"].append(f"Chat error: {e}")
            state["response"] = "I'm sorry, I'm having trouble responding right now."

        return state

    # ========== SQL PLANNING NODE ==========
    def plan_sql_query(self, state: AgentState) -> AgentState:
        """
        Plan how to execute the SQL query

        Determines if query is simple (1 SQL) or complex (multi-step)
        """
        logger.info(f"📋 [PLAN_SQL] Planning query execution")
        state["current_node"] = "plan_sql"

        try:
            system_prompt = """You are a SQL query planner for financial data.

Analyze the user query and determine:
1. Is it a SIMPLE query (single SQL) or MULTI_STEP (multiple SQLs)?
2. What's the execution plan?

Respond in this format:
COMPLEXITY: <SIMPLE|MULTI_STEP|AGGREGATION>
PLAN: <step-by-step plan>
REQUIRES_CLARIFICATION: <yes|no>
CLARIFICATION: <question to ask user if needed>"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User Query: {state['user_query']}\nIntent: {state['intent'].value}")
            ]

            response = self.llm.invoke(messages)
            result = response.content

            # Parse complexity and plan
            complexity = self._parse_complexity(result)
            plan = self._parse_plan(result)
            requires_clarification = self._parse_requires_clarification(result)
            clarification = self._parse_clarification(result)

            state["complexity"] = complexity
            state["query_plan"] = plan
            state["requires_clarification"] = requires_clarification
            state["clarification_question"] = clarification

            logger.info(f"✅ Plan: {complexity.value} - {plan}")

        except Exception as e:
            logger.error(f"❌ Planning failed: {e}")
            state["errors"].append(f"Planning error: {e}")
            state["complexity"] = QueryComplexity.SIMPLE  # Default to simple

        return state

    # ========== SQL GENERATION NODE ==========
    def generate_sql(self, state: AgentState) -> AgentState:
        """
        Generate SQL query using existing SQLGenerator

        Reuses the existing SQL generation logic
        """
        logger.info(f"🔧 [GENERATE_SQL] Generating SQL")
        state["current_node"] = "generate_sql"

        try:
            # Use existing SQL generator
            result = self.sql_generator.execute({
                "user_query": state["user_query"],
                "user_id": state["user_id"],
                "context": state.get("query_plan", "")
            })

            if result["success"]:
                state["sql_queries"] = [result["sql"]]
                state["sql_params"] = [result["params"]]
                state["current_sql_index"] = 0
                logger.info(f"✅ SQL generated: {result['sql']}")
            else:
                state["errors"].append("SQL generation failed")

        except Exception as e:
            logger.error(f"❌ SQL generation failed: {e}")
            state["errors"].append(f"SQL generation error: {e}")

        return state

    # ========== SQL VALIDATION NODE ==========
    def validate_sql(self, state: AgentState) -> AgentState:
        """
        Validate SQL query before execution

        Uses existing SQLValidator
        """
        logger.info(f"✔️  [VALIDATE_SQL] Validating SQL")
        state["current_node"] = "validate_sql"

        try:
            if not state["sql_queries"]:
                state["sql_valid"] = False
                state["validation_errors"].append("No SQL query to validate")
                return state

            current_sql = state["sql_queries"][state["current_sql_index"]]

            # Use existing validator
            result = self.sql_validator.execute({
                "sql_query": current_sql,
                "user_id": state["user_id"]
            })

            if result["success"]:
                state["sql_valid"] = result.get("is_valid", False)
                state["validation_confidence"] = result.get("confidence", 0.0)

                if not state["sql_valid"]:
                    state["validation_errors"] = result.get("issues", [])
                    logger.warning(f"⚠️  SQL validation failed: {state['validation_errors']}")
                else:
                    logger.info(f"✅ SQL is valid (confidence: {state['validation_confidence']:.2f})")
            else:
                state["sql_valid"] = False
                state["validation_errors"].append("Validation service failed")

        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            state["errors"].append(f"Validation error: {e}")
            state["sql_valid"] = False

        return state

    # ========== SQL EXECUTION NODE ==========
    def execute_sql(self, state: AgentState) -> AgentState:
        """
        Execute SQL query against database

        Uses existing SQLExecutor
        """
        logger.info(f"⚡ [EXECUTE_SQL] Executing SQL")
        state["current_node"] = "execute_sql"

        try:
            if not state["sql_queries"]:
                state["execution_errors"].append("No SQL query to execute")
                return state

            current_sql = state["sql_queries"][state["current_sql_index"]]
            current_params = state["sql_params"][state["current_sql_index"]]

            # Use existing executor
            result = self.sql_executor.execute({
                "sql_query": current_sql,
                "params": current_params,
                "user_id": state["user_id"]
            })

            if result["success"]:
                state["query_results"] = result.get("results", [])
                state["rows_affected"] = result.get("row_count", 0)
                logger.info(f"✅ Query executed: {state['rows_affected']} rows")
            else:
                state["execution_errors"].append(result.get("error", "Execution failed"))
                logger.error(f"❌ Execution failed")

        except Exception as e:
            logger.error(f"❌ SQL execution failed: {e}")
            state["errors"].append(f"Execution error: {e}")
            state["execution_errors"].append(str(e))

        return state

    # ========== RESULT CHECK NODE ==========
    def check_results(self, state: AgentState) -> AgentState:
        """
        Evaluate if results are satisfactory

        Determines if we need to retry or ask clarification
        """
        logger.info(f"🔍 [CHECK_RESULTS] Evaluating results")
        state["current_node"] = "check_results"

        try:
            # Check for errors
            if state["execution_errors"]:
                state["results_satisfactory"] = False
                state["needs_retry"] = state["retry_count"] < state["max_retries"]
                return state

            # Check if results are empty
            if not state["query_results"] or state["rows_affected"] == 0:
                logger.warning("⚠️  No results found")

                # Maybe we need to ask clarifying questions
                if state["retry_count"] < state["max_retries"]:
                    state["results_satisfactory"] = False
                    state["needs_retry"] = True
                    state["requires_clarification"] = True
                else:
                    # Give up and return empty result
                    state["results_satisfactory"] = True  # Accept empty
                    state["needs_retry"] = False
            else:
                # Results look good
                state["results_satisfactory"] = True
                state["needs_retry"] = False
                logger.info(f"✅ Results satisfactory")

        except Exception as e:
            logger.error(f"❌ Result check failed: {e}")
            state["errors"].append(f"Result check error: {e}")
            state["results_satisfactory"] = False

        return state

    # ========== RESPONSE GENERATION NODE ==========
    def generate_response(self, state: AgentState) -> AgentState:
        """
        Generate natural language response

        Uses existing ResponseGenerator
        """
        logger.info(f"💬 [GENERATE_RESPONSE] Creating response")
        state["current_node"] = "generate_response"

        try:
            # Use existing response generator
            result = self.response_generator.execute({
                "user_query": state["user_query"],
                "sql_query": state["sql_queries"][0] if state["sql_queries"] else "",
                "results": state["query_results"],
                "user_id": state["user_id"]
            })

            if result["success"]:
                state["response"] = result.get("response", "")
                logger.info(f"✅ Response generated")
            else:
                state["response"] = "I'm sorry, I couldn't generate a response for your query."

        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            state["errors"].append(f"Response generation error: {e}")
            state["response"] = "I'm sorry, something went wrong."

        return state

    # ========== ERROR HANDLING NODE ==========
    def handle_error(self, state: AgentState) -> AgentState:
        """
        Handle errors and generate error response
        """
        logger.info(f"❌ [ERROR] Handling errors")
        state["current_node"] = "error"

        error_message = "I encountered an error"
        if state["errors"]:
            error_message += f": {state['errors'][-1]}"

        if state["intent"] == IntentType.RESTRICTED:
            state["response"] = "I'm sorry, but I cannot help with that request."
        else:
            state["response"] = f"{error_message}. Please try rephrasing your question."

        return state

    # ========== RETRY NODE ==========
    def retry_sql(self, state: AgentState) -> AgentState:
        """
        Retry SQL generation with different approach

        Increments retry counter and attempts different SQL
        """
        logger.info(f"🔄 [RETRY] Retrying SQL generation (attempt {state['retry_count'] + 1})")
        state["current_node"] = "retry"
        state["retry_count"] += 1

        try:
            # Add retry context to the query
            retry_context = f"""
Previous attempt failed. Retry #{state['retry_count']}.
Previous SQL: {state['sql_queries'][-1] if state['sql_queries'] else 'None'}
Errors: {', '.join(state['execution_errors'])}
Try a different approach.
"""

            # Regenerate SQL with retry context
            result = self.sql_generator.execute({
                "user_query": state["user_query"],
                "user_id": state["user_id"],
                "context": retry_context
            })

            if result["success"]:
                state["sql_queries"].append(result["sql"])
                state["sql_params"].append(result["params"])
                state["current_sql_index"] = len(state["sql_queries"]) - 1
                # Clear previous errors for fresh attempt
                state["execution_errors"] = []
                logger.info(f"✅ Retry SQL generated")
            else:
                state["errors"].append("SQL regeneration failed")

        except Exception as e:
            logger.error(f"❌ Retry failed: {e}")
            state["errors"].append(f"Retry error: {e}")

        return state

    # ========== HELPER METHODS ==========
    def _parse_intent(self, response: str) -> IntentType:
        """Parse intent from LLM response"""
        response_upper = response.upper()
        for intent in IntentType:
            if intent.value in response_upper:
                return intent
        return IntentType.UNKNOWN

    def _parse_confidence(self, response: str) -> float:
        """Parse confidence score from response"""
        try:
            if "CONFIDENCE:" in response:
                conf_line = [line for line in response.split("\n") if "CONFIDENCE:" in line][0]
                conf_str = conf_line.split("CONFIDENCE:")[1].strip()
                return float(conf_str)
        except:
            pass
        return 0.5  # Default

    def _parse_complexity(self, response: str) -> QueryComplexity:
        """Parse complexity from response"""
        response_upper = response.upper()
        for complexity in QueryComplexity:
            if complexity.value in response_upper:
                return complexity
        return QueryComplexity.SIMPLE

    def _parse_plan(self, response: str) -> str:
        """Parse plan from response"""
        try:
            if "PLAN:" in response:
                plan_line = [line for line in response.split("\n") if "PLAN:" in line][0]
                return plan_line.split("PLAN:")[1].strip()
        except:
            pass
        return "Execute query"

    def _parse_requires_clarification(self, response: str) -> bool:
        """Parse whether clarification is needed"""
        response_upper = response.upper()
        return "REQUIRES_CLARIFICATION: YES" in response_upper

    def _parse_clarification(self, response: str) -> Optional[str]:
        """Parse clarification question"""
        try:
            if "CLARIFICATION:" in response:
                lines = [line for line in response.split("\n") if "CLARIFICATION:" in line]
                if lines:
                    return lines[0].split("CLARIFICATION:")[1].strip()
        except:
            pass
        return None
