"""
Abstract base class for cache backends
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict


class CacheBackend(ABC):
    """Abstract base class for cache backends"""

    def __init__(self):
        """Initialize the cache backend"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Pattern to match (e.g., "user:123:*")

        Returns:
            Number of keys deleted
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """
        Clear all cache entries

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    def get_size(self) -> int:
        """
        Get number of items in cache

        Returns:
            Number of cached items
        """
        pass

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total_requests if total_requests > 0 else 0.0
        )

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "deletes": self.stats["deletes"],
            "errors": self.stats["errors"],
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 4),
            "size": self.get_size(),
        }

    def reset_stats(self) -> None:
        """Reset cache statistics"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

    def _record_hit(self) -> None:
        """Record cache hit"""
        self.stats["hits"] += 1

    def _record_miss(self) -> None:
        """Record cache miss"""
        self.stats["misses"] += 1

    def _record_set(self) -> None:
        """Record cache set"""
        self.stats["sets"] += 1

    def _record_delete(self) -> None:
        """Record cache delete"""
        self.stats["deletes"] += 1

    def _record_error(self) -> None:
        """Record cache error"""
        self.stats["errors"] += 1
