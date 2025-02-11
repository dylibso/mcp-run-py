from typing import Dict
from datetime import datetime, timedelta


class Cache[K, T]:
    items: Dict[K, T]
    duration: timedelta
    last_update: datetime | None = None

    def __init__(self, t: timedelta | None = None):
        self.items = {}
        self.last_update = None
        self.duration = t

    def add(self, key: K, item: T):
        self.items[key] = item

    def remove(self, key: K):
        self.items.pop(key, None)

    def get(self, key: K) -> T | None:
        return self.items.get(key)

    def __contains__(self, key: K) -> bool:
        return key in self.items

    def clear(self):
        self.items = {}
        self.last_update = None

    def set_last_update(self):
        self.last_update = datetime.now()

    def needs_refresh(self) -> bool:
        if self.duration is None:
            return False
        if self.last_update is None:
            return True
        now = datetime.now()
        return now - self.last_update >= self.duration
