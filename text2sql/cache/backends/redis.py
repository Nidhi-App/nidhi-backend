"""
Redis cache backend implementation
"""
import json
import logging
from typing import Any, Optional, Dict
from .base import CacheBackend

logger = logging.getLogger(__name__)


class RedisCacheBackend(CacheBackend):
    """Redis cache backend with JSON serialization"""

    def __init__(self, redis_url: str):
        """
        Initialize Redis cache

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
        """
        super().__init__()
        self.redis_url = redis_url
        self._client = None

        try:
            import redis
            self._client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._client.ping()
            logger.info(f"✅ Redis cache connected to {redis_url}")
        except ImportError:
            logger.warning(
                "⚠️  redis package not installed. Install with: pip install redis"
            )
            raise ImportError(
                "redis package required for Redis backend. Install with: pip install redis"
            )
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise Exception(f"Failed to connect to Redis at {redis_url}: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            value = self._client.get(key)
            if value is None:
                self._record_miss()
                return None

            self._record_hit()
            # Deserialize JSON
            return json.loads(value)

        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            self._record_error()
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis cache with TTL"""
        try:
            # Serialize to JSON
            serialized = json.dumps(value)
            self._client.setex(key, ttl, serialized)
            self._record_set()
            return True

        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            self._record_error()
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        try:
            deleted = self._client.delete(key)
            if deleted > 0:
                self._record_delete()
            return deleted > 0

        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            self._record_error()
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern in Redis

        Args:
            pattern: Redis pattern (e.g., "user:123:*")

        Returns:
            Number of keys deleted
        """
        try:
            # Find matching keys
            keys = self._client.keys(pattern)

            if not keys:
                return 0

            # Delete all matching keys
            deleted = self._client.delete(*keys)
            for _ in range(deleted):
                self._record_delete()

            return deleted

        except Exception as e:
            logger.error(f"Redis delete_pattern error for pattern {pattern}: {e}")
            self._record_error()
            return 0

    def clear(self) -> bool:
        """Clear all Redis cache entries"""
        try:
            self._client.flushdb()
            logger.info("✅ Redis cache cleared")
            return True

        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            self._record_error()
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            return self._client.exists(key) > 0

        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            self._record_error()
            return False

    def get_size(self) -> int:
        """Get number of keys in Redis database"""
        try:
            return self._client.dbsize()

        except Exception as e:
            logger.error(f"Redis get_size error: {e}")
            self._record_error()
            return 0

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed Redis cache statistics"""
        stats = self.get_stats()

        try:
            # Get Redis info
            redis_info = self._client.info("memory")

            stats.update({
                "backend": "redis",
                "redis_url": self.redis_url,
                "used_memory": redis_info.get("used_memory_human", "unknown"),
                "used_memory_peak": redis_info.get("used_memory_peak_human", "unknown"),
            })

        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")

        return stats

    def ping(self) -> bool:
        """Check if Redis connection is alive"""
        try:
            return self._client.ping()
        except Exception as e:
            logger.error(f"Redis ping error: {e}")
            return False
