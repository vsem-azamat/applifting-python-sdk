import asyncio
import threading
import time
from uuid import UUID

from .models import Offer


class OfferCache:
    """
    An in-memory cache for offer data with a configurable Time-To-Live (TTL).
    This cache is designed to be both thread-safe for synchronous access and
    async-safe for asynchronous access.
    """

    def __init__(self, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._cache: dict[UUID, tuple[list[Offer], float]] = {}
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def get(self, key: UUID) -> list[Offer] | None:
        """
        Synchronously retrieves an item from the cache.
        Returns the item if it exists and has not expired, otherwise returns None.
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]
            if time.monotonic() - timestamp > self._ttl:
                del self._cache[key]
                return None
            return value

    def set(self, key: UUID, value: list[Offer]) -> None:
        """Synchronously adds an item to the cache with the current timestamp."""
        with self._lock:
            self._cache[key] = (value, time.monotonic())

    async def async_get(self, key: UUID) -> list[Offer] | None:
        """
        Asynchronously retrieves an item from the cache.
        Returns the item if it exists and has not expired, otherwise returns None.
        """
        async with self._async_lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]
            if time.monotonic() - timestamp > self._ttl:
                del self._cache[key]
                return None
            return value

    async def async_set(self, key: UUID, value: list[Offer]) -> None:
        """Asynchronously adds an item to the cache with the current timestamp."""
        async with self._async_lock:
            self._cache[key] = (value, time.monotonic())
