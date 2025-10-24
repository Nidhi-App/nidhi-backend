"""
Cache configuration for text2sql system
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class CacheConfig:
    """Configuration for caching system"""

    # Cache Backend
    CACHE_BACKEND: str = "memory"  # "memory" or "redis"
    REDIS_URL: Optional[str] = None  # e.g., "redis://localhost:6379/0"

    # LLM Response Caching (in seconds)
    LLM_SQL_GENERATION_TTL: int = 86400  # 24 hours - schema rarely changes
    LLM_VALIDATION_TTL: int = 43200      # 12 hours - validation logic stable
    LLM_RESPONSE_TTL: int = 21600        # 6 hours - can vary with data freshness

    # Query Result Caching (in seconds)
    STATIC_QUERY_TTL: int = 86400        # 24 hours - historical queries
    SEMI_STATIC_TTL: int = 3600          # 1 hour - recent queries
    DYNAMIC_QUERY_TTL: int = 300         # 5 minutes - current data
    REALTIME_QUERY_TTL: int = 0          # No cache - real-time queries

    # Cache Storage Limits (for in-memory cache)
    MAX_MEMORY_ITEMS: int = 1000         # Maximum number of items in memory cache

    # Cache Key Prefix
    CACHE_KEY_PREFIX: str = "text2sql"

    # Enable/Disable Features
    ENABLE_CACHING: bool = True
    ENABLE_CACHE_STATS: bool = True

    @classmethod
    def from_env(cls) -> 'CacheConfig':
        """Create config from environment variables"""
        import os

        return cls(
            CACHE_BACKEND=os.getenv("CACHE_BACKEND", "memory"),
            REDIS_URL=os.getenv("REDIS_URL"),
            ENABLE_CACHING=os.getenv("ENABLE_CACHING", "true").lower() == "true",
            ENABLE_CACHE_STATS=os.getenv("ENABLE_CACHE_STATS", "true").lower() == "true",
        )

    def get_ttl_for_query_type(self, query_type: str) -> int:
        """Get TTL based on query type"""
        ttl_mapping = {
            "historical": self.STATIC_QUERY_TTL,
            "recent": self.SEMI_STATIC_TTL,
            "current": self.DYNAMIC_QUERY_TTL,
            "realtime": self.REALTIME_QUERY_TTL,
        }
        return ttl_mapping.get(query_type, self.DYNAMIC_QUERY_TTL)
