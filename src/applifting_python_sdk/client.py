import asyncio
import json
import threading
import time
from collections.abc import AsyncGenerator, Callable, Generator, Sequence
from http import HTTPStatus
from pathlib import Path
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
from .cache import OfferCache
from .constants import (
    API_BASE_URL_DEFAULT,
    DEFAULT_RETRIES,
    OFFERS_TTL_SECONDS_DEFAULT,
    TOKEN_TTL_SECONDS_DEFAULT,
)
from .exceptions import APIError, ProductAlreadyExists, ProductNotFound
from .hooks import AsyncHook, SyncHook
from .models import Offer, Product
from .transports import AioHTTPTransport, RequestsTransport

# Type variable used to specialise _BaseClient for sync or async back-ends.
ClientT = TypeVar("ClientT")


class BearerAuth(httpx.Auth):
    """Custom httpx auth flow to handle Bearer token authentication and refresh."""

    def __init__(self, token_manager: "TokenManager"):
        self._token_manager = token_manager

    def _set_auth_header(self, request: httpx.Request, token: str) -> None:
        """Sets the Bearer header with the provided token."""
        request.headers["Bearer"] = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        refreshed_in_this_flow = False
        # Attempt to get a token from the in-memory cache.
        token = self._token_manager.get_access_token()

        # If no token is available (neither in memory nor in file cache), refresh it.
        if not token:
            try:
                token = self._token_manager.refresh_access_token()
                refreshed_in_this_flow = True
            except exceptions.AuthenticationError:
                # If refresh fails, proceed without a token. The request will likely
                # fail with a 401, which will be returned to the user.
                token = None

        if token:
            self._set_auth_header(request, token)

        response = yield request

        if response.status_code == HTTPStatus.UNAUTHORIZED and not refreshed_in_this_flow:
            # The token was invalid or expired. Force a refresh and retry the request.
            try:
                new_token = self._token_manager.refresh_access_token(force=True)
                self._set_auth_header(request, new_token)
                yield request
            except exceptions.AuthenticationError:  # Catches TokenRefreshDeniedError too
                # If the forced refresh fails, we cannot recover.
                # The original 401 response will be returned to the user.
                pass

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        refreshed_in_this_flow = False
        # First attempt: try with cached token if available, otherwise send without auth
        token = await self._token_manager.async_get_access_token()
        if token:
            self._set_auth_header(request, token)
        else:
            try:
                token = await self._token_manager.async_refresh_access_token()
                refreshed_in_this_flow = True
                self._set_auth_header(request, token)
            except exceptions.AuthenticationError:
                token = None

        response = yield request

        if response.status_code == HTTPStatus.UNAUTHORIZED and not refreshed_in_this_flow:
            # The token was invalid or expired. Force a refresh and retry the request.
            try:
                new_token = await self._token_manager.async_refresh_access_token(force=True)
                self._set_auth_header(request, new_token)
                yield request
            except exceptions.AuthenticationError:  # Catches TokenRefreshDeniedError too
                # If the forced refresh fails, we cannot recover.
                # The original 401 response will be returned to the user.
                pass


