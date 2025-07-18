"""Custom exceptions for the Applifting SDK."""


class AppliftingSDKError(Exception):
    """Base exception for all Applifting SDK errors."""

    pass


class AuthenticationError(AppliftingSDKError):
    """Raised when authentication fails."""

    pass


class APIError(AppliftingSDKError):
    """Raised when the API returns an unexpected error.

    Attributes
    ----------
    status_code
        The HTTP status code returned by the API.
    body
        The raw response body, if it is useful for debugging.
    """

    def __init__(self, status_code: int, message: str | None = None, *, body: str | None = None) -> None:
        self.status_code: int = status_code
        self.body: str | None = body
        super().__init__(message or f"API request failed with HTTP {status_code}")

    # A more helpful string representation for logs / traces
    def __str__(self) -> str:  # noqa: D401
        return f"{self.__class__.__name__}({self.status_code}): {super().__str__()}"


class ProductNotFound(APIError):
    """Raised when a product is not found."""

    pass


class ProductAlreadyExists(APIError):
    """Raised when trying to register a product that already exists."""

    pass
