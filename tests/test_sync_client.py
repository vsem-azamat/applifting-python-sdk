"""Test suite for the high-level OffersClient."""

from __future__ import annotations

import time
from uuid import UUID, uuid4

import httpx
import pytest
import respx

from applifting_python_sdk import OffersClient
from applifting_python_sdk.exceptions import APIError, ProductAlreadyExists, ProductNotFound
from applifting_python_sdk.models import Product


def test_register_product_success(respx_mock: respx.MockRouter, base_url: str, offers_client: OffersClient) -> None:
    """Ensure a successful 201 response returns the product ID."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    product_id = uuid4()
    register_route = respx_mock.post(f"{base_url}/api/v1/products/register").mock(
        return_value=httpx.Response(201, json={"id": str(product_id)})
    )

    product = Product(id=product_id, name="Widget", description="Test widget")
    new_id: UUID = offers_client.register_product(product)

    assert new_id == product_id
    assert register_route.called


def test_register_product_conflict(respx_mock: respx.MockRouter, base_url: str, offers_client: OffersClient) -> None:
    """A 409 response should raise ProductAlreadyExists."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    respx_mock.post(f"{base_url}/api/v1/products/register").mock(return_value=httpx.Response(409))

    product = Product(name="Widget", description="Test widget")
    with pytest.raises(ProductAlreadyExists):
        offers_client.register_product(product)


def test_register_product_generic_error(
    respx_mock: respx.MockRouter, base_url: str, offers_client: OffersClient
) -> None:
    """Any unexpected status should raise APIError."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    respx_mock.post(f"{base_url}/api/v1/products/register").mock(return_value=httpx.Response(500))

    product = Product(name="Widget", description="Test widget")
    with pytest.raises(APIError):
        offers_client.register_product(product)


def test_get_offers_success(respx_mock: respx.MockRouter, base_url: str, offers_client: OffersClient) -> None:
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

    offers = offers_client.get_offers(product_id)

    assert len(offers) == 1
    assert offers[0].id == offer_id
    assert offers_route.called


def test_get_offers_not_found(respx_mock: respx.MockRouter, base_url: str, offers_client: OffersClient) -> None:
    """A 404 response should raise ProductNotFound."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    product_id = uuid4()
    respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(return_value=httpx.Response(404))

    with pytest.raises(ProductNotFound):
        offers_client.get_offers(product_id)


def test_get_offers_generic_error(respx_mock: respx.MockRouter, base_url: str, offers_client: OffersClient) -> None:
    """Any unexpected status should raise APIError."""
    respx_mock.post(f"{base_url}/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "token"}))
    product_id = uuid4()
    respx_mock.get(f"{base_url}/api/v1/products/{product_id}/offers").mock(return_value=httpx.Response(500))

    with pytest.raises(APIError):
        offers_client.get_offers(product_id)


def test_authentication_flow(respx_mock: respx.MockRouter, base_url: str, offers_client: OffersClient) -> None:
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
    # Note: The sync client's token manager runs the async refresh in a new event loop.
    offers_client._token_manager._access_token = "oldtoken"
    offers_client._token_manager._expires_at = time.monotonic() + 1000

    offers = offers_client.get_offers(product_id)

    # Assertions
    assert len(offers) == 1
    assert offers_route.call_count == 2
    assert auth_route.called
    first_auth = offers_route.calls[0].request.headers["Authorization"]
    second_auth = offers_route.calls[1].request.headers["Authorization"]
    assert first_auth == "Bearer oldtoken"
    assert second_auth == "Bearer newtoken"
