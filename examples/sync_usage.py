"""
A basic usage example for the sync Applifting Python SDK client using the default HTTP backend.

This script demonstrates how to:
1. Initialize the OffersClient with the default httpx backend.
2. Create and register a new product.
3. Retrieve offers for that product.

To run this example:
1. Make sure you have the SDK installed (`pip install .` or `uv pip install .`).
2. Set your refresh token as an environment variable:
   export APPLIFTING_REFRESH_TOKEN="your-refresh-token-here"
3. Run the script: `python examples/sync_usage.py`

Note: If you get an error about "Cannot generate access token because another is valid",
this is expected behavior when there's already an active token. Wait a few minutes and try again.
"""

import os
from uuid import uuid4

from applifting_python_sdk import (
    OffersClient,
    Product,
    ProductAlreadyExists,
    ProductNotFound,
)
from applifting_python_sdk.exceptions import AppliftingSDKError


def main() -> None:
    """A basic example of using the synchronous SDK client with the default httpx backend."""
    refresh_token = os.getenv("APPLIFTING_REFRESH_TOKEN")
    if not refresh_token:
        raise ValueError("APPLIFTING_REFRESH_TOKEN environment variable not set.")

    # The client can be used as a context manager, which handles cleanup.
    # This uses the default httpx HTTP backend.
    # We can also configure the cache TTL for offer data (default is 60s).
    with OffersClient(refresh_token=refresh_token, offers_ttl_seconds=120) as client:
        product = Product(
            id=uuid4(),
            name="Super Sync Widget",
            description="A high-quality widget for all your sync needs.",
        )
        print(f"Attempting to register product '{product.name}' with ID: {product.id}")
        try:
            registered_id = client.register_product(product)
            print(f"-> Product registered successfully with ID: {registered_id}")

            print(f"Fetching offers for product ID: {registered_id}...")
            offers = client.get_offers(registered_id)
            print(f"-> Found offers: {offers}")

        except (ProductAlreadyExists, ProductNotFound, AppliftingSDKError) as e:
            print(f"-> An error occurred: {e}")


if __name__ == "__main__":
    main()
