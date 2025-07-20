"""Test suite for the high-level AsyncOffersClient."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
import respx

from applifting_python_sdk import AsyncHook, AsyncOffersClient
from applifting_python_sdk.exceptions import APIError, ProductAlreadyExists, ProductNotFound
from applifting_python_sdk.models import Product

# --------------------------------------------------------------------------- #
# register_product                                                            #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_register_product_success(
    respx_mock: respx.MockRouter, base_url: str, async_offers_client: AsyncOffersClient
) -> None:
    """Ensure a successful 201 response returns the product ID."""
    # Mock auth and register endpoints
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    product_id = uuid4()
    register_route = respx_mock.post(f"{base_url}/api/v1/products/register").mock(
        return_value=httpx.Response(201, json={"id": str(product_id)})
    )

    product = Product(id=product_id, name="Widget", description="Test widget")
    new_id: UUID = await async_offers_client.register_product(product)

    assert new_id == product_id
    assert register_route.called


@pytest.mark.asyncio
async def test_register_product_conflict(
    respx_mock: respx.MockRouter, base_url: str, async_offers_client: AsyncOffersClient
) -> None:
    """A 409 response should raise ProductAlreadyExists."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    respx_mock.post(f"{base_url}/api/v1/products/register").mock(return_value=httpx.Response(409))

    product = Product(name="Widget", description="Test widget")
    with pytest.raises(ProductAlreadyExists):
        await async_offers_client.register_product(product)


@pytest.mark.asyncio
async def test_register_product_generic_error(
    respx_mock: respx.MockRouter, base_url: str, async_offers_client: AsyncOffersClient
) -> None:
    """Any unexpected status should raise APIError."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    respx_mock.post(f"{base_url}/api/v1/products/register").mock(return_value=httpx.Response(500))

    product = Product(name="Widget", description="Test widget")
    with pytest.raises(APIError):
        await async_offers_client.register_product(product)


# --------------------------------------------------------------------------- #
# get_offers                                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_offers_success(
    respx_mock: respx.MockRouter, base_url: str, async_offers_client: AsyncOffersClient
) -> None:
    """Ensure a 200 response is converted into Offer objects."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    product_id = uuid4()
    offer_id = uuid4()
    offers_route = respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": str(offer_id), "price": 100, "items_in_stock": 5}],
        )
    )

    offers = await async_offers_client.get_offers(product_id)

    assert len(offers) == 1
    assert offers[0].id == offer_id
    assert offers_route.called


@pytest.mark.asyncio
async def test_get_offers_not_found(
    respx_mock: respx.MockRouter, base_url: str, async_offers_client: AsyncOffersClient
) -> None:
    """A 404 response should raise ProductNotFound."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    product_id = uuid4()
    respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(return_value=httpx.Response(404))

    with pytest.raises(ProductNotFound):
        await async_offers_client.get_offers(product_id)


@pytest.mark.asyncio
async def test_get_offers_generic_error(
    respx_mock: respx.MockRouter, base_url: str, async_offers_client: AsyncOffersClient
) -> None:
    """Any unexpected status should raise APIError."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    product_id = uuid4()
    respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(return_value=httpx.Response(500))

    with pytest.raises(APIError):
        await async_offers_client.get_offers(product_id)


# --------------------------------------------------------------------------- #
# Authentication / token-refresh flow                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_authentication_flow(
    respx_mock: respx.MockRouter, base_url: str, async_offers_client: AsyncOffersClient
) -> None:
    """
    The client should:
    1. Send the request with an existing (expired) token.
    2. Receive a 401, refresh the token via /api/v1/auth.
    3. Retry the request with the new token, succeeding with 200.
    """

    product_id = uuid4()
    offer_id = uuid4()

    # Sequential responses: 401 first, 200 after token refresh
    offers_route = respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(
        side_effect=[
            httpx.Response(401),
            httpx.Response(
                200,
                json=[{"id": str(offer_id), "price": 100, "items_in_stock": 5}],
            ),
        ]
    )

    # Auth endpoint returns a brand-new token
    auth_route = respx_mock.post(f"{base_url}/api/v1/auth").mock(
        return_value=httpx.Response(201, json={"access_token": "newtoken"})
    )

    # Seed an existing (soon-to-expire) token so the first request uses it.
    async_offers_client._token_manager._access_token = "oldtoken"
    async_offers_client._token_manager._expires_at = time.monotonic() + 1000

    offers = await async_offers_client.get_offers(product_id)

    # Assertions
    assert len(offers) == 1
    assert offers_route.call_count == 2
    assert auth_route.called
    first_auth = offers_route.calls[0].request.headers["Authorization"]
    second_auth = offers_route.calls[1].request.headers["Authorization"]
    assert first_auth == "Bearer oldtoken"
    assert second_auth == "Bearer newtoken"


