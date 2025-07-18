"""
Centralised SDK constants.

Keeping "magic numbers" and default strings in one place improves readability,
eases future maintenance, and allows integrators to override defaults without
diving into the core implementation.
"""

from http import HTTPStatus

# --------------------------------------------------------------------------- #
# HTTP status codes                                                           #
# --------------------------------------------------------------------------- #

HTTP_OK = HTTPStatus.OK  # 200
HTTP_CREATED = HTTPStatus.CREATED  # 201
HTTP_CONFLICT = HTTPStatus.CONFLICT  # 409
HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND  # 404
HTTP_UNAUTHORIZED = HTTPStatus.UNAUTHORIZED  # 401

# --------------------------------------------------------------------------- #
# SDK defaults                                                                #
# --------------------------------------------------------------------------- #

# Default base URL for the Applifting Offers API
API_BASE_URL_DEFAULT = "https://python.exercise.applifting.cz"

# The API issues ~5‑minute access tokens; we refresh 30 s early by default.
TOKEN_TTL_SECONDS_DEFAULT = 270

# How many automatic transport‑level retries httpx should perform
DEFAULT_RETRIES = 3

# Sentinel header name used by internal helpers (kept here for completeness)
AUTHORIZATION_HEADER = "Authorization"
