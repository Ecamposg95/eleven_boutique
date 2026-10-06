"""Consultas públicas del catálogo. Toda consulta se restringe al tenant resuelto en servidor y a
productos publicados con oferta web publicada."""

import base64
import binascii
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, Subquery, and_, exists, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session, aliased, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from eleven.catalog.models import (
    ChannelListing,
    Collection,
    CollectionProduct,
    MediaAsset,
    MediaStatus,
    Product,
    ProductMedia,
    PublicationStatus,
    Variant,
    VariantStatus,
)
from eleven.catalog.schemas import (
    Availability,
    CollectionOut,
    Facets,
    FacetValue,
    ImageOut,
    PriceRange,
    ProductCard,
    ProductDetail,
    ProductPage,
    SortKey,
    VariantOut,
)

WEB = "web"
CURRENCY = "MXN"


class InvalidCursorError(ValueError):
    pass


@dataclass
class ProductFilters:
    q: str | None = None
    category: list[str] = field(default_factory=list)
    size: list[str] = field(default_factory=list)
    color: list[str] = field(default_factory=list)
    collection: str | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None


def encode_cursor(offset: int, sort: str) -> str:
    raw = json.dumps({"o": offset, "s": sort}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str, sort: str) -> int:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        offset = int(data["o"])
    except (binascii.Error, ValueError, KeyError, TypeError) as exc:
        raise InvalidCursorError("Cursor inválido") from exc
    if data.get("s") != sort or offset < 0:
        raise InvalidCursorError("El cursor no corresponde a este orden")
    return offset


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _public_products(tenant_id: uuid.UUID) -> ColumnElement[bool]:
    web_listing = aliased(ChannelListing)
    return and_(
        Product.tenant_id == tenant_id,
        Product.status == PublicationStatus.published,
        exists().where(
            web_listing.tenant_id == tenant_id,
            web_listing.product_id == Product.id,
            web_listing.variant_id.is_(None),
            web_listing.channel == WEB,
            web_listing.status == PublicationStatus.published,
        ),
    )


def _price_subquery(tenant_id: uuid.UUID) -> Subquery:
    """Precio efectivo por producto: el de la variante si existe, si no el del producto.

    Devuelve mínimo y máximo entre variantes activas. NULL cuando no hay precio publicado.
    """
    product_listing = aliased(ChannelListing)
    variant_listing = aliased(ChannelListing)
    effective = func.coalesce(variant_listing.price, product_listing.price)
    return (
        select(
            Variant.product_id.label("product_id"),
            func.min(effective).label("price_min"),
            func.max(effective).label("price_max"),
        )
        .outerjoin(
            variant_listing,
            and_(
                variant_listing.tenant_id == tenant_id,
                variant_listing.variant_id == Variant.id,
                variant_listing.channel == WEB,
                variant_listing.status == PublicationStatus.published,
            ),
        )
        .outerjoin(
            product_listing,
            and_(
                product_listing.tenant_id == tenant_id,
                product_listing.product_id == Variant.product_id,
                product_listing.variant_id.is_(None),
                product_listing.channel == WEB,
                product_listing.status == PublicationStatus.published,
            ),
        )
        .where(Variant.tenant_id == tenant_id, Variant.status == VariantStatus.active)
        .group_by(Variant.product_id)
        .subquery("prices")
    )


def _variant_filter(tenant_id: uuid.UUID, column: str, values: list[str]) -> ColumnElement[bool]:
    return exists().where(
        Variant.tenant_id == tenant_id,
        Variant.product_id == Product.id,
        Variant.status == VariantStatus.active,
        getattr(Variant, column).in_(values),
    )


