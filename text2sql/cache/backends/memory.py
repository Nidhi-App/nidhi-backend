"""
In-memory cache backend implementation
"""
import time
import logging
import fnmatch
from typing import Any, Optional, Dict
from collections import OrderedDict
from .base import CacheBackend

logger = logging.getLogger(__name__)


class InMemoryCacheBackend(CacheBackend):
    """In-memory cache backend with TTL support"""

    def __init__(self, max_items: int = 1000):
        """
        Initialize in-memory cache

        Args:
            max_items: Maximum number of items to store (LRU eviction)
        """
        super().__init__()
        self.max_items = max_items
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        logger.info(f"✅ In-memory cache initialized (max_items={max_items})")

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if key not in self._cache:
                self._record_miss()
                return None

            entry = self._cache[key]

            # Check if expired
            if entry["expires_at"] < time.time():
                # Expired, delete it
                del self._cache[key]
                self._record_miss()
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._record_hit()
            return entry["value"]

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self._record_error()
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            # Enforce max items (LRU eviction)
            if len(self._cache) >= self.max_items and key not in self._cache:
                # Remove oldest item (first item in OrderedDict)
                self._cache.popitem(last=False)

            expires_at = time.time() + ttl

            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time(),
            }

            # Move to end (most recently used)
            self._cache.move_to_end(key)

            self._record_set()
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self._record_error()
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if key in self._cache:
                del self._cache[key]
                self._record_delete()
                return True
            return False

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            self._record_error()
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Glob-style pattern (e.g., "user:123:*")

        Returns:
            Number of keys deleted
        """
        try:
            deleted_count = 0
            keys_to_delete = []

            # Find matching keys
            for key in self._cache.keys():
                if fnmatch.fnmatch(key, pattern):
                    keys_to_delete.append(key)

            # Delete matching keys
            for key in keys_to_delete:
                del self._cache[key]
                deleted_count += 1
                self._record_delete()

            return deleted_count

        except Exception as e:
            logger.error(f"Cache delete_pattern error for pattern {pattern}: {e}")
            self._record_error()
            return 0

    def clear(self) -> bool:
        """Clear all cache entries"""
        try:
            self._cache.clear()
            logger.info("✅ Cache cleared")
            return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self._record_error()
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        try:
            if key not in self._cache:
                return False

            entry = self._cache[key]

            # Check if expired
            if entry["expires_at"] < time.time():
                del self._cache[key]
                return False

            return True

        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            self._record_error()
            return False

    def get_size(self) -> int:
        """Get number of items in cache"""
        # Clean up expired entries first
        self._cleanup_expired()
        return len(self._cache)

    def _cleanup_expired(self) -> int:
        """
        Remove expired entries from cache

        Returns:
            Number of expired entries removed
        """
        expired_keys = []
        current_time = time.time()

        for key, entry in self._cache.items():
            if entry["expires_at"] < current_time:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics"""
        stats = self.get_stats()

        # Add memory-specific stats
        stats.update({
            "max_items": self.max_items,
            "backend": "memory",
        })

        return stats
