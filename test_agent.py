"""
Test script for LangGraph autonomous agent

Tests the agent with various query types to verify:
- Intent classification
- Autonomous routing
- Error handling
"""

import logging
from langgraph_agent import run_agent, IntentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_agent():
    """Test the agent with various query types"""

    test_cases = [
        {
            "query": "Hello there!",
            "expected_intent": IntentType.NORMAL_CONVERSATION,
            "description": "Normal conversation (greeting)"
        },
        {
            "query": "What's my account balance?",
            "expected_intent": IntentType.ACCOUNTS_QUERY,
            "description": "Account query"
        },
        {
            "query": "Show me my transactions from last week",
            "expected_intent": IntentType.TRANSACTIONS_QUERY,
            "description": "Transaction query"
        },
        {
            "query": "Which account did I spend the most from?",
            "expected_intent": IntentType.ACCOUNTS_AND_TRANSACTIONS,
            "description": "Complex query (accounts + transactions)"
        },
        {
            "query": "How are you doing today?",
            "expected_intent": IntentType.NORMAL_CONVERSATION,
            "description": "Normal conversation (small talk)"
        }
    ]

    test_user_id = "test-user-123"

    print("\n" + "=" * 80)
    print("🤖 TESTING LANGGRAPH AUTONOMOUS AGENT")
    print("=" * 80)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'─' * 80}")
        print(f"Test {i}/{len(test_cases)}: {test_case['description']}")
        print(f"{'─' * 80}")
        print(f"Query: \"{test_case['query']}\"")
        print(f"Expected Intent: {test_case['expected_intent'].value}")

        try:
            # Run agent
            result = run_agent(
                user_query=test_case["query"],
                user_id=test_user_id
            )

            # Check intent
            actual_intent = result.get("intent", IntentType.UNKNOWN)
            intent_match = actual_intent == test_case["expected_intent"]

            print(f"\n📊 RESULTS:")
            print(f"   Intent: {actual_intent.value} (confidence: {result.get('intent_confidence', 0):.2f})")
            print(f"   Intent Match: {'✅' if intent_match else '❌'}")
            print(f"   SQL Queries: {len(result.get('sql_queries', []))}")
            print(f"   Retries: {result.get('retry_count', 0)}")
            print(f"   Errors: {len(result.get('errors', []))}")
            print(f"\n💬 RESPONSE:")
            print(f"   {result.get('response', 'No response')[:200]}")

            if result.get("errors"):
                print(f"\n⚠️  ERRORS:")
                for error in result["errors"]:
                    print(f"   - {error}")

        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("✅ TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_agent()
