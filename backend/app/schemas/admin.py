"""Admin shapes from docs/admin-api-contract.md. Inputs forbid unknown fields, so a price, cost,
stock or barcode sent by a client is a 422, not something silently dropped."""

import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.public import ImageBlock as PublicImageBlock
from app.schemas.public import Page as Page  # Re-exported for the admin services.
from app.schemas.public import Schema
from app.schemas.public import TextBlock as PublicTextBlock

Status = Literal["draft", "published", "archived"]
Role = Literal["superadmin", "admin", "editor"]
BulkAction = Literal["publish", "unpublish", "archive", "feature", "unfeature"]
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_LOCAL_OR_HTTPS_URL = re.compile(r"(/(?!/)|https://)\S*")
MAX_BULK = 500


def _check_slug(value: str) -> str:
    if not _SLUG.fullmatch(value):
        raise ValueError("debe contener solo minúsculas, números y guiones")
    return value


def _check_image_url(value: str) -> str:
    if not _LOCAL_OR_HTTPS_URL.fullmatch(value):
        raise ValueError("debe ser una ruta local o una URL https")
    return value


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


Slug = Annotated[str, StringConstraints(max_length=200), AfterValidator(_check_slug)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
BrandName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(max_length=300)]
LongText = Annotated[str, StringConstraints(max_length=20_000)]
UtcDatetime = Annotated[datetime, AfterValidator(_as_utc)]
ImageUrl = Annotated[str, StringConstraints(max_length=500), AfterValidator(_check_image_url)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # In a PATCH, these fields may be left out but cannot be set to null.
    not_nullable: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> Self:
        for field in self.not_nullable:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser null")
        return self


# --- Auth ------------------------------------------------------------------------------


class LoginIn(Input):
    email: Annotated[str, StringConstraints(min_length=1, max_length=254)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=1024)]


class Me(Schema):
    id: uuid.UUID
    email: str
    role: Role


# --- Dashboard and audit ---------------------------------------------------------------


class DashboardProducts(Schema):
    draft: int
    published: int
    archived: int
    without_photo: int


class DashboardBrands(Schema):
    draft: int
    published: int


class Dashboard(Schema):
    products: DashboardProducts
    brands: DashboardBrands
    consult_clicks_30d: int
    whatsapp_configured: bool


class AuditEntry(Schema):
    id: uuid.UUID
    user_id: uuid.UUID | None
    user_email: str | None
    operation: str
    entity: str
    entity_id: str | None
    changes: dict[str, Any]
    created_at: datetime


# --- Products --------------------------------------------------------------------------


class ProductPatch(Input):
    not_nullable = (
        "name",
        "slug",
        "brand_id",
        "category_id",
        "status",
        "is_featured",
        "display_order",
        "publish_brand",
        "hidden_on_web",
    )

    name: Name | None = None
    slug: Slug | None = None
    brand_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    status: Status | None = None
    is_featured: bool | None = None
    display_order: int | None = None
    commercial_added_at: UtcDatetime | None = None
    seo_title: ShortText | None = None
    seo_description: LongText | None = None
    internal_notes: LongText | None = None
    publish_brand: bool | None = None
    hidden_on_web: bool | None = None


class ProductBrandRef(Schema):
    id: uuid.UUID
    slug: str
    name: str
    kind: str
    status: str


class ProductCategoryRef(Schema):
    id: uuid.UUID
    slug: str
    name: str


class ProductMediaOut(Schema):
    id: uuid.UUID
    media_asset_id: uuid.UUID | None
    url: str
    alt: str
    is_primary: bool
    position: int
    # Foto que trae Atlas ONE en una pieza de Atlas: no se edita ni se borra desde el panel.
    read_only: bool = False


class VariantOut(Schema):
    id: uuid.UUID
    sku: str
    color: str | None
    size: str | None
    available: bool = True


class AdminProduct(Schema):
    id: uuid.UUID
    sku: str
    name: str
    slug: str
    brand_id: uuid.UUID
    category_id: uuid.UUID
    brand: ProductBrandRef
    category: ProductCategoryRef
    status: Status
    is_featured: bool
    is_demo: bool
    display_order: int
    published_at: datetime | None
    commercial_added_at: datetime | None
    seo_title: str | None
    seo_description: str | None
    internal_notes: str | None
    photo_refs: list[str]
    media: list[ProductMediaOut]
    variants: list[VariantOut]
    from_atlas: bool = False
    available: bool = True
    atlas_missing: str | None = None
    hidden_on_web: bool = False
    gender: str | None = None
    model: str | None = None
    material: str | None = None
    admin_description: str | None = None
    created_at: datetime
    updated_at: datetime


