"""Test suite for the alternative HTTP transports."""

from __future__ import annotations

import json
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import respx

from applifting_python_sdk import AsyncOffersClient, OffersClient
from applifting_python_sdk._generated.python_exercise_client.api.default import (
    auth_api_v1_auth_post,
    get_offers_api_v1_products_product_id_offers_get,
)
from applifting_python_sdk._generated.python_exercise_client.models.auth_response import AuthResponse
from applifting_python_sdk._generated.python_exercise_client.models.offer_response import OfferResponse


def create_test_auth_response(token: str = "test-token") -> AuthResponse:
    """Create a test AuthResponse using the generated model."""
    return AuthResponse(access_token=token)


def create_test_offer_response(offer_id: UUID | None = None, price: int = 100, stock: int = 5) -> OfferResponse:
    """Create a test OfferResponse using the generated model."""
    if offer_id is None:
        offer_id = uuid4()
    return OfferResponse(id=offer_id, price=price, items_in_stock=stock)


def get_api_path_for_offers(base_url: str, product_id: UUID) -> str:
    """Get the API path for getting offers, derived from the generated API function."""
    # Extract the path from the generated function's kwargs
    kwargs = get_offers_api_v1_products_product_id_offers_get._get_kwargs(product_id, bearer="dummy")
    return f"{base_url.rstrip('/')}{kwargs['url']}"


def get_api_path_for_auth(base_url: str) -> str:
    """Get the API path for authentication, derived from the generated API function."""
    # Extract the path from the generated function's kwargs
    kwargs = auth_api_v1_auth_post._get_kwargs(bearer="dummy")
    return f"{base_url.rstrip('/')}{kwargs['url']}"


def get_success_status_for_auth() -> int:
    """Get the success status code for auth endpoint from the generated API function."""
    # The auth endpoint returns 201 on success (as seen in the _parse_response function)
    return HTTPStatus.CREATED.value


def get_success_status_for_offers() -> int:
    """Get the success status code for offers endpoint from the generated API function."""
    # The offers endpoint returns 200 on success (as seen in the _parse_response function)
    return HTTPStatus.OK.value


@patch("requests.Session.send")
def test_offers_client_with_requests_backend(
    mock_send: MagicMock,
    base_url: str,
    refresh_token: str,
) -> None:
    """Ensure OffersClient works correctly with the requests backend."""
    product_id = uuid4()

    # Create test data using generated models and helper functions
    auth_response = create_test_auth_response()
    offer_response = create_test_offer_response()
    expected_url = get_api_path_for_offers(base_url, product_id)
    auth_url = get_api_path_for_auth(base_url)

    # Mock the auth call, which still uses httpx internally for the token manager
    with respx.mock(base_url=base_url) as mock_router:
        mock_router.post(auth_url).respond(get_success_status_for_auth(), json=auth_response.to_dict())

        # Mock the response from `requests`
        mock_response = MagicMock()
        mock_response.status_code = get_success_status_for_offers()
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = json.dumps([offer_response.to_dict()]).encode("utf-8")
        mock_send.return_value = mock_response

        with OffersClient(refresh_token=refresh_token, base_url=base_url, http_backend="requests") as client:
            offers = client.get_offers(product_id)

        # Verify the result using the test model
        assert len(offers) == 1
        assert offers[0].id == offer_response.id
        assert offers[0].price == offer_response.price
        assert offers[0].items_in_stock == offer_response.items_in_stock
        mock_send.assert_called_once()

        # Verify the request was made correctly
        sent_request = mock_send.call_args[0][0]
        assert sent_request.method == "GET"
        assert sent_request.url == expected_url
        assert "authorization" in sent_request.headers
        assert sent_request.headers["authorization"] == f"Bearer {auth_response.access_token}"


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.request")
async def test_async_offers_client_with_aiohttp_backend(
    mock_request: MagicMock,
    base_url: str,
    refresh_token: str,
) -> None:
    """Ensure AsyncOffersClient works correctly with the aiohttp backend."""
    product_id = uuid4()

    # Create test data using generated models and helper functions
    auth_response = create_test_auth_response()
    offer_response = create_test_offer_response()
    expected_url = get_api_path_for_offers(base_url, product_id)
    auth_url = get_api_path_for_auth(base_url)

    # Mock the auth call, which still uses httpx internally for the token manager
    with respx.mock(base_url=base_url) as mock_router:
        mock_router.post(auth_url).respond(get_success_status_for_auth(), json=auth_response.to_dict())

        # Mock the response from `aiohttp`
        mock_response = AsyncMock()
        mock_response.status = get_success_status_for_offers()
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.read.return_value = json.dumps([offer_response.to_dict()]).encode("utf-8")
        mock_response.version = MagicMock()
        mock_response.version.major = 1
        mock_response.version.minor = 1

        # aiohttp's request method returns an async context manager
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__.return_value = mock_response
        mock_request.return_value = async_context_manager

        async with AsyncOffersClient(refresh_token=refresh_token, base_url=base_url, http_backend="aiohttp") as client:
            offers = await client.get_offers(product_id)

        # Verify the result using the test model
        assert len(offers) == 1
        assert offers[0].id == offer_response.id
        assert offers[0].price == offer_response.price
        assert offers[0].items_in_stock == offer_response.items_in_stock
        mock_request.assert_called_once()

        # Verify the request was made correctly
        _, kwargs = mock_request.call_args
        assert kwargs["method"] == "GET"
        assert str(kwargs["url"]) == expected_url
        assert "authorization" in kwargs["headers"]
        assert kwargs["headers"]["authorization"] == f"Bearer {auth_response.access_token}"
