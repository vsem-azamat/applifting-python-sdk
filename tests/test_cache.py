import asyncio
import time
from uuid import uuid4

import pytest

from applifting_python_sdk.cache import OfferCache
from applifting_python_sdk.models import Offer


@pytest.fixture
def offer_cache() -> OfferCache:
    """Provides an OfferCache instance with a 2-second TTL."""
    return OfferCache(ttl_seconds=2)


@pytest.fixture
def sample_offers() -> list[Offer]:
    """Provides a sample list of offers."""
    return [Offer(id=uuid4(), price=100, items_in_stock=10)]


def test_sync_get_set(offer_cache: OfferCache, sample_offers: list[Offer]) -> None:
    """Test basic synchronous get and set functionality."""
    product_id = uuid4()
    assert offer_cache.get(product_id) is None

    offer_cache.set(product_id, sample_offers)
    cached_data = offer_cache.get(product_id)

    assert cached_data is not None
    assert cached_data[0].id == sample_offers[0].id


def test_sync_ttl_expiration(offer_cache: OfferCache, sample_offers: list[Offer]) -> None:
    """Test that synchronous cache entries expire after the TTL."""
    product_id = uuid4()
    offer_cache.set(product_id, sample_offers)

    # Should exist immediately
    assert offer_cache.get(product_id) is not None

    # Wait for TTL to expire
    time.sleep(2.1)

    # Should be gone
    assert offer_cache.get(product_id) is None


@pytest.mark.asyncio
async def test_async_get_set(offer_cache: OfferCache, sample_offers: list[Offer]) -> None:
    """Test basic asynchronous get and set functionality."""
    product_id = uuid4()
    assert await offer_cache.async_get(product_id) is None

    await offer_cache.async_set(product_id, sample_offers)
    cached_data = await offer_cache.async_get(product_id)

    assert cached_data is not None
    assert cached_data[0].id == sample_offers[0].id


@pytest.mark.asyncio
async def test_async_ttl_expiration(offer_cache: OfferCache, sample_offers: list[Offer]) -> None:
    """Test that asynchronous cache entries expire after the TTL."""
    product_id = uuid4()
    await offer_cache.async_set(product_id, sample_offers)

    # Should exist immediately
    assert await offer_cache.async_get(product_id) is not None

    # Wait for TTL to expire
    await asyncio.sleep(2.1)

    # Should be gone
    assert await offer_cache.async_get(product_id) is None


def test_thread_safety(offer_cache: OfferCache, sample_offers: list[Offer]) -> None:
    """A simple test to check for race conditions in synchronous methods."""
    import threading

    product_id = uuid4()
    errors = []

    def worker() -> None:
        try:
            for _ in range(100):
                offer_cache.set(product_id, sample_offers)
                offer_cache.get(product_id)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrency errors occurred: {errors}"
