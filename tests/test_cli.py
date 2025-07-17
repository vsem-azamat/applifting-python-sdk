"""Test suite for the CLI."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from applifting_python_sdk.cli import app
from applifting_python_sdk.exceptions import APIError, ProductNotFound
from applifting_python_sdk.models import Offer

runner = CliRunner()


@patch("applifting_python_sdk.cli._build_client")
def test_register_product_success(mock_build_client: MagicMock) -> None:
    """The 'register-product' command should succeed and print the new ID."""
    product_id = uuid4()
    mock_client = MagicMock()
    mock_client.register_product.return_value = product_id
    mock_build_client.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "register-product",
            "--name",
            "Test Product",
            "--description",
            "A product from a test.",
            "--refresh-token",
            "fake-token",
        ],
    )

    assert result.exit_code == 0
    assert "Success!" in result.stdout
    assert str(product_id) in result.stdout
    mock_client.register_product.assert_called_once()


@patch("applifting_python_sdk.cli._build_client")
def test_register_product_api_error(mock_build_client: MagicMock) -> None:
    """The 'register-product' command should fail gracefully on API error."""
    mock_client = MagicMock()
    mock_client.register_product.side_effect = APIError(500, "Internal Server Error")
    mock_build_client.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "register-product",
            "--name",
            "Test Product",
            "--description",
            "A product from a test.",
            "--refresh-token",
            "fake-token",
        ],
    )

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "Could not register product" in result.stdout


def test_register_product_missing_option() -> None:
    """The 'register-product' command should fail if required options are missing."""
    result = runner.invoke(app, ["register-product", "--name", "Test Product", "--refresh-token", "fake-token"])
    assert result.exit_code != 0
    assert "Missing option" in result.output
    assert "--description" in result.output


@patch("applifting_python_sdk.cli._build_client")
def test_get_offers_success(mock_build_client: MagicMock) -> None:
    """The 'get-offers' command should display a table of offers."""
    product_id = uuid4()
    mock_client = MagicMock()
    mock_client.get_offers.return_value = [
        Offer(id=uuid4(), price=100, items_in_stock=10),
        Offer(id=uuid4(), price=200, items_in_stock=5),
    ]
    mock_build_client.return_value = mock_client

    result = runner.invoke(app, ["get-offers", str(product_id), "--refresh-token", "fake-token"])

    assert result.exit_code == 0
    assert "Offer ID" in result.stdout
    assert "Price" in result.stdout
    assert "Items in Stock" in result.stdout
    assert "100" in result.stdout
    assert "200" in result.stdout
    mock_client.get_offers.assert_called_once_with(product_id)


@patch("applifting_python_sdk.cli._build_client")
def test_get_offers_no_offers_found(mock_build_client: MagicMock) -> None:
    """The 'get-offers' command should show a message when no offers are found."""
    product_id = uuid4()
    mock_client = MagicMock()
    mock_client.get_offers.return_value = []
    mock_build_client.return_value = mock_client

    result = runner.invoke(app, ["get-offers", str(product_id), "--refresh-token", "fake-token"])

    assert result.exit_code == 0
    assert "No offers found" in result.stdout


@patch("applifting_python_sdk.cli._build_client")
def test_get_offers_product_not_found(mock_build_client: MagicMock) -> None:
    """The 'get-offers' command should fail gracefully when the product is not found."""
    product_id = uuid4()
    mock_client = MagicMock()
    mock_client.get_offers.side_effect = ProductNotFound(404)
    mock_build_client.return_value = mock_client

    result = runner.invoke(app, ["get-offers", str(product_id), "--refresh-token", "fake-token"])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert f"Product with ID {product_id} not found" in result.stdout


def test_command_fails_without_token() -> None:
    """Commands should fail if no token is provided via option or env var."""
    result = runner.invoke(app, ["get-offers", str(uuid4())], env={"APPLIFTING_REFRESH_TOKEN": ""})
    assert result.exit_code == 1
    assert "A refresh token must be supplied" in result.stdout


def test_command_uses_env_var_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Commands should use the token from the environment variable if available."""
    monkeypatch.setenv("APPLIFTING_REFRESH_TOKEN", "token-from-env")
    with patch("applifting_python_sdk.cli._build_client") as mock_build_client:
        mock_client = MagicMock()
        mock_client.get_offers.return_value = []
        mock_build_client.return_value = mock_client

        result = runner.invoke(app, ["get-offers", str(uuid4())])

        assert result.exit_code == 0
        assert "A refresh token must be supplied" not in result.stdout
        mock_build_client.assert_called_once_with("token-from-env")
