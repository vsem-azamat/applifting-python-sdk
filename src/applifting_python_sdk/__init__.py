"""
An SDK for the Applifting Offers microservice.
"""

__version__ = "0.1.0"

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
