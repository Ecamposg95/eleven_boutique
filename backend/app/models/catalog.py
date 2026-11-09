import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db import UTCDateTime
from app.models.base import (
    Base,
    IdMixin,
    TimestampMixin,
    in_values,
    status_check,
    status_column,
)
from app.services.text import build_search_text

KIND_BRAND = "brand"
KIND_CLASSIFICATION = "classification"
VALIDATION_PENDING = "pending"
VALIDATION_APPROVED = "approved"


class Brand(IdMixin, TimestampMixin, Base):
    __tablename__ = "brands"
    __table_args__ = (
        status_check(),
        CheckConstraint(in_values("kind", (KIND_BRAND, KIND_CLASSIFICATION)), name="kind"),
        CheckConstraint(
            in_values("validation_status", (VALIDATION_PENDING, VALIDATION_APPROVED)),
            name="validation_status",
        ),
    )

    name: Mapped[str] = mapped_column(String(200))
    original_name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(16), default=KIND_BRAND, server_default=KIND_BRAND)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    editorial_image_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    status: Mapped[str] = status_column()
    validation_status: Mapped[str] = mapped_column(
        String(16), default=VALIDATION_PENDING, server_default=VALIDATION_PENDING
    )
    search_text: Mapped[str] = mapped_column(String(500), index=True)
    # When set, logo_url / editorial_image_url hold the asset's URL, so public reads stay unchanged.
    logo_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True
    )
    editorial_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True
    )

    aliases: Mapped[list["BrandAlias"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )

    @validates("name")
    def _sync_search_text(self, _key: str, value: str) -> str:
        self.search_text = build_search_text(value)
        return value


class BrandAlias(IdMixin, TimestampMixin, Base):
    __tablename__ = "brand_aliases"

    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    search_text: Mapped[str] = mapped_column(String(500), index=True)
    # Position in the source list; null for aliases that did not come from the import.
    source_position: Mapped[int | None] = mapped_column(Integer, unique=True)
    # True when the alias is a verbatim name from the source list.
    is_original: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    brand: Mapped[Brand] = relationship(back_populates="aliases")

    @validates("alias")
    def _sync_search_text(self, _key: str, value: str) -> str:
        self.search_text = build_search_text(value)
        return value


class Category(IdMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    search_text: Mapped[str] = mapped_column(String(500), index=True)

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id")

    @validates("name")
    def _sync_search_text(self, _key: str, value: str) -> str:
        self.search_text = build_search_text(value)
        return value


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (status_check(),)

    sku: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = status_column()
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    # When the piece entered the commercial offer; unrelated to created_at (load date).
    commercial_added_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), index=True
    )
    search_text: Mapped[str] = mapped_column(String(800), index=True)

    # Internal: never add these to a public schema, except the seo_* pair the contract exposes.
    admin_description: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    external_inventory_id: Mapped[str | None] = mapped_column(String(200))
    supplier_ref: Mapped[str | None] = mapped_column(String(200))
    seo_title: Mapped[str | None] = mapped_column(String(300))
    seo_description: Mapped[str | None] = mapped_column(Text)
    # Atomic references such as "Foto 12" or "Foto mujer 5", used to match uploaded photos.
    photo_refs: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")

    brand: Mapped[Brand] = relationship()
    category: Mapped[Category] = relationship()
    media: Mapped[list["ProductMedia"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductMedia.position",
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVariant.sku",
    )

    @validates("name")
    def _sync_search_text(self, _key: str, value: str) -> str:
        self.search_text = build_search_text(value)
        return value


class ProductMedia(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_media"
    __table_args__ = (
        UniqueConstraint("product_id", "position"),
        Index("uq_product_media_product_asset", "product_id", "media_asset_id", unique=True),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    alt: Mapped[str] = mapped_column(String(500))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Null for demo rows, which only have a URL. When set, url holds the asset's URL.
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True
    )

    product: Mapped[Product] = relationship(back_populates="media")


class ProductVariant(IdMixin, TimestampMixin, Base):
    """One catalog row. Holds no price, stock or barcode, by design."""

    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str | None] = mapped_column(String(100))
    size: Mapped[str | None] = mapped_column(String(50))

    product: Mapped[Product] = relationship(back_populates="variants")


class MediaAsset(IdMixin, TimestampMixin, Base):
    __tablename__ = "media_assets"

    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    url: Mapped[str] = mapped_column(String(500), unique=True)
    # Sanitized original name: data only, never used to build a path.
    filename: Mapped[str] = mapped_column(String(255), index=True)
    alt: Mapped[str] = mapped_column(String(500), default="", server_default="")
    content_type: Mapped[str] = mapped_column(String(32))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), index=True
    )
