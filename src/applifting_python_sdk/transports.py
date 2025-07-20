"""Alternative HTTP transports for the Applifting SDK.

These transports allow httpx‑based generated code to communicate through
other popular HTTP libraries (``requests`` for synchronous code and
``aiohttp`` for asynchronous code) without any changes to the generated
client itself.

The approach follows the pattern used in the official openai‑python SDK.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    import aiohttp
    import requests

    from .hooks import AsyncHook, SyncHook
else:
    # For runtime, these might be None if not installed
    try:
        import requests
    except ModuleNotFoundError:  # pragma: no cover
        requests = None  # type: ignore[assignment]

    try:
        import aiohttp
    except ModuleNotFoundError:  # pragma: no cover
        aiohttp = None  # type: ignore[assignment]

# --------------------------------------------------------------------------- #
# requests → httpx bridge                                                     #
# --------------------------------------------------------------------------- #


class RequestsTransport(httpx.BaseTransport):
    """An httpx transport that delegates requests to ``requests``."""

    def __init__(self, *, hooks: Sequence[SyncHook] | None = None, **session_kwargs: Any) -> None:
        if requests is None:  # pragma: no cover
            raise ImportError("`requests` is not installed. Run `pip install requests` to use this backend.")

        self._hooks = hooks or []
        self._session_kwargs = session_kwargs
        self._session: requests.Session | None = None

    # httpx will invoke this for every outgoing request.
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self._session is None:
            import requests

            self._session = requests.Session(**self._session_kwargs)

        import requests

        for hook in self._hooks:
            hook.on_request(request=request)

        prepared = self._session.prepare_request(
            requests.Request(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                data=request.content,
            )
        )

        # Convert httpx timeout to requests format
        httpx_timeout = request.extensions.get("timeout", {})
        timeout = None
        if httpx_timeout:
            connect_timeout = httpx_timeout.get("connect")
            read_timeout = httpx_timeout.get("read")
            if connect_timeout is not None and read_timeout is not None:
                timeout = (connect_timeout, read_timeout)
            elif read_timeout is not None:
                timeout = read_timeout

        try:
            resp = self._session.send(prepared, timeout=timeout, stream=False)
        except Exception as exc:
            # Convert requests exceptions to httpx TransportError
            if hasattr(requests, "exceptions") and isinstance(exc, requests.exceptions.RequestException):
                raise httpx.TransportError(str(exc)) from exc
            raise httpx.TransportError(str(exc)) from exc

        response = httpx.Response(
            status_code=resp.status_code,
            headers=list(resp.headers.items()),
            content=resp.content,
            request=request,
            extensions={"http_version": b"HTTP/1.1"},
        )

        for hook in self._hooks:
            hook.on_response(response=response)

        return response

    def close(self) -> None:
        if self._session is not None:  # pragma: no cover
            self._session.close()
            self._session = None


# --------------------------------------------------------------------------- #
# aiohttp → httpx bridge                                                      #
# --------------------------------------------------------------------------- #


class AioHTTPTransport(httpx.AsyncBaseTransport):
    """An httpx transport that delegates requests to ``aiohttp``."""

    def __init__(self, *, hooks: Sequence[AsyncHook] | None = None, **client_kwargs: Any) -> None:
        if aiohttp is None:  # pragma: no cover
            raise ImportError("`aiohttp` is not installed. Run `pip install aiohttp` to use this backend.")

        self._hooks = hooks or []
        self._client_kwargs = client_kwargs
        self._session: aiohttp.ClientSession | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self._session is None:
            import aiohttp

            self._session = aiohttp.ClientSession(**self._client_kwargs)

        for hook in self._hooks:
            await hook.on_request(request=request)

        # Extract query params – aiohttp wants them separate
        params: list[tuple[str, str]] = list(request.url.params.multi_items())

        # Convert httpx timeout to aiohttp format
        httpx_timeout = request.extensions.get("timeout", {})
        timeout = None
        if httpx_timeout:
            import aiohttp

            timeout = aiohttp.ClientTimeout(
                total=httpx_timeout.get("read"),
                connect=httpx_timeout.get("connect"),
            )

        try:
            async with self._session.request(
                method=request.method,
                url=str(request.url.copy_with(query=None)),
                headers=dict(request.headers),
                data=request.content,
                params=params,
                timeout=timeout,
            ) as resp:
                body = await resp.read()
                http_version = (
                    f"HTTP/{resp.version.major}.{resp.version.minor}".encode() if resp.version else b"HTTP/1.1"
                )

            response = httpx.Response(
                status_code=resp.status,
                headers=list(resp.headers.items()),
                content=body,
                request=request,
                extensions={"http_version": http_version},
            )

            for hook in self._hooks:
                await hook.on_response(response=response)

            return response
        except Exception as exc:
            # Convert aiohttp exceptions to httpx TransportError
            try:
                import aiohttp

                if hasattr(aiohttp, "ClientError") and isinstance(exc, aiohttp.ClientError):
                    raise httpx.TransportError(str(exc)) from exc
            except ImportError:
                pass
            raise httpx.TransportError(str(exc)) from exc

    async def aclose(self) -> None:
        if self._session is not None:  # pragma: no cover
            await self._session.close()
            self._session = None


# --------------------------------------------------------------------------- #

__all__ = ["RequestsTransport", "AioHTTPTransport"]
