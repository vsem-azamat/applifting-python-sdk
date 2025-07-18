"""
A basic usage example for the sync Applifting Python SDK client.

This script demonstrates how to:
1. Initialize the OffersClient.
2. Create and register a new product.
3. Retrieve offers for that product.

To run this example:
1. Make sure you have the SDK installed (`pip install .` or `uv pip install .`).
2. Set your refresh token as an environment variable:
   export APPLIFTING_REFRESH_TOKEN="your-refresh-token-here"
3. Run the script: `python examples/sync_usage.py`
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
    """A basic example of using the synchronous SDK client."""
    refresh_token = os.getenv("APPLIFTING_REFRESH_TOKEN")
    if not refresh_token:
        raise ValueError("APPLIFTING_REFRESH_TOKEN environment variable not set.")

    # The client can be used as a context manager, which handles cleanup.
    with OffersClient(refresh_token=refresh_token) as client:
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
