import asyncio
import time
from typing import AsyncGenerator, Generator, List, Optional, cast
from uuid import UUID

import httpx

from . import exceptions
from ._generated.python_exercise_client import Client as GeneratedClient
from ._generated.python_exercise_client.api.default import (
    auth_api_v1_auth_post,
    get_offers_api_v1_products_product_id_offers_get,
    register_product_api_v1_products_register_post,
)
from ._generated.python_exercise_client.models import (
    AuthResponse,
    OfferResponse,
    RegisterProductResponse,
)
from .exceptions import APIError, ProductAlreadyExists, ProductNotFound
from .models import Offer, Product


class BearerAuth(httpx.Auth):
    """Custom httpx auth flow to handle Bearer token authentication and refresh."""

    def __init__(self, token_manager: "TokenManager"):
        self._token_manager = token_manager

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        # This sync version is not used by the async client but is here for completeness.
        # It would require a separate sync TokenManager implementation to be fully functional without asyncio.run.
        access_token = self._token_manager.get_access_token()
        request.headers["Authorization"] = f"Bearer {access_token}"
        response = yield request

        if response.status_code == 401:
            new_access_token = self._token_manager.refresh_access_token()
            request.headers["Authorization"] = f"Bearer {new_access_token}"
            yield request

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        access_token = await self._token_manager.async_get_access_token()
        request.headers["Authorization"] = f"Bearer {access_token}"
        response = yield request

        if response.status_code == 401:
            # Token expired or invalid, force a refresh and retry the request
            new_access_token = await self._token_manager.async_refresh_access_token()
            request.headers["Authorization"] = f"Bearer {new_access_token}"
            yield request


class TokenManager:
    """Manages retrieving and caching the access token."""

    # Tokens expire in 5 minutes (300 seconds). We'll refresh them after 270 seconds (4.5 minutes) to be safe.
    _TOKEN_TTL_SECONDS = 270

    def __init__(self, refresh_token: str, client: GeneratedClient):
        self._refresh_token = refresh_token
        self._client = client
        self._access_token: Optional[str] = None
        self._expires_at: float = 0
        self._lock = asyncio.Lock()

    def get_access_token(self) -> str:
        """Synchronously get access token. Note: Runs an event loop."""
        return asyncio.run(self.async_get_access_token())

    async def async_get_access_token(self) -> str:
        """Asynchronously get a valid access token, refreshing if needed."""
        async with self._lock:
            if self._access_token and time.monotonic() < self._expires_at:
                return self._access_token
            return await self._async_refresh_access_token_unsafe()

    def refresh_access_token(self) -> str:
        """Synchronously force a refresh of the access token."""
        return asyncio.run(self.async_refresh_access_token())

    async def async_refresh_access_token(self) -> str:
        """Asynchronously force a refresh of the access token."""
        async with self._lock:
            return await self._async_refresh_access_token_unsafe()

    async def _async_refresh_access_token_unsafe(self) -> str:
        """Internal method to fetch a new access token. Assumes a lock is held."""
        try:
            response = await auth_api_v1_auth_post.asyncio_detailed(client=self._client, bearer=self._refresh_token)
        except Exception as e:
            raise exceptions.AuthenticationError(f"Failed to connect to authentication service: {e}") from e

        if response.status_code == 201 and response.parsed:
            parsed = cast(AuthResponse, response.parsed)
            self._access_token = parsed.access_token
            self._expires_at = time.monotonic() + self._TOKEN_TTL_SECONDS
            return self._access_token

        raise exceptions.AuthenticationError(
            f"Failed to refresh access token. Status: {response.status_code}, "
            f"Body: {response.content.decode(errors='ignore')}"
        )


class AsyncOffersClient:
    """High-level async client for the Applifting Offers API."""

    def __init__(self, refresh_token: str, base_url: str = "https://python.exercise.applifting.cz", **httpx_args):
        if not refresh_token:
            raise ValueError("A refresh_token must be provided.")

        auth_client = GeneratedClient(base_url=base_url, raise_on_unexpected_status=False)
        self._token_manager = TokenManager(refresh_token=refresh_token, client=auth_client)

        self._generated_client = GeneratedClient(base_url=base_url, raise_on_unexpected_status=False)
        transport = httpx_args.pop("transport", httpx.AsyncHTTPTransport(retries=3))
        auth = BearerAuth(self._token_manager)

        self._http_client = httpx.AsyncClient(base_url=base_url, auth=auth, transport=transport, **httpx_args)
        # This is the crucial step to link our httpx client with the auto-refresh auth
        # to the low-level generated client.
        self._generated_client.set_async_httpx_client(self._http_client)

    async def register_product(self, product: Product) -> UUID:
        """
        Registers a new product.

        Args:
            product: A `Product` object containing the details of the product to register.

        Returns:
            The UUID of the newly registered product.

        Raises:
            ProductAlreadyExists: If a product with the same ID is already registered.
            APIError: For other unexpected API errors.
        """
        response = await register_product_api_v1_products_register_post.asyncio_detailed(
            client=self._generated_client, body=product.to_register_request()
        )

        if response.status_code == 201 and response.parsed:
            parsed_response = cast(RegisterProductResponse, response.parsed)
            return parsed_response.id
        if response.status_code == 409:
            raise ProductAlreadyExists(
                response.status_code, f"Product with ID '{product.id}' already exists."
            )

        raise APIError(response.status_code, response.content.decode(errors="ignore"))

    async def get_offers(self, product_id: UUID) -> List[Offer]:
        """
        Retrieves all offers for a specific product.

        Args:
            product_id: The UUID of the product to retrieve offers for.

        Returns:
            A list of `Offer` objects.

        Raises:
            ProductNotFound: If no product with the given ID is found.
            APIError: For other unexpected API errors.
        """
        response = await get_offers_api_v1_products_product_id_offers_get.asyncio_detailed(
            client=self._generated_client, product_id=product_id
        )

        if response.status_code == 200 and response.parsed:
            offer_responses = cast(List[OfferResponse], response.parsed)
            return [Offer.from_offer_response(o) for o in offer_responses]
        if response.status_code == 404:
            raise ProductNotFound(response.status_code, f"Product with ID '{product_id}' not found.")

        raise APIError(response.status_code, response.content.decode(errors="ignore"))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._http_client.aclose()
