"""
Query normalization for better cache hit rates

Normalizes natural language queries to improve cache effectiveness by
treating semantically similar queries as identical.
"""
import re
import logging

logger = logging.getLogger(__name__)


class QueryNormalizer:
    """Normalizes natural language queries for better cache matching"""

    # Common filler words that don't affect meaning
    FILLER_WORDS = {
        'the', 'a', 'an', 'my', 'me', 'i', 'please', 'can', 'could', 'would',
        'you', 'your', 'did', 'do', 'does', 'total', 'all', 'number', 'of',
        'just', 'really', 'very', 'much', 'many'
    }

    # Query type synonyms (expand as needed)
    SYNONYMS = {
        'show': 'list',
        'display': 'list',
        'get': 'list',
        'fetch': 'list',
        'retrieve': 'list',
        'transactions': 'transaction',
        'accounts': 'account',
        'expenses': 'expense',
        'spendings': 'spending',
        'purchases': 'purchase',
    }

    # Time period synonyms
    TIME_SYNONYMS = {
        'last week': 'past 7 days',
        'previous week': 'past 7 days',
        'this week': 'current week',
        'last month': 'past 30 days',
        'previous month': 'past 30 days',
        'this month': 'current month',
        'last year': 'past 365 days',
        'this year': 'current year',
    }

    def normalize(self, query: str) -> str:
        """
        Normalize a natural language query

        Args:
            query: Raw user query

        Returns:
            Normalized query string

        Examples:
            "How many transactions did I make last week?"
            → "how many transaction make past 7 days"

            "Show me all my accounts"
            → "list account"
        """
        if not query:
            return ""

        # Step 1: Lowercase and strip
        normalized = query.lower().strip()

        # Step 2: Remove punctuation
        normalized = re.sub(r'[?!.,;:]', '', normalized)

        # Step 3: Replace time period synonyms (do this before removing filler words)
        for original, replacement in self.TIME_SYNONYMS.items():
            normalized = normalized.replace(original, replacement)

        # Step 4: Replace word synonyms
        words = normalized.split()
        normalized_words = []
        for word in words:
            # Replace with synonym if exists
            normalized_word = self.SYNONYMS.get(word, word)
            normalized_words.append(normalized_word)
        normalized = ' '.join(normalized_words)

        # Step 5: Remove filler words
        words = normalized.split()
        filtered_words = [w for w in words if w not in self.FILLER_WORDS]
        normalized = ' '.join(filtered_words)

        # Step 6: Remove extra whitespace
        normalized = ' '.join(normalized.split())

        logger.debug(f"Normalized query: '{query}' → '{normalized}'")

        return normalized

    def are_similar(self, query1: str, query2: str) -> bool:
        """
        Check if two queries are semantically similar after normalization

        Args:
            query1: First query
            query2: Second query

        Returns:
            True if queries normalize to the same string
        """
        return self.normalize(query1) == self.normalize(query2)


# Global normalizer instance
_normalizer = None


def get_normalizer() -> QueryNormalizer:
    """Get the global query normalizer instance"""
    global _normalizer
    if _normalizer is None:
        _normalizer = QueryNormalizer()
    return _normalizer


def normalize_query(query: str) -> str:
    """
    Convenience function to normalize a query

    Args:
        query: Raw user query

    Returns:
        Normalized query string
    """
    return get_normalizer().normalize(query)


# Examples for testing
if __name__ == "__main__":
    normalizer = QueryNormalizer()

    test_cases = [
        ("How many transactions did i make last week?",
         "How many total number of transactions did i make last week?"),
        ("Show me all my accounts",
         "Display all of my accounts"),
        ("What did I spend on food last month?",
         "How much did I spend on food the previous month?"),
        ("List my recent transactions",
         "Show me my recent transactions"),
    ]

    print("Query Normalization Test Cases:")
    print("=" * 80)

    for q1, q2 in test_cases:
        n1 = normalizer.normalize(q1)
        n2 = normalizer.normalize(q2)
        match = "✅ MATCH" if n1 == n2 else "❌ NO MATCH"

        print(f"\nQuery 1: {q1}")
        print(f"Normalized: {n1}")
        print(f"\nQuery 2: {q2}")
        print(f"Normalized: {n2}")
        print(f"\n{match}")
        print("-" * 80)
