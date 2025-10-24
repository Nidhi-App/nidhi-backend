"""
Cache manager for text2sql system
"""
import hashlib
import logging
from typing import Any, Optional, Dict, Callable
from .config import CacheConfig
from .backends.memory import InMemoryCacheBackend
from .backends.redis import RedisCacheBackend
from .backends.base import CacheBackend

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages caching for the text2sql system with user isolation
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache manager

        Args:
            config: Cache configuration (uses default if None)
        """
        self.config = config or CacheConfig.from_env()
        self.backend = self._initialize_backend()
        self.enabled = self.config.ENABLE_CACHING

        if self.enabled:
            logger.info(
                f"✅ Cache manager initialized (backend={self.config.CACHE_BACKEND})"
            )
        else:
            logger.info("⚠️  Caching is disabled")

    def _initialize_backend(self) -> CacheBackend:
        """Initialize the appropriate cache backend"""
        if self.config.CACHE_BACKEND == "redis":
            if not self.config.REDIS_URL:
                logger.warning(
                    "⚠️  Redis backend selected but REDIS_URL not configured. "
                    "Falling back to in-memory cache."
                )
                return InMemoryCacheBackend(max_items=self.config.MAX_MEMORY_ITEMS)

            try:
                return RedisCacheBackend(self.config.REDIS_URL)
            except Exception as e:
                logger.warning(
                    f"⚠️  Failed to initialize Redis backend: {e}. "
                    "Falling back to in-memory cache."
                )
                return InMemoryCacheBackend(max_items=self.config.MAX_MEMORY_ITEMS)

        else:  # memory backend
            return InMemoryCacheBackend(max_items=self.config.MAX_MEMORY_ITEMS)

    def create_cache_key(
        self,
        prefix: str,
        user_id: str,
        *args,
        **kwargs
    ) -> str:
        """
        Create a cache key with user isolation

        Args:
            prefix: Cache key prefix (e.g., "sql_gen", "response")
            user_id: User ID for isolation
            *args: Additional positional arguments to include in hash
            **kwargs: Additional keyword arguments to include in hash

        Returns:
            Cache key string

        Example:
            create_cache_key("sql_gen", "user123", "show accounts", schema_version="v1")
            -> "text2sql:user:user123:sql_gen:a1b2c3d4"
        """
        # Combine all arguments into a string for hashing
        hash_parts = [str(arg) for arg in args]
        hash_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        hash_input = "|".join(hash_parts)

        # Create hash
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:12]

        # Build key with user isolation
        key = f"{self.config.CACHE_KEY_PREFIX}:user:{user_id}:{prefix}:{hash_value}"

        return key

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.enabled:
            return None

        return self.backend.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        # Use default TTL if not provided
        if ttl is None:
            ttl = self.config.DYNAMIC_QUERY_TTL

        return self.backend.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False

        return self.backend.delete(key)

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled:
            return 0

        return self.backend.delete_pattern(pattern)

    def delete_user_cache(self, user_id: str) -> int:
        """
        Delete all cache entries for a user

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        pattern = f"{self.config.CACHE_KEY_PREFIX}:user:{user_id}:*"
        return self.backend.delete_pattern(pattern)

    def clear(self) -> bool:
        """Clear all cache entries"""
        if not self.enabled:
            return False

        return self.backend.clear()

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.enabled:
            return False

        return self.backend.exists(key)

    def get_or_set(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get value from cache or compute and set it

        Args:
            key: Cache key
            fetch_func: Function to call if cache miss
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        # Try to get from cache
        cached_value = self.get(key)
        if cached_value is not None:
            logger.debug(f"Cache HIT: {key}")
            return cached_value

        # Cache miss - compute value
        logger.debug(f"Cache MISS: {key}")
        value = fetch_func()

        # Store in cache
        self.set(key, value, ttl)

        return value

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False}

        stats = self.backend.get_stats()
        stats["enabled"] = True
        stats["backend"] = self.config.CACHE_BACKEND

        return stats

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics"""
        if not self.enabled:
            return {"enabled": False}

        if hasattr(self.backend, "get_detailed_stats"):
            stats = self.backend.get_detailed_stats()
        else:
            stats = self.backend.get_stats()

        stats["enabled"] = True
        stats["config"] = {
            "backend": self.config.CACHE_BACKEND,
            "max_memory_items": self.config.MAX_MEMORY_ITEMS,
            "llm_sql_gen_ttl": self.config.LLM_SQL_GENERATION_TTL,
            "llm_validation_ttl": self.config.LLM_VALIDATION_TTL,
            "llm_response_ttl": self.config.LLM_RESPONSE_TTL,
        }

        return stats

    def reset_stats(self) -> None:
        """Reset cache statistics"""
        if self.enabled and hasattr(self.backend, "reset_stats"):
            self.backend.reset_stats()


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(config: Optional[CacheConfig] = None) -> CacheManager:
    """
    Get the global cache manager instance

    Args:
        config: Cache configuration (only used on first call)

    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(config)
    return _cache_manager