def _filtered(tenant_id: uuid.UUID, filters: ProductFilters, prices: Subquery) -> Select[Any]:
    stmt = (
        select(Product, prices.c.price_min, prices.c.price_max)
        .outerjoin(prices, prices.c.product_id == Product.id)
        .where(_public_products(tenant_id))
    )
    if filters.q:
        pattern = f"%{_escape_like(filters.q.strip())}%"
        stmt = stmt.where(
            Product.name.ilike(pattern, escape="\\") | Product.category.ilike(pattern, escape="\\")
        )
    if filters.category:
        stmt = stmt.where(Product.category.in_(filters.category))
    if filters.size:
        stmt = stmt.where(_variant_filter(tenant_id, "size", filters.size))
    if filters.color:
        stmt = stmt.where(_variant_filter(tenant_id, "color", filters.color))
    if filters.collection:
        stmt = stmt.where(
            exists().where(
                CollectionProduct.tenant_id == tenant_id,
                CollectionProduct.product_id == Product.id,
                CollectionProduct.collection_id == Collection.id,
                Collection.tenant_id == tenant_id,
                Collection.slug == filters.collection,
                Collection.status == PublicationStatus.published,
            )
        )
    if filters.price_min is not None:
        stmt = stmt.where(prices.c.price_min >= filters.price_min)
    if filters.price_max is not None:
        stmt = stmt.where(prices.c.price_min <= filters.price_max)
    return stmt


def _order(stmt: Select[Any], sort: SortKey, prices: Subquery) -> Select[Any]:
    match sort:
        case "name":
            return stmt.order_by(Product.name.asc(), Product.id)
        case "price_asc":
            return stmt.order_by(prices.c.price_min.asc().nulls_last(), Product.name, Product.id)
        case "price_desc":
            return stmt.order_by(prices.c.price_min.desc().nulls_last(), Product.name, Product.id)
        case _:
            return stmt.order_by(Product.published_at.desc().nulls_last(), Product.name, Product.id)


def _image(asset: MediaAsset, base_url: str) -> ImageOut:
    return ImageOut(
        url=f"{base_url}{asset.object_key}",
        alt=asset.alt_text,
        width=asset.width,
        height=asset.height,
    )


def _approved_media(product: Product) -> list[ProductMedia]:
    return [m for m in product.media if m.asset.status == MediaStatus.approved]


def _card(
    product: Product, price_min: Decimal | None, price_max: Decimal | None, media_base: str
) -> ProductCard:
    active = [v for v in product.variants if v.status == VariantStatus.active]
    media = _approved_media(product)
    cover = next((m for m in media if m.is_cover), media[0] if media else None)
    return ProductCard(
        slug=product.slug,
        name=product.name,
        category=product.category,
        cover=_image(cover.asset, media_base) if cover else None,
        price_from=price_min,
        price_varies=price_min is not None and price_max is not None and price_min != price_max,
        currency=CURRENCY,
        colors=_unique(v.color for v in active),
        sizes=_unique(v.size for v in active),
        is_demo=product.is_demo,
    )


def _unique(values: Iterable[str | None]) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        if value:
            seen.setdefault(value, None)
    return list(seen)


def _load_options() -> tuple[LoaderOption, ...]:
    return (
        selectinload(Product.variants),
        selectinload(Product.media).selectinload(ProductMedia.asset),
    )


def list_products(
    session: Session,
    tenant_id: uuid.UUID,
    filters: ProductFilters,
    sort: SortKey,
    limit: int,
    cursor: str | None,
    media_base: str,
) -> ProductPage:
    offset = decode_cursor(cursor, sort) if cursor else 0
    prices = _price_subquery(tenant_id)
    base = _filtered(tenant_id, filters, prices)

    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.execute(
        _order(base, sort, prices).options(*_load_options()).offset(offset).limit(limit)
    ).all()

    items = [_card(p, pmin, pmax, media_base) for p, pmin, pmax in rows]
    next_offset = offset + len(items)
    return ProductPage(
        items=items,
        total=total,
        next_cursor=encode_cursor(next_offset, sort) if next_offset < total else None,
    )


