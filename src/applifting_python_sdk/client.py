import asyncio
import time
from collections.abc import AsyncGenerator, Generator, Sequence
from http import HTTPStatus
from types import TracebackType
from typing import Any, Literal, TypeVar, cast
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
from .constants import (
    API_BASE_URL_DEFAULT,
    DEFAULT_RETRIES,
    TOKEN_TTL_SECONDS_DEFAULT,
)
from .exceptions import APIError, ProductAlreadyExists, ProductNotFound
from .models import Offer, Product
from .transports import AioHTTPTransport, RequestsTransport

# Type variable used to specialise _BaseClient for sync or async back-ends.
ClientT = TypeVar("ClientT")


class BearerAuth(httpx.Auth):
    """Custom httpx auth flow to handle Bearer token authentication and refresh."""

    def __init__(self, token_manager: "TokenManager"):
        self._token_manager = token_manager

    def _set_auth_header(self, request: httpx.Request, token: str) -> None:
        """Sets the Authorization header with the provided Bearer token."""
        request.headers["Authorization"] = f"Bearer {token}"

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        self._set_auth_header(request, self._token_manager.get_access_token())
        response = yield request

        if response.status_code == HTTPStatus.UNAUTHORIZED:
            self._set_auth_header(request, self._token_manager.refresh_access_token())
            yield request

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        self._set_auth_header(request, await self._token_manager.async_get_access_token())
        response = yield request

        if response.status_code == HTTPStatus.UNAUTHORIZED:
            # Token expired or invalid, force a refresh and retry the request
            self._set_auth_header(request, await self._token_manager.async_refresh_access_token())
            yield request


class TokenManager:
    """Manages retrieving and caching the access token."""

    def __init__(self, refresh_token: str, client: GeneratedClient, token_ttl_seconds: int):
        self._refresh_token = refresh_token
        self._client = client
        self._token_ttl_seconds = token_ttl_seconds
        self._access_token: str | None = None
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

        if response.status_code == HTTPStatus.CREATED and response.parsed:
            parsed = cast(AuthResponse, response.parsed)
            self._access_token = parsed.access_token
            self._expires_at = time.monotonic() + self._token_ttl_seconds
            return self._access_token

        raise exceptions.AuthenticationError(
            f"Failed to refresh access token. Status: {response.status_code}, "
            f"Body: {response.content.decode(errors='ignore')}"
        )


class _BaseClient[ClientT]:
    """Shared logic between the sync and async facade clients."""

    _http_client: ClientT

    def __init__(
        self,
        refresh_token: str,
        base_url: str = API_BASE_URL_DEFAULT,
        token_ttl_seconds: int = TOKEN_TTL_SECONDS_DEFAULT,
    ) -> None:
        if not refresh_token:
            raise ValueError("A refresh_token must be provided.")

        auth_client = GeneratedClient(base_url=base_url, raise_on_unexpected_status=False)
        self._token_manager = TokenManager(
            refresh_token=refresh_token, client=auth_client, token_ttl_seconds=token_ttl_seconds
        )

        self._generated_client = GeneratedClient(base_url=base_url, raise_on_unexpected_status=False)
        self._auth = BearerAuth(self._token_manager)

    def _handle_register_product_response(self, response: Any, product_id: UUID) -> UUID:
        if response.status_code == HTTPStatus.CREATED and response.parsed:
            parsed_response = cast(RegisterProductResponse, response.parsed)
            return parsed_response.id
        if response.status_code == HTTPStatus.CONFLICT:
            raise ProductAlreadyExists(response.status_code, f"Product with ID '{product_id}' already exists.")

        raise APIError(response.status_code, response.content.decode(errors="ignore"))

    def _handle_get_offers_response(self, response: Any, product_id: UUID) -> list[Offer]:
        if response.status_code == HTTPStatus.OK and response.parsed:
            offer_responses = cast(Sequence[OfferResponse], response.parsed)
            return [Offer.from_offer_response(o) for o in offer_responses]
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise ProductNotFound(response.status_code, f"Product with ID '{product_id}' not found.")

        raise APIError(response.status_code, response.content.decode(errors="ignore"))


class AsyncOffersClient(_BaseClient[httpx.AsyncClient]):
    """High-level async client for the Applifting Offers API."""

    _http_client: httpx.AsyncClient

    def __init__(
        self,
        refresh_token: str,
        base_url: str = API_BASE_URL_DEFAULT,
        retries: int = DEFAULT_RETRIES,
        token_ttl_seconds: int = TOKEN_TTL_SECONDS_DEFAULT,
        http_backend: Literal["httpx", "aiohttp"] = "httpx",
        **httpx_args: Any,
    ) -> None:
        super().__init__(refresh_token, base_url, token_ttl_seconds=token_ttl_seconds)

        if http_backend == "aiohttp":
            transport = httpx_args.pop("transport", AioHTTPTransport())
        elif http_backend == "httpx":
            transport = httpx_args.pop("transport", httpx.AsyncHTTPTransport(retries=retries))
        else:  # pragma: no cover
            raise ValueError("AsyncOffersClient supports only 'httpx' or 'aiohttp' backends.")

        self._http_client = httpx.AsyncClient(base_url=base_url, auth=self._auth, transport=transport, **httpx_args)
        self._generated_client.set_async_httpx_client(self._http_client)

    async def register_product(self, product: Product) -> UUID:
        """Registers a new product."""
        response = await register_product_api_v1_products_register_post.asyncio_detailed(
            client=self._generated_client, body=product.to_register_request()
        )
        return self._handle_register_product_response(response, product.id)

    async def get_offers(self, product_id: UUID) -> list[Offer]:
        """Retrieves all offers for a specific product."""
        response = await get_offers_api_v1_products_product_id_offers_get.asyncio_detailed(
            client=self._generated_client, product_id=product_id
        )
        return self._handle_get_offers_response(response, product_id)

    async def __aenter__(self) -> "AsyncOffersClient":
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        await self._http_client.aclose()


class OffersClient(_BaseClient[httpx.Client]):
    """High-level sync client for the Applifting Offers API."""

    _http_client: httpx.Client

    def __init__(
        self,
        refresh_token: str,
        base_url: str = API_BASE_URL_DEFAULT,
        retries: int = DEFAULT_RETRIES,
        token_ttl_seconds: int = TOKEN_TTL_SECONDS_DEFAULT,
        http_backend: Literal["httpx", "requests"] = "httpx",
        **httpx_args: Any,
    ) -> None:
        super().__init__(refresh_token, base_url, token_ttl_seconds=token_ttl_seconds)

        if http_backend == "requests":
            transport = httpx_args.pop("transport", RequestsTransport())
        elif http_backend == "httpx":
            transport = httpx_args.pop("transport", httpx.HTTPTransport(retries=retries))
        else:  # pragma: no cover
            raise ValueError("OffersClient supports only 'httpx' or 'requests' backends.")

        self._http_client = httpx.Client(base_url=base_url, auth=self._auth, transport=transport, **httpx_args)
        self._generated_client.set_httpx_client(self._http_client)

    def register_product(self, product: Product) -> UUID:
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
        response = register_product_api_v1_products_register_post.sync_detailed(
            client=self._generated_client, body=product.to_register_request()
        )
        return self._handle_register_product_response(response, product.id)

    def get_offers(self, product_id: UUID) -> list[Offer]:
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
        response = get_offers_api_v1_products_product_id_offers_get.sync_detailed(
            client=self._generated_client, product_id=product_id
        )
        return self._handle_get_offers_response(response, product_id)

    def __enter__(self) -> "OffersClient":
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        self._http_client.close()
