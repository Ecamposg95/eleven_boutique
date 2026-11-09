"""Public response shapes from docs/api-contract.md. Fields are an explicit allow-list."""

from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorBody(Schema):
    code: str
    message: str


class ErrorResponse(Schema):
    error: ErrorBody


class Health(Schema):
    status: Literal["ok"] = "ok"


class Items(Schema, Generic[T]):
    items: list[T]


class Page(Schema, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Media(Schema):
    url: str
    alt: str
    is_primary: bool
    position: int


class BrandSummary(Schema):
    slug: str
    name: str
    logo_url: str | None
    is_featured: bool
    aliases: list[str]
    product_count: int


class BrandDetail(BrandSummary):
    description: str | None
    editorial_image_url: str | None


class Category(Schema):
    slug: str
    name: str
    parent_slug: str | None


class CardBrand(Schema):
    slug: str | None
    name: str | None


class CardCategory(Schema):
    slug: str
    name: str


class ProductCard(Schema):
    slug: str
    name: str
    brand: CardBrand
    category: CardCategory
    primary_image: Media | None
    secondary_image: Media | None


class ProductDetail(ProductCard):
    gallery: list[Media]
    consult_url: str | None
    seo_title: str | None
    seo_description: str | None
    published_at: datetime | None


class CollectionSummary(Schema):
    slug: str
    title: str
    summary: str | None
    cover_url: str | None
    product_count: int


class CollectionDetail(CollectionSummary):
    products: list[ProductCard]


class LookbookSummary(Schema):
    slug: str
    title: str
    summary: str | None
    cover_url: str | None


class TextBlock(Schema):
    type: Literal["text"] = "text"
    position: int
    heading: str | None
    body: str


class ImageBlock(Schema):
    type: Literal["image"] = "image"
    position: int
    url: str
    alt: str
    layout: Literal["full", "left", "right"]


LookbookBlock = Annotated[TextBlock | ImageBlock, Field(discriminator="type")]


class LookbookDetail(LookbookSummary):
    blocks: list[LookbookBlock]
    products: list[ProductCard]


class SearchResults(Schema):
    brands: list[BrandSummary]
    products: list[ProductCard]


class Hero(Schema):
    image_url: str | None
    mobile_image_url: str | None
    headline: str | None
    subhead: str | None


class BodyText(Schema):
    body: str | None


class PublicSettings(Schema):
    demo_mode: bool
    whatsapp_enabled: bool
    site_name: str
    hero: Hero
    intro: str | None
    boutique: BodyText
    contact: BodyText


class EventIn(BaseModel):
    type: Literal["whatsapp_click"]
    product_slug: str
