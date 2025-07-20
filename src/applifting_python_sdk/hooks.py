"""Interfaces for request/response middleware hooks."""

from typing import Protocol

import httpx


class SyncHook(Protocol):
    """A protocol for synchronous request/response hooks."""

    def on_request(self, *, request: httpx.Request) -> None:
        """A hook to be called before a request is sent."""
        ...

    def on_response(self, *, response: httpx.Response) -> None:
        """A hook to be called after a response is received."""
        ...


class AsyncHook(Protocol):
    """A protocol for asynchronous request/response hooks."""

    async def on_request(self, *, request: httpx.Request) -> None:
        """An async hook to be called before a request is sent."""
        ...

    async def on_response(self, *, response: httpx.Response) -> None:
        """An async hook to be called after a response is received."""
        ...
