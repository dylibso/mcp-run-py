from typing import Dict, Generic, TypeVar
from datetime import datetime, timedelta

K = TypeVar("K")  # Key type
T = TypeVar("T")  # Value type


class Cache(Generic[K, T]):
    """
    A simple time-based cache implementation.

    The cache stores key-value pairs and optionally expires them after a specified duration.
    If no duration is specified, entries remain valid until explicitly removed.

    Type Parameters:
        K: The type of keys in the cache
        T: The type of values in the cache

    Examples:
        # Create a cache that expires after 5 minutes
        cache = Cache(timedelta(minutes=5))

        # Create a permanent cache
        permanent = Cache()
    """

    def __init__(self, duration: timedelta | None = None):
        """
        Initialize a new cache.

        Args:
            duration: Optional time after which entries should be considered stale.
                     If None, entries never expire.
        """
        self.items: Dict[K, T] = {}
        self.duration = duration
        self.last_update: datetime | None = None

    def add(self, key: K, item: T) -> None:
        """
        Add an item to the cache.

        Args:
            key: The key to store the item under
            item: The item to cache
        """
        self.items[key] = item

    def remove(self, key: K) -> None:
        """
        Remove an item from the cache if it exists.

        Args:
            key: The key to remove
        """
        self.items.pop(key, None)

    def get(self, key: K) -> T | None:
        """
        Get an item from the cache.

        Args:
            key: The key to look up

        Returns:
            The cached item if found, else None
        """
        return self.items.get(key)

    def __contains__(self, key: K) -> bool:
        """Test if a key exists in the cache"""
        return key in self.items

    def clear(self) -> None:
        """Remove all items from the cache and reset the last update time"""
        self.items = {}
        self.last_update = None

    def set_last_update(self) -> None:
        """Set the last update time to now"""
        self.last_update = datetime.now()

    def needs_refresh(self) -> bool:
        """
        Check if the cache needs to be refreshed based on its duration.

        Returns:
            True if:
            - A duration is set AND
            - Either no last update time exists OR the duration has elapsed
            False otherwise
        """
        if self.duration is None:
            return False
        if self.last_update is None:
            return True
        return datetime.now() - self.last_update >= self.duration
