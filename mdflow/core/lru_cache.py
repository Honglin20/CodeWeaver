"""LRU cache for memory manager."""
from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    """Least Recently Used (LRU) cache implementation."""

    def __init__(self, capacity: int = 100):
        """Initialize LRU cache.

        Args:
            capacity: Maximum number of items to cache
        """
        self.capacity = capacity
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        else:
            self.misses += 1
            return None

    def put(self, key: str, value: Any):
        """Put value into cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            # Update existing key
            self.cache.move_to_end(key)
        else:
            # Add new key
            if len(self.cache) >= self.capacity:
                # Remove least recently used item
                self.cache.popitem(last=False)

        self.cache[key] = value

    def clear(self):
        """Clear all cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "capacity": self.capacity,
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2)
        }
