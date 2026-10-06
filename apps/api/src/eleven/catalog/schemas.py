import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ImageOut(BaseModel):
    url: str
    alt: str | None
    width: int | None
    height: int | None


class VariantOut(BaseModel):
    id: uuid.UUID
    sku: str
    size: str | None
    color: str | None
    # None = «Consultar precio». Se serializa como cadena decimal para no perder precisión.
    price: Decimal | None
    currency: str


class ProductCard(BaseModel):
    model_config = ConfigDict(json_schema_extra={"description": "Producto publicado (tarjeta)"})

    slug: str
    name: str
    category: str
    cover: ImageOut | None
    price_from: Decimal | None
    price_varies: bool
    currency: str
    colors: list[str]
    sizes: list[str]
    is_demo: bool


class ProductDetail(ProductCard):
    description: str | None
    images: list[ImageOut]
    variants: list[VariantOut]
    collections: list[str]


class ProductPage(BaseModel):
    items: list[ProductCard]
    total: int
    next_cursor: str | None


class FacetValue(BaseModel):
    value: str
    count: int


class PriceRange(BaseModel):
    min: Decimal
    max: Decimal


class Facets(BaseModel):
    categories: list[FacetValue]
    sizes: list[FacetValue]
    colors: list[FacetValue]
    price_range: PriceRange | None


class CollectionOut(BaseModel):
    slug: str
    name: str
    description: str | None
    product_count: int
    is_demo: bool


class Availability(BaseModel):
    """Disponibilidad vendible. Sin fuente autorizada el estado es `unknown`, nunca disponible."""

    variant_id: uuid.UUID
    state: Literal["known", "unknown", "stale"]
    available: bool | None
    source: str | None
    checked_at: str | None
    locations: list[str]


SortKey = Literal["new", "name", "price_asc", "price_desc"]