# --------------------------------------------------------------------------- #
# Caching                                                                     #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_offers_caching(respx_mock: respx.MockRouter, base_url: str, refresh_token: str) -> None:
    """Calling get_offers twice for the same product should only hit the API once."""
    async with AsyncOffersClient(refresh_token=refresh_token, base_url=base_url, offers_ttl_seconds=60) as client:
        respx_mock.post(f"{base_url}/api/v1/auth").mock(
            return_value=httpx.Response(201, json={"access_token": "token"})
        )
        product_id = uuid4()
        offer_id = uuid4()
        offers_route = respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": str(offer_id), "price": 100, "items_in_stock": 5}],
            )
        )

        # First call - should hit the API
        offers1 = await client.get_offers(product_id)
        assert offers_route.call_count == 1
        assert len(offers1) == 1

        # Second call - should use the cache
        offers2 = await client.get_offers(product_id)
        assert offers_route.call_count == 1  # No new API call
        assert len(offers2) == 1
        assert offers1[0].id == offers2[0].id


@pytest.mark.asyncio
async def test_get_offers_cache_expiration(respx_mock: respx.MockRouter, base_url: str, refresh_token: str) -> None:
    """After the TTL expires, get_offers should hit the API again."""
    async with AsyncOffersClient(refresh_token=refresh_token, base_url=base_url, offers_ttl_seconds=1) as client:
        respx_mock.post(f"{base_url}/api/v1/auth").mock(
            return_value=httpx.Response(201, json={"access_token": "token"})
        )
        product_id = uuid4()
        offer_id = uuid4()
        offers_route = respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": str(offer_id), "price": 100, "items_in_stock": 5}],
            )
        )

        # First call
        await client.get_offers(product_id)
        assert offers_route.call_count == 1

        # Wait for cache to expire
        await asyncio.sleep(1.1)

        # Second call - should hit the API again
        await client.get_offers(product_id)
        assert offers_route.call_count == 2


# --------------------------------------------------------------------------- #
# Hooks                                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_async_client_with_httpx_hooks(respx_mock: respx.MockRouter, base_url: str, refresh_token: str) -> None:
    """Ensure that httpx hooks are correctly called for the async client."""
    # Create a mock hook
    mock_hook = MagicMock(spec=AsyncHook)
    mock_hook.on_request = AsyncMock()
    mock_hook.on_response = AsyncMock()

    async with AsyncOffersClient(
        refresh_token=refresh_token, base_url=base_url, http_backend="httpx", hooks=[mock_hook]
    ) as client:
        # Mock API calls
        respx_mock.post(f"{base_url}/api/v1/auth").mock(
            return_value=httpx.Response(201, json={"access_token": "token"})
        )
        product_id = uuid4()
        respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(
            return_value=httpx.Response(200, json=[])
        )

        # Make a request to trigger the hooks
        await client.get_offers(product_id)

    # Assert that the hook methods were called
    mock_hook.on_request.assert_awaited_once()
    mock_hook.on_response.assert_awaited_once()

    # Verify the arguments passed to the hooks
    request_call = mock_hook.on_request.call_args
    assert "request" in request_call.kwargs
    assert isinstance(request_call.kwargs["request"], httpx.Request)

    response_call = mock_hook.on_response.call_args
    assert "response" in response_call.kwargs
    assert isinstance(response_call.kwargs["response"], httpx.Response)
