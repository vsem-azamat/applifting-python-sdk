"""Command‑line interface (CLI) for the Applifting Python SDK.

The CLI purposefully remains a *thin* wrapper – it only parses CLI arguments,
creates an :class:`~applifting_python_sdk.OffersClient`, and presents the
results in a human‑friendly way. All heavy lifting is still delegated to the
SDK itself, guaranteeing identical behaviour between in‑process and CLI usage.
"""

from __future__ import annotations

import os
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from . import OffersClient, Product
from .exceptions import AppliftingSDKError, ProductNotFound, TokenRefreshDeniedError

# ---------------------------------------------------------------------------- #
# Typer application                                                            #
# ---------------------------------------------------------------------------- #

app = typer.Typer(
    name="applifting-sdk",
    help="Interact with the Applifting Offers API from your terminal.",
    add_completion=False,
)

console = Console()

# ---------------------------------------------------------------------------- #
# Helpers                                                                      #
# ---------------------------------------------------------------------------- #


def _build_client(refresh_token: str) -> OffersClient:
    """Return a configured :class:`OffersClient` instance."""
    return OffersClient(refresh_token=refresh_token)


# ---------------------------------------------------------------------------- #
# Global options / root command                                                #
# ---------------------------------------------------------------------------- #


def _get_refresh_token(token_option: str | None) -> str:
    """Get refresh token from option or environment variable."""
    refresh_token = token_option or os.getenv("APPLIFTING_REFRESH_TOKEN")
    if not refresh_token:
        console.print(
            "[bold red]Error:[/bold red] A refresh token must be supplied via "
            "`--refresh-token` (preferred) or the APPLIFTING_REFRESH_TOKEN "
            "environment variable."
        )
        raise typer.Exit(code=1)
    return refresh_token


# Define the refresh token option as a module-level constant to avoid B008
REFRESH_TOKEN_OPTION = typer.Option(
    None,
    "--refresh-token",
    "-t",
    envvar="APPLIFTING_REFRESH_TOKEN",
    help=(
        "Refresh token used to authenticate with the API. "
        "If omitted, the value of the APPLIFTING_REFRESH_TOKEN environment "
        "variable is used."
    ),
)

PRODUCT_ID_ARGUMENT = typer.Argument(..., help="The UUID of the product whose offers you want to retrieve.")


# ---------------------------------------------------------------------------- #
# Commands                                                                     #
# ---------------------------------------------------------------------------- #


@app.command("register-product")
def register_product(
    name: str = typer.Option(..., "--name", "-n", help="The name of the product."),
    description: str = typer.Option(..., "--description", "-d", help="The product description."),
    refresh_token: str = REFRESH_TOKEN_OPTION,
) -> None:
    """Register a new product with the Offers API."""
    token = _get_refresh_token(refresh_token)
    client = _build_client(token)
    product = Product(name=name, description=description)

    console.print(f"Attempting to register product '[cyan]{product.name}[/cyan]'…")
    try:
        with client:
            registered_id = client.register_product(product)
        console.print(
            f"[bold green]Success![/bold green] Product registered with ID: [magenta]{registered_id}[/magenta]"
        )
    except AppliftingSDKError as exc:
        if isinstance(exc, TokenRefreshDeniedError):
            console.print(
                "[bold yellow]Warning:[/bold yellow] The API denied a token refresh request. "
                "This can happen if a command was run very recently. "
                "Please wait a moment and try again."
            )
        else:
            console.print(f"[bold red]Error:[/bold red] Could not register product. {exc}")
        raise typer.Exit(code=1) from None


@app.command("get-offers")
def get_offers(
    product_id: UUID = PRODUCT_ID_ARGUMENT,
    refresh_token: str = REFRESH_TOKEN_OPTION,
) -> None:
    """Retrieve all offers for a specific product."""
    token = _get_refresh_token(refresh_token)
    client = _build_client(token)

    console.print(f"Fetching offers for product ID: [magenta]{product_id}[/magenta]…")
    try:
        with client:
            offers = client.get_offers(product_id)

        if not offers:
            console.print("[yellow]No offers found for this product.[/yellow]")
            return

        table = Table("Offer ID", "Price", "Items in Stock")
        for offer in offers:
            table.add_row(str(offer.id), f"{offer.price}", f"{offer.items_in_stock}")
        console.print(table)

    except ProductNotFound:
        console.print(f"[bold red]Error:[/bold red] Product with ID [magenta]{product_id}[/magenta] not found.")
        raise typer.Exit(code=1) from None
    except AppliftingSDKError as exc:
        if isinstance(exc, TokenRefreshDeniedError):
            console.print(
                "[bold yellow]Warning:[/bold yellow] The API denied a token refresh request. "
                "This can happen if a command was run very recently. "
                "Please wait a moment and try again."
            )
        else:
            console.print(f"[bold red]Error:[/bold red] Could not retrieve offers. {exc}")
        raise typer.Exit(code=1) from None


# ---------------------------------------------------------------------------- #
# Entrypoint                                                                   #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    app()
