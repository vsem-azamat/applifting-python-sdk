"""
An example of using the async client with the `aiohttp` HTTP backend.

This script demonstrates how to:
1. Initialize the AsyncOffersClient with the `aiohttp` backend.
2. Create and register a new product.
3. Retrieve offers for that product.

To run this example:
1. Make sure you have the SDK and `aiohttp` installed:
   `uv pip install .[aiohttp]` or `pip install .[aiohttp]`
2. Set your refresh token as an environment variable:
   export APPLIFTING_REFRESH_TOKEN="your-refresh-token-here"
3. Run the script: `python examples/async_usage_aiohttp.py`

Note: If you get an error about "Cannot generate access token because another is valid",
this is expected behavior when there's already an active token. Wait a few minutes and try again.
"""

import asyncio
import os
from uuid import uuid4

from applifting_python_sdk import (
    AsyncOffersClient,
    Product,
    ProductAlreadyExists,
    ProductNotFound,
)
from applifting_python_sdk.exceptions import AppliftingSDKError


async def main() -> None:
    """An example of using the async SDK client with `aiohttp`."""
    refresh_token = os.getenv("APPLIFTING_REFRESH_TOKEN")
    if not refresh_token:
        raise ValueError("APPLIFTING_REFRESH_TOKEN environment variable not set.")

    # Initialize the client with the `aiohttp` backend.
    # This requires the `aiohttp` extra to be installed.
    async with AsyncOffersClient(refresh_token=refresh_token, http_backend="aiohttp") as client:
        product = Product(
            id=uuid4(),
            name="Super Async Widget (via aiohttp)",
            description="A high-quality widget registered via the aiohttp backend.",
        )
        print(f"Attempting to register product '{product.name}' with ID: {product.id}")
        try:
            registered_id = await client.register_product(product)
            print(f"-> Product registered successfully with ID: {registered_id}")

            print(f"Fetching offers for product ID: {registered_id}...")
            offers = await client.get_offers(registered_id)
            print(f"-> Found offers: {offers}")

        except (ProductAlreadyExists, ProductNotFound, AppliftingSDKError) as e:
            print(f"-> An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
