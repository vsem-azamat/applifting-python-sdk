"""
A basic usage example for the Applifting Python SDK.

This script demonstrates how to:
1. Initialize the AsyncOffersClient.
2. Create and register a new product.
3. Retrieve offers for that product.

To run this example:
1. Make sure you have the SDK installed (`pip install .` or `uv pip install .`).
2. Set your refresh token as an environment variable:
   export APPLIFTING_REFRESH_TOKEN="your-refresh-token-here"
3. Run the script: `python examples/basic_usage.py`
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


async def main():
    """A basic example of using the SDK."""
    refresh_token = os.getenv("APPLIFTING_REFRESH_TOKEN")
    if not refresh_token:
        raise ValueError("APPLIFTING_REFRESH_TOKEN environment variable not set.")

    # The client can be used as an async context manager, which handles cleanup.
    async with AsyncOffersClient(refresh_token=refresh_token) as client:
        # 1. Create a product instance.
        # The ID is a UUID. If you omit it, a random one will be generated.
        product = Product(
            id=uuid4(),
            name="Super Widget",
            description="A high-quality widget for all your needs.",
        )
        print(f"Attempting to register product '{product.name}' with ID: {product.id}")
        try:
            # 2. Register the product with the API.
            registered_id = await client.register_product(product)
            print(f"-> Product registered successfully with ID: {registered_id}")

            # 3. Retrieve offers for the newly registered product.
            print(f"Fetching offers for product ID: {registered_id}...")
            offers = await client.get_offers(registered_id)
            print(f"-> Found offers: {offers}")

        except ProductAlreadyExists:
            print(f"-> Product with ID {product.id} already exists.")
        except (ProductNotFound, AppliftingSDKError) as e:
            print(f"-> An API error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
