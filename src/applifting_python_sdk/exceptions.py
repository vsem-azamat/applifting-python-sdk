"""Custom exceptions for the Applifting SDK."""


class AppliftingSDKError(Exception):
    """Base exception for all Applifting SDK errors."""

    pass


class AuthenticationError(AppliftingSDKError):
    """Raised when authentication fails."""

    pass


class APIError(AppliftingSDKError):
    """Raised when the API returns an unexpected error."""

    pass


class ProductNotFound(APIError):
    """Raised when a product is not found."""

    pass


class ProductAlreadyExists(APIError):
    """Raised when trying to register a product that already exists."""

    pass
