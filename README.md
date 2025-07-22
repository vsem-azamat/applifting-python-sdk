# Applifting Python SDK

A production-ready Python SDK for the Applifting Offers API. This SDK provides both asynchronous and synchronous clients for registering products and retrieving offers, with automatic handling of API authentication.

## 📚 Table of Contents

- [**Features**](#features) - Key capabilities and highlights of the SDK
- [**Installation**](#installation) - How to install the SDK and optional dependencies
- [**Getting Started**](#getting-started) - Quick setup guide and basic usage examples
- [**Usage**](#usage) - CLI tool and basic operations
- [**Advanced Usage**](#advanced-usage) - Caching, hooks, and HTTP backend configuration
- [**Requirements & Implementation Status**](#-requirements--implementation-status) - Complete checklist of implemented features
- [**Architecture & Design**](#architecture--design) - Technical details and design decisions
- [**Development**](#development) - Setup guide for contributors and local development

---

## Features

-   **Dual Clients**: Offers both `AsyncOffersClient` and `OffersClient` to fit modern asynchronous applications and traditional synchronous codebases.
-   **Pluggable HTTP Backends**: Supports `httpx` (default), `requests`, and `aiohttp` as underlying HTTP backends.
-   **Transparent Authentication**: Automatically manages JWT access token refreshing, simplifying API interaction.
-   **Configurable Caching**: In-memory, time-based caching for `get_offers` to reduce redundant API calls.
-   **Clean API Design**: Provides a high-level, intuitive interface (`register_product`, `get_offers`) over the generated API client.
-   **Robust Error Handling**: Maps API responses to specific, custom exceptions for predictable error management (e.g., `ProductNotFound`, `ProductAlreadyExists`).
-   **Comprehensive CLI**: Includes a `applifting-sdk` command-line tool for easy interaction.
-   **Middleware Hooks**: Extensible request/response hooks for logging, metrics, or custom logic.
-   **Type Safety**: Fully type-hinted codebase to support static analysis and improve developer experience.
-   **Resilience**: Includes built-in request retries for transient network issues (with the default `httpx` backend).

## Installation

Clone the repository and install the SDK using `uv` or `pip`.

```bash
uv pip install . # or pip install .
```

To use alternative HTTP backends, you can install the necessary extras:
```bash
# For requests backend
uv pip install ".[requests]"

# For aiohttp backend
uv pip install ".[aiohttp]"

# For all optional backends
uv pip install ".[all]"
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

## Usage

### CLI

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

## Advanced Usage

### Configuration & Environment Variables

The SDK can be configured through various parameters and environment variables:

#### Environment Variables
-   **`APPLIFTING_REFRESH_TOKEN`**: Your refresh token for authentication (used by CLI and examples)
-   **Default API Base URL**: `https://python.exercise.applifting.cz` (can be overridden in client constructor)
-   **Default Token TTL**: 270 seconds (4.5 minutes) - refreshes 30 seconds early from the ~5-minute API tokens

#### Client Configuration
```python
client = OffersClient(
    refresh_token="your-token",
    base_url="https://custom-api.example.com",  # Override default URL
    retries=5,                                   # HTTP retries (default: 3)
    token_ttl_seconds=300,                      # Token cache duration
    offers_ttl_seconds=120,                     # Offers cache duration
    http_backend="httpx",                       # Backend choice
    hooks=[LoggingHook()],                      # Middleware hooks
)
```

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

### Middleware Hooks

The SDK supports middleware hooks, allowing you to inspect or modify requests and responses. This is useful for implementing custom logging, metrics, or header manipulation.

To create a hook, define a class that implements the `SyncHook` or `AsyncHook` protocol and pass an instance of it to the client.

Here is an example of a simple logging hook:

```python
import httpx
from applifting_python_sdk import OffersClient, SyncHook

class LoggingHook(SyncHook):
    def on_request(self, *, request: httpx.Request) -> None:
        print(f">>> Request: {request.method} {request.url}")

    def on_response(self, *, response: httpx.Response) -> None:
        print(f"<<< Response: {response.status_code}")

# Initialize the client with the hook
client = OffersClient(
    refresh_token="your-token",
    hooks=[LoggingHook()],
)

# Now, all requests made with this client will be logged.
```

### Using Different HTTP Backends

By default, the SDK uses `httpx`. You can switch to `requests` (for the sync client) or `aiohttp` (for the async client) by specifying the `http_backend` parameter.

**Sync client with `requests`:**
```python
from applifting_python_sdk import OffersClient

# Make sure you have installed the requests extra: uv pip install ".[requests]"
client = OffersClient(
    refresh_token="your-token",
    http_backend="requests",
)
```

**Async client with `aiohttp`:**
```python
from applifting_python_sdk import AsyncOffersClient

# Make sure you have installed the aiohttp extra: uv pip install ".[aiohttp]"
client = AsyncOffersClient(
    refresh_token="your-token",
    http_backend="aiohttp",
)
```

## 📋 Requirements & Implementation Status

This section provides a comprehensive checklist of the project requirements from the original specification and their implementation status in this SDK.

### 🎯 Core Requirements (Must-Have)

- [x] **Intuitive and Pythonic SDK**: High-level `OffersClient` and `AsyncOffersClient` classes provide clean, easy-to-use interfaces that follow Python conventions
- [x] **Automatic Token Refresh**: Transparent JWT access token management with automatic refresh when tokens expire - users never need to handle authentication manually
- [x] **Async-first SDK**: `AsyncOffersClient` is the primary implementation with full async/await support for modern Python applications
- [x] **HTTP Client of Choice**: Built on `httpx` for both sync and async operations, providing excellent performance and modern HTTP features
- [x] **Full Type Hints**: Comprehensive type annotations throughout the codebase, validated with `mypy` for better IDE support and code safety
- [x] **Comprehensive Error Handling**: Custom exception hierarchy (`ProductNotFound`, `ProductAlreadyExists`, `AppliftingSDKError`) with clear error messages
- [x] **Comprehensive Test Suite**: Extensive test coverage using `pytest` with `respx` for HTTP mocking, covering all main functionality
- [x] **Clear Documentation**: Complete README with installation guides, usage examples, API reference, and architecture documentation
- [x] **Git Repository Management**: Proper Git workflow with feature branches, CI/CD pipelines, and automated releases

### 🚀 Extra Features (Bonus Points)

#### Multiple HTTP Client Support
- [x] **httpx Backend**: Default, high-performance HTTP client with full async support
- [x] **requests Backend**: Support for the popular `requests` library for sync operations
- [x] **aiohttp Backend**: Integration with `aiohttp` for async operations in aiohttp-based applications
- [x] **Unified Interface**: All backends provide the same API through transport abstraction layer

#### Advanced SDK Features
- [x] **CLI Companion Tool**: `applifting-sdk` command-line interface built with `Typer` for easy testing and integration
- [x] **Synchronous Wrapper**: `OffersClient` provides a complete sync interface wrapping the async implementation
- [x] **Caching Layer**: Configurable in-memory cache for `get_offers` with TTL support (default 60 seconds)
- [x] **Middleware Hooks**: Extensible request/response hooks for logging, metrics, and custom processing
- [x] **Advanced Configuration**: Support for custom base URLs, retry policies, timeouts, and environment-based configuration
- [ ] **Plugin Architecture**: Not implemented (extensible plugin system for custom functionality)
- [ ] **Batch Operations**: Not implemented (bulk operations for multiple products/offers)

#### Development & Deployment
- [x] **Retry Logic**: Built-in retry mechanisms using `httpx`'s transport-level retries for handling transient failures
- [x] **OpenAPI Integration**: Hand-crafted SDK built on top of OpenAPI-generated client foundation
- [x] **Packaging for Distribution**: Proper `pyproject.toml` configuration with `hatchling` build system
- [x] **Local Build/Install**: Easy development setup with `uv` and `Makefile` for common tasks
- [x] **TestPyPI Publishing**: Automated CI/CD pipeline with GitHub Actions for testing, building, and publishing
- [x] **Code Quality Tools**: Integration with `ruff` for linting/formatting, `mypy` for type checking
- [x] **Pre-commit Hooks**: Automated code quality checks before commits

### 🧪 Testing & Quality Assurance
- [x] **Unit Tests**: Comprehensive test suite covering all SDK functionality
- [x] **Integration Tests**: End-to-end tests with mocked API responses
- [x] **Type Checking**: Full `mypy` validation with strict type checking enabled
- [x] **Code Coverage**: Coverage reporting with detailed HTML reports
- [x] **Linting & Formatting**: Automated code style enforcement with `ruff`
- [x] **CI/CD Pipeline**: Automated testing on multiple Python versions and platforms

### 📦 API Coverage
- [x] **Authentication Endpoint**: `POST /api/v1/auth` - Token exchange functionality
- [x] **Product Registration**: `POST /api/v1/products/register` - Register new products with validation
- [x] **Offer Retrieval**: `GET /api/v1/products/{product_id}/offers` - Fetch offers for products with caching
- [x] **Error Handling**: Proper handling of all API error responses (401, 404, 422, etc.)
- [x] **Request/Response Models**: Type-safe data models for all API interactions

### 🔧 Architecture Features
- [x] **Token Management**: Sophisticated token lifecycle management with automatic refresh
- [x] **Transport Abstraction**: Clean separation between high-level API and HTTP transport layer
- [x] **Protocol-Based Design**: Use of Python protocols for type-safe, flexible interfaces
- [x] **Async/Sync Compatibility**: Seamless support for both async and sync programming models
- [x] **Memory-Efficient Caching**: Thread-safe and async-safe in-memory caching implementation
- [x] **Extensible Hook System**: Plugin-style hooks for request/response processing

### 💡 Developer Experience
- [x] **Rich Examples**: Multiple example scripts demonstrating different use cases and backends
- [x] **Interactive CLI**: User-friendly command-line tool for quick API testing
- [x] **Environment Configuration**: Support for environment variables and configuration files
- [x] **IDE Support**: Full IntelliSense and auto-completion through comprehensive type hints
- [x] **Debug-Friendly**: Clear error messages and logging support for troubleshooting

This SDK successfully implements all core requirements and the majority of bonus features, providing a production-ready solution for integrating with the Applifting Offers API.

## Architecture & Design

This section provides a deeper look into the SDK's internal architecture and design decisions.

### Project Structure

The repository is organized into several key directories:

-   `src/applifting_python_sdk`: The main source code for the SDK.
    -   `_generated`: Contains the low-level API client automatically generated from the OpenAPI specification.
    -   `client.py`: The high-level `OffersClient` and `AsyncOffersClient` that provide the user-facing interface and core logic.
    -   `models.py`: User-friendly data models (`Product`, `Offer`).
    -   `exceptions.py`: Custom exception classes for error handling.
    -   `cli.py`: Command-line interface for interacting with the API from the terminal.
    -   `cache.py`: In-memory caching layer for offers.
    -   `transports.py`: Custom transport bridges that enable support for `requests` and `aiohttp`.
    -   `hooks.py`: Protocol definitions for middleware hooks system.
    -   `constants.py`: Configuration constants and defaults.
-   `tests`: The test suite, using `pytest` and `respx` for mocking API calls.
-   `examples`: Runnable scripts demonstrating SDK usage.
    -   `async_usage.py`: Basic async client example.
    -   `sync_usage.py`: Basic sync client example.
    -   `async_usage_aiohttp.py`: Async client with aiohttp backend.
    -   `sync_usage_requests.py`: Sync client with requests backend.
    -   `hooks_usage.py`: Middleware hooks examples.
    -   `cli_usage.sh`: CLI usage examples.
-   `.github/workflows`: CI/CD pipelines for testing, releasing, and PR automation.

### Authentication Flow

The SDK handles the API's token-based authentication automatically. This is one of the most complex parts of the SDK, designed to be completely transparent to the end-user.

1.  **Initialization**: The user provides a long-lived **Refresh Token** when creating a client.
2.  **First Request**: The client's authentication handler requests an **Access Token** from an internal `TokenManager`.
3.  **Token Fetch**: The `TokenManager` sees it has no valid token, calls the `/api/v1/auth` endpoint to get a new one, and caches it with an expiry time (the API issues tokens that last ~5 minutes).
4.  **Authorized Request**: The client adds the `Authorization: Bearer <access-token>` header and sends the original request.
5.  **Token Expiration**: Later, if a request is sent with an expired token, the API will return a `401 Unauthorized` error.
6.  **Automatic Refresh**: The client's authentication handler detects the `401` status, instructs the `TokenManager` to force a refresh (which gets a new access token), and then automatically retries the original request with the new token.

### Caching Mechanism

To improve performance and reduce API calls, the SDK implements an in-memory caching layer for the `get_offers` method.

-   **Functionality**: When `get_offers` is called, the client first checks the cache for a valid (non-expired) entry for the given `product_id`.
-   **Cache Hit**: If a valid entry is found, the cached data is returned immediately without making an API call.
-   **Cache Miss**: If no entry is found or the existing entry has expired, the client proceeds to fetch the data from the API, stores the new data in the cache with a fresh timestamp, and then returns it.
-   **Configuration**: The cache's Time-To-Live (TTL) is configurable via the `offers_ttl_seconds` parameter in the client constructor (default is 60 seconds). Setting it to `0` disables the cache.
-   **Concurrency Safety**: The cache is designed to be safe for use in both multi-threaded (sync) and concurrent (async) applications.

### Middleware Hooks Architecture

The SDK implements a flexible middleware hooks system that allows users to intercept and inspect HTTP requests and responses. This feature enables custom logging, metrics collection, and other cross-cutting concerns.

#### Core Design Principles

-   **Protocol-Based**: Uses Python's `typing.Protocol` (`SyncHook`, `AsyncHook`) for type safety and flexibility, avoiding rigid class inheritance.
-   **Backend Agnostic**: Works seamlessly across all supported HTTP backends (`httpx`, `requests`, `aiohttp`).
-   **Unified Interface**: All hooks receive `httpx.Request` and `httpx.Response` objects, regardless of the underlying transport, providing a consistent developer experience.
-   **Zero-Overhead**: Hooks are only invoked when provided; no performance penalty when unused.

#### Architecture Overview

The client layer passes the hooks to the transport layer. For `requests` and `aiohttp`, custom transport bridges convert the native request/response objects of those libraries into `httpx` objects before calling the hooks. This ensures the hook implementation is independent of the chosen backend.

```
┌─────────────┐    ┌───────────────────┐    ┌──────────────────────────┐
│  User Code  │───▶│   OffersClient    │───▶│    Transport Bridge      │
│             │    │ (Sync or Async)   │    │ (e.g., RequestsTransport)│
└─────────────┘    └───────────────────┘    └──────────────────────────┘
      ▲                    │                          │
      │                    ▼                          ▼
      └────────────┌───────────────────┐    ┌──────────────────────────┐
                   │   Hook System     │◀───│     Hook Callbacks       │
                   │ (Calls user hooks)│    │ (on_request, on_response)│
                   └───────────────────┘    └──────────────────────────┘
```

#### Usage Patterns

**Basic Logging Hook:**
```python
class LoggingHook(SyncHook):
    def on_request(self, *, request: httpx.Request) -> None:
        print(f">>> {request.method} {request.url}")

    def on_response(self, *, response: httpx.Response) -> None:
        print(f"<<< {response.status_code}")

client = OffersClient(hooks=[LoggingHook()])
```

**Metrics Collection Hook:**
```python
class MetricsHook(AsyncHook):
    async def on_request(self, *, request: httpx.Request) -> None:
        self.start_time = time.time()

    async def on_response(self, *, response: httpx.Response) -> None:
        duration = time.time() - self.start_time
        await self.metrics_client.record_http_request(
            method=request.method,
            status=response.status_code,
            duration=duration
        )
```

### Data Models

The SDK provides clean, type-safe data models:

-   **Product**: Represents an item that can be registered.
    -   `id`: `UUID` (auto-generated if not provided)
    -   `name`: `str`
    -   `description`: `str`
-   **Offer**: Represents a price offering for a product.
    -   `id`: `UUID`
    -   `price`: `int` (price in cents/smallest currency unit)
    -   `items_in_stock`: `int`

### API Endpoints

The SDK interacts with three main API endpoints:

-   `POST /api/v1/auth`: Exchanges a long-lived **Refresh Token** for a short-lived **Access Token**.
-   `POST /api/v1/products/register`: Registers a new product. Requires a valid Access Token.
-   `GET /api/v1/products/{product_id}/offers`: Retrieves all available offers for a given product ID. Requires a valid Access Token.

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
make help                  # Show all available commands
make install              # Install package in development mode
make dev-install          # Install package and dev dependencies
make test                 # Run tests
make test-cov             # Run tests with coverage report
make lint                 # Run linting
make format               # Format code
make type-check           # Run type checking
make ci                   # Run all CI checks (lint, format, type-check, test)
make build                # Build package
make clean                # Clean build artifacts
make pre-commit-install   # Install pre-commit hooks
make pre-commit-run       # Run pre-commit on all files
```

### Running Tests

The test suite ensures the reliability of the SDK. Before running tests, copy the example environment file and add your refresh token (if it exists).

```bash
# If .env.example exists, copy it and add your token
cp .env.example .env  # (optional, only if .env.example exists)
# Edit .env and add your APPLIFTING_REFRESH_TOKEN
```

Then, run the tests:

```bash
make test
# or directly:
uv run pytest

# Run with coverage:
make test-cov
# or directly:
uv run pytest tests/ -v --cov=src/applifting_python_sdk --cov-report=html
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality. Install them with:

```bash
make pre-commit-install
# or directly:
uv run pre-commit install

# Run pre-commit on all files:
make pre-commit-run
# or directly:
uv run pre-commit run --all-files
```

### CI/CD
The project includes GitHub Actions workflows for:

- **Continuous Integration** – runs linting, type checking, tests, and coverage on pushes & PRs targeting `dev` and `main`.
- **Release** – on tags matching `v*`, verifies the tag matches `pyproject.toml` version, builds the distribution, and publishes to TestPyPI (configure secrets to publish to real PyPI).
- **Dev → Main PR automation** – when you push to `dev`, a pull request from `dev` to `main` is (created if missing) or left alone if already open. Review the PR, ensure CI is green, then merge via the GitHub UI. Enable GitHub auto‑merge if you want the merge to happen automatically after checks pass.