class ProductBulkIn(Input):
    ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=MAX_BULK)]
    action: BulkAction
    publish_brand: bool = False


class ItemError(Schema):
    code: str
    message: str


class ProductBulkResult(Schema):
    id: uuid.UUID
    ok: bool
    error: ItemError | None


class ProductBulkOut(Schema):
    results: list[ProductBulkResult]


class ProductMediaAdd(Input):
    media_asset_id: uuid.UUID
    alt: Annotated[str, StringConstraints(max_length=500)] | None = None


class ProductMediaOrder(Input):
    order: Annotated[list[uuid.UUID], Field(min_length=1, max_length=MAX_BULK)]
    primary_id: uuid.UUID | None = None


# --- Media -----------------------------------------------------------------------------


class AdminMedia(Schema):
    id: uuid.UUID
    url: str
    filename: str
    alt: str
    content_type: str
    width: int
    height: int
    size_bytes: int
    in_use: bool
    created_at: datetime


class UploadError(Schema):
    filename: str
    code: str
    message: str


class MediaUploadOut(Schema):
    items: list[AdminMedia]
    errors: list[UploadError]


class MediaPatch(Input):
    alt: Annotated[str, StringConstraints(max_length=500)]


class BulkMatchIn(Input):
    media_asset_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=MAX_BULK)]


class MatchCandidate(Schema):
    id: uuid.UUID
    sku: str
    name: str


class BulkMatchItem(Schema):
    media_asset_id: uuid.UUID
    filename: str
    product_id: uuid.UUID | None
    match: Literal["sku", "photo_ref", "none"]
    candidates: list[MatchCandidate]


class BulkMatchOut(Schema):
    items: list[BulkMatchItem]


class BulkAssignItem(Input):
    media_asset_id: uuid.UUID
    product_id: uuid.UUID


class BulkAssignIn(Input):
    items: Annotated[list[BulkAssignItem], Field(min_length=1, max_length=MAX_BULK)]


class BulkAssignResult(Schema):
    media_asset_id: uuid.UUID
    product_id: uuid.UUID
    ok: bool
    error: ItemError | None


class BulkAssignOut(Schema):
    results: list[BulkAssignResult]


# --- Brands and categories -------------------------------------------------------------


Alias = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class BrandCreate(Input):
    name: BrandName
    slug: Slug | None = None
    logo_asset_id: uuid.UUID | None = None
    editorial_asset_id: uuid.UUID | None = None
    description: LongText | None = None
    display_order: int = 0
    is_featured: bool = False
    is_premium: bool = False
    status: Status = "draft"
    validation_status: Literal["pending", "approved"] = "pending"
    aliases: Annotated[list[Alias], Field(max_length=100)] = []


class BrandPatch(Input):
    not_nullable = (
        "name",
        "slug",
        "display_order",
        "is_featured",
        "is_premium",
        "status",
        "validation_status",
        "aliases",
    )

    name: BrandName | None = None
    slug: Slug | None = None
    logo_asset_id: uuid.UUID | None = None
    editorial_asset_id: uuid.UUID | None = None
    description: LongText | None = None
    display_order: int | None = None
    is_featured: bool | None = None
    is_premium: bool | None = None
    status: Status | None = None
    validation_status: Literal["pending", "approved"] | None = None
    aliases: Annotated[list[Alias], Field(max_length=100)] | None = None


class AdminBrand(Schema):
    id: uuid.UUID
    name: str
    slug: str
    kind: str
    logo_asset_id: uuid.UUID | None
    logo_url: str | None
    editorial_asset_id: uuid.UUID | None
    editorial_image_url: str | None
    description: str | None
    display_order: int
    is_featured: bool
    is_premium: bool
    status: Status
    validation_status: str
    aliases: list[str]
    product_count: int


class CategoryCreate(Input):
    name: BrandName
    slug: Slug | None = None
    parent_id: uuid.UUID | None = None
    display_order: int = 0


class CategoryPatch(Input):
    not_nullable = ("name", "slug", "display_order")

    name: BrandName | None = None
    slug: Slug | None = None
    parent_id: uuid.UUID | None = None
    display_order: int | None = None


class AdminCategory(Schema):
    id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None
    display_order: int
    product_count: int


# --- Collections and lookbooks ---------------------------------------------------------

ProductIds = Annotated[list[uuid.UUID], Field(max_length=MAX_BULK)]


class CollectionCreate(Input):
    title: Name
    slug: Slug | None = None
    summary: LongText | None = None
    cover_asset_id: uuid.UUID | None = None
    status: Status = "draft"
    display_order: int = 0
    product_ids: ProductIds = []


