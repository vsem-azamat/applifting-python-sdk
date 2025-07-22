"""Comprehensive test suite for token management functionality."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path

import httpx
import pytest
import respx

from applifting_python_sdk._generated.python_exercise_client import Client as GeneratedClient
from applifting_python_sdk.client import BearerAuth, TokenManager
from applifting_python_sdk.exceptions import AuthenticationError


@pytest.fixture
def generated_client() -> GeneratedClient:
    """Create a real GeneratedClient for testing with respx."""
    return GeneratedClient(base_url="https://test.example.com")


@pytest.fixture
def token_manager(generated_client: GeneratedClient) -> TokenManager:
    """Create a TokenManager instance with an isolated cache."""
    # The isolated_cache autouse fixture in conftest handles patching Path.home
    return TokenManager(refresh_token="test_refresh_token", client=generated_client, token_ttl_seconds=3600)


class TestTokenManager:
    """Test suite for the TokenManager class."""

    def test_init_creates_cache_path(self, token_manager: TokenManager) -> None:
        """Test that TokenManager initialization sets up the correct cache path."""
        assert str(token_manager._cache_path).endswith("applifting_python_sdk/token.json")

    def test_load_token_from_file_missing_file(self, token_manager: TokenManager) -> None:
        """Test loading token when cache file doesn't exist."""
        # Ensure cache file doesn't exist
        if token_manager._cache_path.exists():
            token_manager._cache_path.unlink()

        token_manager._load_token_from_file()

        assert token_manager._access_token is None
        assert token_manager._expires_at == 0

    def test_load_token_from_file_valid_token(self, token_manager: TokenManager) -> None:
        """Test loading a valid token from cache file."""
        # Create a valid token cache file
        future_expiry = time.monotonic() + 1800  # 30 minutes from now
        token_data = {"access_token": "valid_token_123", "expires_at": future_expiry}

        token_manager._cache_path.parent.mkdir(parents=True, exist_ok=True)
        token_manager._cache_path.write_text(json.dumps(token_data))

        token_manager._load_token_from_file()

        assert token_manager._access_token == "valid_token_123"
        assert token_manager._expires_at == future_expiry

    def test_load_token_from_file_expired_token(self, token_manager: TokenManager) -> None:
        """Test loading an expired token from cache file."""
        # Create an expired token cache file
        past_expiry = time.monotonic() - 600  # 10 minutes ago
        token_data = {"access_token": "expired_token_123", "expires_at": past_expiry}

        token_manager._cache_path.parent.mkdir(parents=True, exist_ok=True)
        token_manager._cache_path.write_text(json.dumps(token_data))

        token_manager._load_token_from_file()

        # Expired token should not be loaded
        assert token_manager._access_token is None
        assert token_manager._expires_at == 0

    def test_load_token_from_file_invalid_json(self, token_manager: TokenManager) -> None:
        """Test loading token from invalid JSON file."""
        token_manager._cache_path.parent.mkdir(parents=True, exist_ok=True)
        token_manager._cache_path.write_text("invalid json content")

        token_manager._load_token_from_file()

        assert token_manager._access_token is None
        assert token_manager._expires_at == 0

    def test_save_token_to_file(self, token_manager: TokenManager) -> None:
        """Test saving token to cache file."""
        token_manager._access_token = "test_token_456"
        token_manager._expires_at = time.monotonic() + 1800

        token_manager._save_token_to_file()

        assert token_manager._cache_path.exists()

        saved_data = json.loads(token_manager._cache_path.read_text())
        assert saved_data["access_token"] == "test_token_456"
        assert saved_data["expires_at"] == token_manager._expires_at

    def test_clear_cached_token(self, token_manager: TokenManager) -> None:
        """Test clearing cached token both from memory and file."""
        # Set up token in memory and file
        token_manager._access_token = "token_to_clear"
        token_manager._expires_at = time.monotonic() + 1800
        token_manager._save_token_to_file()

        assert token_manager._cache_path.exists()

        token_manager._clear_cached_token()

        # Check memory is cleared
        assert token_manager._access_token is None
        assert token_manager._expires_at == 0

        # Check file is deleted
        assert not token_manager._cache_path.exists()

    def test_get_access_token_from_memory(self, token_manager: TokenManager) -> None:
        """Test getting valid token from in-memory cache."""
        token_manager._access_token = "memory_token"
        token_manager._expires_at = time.monotonic() + 1800

        token = token_manager.get_access_token()

        assert token == "memory_token"

    def test_get_access_token_from_file_cache(self, token_manager: TokenManager) -> None:
        """Test getting valid token from file cache when memory is empty."""
        # Clear memory cache
        token_manager._access_token = None
        token_manager._expires_at = 0

        # Set up file cache
        future_expiry = time.monotonic() + 1800
        token_data = {"access_token": "file_cached_token", "expires_at": future_expiry}
        token_manager._cache_path.parent.mkdir(parents=True, exist_ok=True)
        token_manager._cache_path.write_text(json.dumps(token_data))

        token = token_manager.get_access_token()

        assert token == "file_cached_token"
        # Should also load into memory
        assert token_manager._access_token == "file_cached_token"

    def test_get_access_token_no_valid_token(self, token_manager: TokenManager) -> None:
        """Test getting token when no valid token exists."""
        # Clear memory cache
        token_manager._access_token = None
        token_manager._expires_at = 0

        # Ensure no cache file exists
        if token_manager._cache_path.exists():
            token_manager._cache_path.unlink()

        token = token_manager.get_access_token()

        assert token is None

    @pytest.mark.asyncio
    async def test_async_get_access_token_from_memory(self, token_manager: TokenManager) -> None:
        """Test async getting valid token from in-memory cache."""
        token_manager._access_token = "async_memory_token"
        token_manager._expires_at = time.monotonic() + 1800

        token = await token_manager.async_get_access_token()

        assert token == "async_memory_token"

    @pytest.mark.asyncio
    async def test_async_get_access_token_from_file_cache(self, token_manager: TokenManager) -> None:
        """Test async getting valid token from file cache when memory is empty."""
        # Clear memory cache
        token_manager._access_token = None
        token_manager._expires_at = 0

        # Set up file cache
        future_expiry = time.monotonic() + 1800
        token_data = {"access_token": "async_file_cached_token", "expires_at": future_expiry}
        token_manager._cache_path.parent.mkdir(parents=True, exist_ok=True)
        token_manager._cache_path.write_text(json.dumps(token_data))

        token = await token_manager.async_get_access_token()

        assert token == "async_file_cached_token"
        # Should also load into memory
        assert token_manager._access_token == "async_file_cached_token"

    def test_refresh_access_token_success(self, token_manager: TokenManager, respx_mock: respx.MockRouter) -> None:
        """Test successful token refresh."""
        # Mock the auth API response
        mock_response = {
            "access_token": "new_refreshed_token",
        }
        auth_route = respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json=mock_response))

        token = token_manager.refresh_access_token()

        assert token == "new_refreshed_token"
        assert token_manager._access_token == "new_refreshed_token"
        assert token_manager._expires_at > time.monotonic()
        assert auth_route.called

    def test_refresh_access_token_with_force(self, token_manager: TokenManager, respx_mock: respx.MockRouter) -> None:
        """Test forced token refresh even when valid token exists."""
        # Set up existing valid token
        token_manager._access_token = "existing_valid_token"
        token_manager._expires_at = time.monotonic() + 1800

        # Mock the auth API response
        mock_response = {
            "access_token": "forced_new_token",
        }
        auth_route = respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json=mock_response))

        token = token_manager.refresh_access_token(force=True)

        assert token == "forced_new_token"
        assert token_manager._access_token == "forced_new_token"
        assert auth_route.called

    def test_refresh_access_token_without_force_returns_existing(self, token_manager: TokenManager) -> None:
        """Test that refresh without force returns existing valid token."""
        # Set up existing valid token
        existing_token = "existing_valid_token"
        token_manager._access_token = existing_token
        token_manager._expires_at = time.monotonic() + 1800

        token = token_manager.refresh_access_token(force=False)

        assert token == existing_token

    def test_refresh_access_token_auth_failure(self, token_manager: TokenManager, respx_mock: respx.MockRouter) -> None:
        """Test token refresh when auth API returns error."""
        # Mock the auth API to return 401
        auth_route = respx_mock.post("/api/v1/auth").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid refresh token"})
        )

        with pytest.raises(AuthenticationError) as exc_info:
            token_manager.refresh_access_token()

        assert "Failed to refresh access token" in str(exc_info.value)
        assert auth_route.called

    def test_refresh_access_token_connection_error(
        self, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test token refresh when connection fails."""
        # Mock the auth API to raise a connection error
        auth_route = respx_mock.post("/api/v1/auth").mock(side_effect=httpx.ConnectError("Connection failed"))

        with pytest.raises(AuthenticationError) as exc_info:
            token_manager.refresh_access_token()

        assert "Failed to connect to authentication service" in str(exc_info.value)
        assert auth_route.called

    @pytest.mark.asyncio
    async def test_async_refresh_access_token_success(
        self, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test successful async token refresh."""
        # Mock the auth API response
        mock_response = {
            "access_token": "new_async_refreshed_token",
        }
        auth_route = respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json=mock_response))

        token = await token_manager.async_refresh_access_token()

        assert token == "new_async_refreshed_token"
        assert token_manager._access_token == "new_async_refreshed_token"
        assert token_manager._expires_at > time.monotonic()
        assert auth_route.called

    def test_concurrent_refresh_thread_safety(self, token_manager: TokenManager, respx_mock: respx.MockRouter) -> None:
        """Test that concurrent access doesn't cause race conditions in token refresh."""
        # Mock the auth API response
        respx_mock.post("/api/v1/auth").mock(
            return_value=httpx.Response(201, json={"access_token": "thread_safe_token"})
        )

        results: list[str | None] = []
        errors: list[Exception] = []

        def try_get_token() -> None:
            try:
                # Use force=True to ensure refresh is attempted
                token = token_manager.refresh_access_token(force=True)
                results.append(token)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=try_get_token) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors occurred: {errors}"
        assert len(results) == 5
        assert all(token == "thread_safe_token" for token in results)

    @pytest.mark.asyncio
    async def test_concurrent_refresh_async_safety(
        self, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test that concurrent async access doesn't cause race conditions."""
        # Mock the auth API response
        respx_mock.post("/api/v1/auth").mock(
            return_value=httpx.Response(201, json={"access_token": "async_safe_token"})
        )

        tasks = [token_manager.async_refresh_access_token(force=True) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            assert not isinstance(result, Exception)
            assert result == "async_safe_token"


class TestBearerAuth:
    """Test suite for the BearerAuth class."""

    @pytest.fixture
    def bearer_auth(self, token_manager: TokenManager) -> BearerAuth:
        """Create a BearerAuth instance for testing."""
        return BearerAuth(token_manager)

    def test_set_auth_header(self, bearer_auth: BearerAuth) -> None:
        """Test setting the Bearer header."""
        request = httpx.Request("GET", "https://test.example.com")

        bearer_auth._set_auth_header(request, "test_token_123")

        assert request.headers["Bearer"] == "test_token_123"

    def test_auth_flow_with_cached_token(self, bearer_auth: BearerAuth, token_manager: TokenManager) -> None:
        """Test auth flow when a valid cached token exists."""
        # Set up valid cached token
        token_manager._access_token = "cached_token"
        token_manager._expires_at = time.monotonic() + 1800

        request = httpx.Request("GET", "https://test.example.com")

        # Simulate the auth flow
        flow = bearer_auth.auth_flow(request)

        # First yield should include the Bearer header
        first_request = next(flow)
        assert first_request.headers["Bearer"] == "cached_token"

        # Simulate successful response (no retry needed)
        success_response = httpx.Response(200)
        try:
            flow.send(success_response)
        except StopIteration:
            pass  # Expected end of generator

    def test_auth_flow_no_cached_token_refresh_success(
        self, bearer_auth: BearerAuth, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test auth flow when no cached token exists but refresh succeeds."""
        # No cached token
        token_manager._access_token = None
        token_manager._expires_at = 0

        # Mock successful refresh
        mock_response = {"access_token": "refreshed_token"}
        respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json=mock_response))

        request = httpx.Request("GET", "https://test.example.com")

        # Simulate the auth flow
        flow = bearer_auth.auth_flow(request)

        # First yield should include the Bearer header with refreshed token
        first_request = next(flow)
        assert first_request.headers["Bearer"] == "refreshed_token"

    def test_auth_flow_no_cached_token_refresh_fails(
        self, bearer_auth: BearerAuth, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test auth flow when no cached token exists and refresh fails."""
        # No cached token
        token_manager._access_token = None
        token_manager._expires_at = 0

        # Mock failed refresh
        respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(401, json={"detail": "Invalid refresh token"}))

        request = httpx.Request("GET", "https://test.example.com")

        # Simulate the auth flow
        flow = bearer_auth.auth_flow(request)

        # First yield should not include Bearer header
        first_request = next(flow)
        assert "Bearer" not in first_request.headers

    def test_auth_flow_token_expired_retry_success(
        self, bearer_auth: BearerAuth, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test auth flow when token is expired and retry succeeds."""
        # Set up expired token
        token_manager._access_token = "expired_token"
        token_manager._expires_at = time.monotonic() + 1800  # Still valid in cache

        # Mock successful forced refresh
        mock_response = {"access_token": "new_token_after_401"}
        respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json=mock_response))

        request = httpx.Request("GET", "https://test.example.com")

        # Simulate the auth flow
        flow = bearer_auth.auth_flow(request)

        # First yield with cached token
        first_request = next(flow)
        assert first_request.headers["Bearer"] == "expired_token"

        # Simulate 401 response
        unauthorized_response = httpx.Response(401)

        # Second yield should have new token
        retry_request = flow.send(unauthorized_response)
        assert retry_request.headers["Bearer"] == "new_token_after_401"

    def test_auth_flow_token_expired_retry_fails(
        self, bearer_auth: BearerAuth, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test auth flow when token is expired and retry also fails."""
        # Set up expired token
        token_manager._access_token = "expired_token"
        token_manager._expires_at = time.monotonic() + 1800

        # Mock failed forced refresh
        respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(401, json={"detail": "Invalid refresh token"}))

        request = httpx.Request("GET", "https://test.example.com")

        # Simulate the auth flow
        flow = bearer_auth.auth_flow(request)

        # First yield with cached token
        first_request = next(flow)
        assert first_request.headers["Bearer"] == "expired_token"

        # Simulate 401 response - should not retry since forced refresh fails
        unauthorized_response = httpx.Response(401)

        try:
            flow.send(unauthorized_response)
        except StopIteration:
            pass  # Expected end of generator when retry fails

    def test_auth_flow_expired_file_token_triggers_refresh(
        self, bearer_auth: BearerAuth, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test that an expired token in the file cache triggers an automatic refresh."""
        # Create an expired token file
        past_expiry = time.monotonic() - 300
        token_data = {"access_token": "expired_file_token", "expires_at": past_expiry}
        token_manager._cache_path.parent.mkdir(parents=True, exist_ok=True)
        token_manager._cache_path.write_text(json.dumps(token_data))

        # Manually re-run the loading logic that __init__ does
        token_manager._load_token_from_file()
        assert token_manager.get_access_token() is None

        # Mock successful refresh
        respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "new_token"}))

        request = httpx.Request("GET", "https://test.example.com")
        flow = bearer_auth.auth_flow(request)
        authenticated_request = next(flow)

        assert authenticated_request.headers["Bearer"] == "new_token"

    @pytest.mark.asyncio
    async def test_async_auth_flow_with_cached_token(
        self, bearer_auth: BearerAuth, token_manager: TokenManager
    ) -> None:
        """Test async auth flow when a valid cached token exists."""
        # Set up valid cached token
        token_manager._access_token = "async_cached_token"
        token_manager._expires_at = time.monotonic() + 1800

        request = httpx.Request("GET", "https://test.example.com")

        # Simulate the async auth flow
        flow = bearer_auth.async_auth_flow(request)

        # First yield should include the Bearer header
        first_request = await flow.__anext__()
        assert first_request.headers["Bearer"] == "async_cached_token"

        # Simulate successful response (no retry needed)
        success_response = httpx.Response(200)
        try:
            await flow.asend(success_response)
        except StopAsyncIteration:
            pass  # Expected end of async generator

    @pytest.mark.asyncio
    async def test_async_auth_flow_no_cached_token_refresh_success(
        self, bearer_auth: BearerAuth, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test async auth flow when no cached token exists but refresh succeeds."""
        # No cached token
        token_manager._access_token = None
        token_manager._expires_at = 0

        # Mock successful refresh
        mock_response = {"access_token": "async_refreshed_token"}
        respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json=mock_response))

        request = httpx.Request("GET", "https://test.example.com")

        # Simulate the async auth flow
        flow = bearer_auth.async_auth_flow(request)

        # First yield should include the Bearer header with refreshed token
        first_request = await flow.__anext__()
        assert first_request.headers["Bearer"] == "async_refreshed_token"

    @pytest.mark.asyncio
    async def test_async_auth_flow_expired_file_token_triggers_refresh(
        self, bearer_auth: BearerAuth, token_manager: TokenManager, respx_mock: respx.MockRouter
    ) -> None:
        """Test that an expired token in the file cache triggers an automatic async refresh."""
        # Create an expired token file
        past_expiry = time.monotonic() - 300
        token_data = {"access_token": "expired_file_token", "expires_at": past_expiry}
        token_manager._cache_path.parent.mkdir(parents=True, exist_ok=True)
        token_manager._cache_path.write_text(json.dumps(token_data))

        # Manually re-run the loading logic that __init__ does
        token_manager._load_token_from_file()
        assert await token_manager.async_get_access_token() is None

        # Mock successful refresh
        respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json={"access_token": "new_async_token"}))

        request = httpx.Request("GET", "https://test.example.com")
        flow = bearer_auth.async_auth_flow(request)
        authenticated_request = await flow.__anext__()

        assert authenticated_request.headers["Bearer"] == "new_async_token"


