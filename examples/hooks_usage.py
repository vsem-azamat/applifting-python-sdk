"""
An example demonstrating the usage of middleware hooks with all supported backends.

This script shows how to create custom hooks for both synchronous and asynchronous
clients to intercept and log requests and responses.

To run this example:
1. Make sure you have the SDK and optional backends installed:
   `uv pip install .[all]` or `pip install .[all]`
2. Set your refresh token as an environment variable:
   export APPLIFTING_REFRESH_TOKEN="your-refresh-token-here"
3. Run the script: `python examples/hooks_usage.py`

You should see log messages prefixed with [Sync Hook] or [Async Hook] for each
request/response cycle, demonstrating that the hooks are being called correctly
for each backend.
"""

import asyncio
import os

import httpx

from applifting_python_sdk import (
    AsyncHook,
    AsyncOffersClient,
    OffersClient,
    Product,
    SyncHook,
)
from applifting_python_sdk.exceptions import AppliftingSDKError


# 1. Define custom hooks by implementing the SyncHook or AsyncHook protocol.
class SyncLoggingHook(SyncHook):
    """A simple synchronous hook that logs request and response details."""

    def on_request(self, *, request: httpx.Request) -> None:
        """Called before a request is sent."""
        print(f"[Sync Hook] >>> Request: {request.method} {request.url}")

    def on_response(self, *, response: httpx.Response) -> None:
        """Called after a response is received."""
        print(f"[Sync Hook] <<< Response: {response.status_code}")


class AsyncLoggingHook(AsyncHook):
    """A simple asynchronous hook that logs request and response details."""

    async def on_request(self, *, request: httpx.Request) -> None:
        """Called before a request is sent."""
        print(f"[Async Hook] >>> Request: {request.method} {request.url}")

    async def on_response(self, *, response: httpx.Response) -> None:
        """Called after a response is received."""
        print(f"[Async Hook] <<< Response: {response.status_code}")


def sync_main(refresh_token: str) -> None:
    """Demonstrates using hooks with the synchronous OffersClient."""
    print("\n--- Running Synchronous Examples ---")
    logging_hook = SyncLoggingHook()

    # Example 1: Sync client with default httpx backend
    print("\n[1. Sync Client with httpx backend]")
    try:
        with OffersClient(refresh_token=refresh_token, hooks=[logging_hook]) as client:
            product = Product(name="Sync Widget (httpx)", description="Test")
            client.register_product(product)
    except AppliftingSDKError as e:
        print(f"-> An error occurred (this is expected if product exists): {e}")

    # Example 2: Sync client with requests backend
    print("\n[2. Sync Client with requests backend]")
    try:
        with OffersClient(refresh_token=refresh_token, http_backend="requests", hooks=[logging_hook]) as client:
            product = Product(name="Sync Widget (requests)", description="Test")
            client.register_product(product)
    except AppliftingSDKError as e:
        print(f"-> An error occurred (this is expected if product exists): {e}")


async def async_main(refresh_token: str) -> None:
    """Demonstrates using hooks with the asynchronous AsyncOffersClient."""
    print("\n--- Running Asynchronous Examples ---")
    logging_hook = AsyncLoggingHook()

    # Example 1: Async client with default httpx backend
    print("\n[1. Async Client with httpx backend]")
    try:
        async with AsyncOffersClient(refresh_token=refresh_token, hooks=[logging_hook]) as client:
            product = Product(name="Async Widget (httpx)", description="Test")
            await client.register_product(product)
    except AppliftingSDKError as e:
        print(f"-> An error occurred (this is expected if product exists): {e}")

    # Example 2: Async client with aiohttp backend
    print("\n[2. Async Client with aiohttp backend]")
    try:
        async with AsyncOffersClient(
            refresh_token=refresh_token, http_backend="aiohttp", hooks=[logging_hook]
        ) as client:
            product = Product(name="Async Widget (aiohttp)", description="Test")
            await client.register_product(product)
    except AppliftingSDKError as e:
        print(f"-> An error occurred (this is expected if product exists): {e}")


if __name__ == "__main__":
    token = os.getenv("APPLIFTING_REFRESH_TOKEN")
    if not token:
        raise ValueError("APPLIFTING_REFRESH_TOKEN environment variable not set.")

    sync_main(token)
    asyncio.run(async_main(token))
