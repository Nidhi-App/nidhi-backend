# LangGraph Autonomous AI Agent Architecture

## Overview

This document explains the **autonomous AI agent** architecture implemented using **LangGraph** for the Text2SQL chatbot system. This is a TRUE AI agent with autonomous decision-making capabilities, not just a linear pipeline.

---

## Table of Contents

1. [What Makes This a True AI Agent?](#what-makes-this-a-true-ai-agent)
2. [Architecture Comparison](#architecture-comparison)
3. [Agent Capabilities](#agent-capabilities)
4. [System Architecture](#system-architecture)
5. [Components](#components)
6. [Usage](#usage)
7. [API Reference](#api-reference)
8. [Examples](#examples)

---

## What Makes This a True AI Agent?

### Old System (Linear Pipeline)
```
User Query → [Always runs all 4 steps]
  1. SQL Generator
  2. SQL Executor
  3. SQL Validator
  4. Response Generator
→ Response
```

**Problems:**
- ❌ No intent classification - "Hello!" still generates SQL
- ❌ Fixed execution path - can't adapt to different query types
- ❌ No error recovery - failures just return errors
- ❌ No multi-step reasoning - can't break down complex queries
- ❌ No dynamic tool selection - always uses same functions

### New System (Autonomous Agent)
```
User Query → Agent Brain (LLM with reasoning)
             ↓
     [Analyzes intent and context]
             ↓
     [Decides which path to take]
             ↓
     ┌─────┴─────┬────────┬─────────┐
     ▼           ▼        ▼         ▼
  Chat     SQL Query   Metadata   Error
             ↓
     [Plans execution]
             ↓
     [Executes with retries]
             ↓
     [Validates results]
             ↓
     [Decides: done or retry?]
             ↓
Response
```

**Improvements:**
- ✅ **Intent classification** - Routes queries intelligently
- ✅ **Autonomous routing** - Different paths for different query types
- ✅ **Error recovery** - Retries with different approaches
- ✅ **Multi-step reasoning** - Plans and executes complex queries
- ✅ **Result validation** - Ensures quality before responding
- ✅ **Dynamic tool selection** - Uses only what's needed

---

## Architecture Comparison

| Feature | Old Pipeline | New Agent |
|---------|-------------|-----------|
| **Decision Making** | Fixed sequence | Autonomous choices |
| **Intent Classification** | ❌ No | ✅ Yes (6 categories) |
| **Tool Selection** | ❌ Always all tools | ✅ Dynamic based on need |
| **Error Handling** | ❌ Return error | ✅ Retry with different approach |
| **Multi-step Queries** | ❌ No | ✅ Yes |
| **Conversation** | ❌ Database queries only | ✅ Natural conversations |
| **Query Planning** | ❌ No | ✅ Analyzes complexity |
| **Result Validation** | ❌ No | ✅ Validates before responding |
| **Retry Logic** | ❌ No | ✅ Up to 3 retries |
| **Framework** | Custom pipeline | LangGraph (industry standard) |

---

## Agent Capabilities

### 1. Intent Classification

The agent classifies every query into one of 6 categories:

```python
class IntentType:
    NORMAL_CONVERSATION = "NORMAL_CONVERSATION"        # "Hello", "How are you?"
    ACCOUNTS_QUERY = "ACCOUNTS_QUERY"                  # "Show my accounts"
    TRANSACTIONS_QUERY = "TRANSACTIONS_QUERY"          # "My recent transactions"
    ACCOUNTS_AND_TRANSACTIONS = "ACCOUNTS_AND_TRANSACTIONS"  # "Spending from Chase"
    USER_METADATA = "USER_METADATA"                    # "Update my email"
    RESTRICTED = "RESTRICTED"                          # "Delete all data"
```

**Example:**
```
Query: "Hello there!"
Intent: NORMAL_CONVERSATION
Route: Chat handler (no SQL needed)

Query: "What's my balance?"
Intent: ACCOUNTS_QUERY
Route: SQL pipeline with planning
```

### 2. Autonomous Routing

Based on intent, the agent chooses different execution paths:

- **Normal Conversation** → Direct chat response (no database access)
- **SQL Queries** → Plan → Generate → Validate → Execute → Check → Respond
- **Restricted** → Polite rejection
- **Metadata** → Future: Profile management (not implemented yet)

### 3. Query Planning

For SQL queries, the agent analyzes complexity:

```python
class QueryComplexity:
    SIMPLE = "SIMPLE"              # Single SELECT query
    MULTI_STEP = "MULTI_STEP"      # Multiple queries needed
    AGGREGATION = "AGGREGATION"     # Complex aggregations
```

### 4. Error Recovery

If something fails, the agent:
1. Analyzes what went wrong
2. Generates a different SQL query
3. Retries (up to 3 times)
4. If still failing, provides helpful error message

**Example Flow:**
```
Attempt 1: SELECT balance FROM accounts WHERE user_id = %s
          ❌ Error: Column 'balance' doesn't exist

Attempt 2: SELECT amount FROM accounts WHERE user_id = %s
          ✅ Success!
```

### 5. Result Validation

Before responding, the agent:
- Checks if results are empty
- Validates result structure
- Decides if clarification is needed
- Can retry if results don't make sense

---

## System Architecture

### Directory Structure

```
langgraph_agent/
├── __init__.py          # Module exports
├── state.py             # Agent state schema
├── nodes.py             # Agent actions (nodes)
├── router.py            # Routing logic
├── graph.py             # LangGraph workflow
└── endpoints.py         # FastAPI endpoints (not used, integrated in app.py)
```

### Component Diagram

```
┌─────────────────────────────────────────────┐
│  FastAPI Endpoint: POST /api/agent/chat    │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  LangGraph Autonomous Agent                 │
│  ┌───────────────────────────────────────┐  │
│  │  State Machine (AgentState)           │  │
│  │  - User query, intent, SQL, results   │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Nodes (Agent Actions)                │  │
│  │  - classify_intent                    │  │
│  │  - handle_chat                        │  │
│  │  - plan_sql_query                     │  │
│  │  - generate_sql                       │  │
│  │  - validate_sql                       │  │
│  │  - execute_sql                        │  │
│  │  - check_results                      │  │
│  │  - generate_response                  │  │
│  │  - retry_sql                          │  │
│  │  - handle_error                       │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Router (Conditional Logic)           │  │
│  │  - route_after_intent                 │  │
│  │  - route_after_planning               │  │
│  │  - route_after_validation             │  │
│  │  - route_after_execution              │  │
│  │  - route_after_check                  │  │
│  └───────────────────────────────────────┘  │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌──────────────┴──────────────┐
│  Database / LLM Services    │
│  - PostgreSQL               │
│  - OpenAI GPT-4            │
│  - Caching Layer           │
└─────────────────────────────┘
```

---

## Components

### 1. State (state.py)

The `AgentState` is a TypedDict that flows through the agent:

```python
class AgentState(TypedDict):
    # Input
    user_query: str
    user_id: str
    conversation_id: Optional[str]

    # Intent Classification
    intent: IntentType
    intent_confidence: float

    # Query Planning
    query_plan: Optional[str]
    complexity: QueryComplexity
    requires_clarification: bool

    # SQL Generation
    sql_queries: list[str]
    sql_params: list[tuple]

    # Execution
    query_results: list[Any]
    execution_errors: list[str]

    # Result Evaluation
    results_satisfactory: bool
    needs_retry: bool
    retry_count: int

    # Response
    response: Optional[str]
    errors: list[str]
```

### 2. Nodes (nodes.py)

Each node is a function that takes state and returns updated state:

**Key Nodes:**

1. **classify_intent** - Determines query type using LLM
2. **handle_chat** - Responds to conversational queries
3. **plan_sql_query** - Plans SQL execution strategy
4. **generate_sql** - Generates SQL from natural language
5. **validate_sql** - Validates SQL before execution
6. **execute_sql** - Runs SQL query against database
7. **check_results** - Evaluates if results are satisfactory
8. **generate_response** - Creates natural language response
9. **retry_sql** - Retries failed queries with new approach
10. **handle_error** - Handles errors gracefully

### 3. Router (router.py)

Conditional edges that determine next node:

```python
def route_after_intent(state: AgentState) -> str:
    """Route based on intent classification"""
    if state["intent"] == IntentType.NORMAL_CONVERSATION:
        return "chat"
    elif state["intent"] == IntentType.RESTRICTED:
        return "error"
    elif state["intent"] in [IntentType.ACCOUNTS_QUERY, ...]:
        return "plan_sql"
    # ...
```

### 4. Graph (graph.py)

Builds the LangGraph workflow:

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classify_intent", nodes.classify_intent)
workflow.add_node("chat", nodes.handle_chat)
# ... more nodes

# Add routing
workflow.add_conditional_edges(
    "classify_intent",
    router.route_after_intent,
    {
        "chat": "chat",
        "plan_sql": "plan_sql",
        "error": "error"
    }
)

# Compile
agent = workflow.compile()
```

---

## Usage

### Option 1: Direct Python Usage

```python
from langgraph_agent import run_agent

result = run_agent(
    user_query="What's my account balance?",
    user_id="user-123"
)

print(f"Intent: {result['intent']}")
print(f"Response: {result['response']}")
```

### Option 2: FastAPI Endpoint

```bash
POST /api/agent/chat
Content-Type: application/json

{
  "user_id": "user-123",
  "query": "Show me my transactions from last week",
  "conversation_id": null
}
```

**Response:**
```json
{
  "success": true,
  "user_query": "Show me my transactions from last week",
  "response": "Here are your transactions from last week...",
  "intent": "TRANSACTIONS_QUERY",
  "intent_confidence": 0.95,
  "sql_queries": ["SELECT * FROM transactions WHERE user_id = %s AND date > NOW() - INTERVAL '7 days'"],
  "results": [...],
  "row_count": 15,
  "execution_time": 1.23,
  "retry_count": 0,
  "errors": null
}
```

---

## API Reference

### Endpoints

#### 1. POST /api/agent/chat

Autonomous agent chatbot endpoint.

**Request:**
```typescript
{
  user_id: string;          // Required: User UUID
  query: string;            // Required: Natural language query
  conversation_id?: string; // Optional: Conversation ID
}
```

**Response:**
```typescript
{
  success: boolean;
  user_query: string;
  response: string;

  // Intent
  intent: string;
  intent_confidence: number;

  // SQL (if applicable)
  sql_queries?: string[];
  results?: object[];
  row_count: number;

  // Metadata
  execution_time: number;
  retry_count: number;
  cache_hit: boolean;
  errors?: string[];

  // Conversation
  conversation_id?: string;
}
```

#### 2. GET /api/agent/health

Health check for agent.

**Response:**
```json
{
  "status": "healthy",
  "agent_type": "langgraph_autonomous",
  "framework": "LangGraph",
  "capabilities": [
    "intent_classification",
    "autonomous_routing",
    "multi_step_reasoning",
    "error_recovery",
    "result_validation",
    "retry_logic",
    "conversation_handling"
  ]
}
```

---

## Examples

### Example 1: Normal Conversation

**Input:**
```json
{
  "user_id": "user-123",
  "query": "Hello! How are you?"
}
```

**Agent Flow:**
```
1. classify_intent → NORMAL_CONVERSATION
2. route_after_intent → "chat"
3. handle_chat → Generate friendly response
4. END
```

**Output:**
```json
{
  "success": true,
  "response": "Hello! I'm doing great, thanks for asking! I'm here to help you with your financial accounts and transactions. What can I help you with today?",
  "intent": "NORMAL_CONVERSATION",
  "intent_confidence": 0.98,
  "execution_time": 0.45,
  "retry_count": 0
}
```

---

### Example 2: Account Query

**Input:**
```json
{
  "user_id": "user-123",
  "query": "What's my Chase account balance?"
}
```

**Agent Flow:**
```
1. classify_intent → ACCOUNTS_QUERY
2. route_after_intent → "plan_sql"
3. plan_sql_query → Complexity: SIMPLE
4. generate_sql → "SELECT balance FROM accounts WHERE user_id = %s AND name LIKE '%Chase%'"
5. validate_sql → Valid: true
6. execute_sql → Results: [{balance: 5432.10}]
7. check_results → Satisfactory: true
8. generate_response → Natural language
9. END
```

**Output:**
```json
{
  "success": true,
  "response": "Your Chase Bank Savings account has a balance of $5,432.10.",
  "intent": "ACCOUNTS_QUERY",
  "intent_confidence": 0.95,
  "sql_queries": ["SELECT balance FROM accounts WHERE user_id = %s AND name LIKE '%Chase%'"],
  "results": [{"balance": 5432.10}],
  "row_count": 1,
  "execution_time": 1.23,
  "retry_count": 0
}
```

---

### Example 3: Error Recovery with Retry

**Input:**
```json
{
  "user_id": "user-123",
  "query": "Show me my account info"
}
```

**Agent Flow:**
```
1. classify_intent → ACCOUNTS_QUERY
2. plan_sql_query → SIMPLE
3. generate_sql → "SELECT * FROM account WHERE user_id = %s"
4. validate_sql → Valid: true
5. execute_sql → ❌ Error: table "account" doesn't exist
6. route_after_execution → "error" → Actually should retry
7. check_results → Unsatisfactory: true, Needs retry: true
8. retry_sql → Generate new SQL: "SELECT * FROM accounts WHERE user_id = %s"
9. validate_sql → Valid: true
10. execute_sql → ✅ Success!
11. check_results → Satisfactory: true
12. generate_response → Natural language
13. END
```

**Output:**
```json
{
  "success": true,
  "response": "You have 2 accounts: Chase Bank Savings ($5,432.10) and Wells Fargo Checking ($1,234.56).",
  "intent": "ACCOUNTS_QUERY",
  "intent_confidence": 0.92,
  "sql_queries": [
    "SELECT * FROM account WHERE user_id = %s",
    "SELECT * FROM accounts WHERE user_id = %s"
  ],
  "results": [...],
  "row_count": 2,
  "execution_time": 2.45,
  "retry_count": 1
}
```

---

## Industry Comparison

### How Text2SQL Systems Use AI Agents

| System | Framework | Agentic? | Key Features |
|--------|-----------|----------|--------------|
| **Defog.ai** | LangChain | ✅ Yes | Multi-step decomposition, self-correction |
| **Vanna.ai** | Custom + RAG | ⚠️ Partial | Retrieves similar queries, limited autonomy |
| **Dataherald** | LangGraph | ✅ Yes | Query decomposition, intent classification |
| **OpenAI Data Analyst** | GPT-4 + Code Interpreter | ✅ Yes | Multi-step reasoning, visualizations |
| **Our Old System** | Custom Pipeline | ❌ No | Fixed sequence, no autonomy |
| **Our New System** | LangGraph | ✅ Yes | Intent classification, autonomous routing, retries |

---

## Future Enhancements

1. **Clarifying Questions** - Ask user for more info when ambiguous
2. **Multi-turn Conversations** - Remember context across messages
3. **Query Decomposition** - Break very complex queries into multiple steps
4. **Human-in-the-Loop** - Ask for confirmation before executing updates
5. **Streaming Responses** - Stream responses as agent progresses
6. **Visualization** - Automatically create charts for numeric results
7. **Metadata Management** - Handle profile updates, settings changes

---

## Conclusion

This LangGraph-based autonomous agent transforms the Text2SQL system from a simple pipeline into a **true AI agent** with:

- ✅ **Autonomous decision-making** - Chooses its own path
- ✅ **Intent understanding** - Knows what user wants
- ✅ **Error recovery** - Adapts when things fail
- ✅ **Multi-step reasoning** - Plans and executes complex tasks
- ✅ **Result validation** - Ensures quality

This is the **industry standard** for building production AI agents and provides a solid foundation for future enhancements.
