# Applifting Python SDK

A Python SDK for the Applifting Offers microservice. This SDK provides both asynchronous and synchronous clients for registering products and retrieving offers, with automatic handling of API authentication.

## Features

-   **Dual Clients**: Offers both `AsyncOffersClient` and `OffersClient` to fit modern asynchronous applications and traditional synchronous codebases.
-   **Transparent Authentication**: Automatically manages JWT access token refreshing, simplifying API interaction.
-   **Clean API Design**: Provides a high-level, intuitive interface (`register_product`, `get_offers`) over the generated API client.
-   **Robust Error Handling**: Maps API responses to specific, custom exceptions for predictable error management (e.g., `ProductNotFound`, `ProductAlreadyExists`).
-   **Type Safety**: Fully type-hinted codebase to support static analysis and improve developer experience.
-   **Resilience**: Includes built-in request retries for transient network issues.

## Installation

Clone the repository and install the SDK using `uv` or `pip`.

```bash
# Using uv
uv pip install .

# Using pip
pip install .
```

## Getting Started

### 1. Obtain a Refresh Token

A refresh token is required for authentication. You can request one by providing your email at the [assignment page](https://python.exercise.applifting.cz/assignment/sdk/).

For security, export the token as an environment variable:

```bash
export APPLIFTING_REFRESH_TOKEN="your-long-refresh-token-here"
```

### 2. Quickstart

The SDK provides both an `AsyncOffersClient` and a synchronous `OffersClient`.

Here is a basic example using the `AsyncOffersClient`:

```python
import asyncio
import os
from uuid import uuid4

from applifting_python_sdk import AsyncOffersClient, Product
from applifting_python_sdk.exceptions import AppliftingSDKError

async def main():
    refresh_token = os.getenv("APPLIFTING_REFRESH_TOKEN")
    if not refresh_token:
        raise ValueError("APPLIFTING_REFRESH_TOKEN not set.")

    async with AsyncOffersClient(refresh_token=refresh_token) as client:
        try:
            product = Product(name="Super Widget", description="A great widget.")
            print(f"Registering product: {product.name}...")
            registered_id = await client.register_product(product)
            print(f"-> Product registered with ID: {registered_id}")

            print(f"Fetching offers for product...")
            offers = await client.get_offers(registered_id)
            print(f"-> Found offers: {offers}")

        except AppliftingSDKError as e:
            print(f"An API error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

For detailed, runnable scripts, including a synchronous example, see the `examples/` directory.

### 3. Using the CLI

If you prefer a quick test from your terminal, the SDK ships with a standalone
command‑line interface (CLI). After installation the `applifting-sdk` command
is available on your `$PATH`.

```bash
# Register a new product
applifting-sdk register-product \
  --name "CLI Widget" \
  --description "A widget registered from the CLI"

# Fetch offers for a product (replace with the real UUID)
applifting-sdk get-offers 123e4567-e89b-12d3-a456-426614174000
```

The `--refresh-token/-t` option can be used to override the `APPLIFTING_REFRESH_TOKEN`
environment variable if needed. When the environment variable is set, you don't
need to pass the token explicitly. Run `applifting-sdk --help` or `applifting-sdk
<command> --help` for the full reference.

You can find a ready‑to‑run script demonstrating the above commands in
`examples/cli_usage.sh`.

## Project Structure

The repository is organized into several key directories:

-   `src/applifting_python_sdk`: The main source code for the SDK.
    -   `_generated`: Contains the low-level API client automatically generated from the OpenAPI specification.
    -   `client.py`: The high-level `OffersClient` and `AsyncOffersClient` that provide the user-facing interface.
    -   `models.py`: User-friendly data models (`Product`, `Offer`).
    -   `exceptions.py`: Custom exception classes for error handling.
    -   `cli.py`: Command-line interface for interacting with the API from the terminal.
-   `tests`: The test suite, using `pytest` and `respx` for mocking API calls.
-   `examples`: Runnable scripts demonstrating how to use both the synchronous and asynchronous clients.

## Development

To set up a development environment, clone the repository and install the required dependencies. We use `uv` for dependency management.

```bash
# Create a virtual environment and activate it
uv venv
source .venv/bin/activate

# Install the package in editable mode with dev dependencies
uv sync --dev
```

### Running Tests

The test suite ensures the reliability of the SDK. Before running tests, copy the example environment file and add your refresh token.

```bash
cp .env.example .env
# Now edit .env and add your token
```

Then, run `pytest`:

```bash
uv run pytest
```

---
This SDK was created as a solution to the Applifting Python task.