class TokenManager:
    """Manages retrieving and caching the access token."""

    def __init__(self, refresh_token: str, client: GeneratedClient, token_ttl_seconds: int):
        self._refresh_token = refresh_token
        self._client = client
        self._token_ttl_seconds = token_ttl_seconds
        self._access_token: str | None = None
        self._expires_at: float = 0
        self._cache_path = Path.home() / ".cache" / "applifting_python_sdk" / "token.json"
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._load_token_from_file()

    def _load_token_from_file(self) -> None:
        """Loads a token from the file cache if it exists and is valid."""
        if not self._cache_path.exists():
            return
        try:
            data = json.loads(self._cache_path.read_text())
            if time.monotonic() < data.get("expires_at", 0):
                self._access_token = data.get("access_token")
                self._expires_at = data.get("expires_at", 0)
            else:
                # If the token in the file is expired, ensure we clear any
                # potentially stale in-memory token.
                self._access_token = None
                self._expires_at = 0
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            self._access_token = None
            self._expires_at = 0

    def _save_token_to_file(self) -> None:
        """Saves the current token and its expiry to the file cache."""
        if not self._access_token:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "access_token": self._access_token,
                "expires_at": self._expires_at,
            }
            self._cache_path.write_text(json.dumps(data))
        except OSError:
            # Silently fail if unable to write to the cache directory.
            pass

    def _clear_cached_token(self) -> None:
        """Clears the cached token both from memory and file."""
        self._access_token = None
        self._expires_at = 0
        try:
            if self._cache_path.exists():
                self._cache_path.unlink()
        except OSError:
            # Silently fail if unable to delete the cache file.
            pass

    def get_access_token(self) -> str | None:
        """
        Synchronously gets a valid, non-expired token from the cache.
        This method does not perform any network requests.
        """
        with self._lock:
            # If we have a valid token in memory, use it.
            if self._access_token and time.monotonic() < self._expires_at:
                return self._access_token
            # If the in-memory token is present but expired, it's definitively expired.
            # We should not reload from the file cache, as it might be stale or from
            # another process. The correct action is to signal expiry so a refresh occurs.
            if self._access_token:
                return None

            # If no token is in memory, try loading from the file cache.
            self._load_token_from_file()
            if self._access_token and time.monotonic() < self._expires_at:
                return self._access_token
            return None

    async def async_get_access_token(self) -> str | None:
        """Asynchronously gets a valid, non-expired token from the cache."""
        async with self._async_lock:
            if self._access_token and time.monotonic() < self._expires_at:
                return self._access_token
            if self._access_token:  # Token is present but expired
                return None

            # Only load from file if no token is in memory
            self._load_token_from_file()
            if self._access_token and time.monotonic() < self._expires_at:
                return self._access_token
            return None

    def refresh_access_token(self, force: bool = False) -> str:
        """Synchronously force a refresh of the access token."""
        with self._lock:
            # If not forcing, check if we already have a valid token.
            if not force and self._access_token and time.monotonic() < self._expires_at:
                return self._access_token
            return self._refresh_access_token_sync_unsafe()

    def _refresh_access_token_sync_unsafe(self) -> str:
        """Internal method to fetch a new token. Assumes a lock is held."""
        try:
            response = auth_api_v1_auth_post.sync_detailed(client=self._client, bearer=self._refresh_token)
        except Exception as e:
            raise exceptions.AuthenticationError(f"Failed to connect to authentication service: {e}") from e

        if response.status_code == HTTPStatus.CREATED and response.parsed:
            parsed = cast(AuthResponse, response.parsed)
            self._access_token = parsed.access_token
            self._expires_at = time.monotonic() + self._token_ttl_seconds
            self._save_token_to_file()
            return self._access_token

        if response.status_code == HTTPStatus.BAD_REQUEST and "Cannot generate" in response.content.decode(
            errors="ignore"
        ):
            raise exceptions.TokenRefreshDeniedError("API denied token refresh, likely due to rate-limiting.")

        raise exceptions.AuthenticationError(
            f"Failed to refresh access token. Status: {response.status_code}, "
            f"Body: {response.content.decode(errors='ignore')}"
        )

    async def async_refresh_access_token(self, force: bool = False) -> str:
        """Asynchronously refresh the access token."""
        async with self._async_lock:
            # If not forcing, check if we already have a valid token.
            if not force and self._access_token and time.monotonic() < self._expires_at:
                return self._access_token
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
            self._save_token_to_file()
            return self._access_token

        if response.status_code == HTTPStatus.BAD_REQUEST and "Cannot generate" in response.content.decode(
            errors="ignore"
        ):
            raise exceptions.TokenRefreshDeniedError("API denied token refresh, likely due to rate-limiting.")

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
        offers_ttl_seconds: int = OFFERS_TTL_SECONDS_DEFAULT,
    ) -> None:
        if not refresh_token:
            raise ValueError("A refresh_token must be provided.")

        auth_client = GeneratedClient(base_url=base_url, raise_on_unexpected_status=False)
        self._token_manager = TokenManager(
            refresh_token=refresh_token,
            client=auth_client,
            token_ttl_seconds=token_ttl_seconds,
        )
        self._offer_cache = OfferCache(ttl_seconds=offers_ttl_seconds)

        self._generated_client = GeneratedClient(base_url=base_url, raise_on_unexpected_status=False)
        self._auth = BearerAuth(self._token_manager)

    def _handle_register_product_response(self, response: Any, product_id: UUID) -> UUID:
        if response.status_code == HTTPStatus.CREATED and response.parsed:
            parsed_response = cast(RegisterProductResponse, response.parsed)
            return parsed_response.id
        if response.status_code == HTTPStatus.CONFLICT:
            raise ProductAlreadyExists(response.status_code, f"Product with ID '{product_id}' already exists.")
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            # This means the auth flow (including retry) failed.
            raise exceptions.AuthenticationError("Authentication failed. The refresh token may be invalid or expired.")

        raise APIError(response.status_code, response.content.decode(errors="ignore"))

    def _handle_get_offers_response(self, response: Any, product_id: UUID) -> list[Offer]:
        if response.status_code == HTTPStatus.OK and response.parsed is not None:
            offer_responses = cast(Sequence[OfferResponse], response.parsed)
            return [Offer.from_offer_response(o) for o in offer_responses]
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise ProductNotFound(response.status_code, f"Product with ID '{product_id}' not found.")
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            # This means the auth flow (including retry) failed.
            raise exceptions.AuthenticationError("Authentication failed. The refresh token may be invalid or expired.")

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
        offers_ttl_seconds: int = OFFERS_TTL_SECONDS_DEFAULT,
        http_backend: Literal["httpx", "aiohttp"] = "httpx",
        hooks: Sequence[AsyncHook] | None = None,
        **httpx_args: Any,
    ) -> None:
        super().__init__(
            refresh_token,
            base_url,
            token_ttl_seconds=token_ttl_seconds,
            offers_ttl_seconds=offers_ttl_seconds,
        )

        event_hooks: dict[str, list[Callable[..., Any]]] = {}
        if http_backend == "aiohttp":
            transport = httpx_args.pop("transport", AioHTTPTransport(hooks=hooks))
        elif http_backend == "httpx":
            transport = httpx_args.pop("transport", httpx.AsyncHTTPTransport(retries=retries))
            if hooks:
                # Convert hooks to httpx event hook format
                event_hooks["request"] = [
                    lambda request, hook=hook: asyncio.create_task(hook.on_request(request=request)) for hook in hooks
                ]
                event_hooks["response"] = [
                    lambda response, hook=hook: asyncio.create_task(hook.on_response(response=response))
                    for hook in hooks
                ]
        else:  # pragma: no cover
            raise ValueError("AsyncOffersClient supports only 'httpx' or 'aiohttp' backends.")

        self._http_client = httpx.AsyncClient(
            base_url=base_url,
            auth=self._auth,
            transport=transport,
            event_hooks=event_hooks,
            **httpx_args,
        )
        self._generated_client.set_async_httpx_client(self._http_client)

    async def register_product(self, product: Product) -> UUID:
        """Registers a new product."""
        response = await register_product_api_v1_products_register_post.asyncio_detailed(
            client=self._generated_client, body=product.to_register_request()
        )
        return self._handle_register_product_response(response, product.id)

    async def get_offers(self, product_id: UUID) -> list[Offer]:
        """Retrieves all offers for a specific product."""
        # Check cache first
        cached_offers = await self._offer_cache.async_get(product_id)
        if cached_offers is not None:
            return cached_offers

        # If not in cache, fetch from API
        response = await get_offers_api_v1_products_product_id_offers_get.asyncio_detailed(
            client=self._generated_client, product_id=product_id
        )
        offers = self._handle_get_offers_response(response, product_id)

        await self._offer_cache.async_set(product_id, offers)
        return offers

    async def __aenter__(self) -> "AsyncOffersClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
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
        offers_ttl_seconds: int = OFFERS_TTL_SECONDS_DEFAULT,
        http_backend: Literal["httpx", "requests"] = "httpx",
        hooks: Sequence[SyncHook] | None = None,
        **httpx_args: Any,
    ) -> None:
        super().__init__(
            refresh_token,
            base_url,
            token_ttl_seconds=token_ttl_seconds,
            offers_ttl_seconds=offers_ttl_seconds,
        )

        event_hooks: dict[str, list[Callable[..., Any]]] = {}
        if http_backend == "requests":
            transport = httpx_args.pop("transport", RequestsTransport(hooks=hooks))
        elif http_backend == "httpx":
            transport = httpx_args.pop("transport", httpx.HTTPTransport(retries=retries))
            if hooks:
                # Convert hooks to httpx event hook format
                event_hooks["request"] = [lambda request, hook=hook: hook.on_request(request=request) for hook in hooks]
                event_hooks["response"] = [
                    lambda response, hook=hook: hook.on_response(response=response) for hook in hooks
                ]
        else:  # pragma: no cover
            raise ValueError("OffersClient supports only 'httpx' or 'requests' backends.")

        self._http_client = httpx.Client(
            base_url=base_url,
            auth=self._auth,
            transport=transport,
            event_hooks=event_hooks,
            **httpx_args,
        )
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
        # Check cache first
        cached_offers = self._offer_cache.get(product_id)
        if cached_offers is not None:
            return cached_offers

        # If not in cache, fetch from API
        response = get_offers_api_v1_products_product_id_offers_get.sync_detailed(
            client=self._generated_client, product_id=product_id
        )
        offers = self._handle_get_offers_response(response, product_id)

        self._offer_cache.set(product_id, offers)
        return offers

    def __enter__(self) -> "OffersClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._http_client.close()
