"""Pytest fixtures and .env loader for the test suite."""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from applifting_python_sdk import AsyncOffersClient


def _load_dotenv() -> None:
    """Populate ``os.environ`` from a simple ``.env`` file if present.

    A minimal parser is used to avoid external dependencies (e.g. python-dotenv).
    """

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        # Ignore blanks and comments
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


# Load the environment variables as early as possible
_load_dotenv()


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for the mocked API."""
    return os.getenv("BASE_URL", "https://python.exercise.applifting.cz")


@pytest.fixture(scope="session")
def refresh_token() -> str:
    """Refresh token used for authentication."""
    return os.getenv("APPLIFTING_REFRESH_TOKEN", "refresh")


@pytest_asyncio.fixture
async def async_offers_client(
    base_url: str, refresh_token: str
) -> AsyncGenerator[AsyncOffersClient, None]:
    """Provides an initialized AsyncOffersClient instance that is properly closed."""
    async with AsyncOffersClient(refresh_token=refresh_token, base_url=base_url) as client:
        yield client
