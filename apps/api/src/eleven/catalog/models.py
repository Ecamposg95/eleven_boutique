"""Modelo de catálogo.

Separaciones del task pack §6: Product (estilo) ≠ Variant (SKU vendible) ≠ MediaAsset (foto)
≠ ChannelListing (precio y publicación por canal). La existencia y el pedido viven en otros
módulos (E5/E6).

Aislamiento por tenant en la base de datos: cada tabla hija referencia a su padre con una FK
compuesta (tenant_id, id), de modo que no es posible relacionar filas de tenants distintos.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eleven.db import Base, TimestampMixin, new_id


class PublicationStatus(enum.StrEnum):
    draft = "draft"
    review = "review"
    published = "published"
    archived = "archived"


class VariantStatus(enum.StrEnum):
    active = "active"
    inactive = "inactive"


class MediaStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


def _enum(cls: type[enum.StrEnum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


def _tenant_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("tenant.id", ondelete="RESTRICT"), index=True)


class Product(TimestampMixin, Base):
    __tablename__ = "product"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "slug"),
        Index("ix_product_tenant_status_category", "tenant_id", "status", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[uuid.UUID] = _tenant_fk()
    slug: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PublicationStatus] = mapped_column(
        _enum(PublicationStatus, "publication_status"), default=PublicationStatus.draft
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    variants: Mapped[list["Variant"]] = relationship(
        back_populates="product", order_by="Variant.position", viewonly=True
    )
    media: Mapped[list["ProductMedia"]] = relationship(
        order_by="ProductMedia.position", viewonly=True
    )


class Variant(TimestampMixin, Base):
    """Combinación vendible (talla y color) con SKU.

    `size` NULL significa talla desconocida; una talla única confirmada se guarda como "UNI".
    """

    __tablename__ = "variant"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "sku"),
        ForeignKeyConstraint(
            ["tenant_id", "product_id"], ["product.tenant_id", "product.id"], ondelete="CASCADE"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[uuid.UUID] = _tenant_fk()
    product_id: Mapped[uuid.UUID] = mapped_column(index=True)
    sku: Mapped[str] = mapped_column(String(80))
    size: Mapped[str | None] = mapped_column(String(20))
    color: Mapped[str | None] = mapped_column(String(60))
    barcode: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[VariantStatus] = mapped_column(
        _enum(VariantStatus, "variant_status"), default=VariantStatus.active
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="variants", viewonly=True)


class ChannelListing(TimestampMixin, Base):
    """Oferta por canal. `price` NULL = «Consultar precio», nunca cero."""

    __tablename__ = "channel_listing"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "product_id"], ["product.tenant_id", "product.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "variant_id"], ["variant.tenant_id", "variant.id"], ondelete="CASCADE"
        ),
        CheckConstraint("price IS NULL OR price >= 0", name="price_non_negative"),
        Index(
            "uq_channel_listing_product_level",
            "tenant_id",
            "channel",
            "product_id",
            unique=True,
            postgresql_where=text("variant_id IS NULL"),
        ),
        Index(
            "uq_channel_listing_variant_level",
            "tenant_id",
            "channel",
            "variant_id",
            unique=True,
            postgresql_where=text("variant_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[uuid.UUID] = _tenant_fk()
    product_id: Mapped[uuid.UUID] = mapped_column(index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column()
    channel: Mapped[str] = mapped_column(String(32), default="web")
    status: Mapped[PublicationStatus] = mapped_column(
        _enum(PublicationStatus, "publication_status"), default=PublicationStatus.draft
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="MXN")
    version: Mapped[int] = mapped_column(Integer, default=1)


class MediaAsset(TimestampMixin, Base):
    """Fotografía u otro activo. En E1 solo referencia archivos demo estáticos."""

    __tablename__ = "media_asset"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "object_key"),
        Index("ix_media_asset_tenant_sha256", "tenant_id", "sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[uuid.UUID] = _tenant_fk()
    original_name: Mapped[str | None] = mapped_column(String(400))
    object_key: Mapped[str] = mapped_column(String(400))
    sha256: Mapped[str | None] = mapped_column(String(64))
    mime: Mapped[str | None] = mapped_column(String(80))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(40), default="upload")
    status: Mapped[MediaStatus] = mapped_column(
        _enum(MediaStatus, "media_status"), default=MediaStatus.pending
    )
    alt_text: Mapped[str | None] = mapped_column(String(300))


class ProductMedia(Base):
    __tablename__ = "product_media"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "product_id"], ["product.tenant_id", "product.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "asset_id"],
            ["media_asset.tenant_id", "media_asset.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "variant_id"],
            ["variant.tenant_id", "variant.id"],
            # Solo anula variant_id; tenant_id forma parte de la PK.
            ondelete="SET NULL (variant_id)",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column()
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)

    asset: Mapped[MediaAsset] = relationship(viewonly=True)


class Collection(TimestampMixin, Base):
    __tablename__ = "collection"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[uuid.UUID] = _tenant_fk()
    slug: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PublicationStatus] = mapped_column(
        _enum(PublicationStatus, "publication_status"), default=PublicationStatus.draft
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)


class CollectionProduct(Base):
    __tablename__ = "collection_product"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "collection_id"],
            ["collection.tenant_id", "collection.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "product_id"], ["product.tenant_id", "product.id"], ondelete="CASCADE"
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), primary_key=True
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    product_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
