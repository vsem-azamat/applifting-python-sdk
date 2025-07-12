"""User-friendly models for the Applifting SDK."""

from typing import List, Optional
from uuid import UUID, uuid4
from ._generated.python_exercise_client.models.offer_response import OfferResponse
from ._generated.python_exercise_client.models.register_product_request import RegisterProductRequest
from ._generated.python_exercise_client.models.register_product_response import RegisterProductResponse


class Product:
    """A product to register with the Applifting Offers API."""
    
    def __init__(self, name: str, description: str, id: Optional[UUID] = None):
        self.name = name
        self.description = description
        self.id = id or uuid4()
    
    def to_register_request(self) -> RegisterProductRequest:
        """Convert to the generated model for API calls."""
        return RegisterProductRequest(id=self.id, name=self.name, description=self.description)


class Offer:
    """An offer for a product."""
    
    def __init__(self, id: UUID, price: int, items_in_stock: int):
        self.id = id
        self.price = price
        self.items_in_stock = items_in_stock
    
    @classmethod
    def from_offer_response(cls, offer_response: OfferResponse) -> "Offer":
        """Create an Offer from the generated model."""
        return cls(
            id=offer_response.id,
            price=offer_response.price,
            items_in_stock=offer_response.items_in_stock
        )
