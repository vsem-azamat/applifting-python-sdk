# Applifting Python SDK

A Python SDK for the Applifting Offers microservice. This SDK provides both asynchronous and synchronous clients for registering products and retrieving offers, with automatic handling of API authentication.

## Features

-   **Dual Clients**: Offers both `AsyncOffersClient` and `OffersClient` to fit modern asynchronous applications and traditional synchronous codebases.
-   **Pluggable HTTP Clients**: Supports `httpx`, `requests`, and `aiohttp` as underlying HTTP backends.
-   **Transparent Authentication**: Automatically manages JWT access token refreshing, simplifying API interaction.
-   **Configurable Caching**: In-memory, time-based caching for `get_offers` to reduce redundant API calls.
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

For detailed, runnable scripts, including a synchronous example and examples of using different HTTP backends, see the `examples/` directory.

### Caching

To reduce network traffic, the client includes a built-in in-memory cache for the `get_offers` method. By default, results are cached for 60 seconds. You can configure this by passing the `offers_ttl_seconds` parameter to the client constructor.

```python
# Cache offers for 5 minutes (300 seconds)
client = OffersClient(
    refresh_token=refresh_token,
    offers_ttl_seconds=300,
)

# Disable caching completely
client = OffersClient(
    refresh_token=refresh_token,
    offers_ttl_seconds=0,
)
```

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
-   `examples`: Runnable scripts demonstrating SDK usage, including how to use different HTTP client backends (`httpx`, `requests`, `aiohttp`).

## Development

To set up a development environment, clone the repository and install the required dependencies. We use `uv` for dependency management.

```bash
# Create a virtual environment and activate it
uv venv
source .venv/bin/activate

# Install the package in editable mode with dev dependencies
uv sync --dev
```

### Development Commands

We provide a Makefile for common development tasks:

```bash
make help              # Show all available commands
make dev-install       # Install package and dev dependencies
make test              # Run tests
make test-cov          # Run tests with coverage report
make lint              # Run linting
make format            # Format code
make type-check        # Run type checking
make ci                # Run all CI checks
make build             # Build package
make clean             # Clean build artifacts
```

### Running Tests

The test suite ensures the reliability of the SDK. Before running tests, copy the example environment file and add your refresh token.

```bash
cp .env.example .env
# Now edit .env and add your token
```

Then, run `pytest`:

```bash
make test
# or directly:
uv run pytest
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality. Install them with:

```bash
make pre-commit-install
```

### CI/CD
The project includes GitHub Actions workflows for:

- **Continuous Integration** – runs linting, type checking, tests, and coverage on pushes & PRs targeting `dev` and `main`.
- **Release** – on tags matching `v*`, verifies the tag matches `pyproject.toml` version, builds the distribution, and publishes to TestPyPI (configure secrets to publish to real PyPI).
- **Dev → Main PR automation** – when you push to `dev`, a pull request from `dev` to `main` is (created if missing) or left alone if already open. Review the PR, ensure CI is green, then merge via the GitHub UI. Enable GitHub auto‑merge if you want the merge to happen automatically after checks pass.
