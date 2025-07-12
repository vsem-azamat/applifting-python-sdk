from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="OfferResponse")


@_attrs_define
class OfferResponse:
    """
    Attributes:
        id (UUID):
        price (int):
        items_in_stock (int):
    """

    id: UUID
    price: int
    items_in_stock: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = str(self.id)

        price = self.price

        items_in_stock = self.items_in_stock

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "price": price,
                "items_in_stock": items_in_stock,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = UUID(d.pop("id"))

        price = d.pop("price")

        items_in_stock = d.pop("items_in_stock")

        offer_response = cls(
            id=id,
            price=price,
            items_in_stock=items_in_stock,
        )

        offer_response.additional_properties = d
        return offer_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