class TestTokenManagementIntegration:
    """Integration tests for token management scenarios."""

    def test_full_token_lifecycle_sync(self, token_manager: TokenManager, respx_mock: respx.MockRouter) -> None:
        """Test complete token lifecycle: refresh, cache, load, expire, refresh again."""
        # 1. Initial refresh
        mock_response_1 = {"access_token": "initial_token"}
        auth_route = respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json=mock_response_1))

        token1 = token_manager.refresh_access_token()
        assert token1 == "initial_token"
        assert token_manager._cache_path.exists()

        # 2. Get token from memory cache
        token2 = token_manager.get_access_token()
        assert token2 == "initial_token"

        # 3. Simulate new TokenManager instance (e.g., new CLI session)
        new_token_manager = TokenManager(
            refresh_token="test_refresh_token", client=token_manager._client, token_ttl_seconds=3600
        )
        new_token_manager._cache_path = token_manager._cache_path

        # 4. Should load from file cache
        token3 = new_token_manager.get_access_token()
        assert token3 == "initial_token"

        # 5. Simulate token expiration by manually setting expiry
        new_token_manager._expires_at = time.monotonic() - 1  # Expired

        # 6. Should return None for expired token
        token4 = new_token_manager.get_access_token()
        assert token4 is None

        # 7. Force refresh should get new token
        mock_response_2 = {"access_token": "refreshed_token"}
        auth_route.mock(return_value=httpx.Response(201, json=mock_response_2))

        token5 = new_token_manager.refresh_access_token()
        assert token5 == "refreshed_token"

    @pytest.mark.asyncio
    async def test_full_token_lifecycle_async(self, token_manager: TokenManager, respx_mock: respx.MockRouter) -> None:
        """Test complete async token lifecycle."""
        # 1. Initial refresh
        mock_response_1 = {"access_token": "async_initial_token"}
        auth_route = respx_mock.post("/api/v1/auth").mock(return_value=httpx.Response(201, json=mock_response_1))

        token1 = await token_manager.async_refresh_access_token()
        assert token1 == "async_initial_token"
        assert token_manager._cache_path.exists()

        # 2. Get token from memory cache
        token2 = await token_manager.async_get_access_token()
        assert token2 == "async_initial_token"

        # 3. Simulate token expiration
        token_manager._expires_at = time.monotonic() - 1  # Expired

        # 4. Should return None for expired token
        token3 = await token_manager.async_get_access_token()
        assert token3 is None

        # 5. Force refresh should get new token
        mock_response_2 = {"access_token": "async_refreshed_token"}
        auth_route.mock(return_value=httpx.Response(201, json=mock_response_2))

        token4 = await token_manager.async_refresh_access_token(force=True)
        assert token4 == "async_refreshed_token"

    def test_cli_scenario_token_exists_but_not_loaded(self, generated_client: GeneratedClient) -> None:
        """Test the exact CLI scenario: token exists in file but CLI doesn't see it."""
        # 1. Create a token file (simulating previous CLI run)
        cache_dir = Path.home() / ".cache" / "applifting_python_sdk"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "token.json"

        future_expiry = time.monotonic() + 1800  # 30 minutes from now
        token_data = {"access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.token", "expires_at": future_expiry}
        cache_file.write_text(json.dumps(token_data))

        # 2. Create new TokenManager (simulating new CLI session)
        token_manager = TokenManager(
            refresh_token="test_refresh_token", client=generated_client, token_ttl_seconds=3600
        )

        # 3. The TokenManager should load the token during initialization
        assert token_manager._access_token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.token"
        assert token_manager._expires_at == future_expiry

        # 4. get_access_token should return the loaded token
        token = token_manager.get_access_token()
        assert token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.token"

        # 5. BearerAuth should use this token
        bearer_auth = BearerAuth(token_manager)
        request = httpx.Request("GET", "https://test.example.com")

        flow = bearer_auth.auth_flow(request)
        first_request = next(flow)

        assert first_request.headers["Bearer"] == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.token"
