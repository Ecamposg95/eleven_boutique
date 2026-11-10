import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Integer, String, Text, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import UTCDateTime
from app.models.base import (
    Base,
    IdMixin,
    TimestampMixin,
    in_values,
    status_check,
    status_column,
    utcnow,
)
from app.models.catalog import Product

BLOCK_TEXT = "text"
BLOCK_IMAGE = "image"


class Collection(IdMixin, TimestampMixin, Base):
    __tablename__ = "collections"
    __table_args__ = (status_check(),)

    slug: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = status_column()
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class CollectionProduct(Base):
    __tablename__ = "collection_products"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Lookbook(IdMixin, TimestampMixin, Base):
    __tablename__ = "lookbooks"
    __table_args__ = (status_check(),)

    slug: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = status_column()
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    blocks: Mapped[list["LookbookBlock"]] = relationship(
        cascade="all, delete-orphan", order_by="LookbookBlock.position"
    )


class LookbookBlock(IdMixin, TimestampMixin, Base):
    __tablename__ = "lookbook_blocks"
    __table_args__ = (
        CheckConstraint(in_values("type", (BLOCK_TEXT, BLOCK_IMAGE)), name="type"),
    )

    lookbook_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lookbooks.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # text: {heading, body}; image: {url, alt, layout}.
    content: Mapped[dict[str, Any]] = mapped_column(JSON)


class LookbookProduct(Base):
    __tablename__ = "lookbook_products"

    lookbook_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lookbooks.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class SiteSettings(IdMixin, TimestampMixin, Base):
    """At most two rows: the real one and the demo one, used only with DEMO_MODE=true."""

    __tablename__ = "site_settings"

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), unique=True)
    site_name: Mapped[str | None] = mapped_column(String(200))
    whatsapp_number: Mapped[str | None] = mapped_column(String(40))
    # Boutique line for premium brands; empty falls back to whatsapp_number.
    whatsapp_premium_number: Mapped[str | None] = mapped_column(String(40))
    hero_image_url: Mapped[str | None] = mapped_column(String(500))
    hero_mobile_image_url: Mapped[str | None] = mapped_column(String(500))
    hero_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True
    )
    hero_mobile_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True
    )
    # Extra portada photos that rotate after the main one: [{"asset_id": str, "url": str}].
    # JSON keeps the order; media usage reads it like lookbook image blocks.
    hero_gallery: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list, server_default="[]"
    )
    hero_headline: Mapped[str | None] = mapped_column(Text)
    hero_subhead: Mapped[str | None] = mapped_column(Text)
    intro: Mapped[str | None] = mapped_column(Text)
    boutique_body: Mapped[str | None] = mapped_column(Text)
    contact_body: Mapped[str | None] = mapped_column(Text)


class CatalogEvent(Base):
    """Anonymous counter: no IP, phone or user agent, by design."""

    __tablename__ = "catalog_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(64), index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    product: Mapped[Product | None] = relationship()