class CollectionPatch(Input):
    not_nullable = ("title", "slug", "status", "display_order", "product_ids")

    title: Name | None = None
    slug: Slug | None = None
    summary: LongText | None = None
    cover_asset_id: uuid.UUID | None = None
    status: Status | None = None
    display_order: int | None = None
    product_ids: ProductIds | None = None


class AdminCollection(Schema):
    id: uuid.UUID
    title: str
    slug: str
    summary: str | None
    cover_asset_id: uuid.UUID | None
    cover_url: str | None
    status: Status
    is_demo: bool
    display_order: int
    product_ids: list[uuid.UUID]


class TextBlockIn(Input):
    type: Literal["text"]
    position: int | None = None
    heading: ShortText | None = None
    body: LongText


class ImageBlockIn(Input):
    type: Literal["image"]
    position: int | None = None
    url: ImageUrl
    alt: Annotated[str, StringConstraints(max_length=500)]
    layout: Literal["full", "left", "right"] = "full"


BlockIn = Annotated[TextBlockIn | ImageBlockIn, Field(discriminator="type")]
BlockOut = Annotated[PublicTextBlock | PublicImageBlock, Field(discriminator="type")]
Blocks = Annotated[list[BlockIn], Field(max_length=200)]


class LookbookCreate(CollectionCreate):
    blocks: Blocks = []


class LookbookPatch(CollectionPatch):
    not_nullable = ("title", "slug", "status", "display_order", "product_ids", "blocks")

    blocks: Blocks | None = None


class AdminLookbook(AdminCollection):
    blocks: list[BlockOut]


# --- Settings --------------------------------------------------------------------------


HERO_GALLERY_MAX = 8


class HeroSlide(Schema):
    asset_id: uuid.UUID
    url: str
    # Art direction: vertical version for portrait screens (phones). Optional.
    mobile_asset_id: uuid.UUID | None = None
    mobile_url: str | None = None


class HeroSlideIn(Input):
    asset_id: uuid.UUID
    mobile_asset_id: uuid.UUID | None = None


class SettingsPatch(Input):
    whatsapp_number: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    whatsapp_premium_number: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None
    ) = None
    hero_asset_id: uuid.UUID | None = None
    hero_mobile_asset_id: uuid.UUID | None = None
    hero_gallery_asset_ids: Annotated[list[uuid.UUID], Field(max_length=HERO_GALLERY_MAX)] | None = None
    # Replaces hero_gallery_asset_ids when sent: each slide may carry its phone version.
    hero_gallery_slides: Annotated[list[HeroSlideIn], Field(max_length=HERO_GALLERY_MAX)] | None = None
    hero_headline: LongText | None = None
    hero_subhead: LongText | None = None
    intro: LongText | None = None
    boutique_body: LongText | None = None
    contact_body: LongText | None = None


class AdminSettings(Schema):
    whatsapp_number: str | None
    whatsapp_premium_number: str | None
    hero_asset_id: uuid.UUID | None
    hero_image_url: str | None
    hero_mobile_asset_id: uuid.UUID | None
    hero_mobile_image_url: str | None
    hero_gallery: list[HeroSlide]
    hero_headline: str | None
    hero_subhead: str | None
    intro: str | None
    boutique_body: str | None
    contact_body: str | None


# --- Imports ---------------------------------------------------------------------------


# --- Atlas ONE -------------------------------------------------------------------------


class AtlasRun(Schema):
    kind: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    counts: dict[str, int]
    error: str | None
    # Aviso de una corrida buena (p. ej. la baja nocturna se omitió); no es una falla.
    note: str | None = None


class AtlasDraft(Schema):
    id: uuid.UUID
    name: str
    atlas_missing: str | None


class AtlasStatus(Schema):
    enabled: bool
    last_run: AtlasRun | None
    last_ok_at: datetime | None
    last_error: str | None = None
    drafts: list[AtlasDraft]


class AtlasSyncStarted(Schema):
    started: bool


class AtlasBrandMapOut(Schema):
    atlas_brand_id: str
    atlas_name: str
    brand_id: uuid.UUID | None


class AtlasBrandMapPatch(Input):
    atlas_brand_id: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    # Sin "desligar": el emparejador automático volvería a ligar la fila en la siguiente corrida.
    brand_id: uuid.UUID


class AtlasCategoryMapOut(Schema):
    atlas_department_id: str
    atlas_name: str
    category_id: uuid.UUID | None


class AtlasCategoryMapPatch(Input):
    atlas_department_id: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    category_id: uuid.UUID | None