def get_product(
    session: Session, tenant_id: uuid.UUID, slug: str, media_base: str
) -> ProductDetail | None:
    prices = _price_subquery(tenant_id)
    row = session.execute(
        select(Product, prices.c.price_min, prices.c.price_max)
        .outerjoin(prices, prices.c.product_id == Product.id)
        .where(_public_products(tenant_id), Product.slug == slug)
        .options(*_load_options())
    ).first()
    if row is None:
        return None
    product, pmin, pmax = row

    listings = session.scalars(
        select(ChannelListing).where(
            ChannelListing.tenant_id == tenant_id,
            ChannelListing.product_id == product.id,
            ChannelListing.channel == WEB,
            ChannelListing.status == PublicationStatus.published,
        )
    ).all()
    product_price = next((cl.price for cl in listings if cl.variant_id is None), None)
    variant_prices = {cl.variant_id: cl.price for cl in listings if cl.variant_id is not None}

    collections = session.scalars(
        select(Collection.slug)
        .join(
            CollectionProduct,
            and_(
                CollectionProduct.collection_id == Collection.id,
                CollectionProduct.tenant_id == tenant_id,
            ),
        )
        .where(
            Collection.tenant_id == tenant_id,
            Collection.status == PublicationStatus.published,
            CollectionProduct.product_id == product.id,
        )
        .order_by(Collection.position)
    ).all()

    return ProductDetail(
        **dict(_card(product, pmin, pmax, media_base)),
        description=product.description,
        images=[_image(m.asset, media_base) for m in _approved_media(product)],
        variants=[
            VariantOut(
                id=v.id,
                sku=v.sku,
                size=v.size,
                color=v.color,
                price=(
                    variant_prices[v.id] if variant_prices.get(v.id) is not None else product_price
                ),
                currency=CURRENCY,
            )
            for v in product.variants
            if v.status == VariantStatus.active
        ],
        collections=list(collections),
    )


def facets(session: Session, tenant_id: uuid.UUID) -> Facets:
    public = _public_products(tenant_id)

    categories = session.execute(
        select(Product.category, func.count())
        .where(public)
        .group_by(Product.category)
        .order_by(Product.category)
    ).all()

    def variant_facet(column: InstrumentedAttribute[str | None]) -> list[tuple[str, int]]:
        rows = session.execute(
            select(column, func.count(func.distinct(Product.id)))
            .join(Product, and_(Product.id == Variant.product_id, Product.tenant_id == tenant_id))
            .where(
                public,
                Variant.tenant_id == tenant_id,
                Variant.status == VariantStatus.active,
                column.is_not(None),
            )
            .group_by(column)
            .order_by(column)
        ).all()
        return [(value, count) for value, count in rows if value is not None]

    prices = _price_subquery(tenant_id)
    price_row = session.execute(
        select(func.min(prices.c.price_min), func.max(prices.c.price_max))
        .select_from(Product)
        .join(prices, prices.c.product_id == Product.id)
        .where(public)
    ).one()

    return Facets(
        categories=[FacetValue(value=c, count=n) for c, n in categories],
        sizes=[FacetValue(value=s, count=n) for s, n in variant_facet(Variant.size)],
        colors=[FacetValue(value=c, count=n) for c, n in variant_facet(Variant.color)],
        price_range=(
            PriceRange(min=price_row[0], max=price_row[1])
            if price_row[0] is not None and price_row[1] is not None
            else None
        ),
    )


def list_collections(session: Session, tenant_id: uuid.UUID) -> list[CollectionOut]:
    rows = session.execute(
        select(Collection, func.count(Product.id))
        .outerjoin(
            CollectionProduct,
            and_(
                CollectionProduct.collection_id == Collection.id,
                CollectionProduct.tenant_id == tenant_id,
            ),
        )
        .outerjoin(
            Product,
            and_(Product.id == CollectionProduct.product_id, _public_products(tenant_id)),
        )
        .where(Collection.tenant_id == tenant_id, Collection.status == PublicationStatus.published)
        .group_by(Collection.id)
        .order_by(Collection.position, Collection.name)
    ).all()
    return [
        CollectionOut(
            slug=c.slug,
            name=c.name,
            description=c.description,
            product_count=n,
            is_demo=c.is_demo,
        )
        for c, n in rows
    ]


def variant_availability(
    session: Session, tenant_id: uuid.UUID, variant_id: uuid.UUID
) -> Availability | None:
    """Sin fuente de existencias autorizada (Atlas ONE, E5) la disponibilidad es `unknown`."""
    variant = session.scalar(
        select(Variant)
        .join(Product, and_(Product.id == Variant.product_id, Product.tenant_id == tenant_id))
        .where(
            Variant.tenant_id == tenant_id,
            Variant.id == variant_id,
            Variant.status == VariantStatus.active,
            _public_products(tenant_id),
        )
    )
    if variant is None:
        return None
    return Availability(
        variant_id=variant.id,
        state="unknown",
        available=None,
        source=None,
        checked_at=None,
        locations=[],
    )
