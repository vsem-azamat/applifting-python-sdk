# Applifting Python SDK Development Roadmap

This document outlines the development plan for the Applifting Python SDK, breaking it down into logical phases.

---

## Phase 1: Core SDK Setup & Authentication

**Status: ✅ Done**

This initial phase establishes the project's foundation. It focuses on setting up the core client structure, a robust authentication mechanism with automatic token refreshing, and a clean, user-facing API for models and exceptions.

### Tasks Completed:

1.  **Project Scaffolding**:
    -   Initialized the project with a `src` layout.
    -   Used `openapi-python-client` to generate a low-level API client from the provided `openapi.json` into `src/applifting_python_sdk/_generated/`.

2.  **Facade Pattern Implementation**:
    -   Created a high-level `AsyncOffersClient` in `src/applifting_python_sdk/client.py`. This will be the primary entry point for users.
    -   Created `src/applifting_python_sdk/models.py` to re-export generated data models (`attrs`-based classes), providing a clean namespace for users (e.g., `from applifting_python_sdk.models import Product`).
    -   Created `src/applifting_python_sdk/exceptions.py` for custom, user-friendly exceptions (`AuthenticationError`, `ProductNotFound`, etc.).

3.  **Automatic Token Refresh**:
    -   Implemented a `TokenManager` class to handle the logic of fetching and caching the access token.
    -   Implemented a custom `httpx.Auth` class (`BearerAuth`) that automatically intercepts `401 Unauthorized` responses, triggers a token refresh via the `TokenManager`, and retries the original request seamlessly. This fulfills a key "must-have" requirement.

4.  **Packaging & Dependencies**:
    -   Updated `pyproject.toml` with correct runtime dependencies (`httpx`, `attrs`) and development dependencies.
    -   Cleaned up `src/applifting_python_sdk/__init__.py` to expose the public-facing components of the SDK (`AsyncOffersClient`, models, exceptions).

---

## Phase 2: High-Level API Methods & Error Handling

**Status: ⏳ To Do**

This phase involves implementing the main business logic of the SDK within the `AsyncOffersClient`.

### Next Steps:

-   **Implement `register_product` method**: This method will take a user-friendly `Product` object and use the internal generated client to make the API call.
-   **Implement `get_offers` method**: This method will take a `product_id` and return a list of `Offer` objects.
-   **Map API Errors to Custom Exceptions**: Wrap the low-level API calls to catch specific HTTP status codes (e.g., 404, 409) and raise the corresponding custom exceptions defined in Phase 1.

---

## Phase 3: Testing

**Status: ⏳ To Do**

### Next Steps:
-   Write unit tests for the `TokenManager` and auth flow using `respx` to mock API calls.
-   Write integration tests for the high-level `register_product` and `get_offers` methods, covering both success and error cases.

---

## Phase 4: Bonus Features & Finalization

**Status: ⏳ To Do**

### Next Steps:
-   Implement a thin synchronous wrapper (`OffersClient`) around the `AsyncOffersClient`.
-   Add retry logic for transient network errors (e.g., 5xx status codes) using `httpx` transport configuration.
-   Create a simple CLI tool using Typer.
-   Implement a TTL cache for the `get_offers` method.
-   Finalize `README.md` with comprehensive examples.
-   Package the SDK and test publishing to TestPyPI.
