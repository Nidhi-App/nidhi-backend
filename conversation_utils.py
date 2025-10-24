"""
Conversation utilities for title generation and other helpers
"""

import os
import logging
import requests
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ConversationTitleGenerator:
    """Generate conversation titles using GPT"""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.timeout = int(os.getenv("OPENAI_TIMEOUT", "10"))

        if not self.openai_api_key:
            logger.warning("⚠️  OpenAI API key not found - title generation will use fallback")

    def generate_title(self, first_message: str, max_length: int = 50) -> str:
        """
        Generate a descriptive title for a conversation based on the first message

        Args:
            first_message: The first user message in the conversation
            max_length: Maximum length of the title (default: 50 characters)

        Returns:
            Generated title string
        """
        # Fallback: Use truncated first message if API key not available
        if not self.openai_api_key:
            return self._fallback_title(first_message, max_length)

        try:
            # Create prompt for title generation
            prompt = f"""Generate a short, descriptive title (max {max_length} characters) for a financial chat conversation that starts with this user query:

"{first_message}"

Rules:
1. Title should be 3-6 words maximum
2. Focus on the main topic (e.g., "Account Overview", "Monthly Spending Analysis")
3. Be specific but concise
4. Do NOT use quotes or special characters
5. Capitalize properly like a title

Examples:
- "Show me my accounts" → "Account Overview"
- "How much did I spend on food last month?" → "Monthly Food Expenses"
- "What's my total balance?" → "Total Balance Check"

Generate ONLY the title, nothing else."""

            # Make request to OpenAI
            response = self._make_openai_request(prompt)

            # Extract title from response
            title = self._extract_title_from_response(response)

            # Clean and validate title
            title = title.strip()
            if len(title) > max_length:
                title = title[:max_length].strip()

            # Fallback if title is empty or too short
            if not title or len(title) < 3:
                logger.warning("Generated title too short, using fallback")
                return self._fallback_title(first_message, max_length)

            logger.info(f"✅ Generated title: '{title}' for message: '{first_message[:50]}...'")
            return title

        except Exception as e:
            logger.error(f"Failed to generate title: {e}")
            return self._fallback_title(first_message, max_length)

    def _make_openai_request(self, prompt: str) -> dict:
        """
        Make request to OpenAI API for title generation

        Args:
            prompt: The prompt for title generation

        Returns:
            API response dictionary
        """
        url = f"{self.openai_base_url}/responses"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "input": prompt,
            "reasoning": {"effort": "low"},
            "text": {"verbosity": "low"},
        }

        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _extract_title_from_response(self, response: dict) -> str:
        """
        Extract title from OpenAI API response

        Args:
            response: OpenAI API response

        Returns:
            Extracted title string
        """
        title = None

        if "output" in response and isinstance(response["output"], list):
            for output_item in response["output"]:
                if output_item.get("type") == "message" and "content" in output_item:
                    for content_item in output_item["content"]:
                        if content_item.get("type") == "output_text" and "text" in content_item:
                            title = content_item["text"]
                            break
                    if title:
                        break

        if not title:
            raise ValueError("No title found in OpenAI API response")

        return title.strip()

    def _fallback_title(self, first_message: str, max_length: int = 50) -> str:
        """
        Fallback title generation using simple truncation

        Args:
            first_message: The first user message
            max_length: Maximum title length

        Returns:
            Truncated title
        """
        # Remove question marks and extra whitespace
        title = first_message.replace("?", "").strip()

        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]

        # Truncate if too long
        if len(title) > max_length:
            # Try to truncate at word boundary
            title = title[:max_length].rsplit(" ", 1)[0]
            if len(title) < 10:  # If too short after truncation, just hard cut
                title = first_message[:max_length]

        # Add ellipsis if truncated
        if len(first_message) > max_length:
            title = title.rstrip() + "..."

        return title.strip() or "New Conversation"


# Singleton instance
_title_generator = None


def get_title_generator() -> ConversationTitleGenerator:
    """Get the global conversation title generator instance"""
    global _title_generator
    if _title_generator is None:
        _title_generator = ConversationTitleGenerator()
    return _title_generator


def generate_conversation_title(first_message: str, max_length: int = 50) -> str:
    """
    Convenience function to generate a conversation title

    Args:
        first_message: The first user message in the conversation
        max_length: Maximum length of the title

    Returns:
        Generated title string
    """
    return get_title_generator().generate_title(first_message, max_length)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_messages = [
        "Show me all my accounts",
        "How much did I spend on food last month?",
        "What's my total balance across all accounts?",
        "List my recent transactions from last week",
        "How many transactions did I make in the past 30 days?",
    ]

    generator = ConversationTitleGenerator()

    print("Testing Conversation Title Generation:")
    print("=" * 80)

    for message in test_messages:
        title = generator.generate_title(message)
        print(f"\nMessage: {message}")
        print(f"Title: {title}")
        print("-" * 80)
