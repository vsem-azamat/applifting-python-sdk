"""Applifting Offers API SDK."""

from importlib.metadata import PackageNotFoundError, version

try:  # Retrieve the installed package version
    __version__ = version("applifting-python-sdk")
except PackageNotFoundError:
    # fallback for editable installs
    __version__ = "0.0.0"

from .client import AsyncOffersClient, OffersClient
from .exceptions import (
    APIError,
    AppliftingSDKError,
    AuthenticationError,
    ProductAlreadyExists,
    ProductNotFound,
)
from .hooks import AsyncHook, SyncHook
from .models import (
    Offer,
    Product,
    RegisterProductRequest,
    RegisterProductResponse,
)

__all__ = [
    "AsyncOffersClient",
    "OffersClient",
    "AppliftingSDKError",
    "AuthenticationError",
    "ProductAlreadyExists",
    "ProductNotFound",
    "APIError",
    "Offer",
    "Product",
    "RegisterProductRequest",
    "RegisterProductResponse",
    "AsyncHook",
    "SyncHook",
]
