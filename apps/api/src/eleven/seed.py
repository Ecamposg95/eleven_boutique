"""Carga idempotente de fixtures DEMO.

Solo opera sobre un tenant marcado como demo: nunca escribe en un tenant real. Reejecutarla
actualiza los registros existentes (por slug y SKU) sin duplicarlos; los productos demo que ya
no están en el archivo pasan a `archived`.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

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
from eleven.tenancy import Tenant

WEB = "web"


class SeedError(RuntimeError):
    pass


@dataclass
class SeedReport:
    products: int = 0
    variants: int = 0
    collections: int = 0
    archived: int = 0


def _price(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _upsert_tenant(session: Session, data: dict[str, Any]) -> Tenant:
    if not data.get("is_demo"):
        raise SeedError("El fixture debe declarar un tenant demo (is_demo: true)")
    tenant = session.scalar(select(Tenant).where(Tenant.slug == data["slug"]))
    if tenant is None:
        tenant = Tenant(slug=data["slug"], name=data["name"], is_demo=True)
        session.add(tenant)
    elif not tenant.is_demo:
        raise SeedError(f"El tenant '{tenant.slug}' no es demo; no se cargan fixtures en él")
    tenant.name = data["name"]
    tenant.settings = data.get("settings", {})
    session.flush()
    return tenant


def _upsert_listing(
    session: Session,
    tenant: Tenant,
    product: Product,
    variant: Variant | None,
    price: Decimal | None,
    status: PublicationStatus,
) -> None:
    stmt = select(ChannelListing).where(
        ChannelListing.tenant_id == tenant.id,
        ChannelListing.product_id == product.id,
        ChannelListing.channel == WEB,
    )
    stmt = stmt.where(
        ChannelListing.variant_id == variant.id if variant else ChannelListing.variant_id.is_(None)
    )
    listing = session.scalar(stmt)
    if listing is None:
        listing = ChannelListing(
            tenant_id=tenant.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            channel=WEB,
        )
        session.add(listing)
    elif listing.price != price or listing.status != status:
        listing.version += 1
    listing.price = price
    listing.status = status
    listing.currency = "MXN"


def _sync_images(
    session: Session, tenant: Tenant, product: Product, images: list[dict[str, Any]]
) -> None:
    session.execute(
        delete(ProductMedia).where(
            ProductMedia.tenant_id == tenant.id, ProductMedia.product_id == product.id
        )
    )
    for position, image in enumerate(images):
        asset = session.scalar(
            select(MediaAsset).where(
                MediaAsset.tenant_id == tenant.id, MediaAsset.object_key == image["key"]
            )
        )
        if asset is None:
            asset = MediaAsset(tenant_id=tenant.id, object_key=image["key"], source="demo")
            session.add(asset)
        asset.original_name = image.get("original_name")
        asset.alt_text = image.get("alt")
        asset.width = image.get("width")
        asset.height = image.get("height")
        asset.status = MediaStatus.approved
        session.flush()
        session.add(
            ProductMedia(
                tenant_id=tenant.id,
                product_id=product.id,
                asset_id=asset.id,
                position=position,
                is_cover=position == 0,
            )
        )


def load_demo_catalog(session: Session, path: Path) -> SeedReport:
    data = json.loads(path.read_text(encoding="utf-8"))
    report = SeedReport()
    tenant = _upsert_tenant(session, data["tenant"])

    collections: dict[str, Collection] = {}
    for item in data.get("collections", []):
        collection = session.scalar(
            select(Collection).where(
                Collection.tenant_id == tenant.id, Collection.slug == item["slug"]
            )
        )
        if collection is None:
            collection = Collection(tenant_id=tenant.id, slug=item["slug"])
            session.add(collection)
        collection.name = item["name"]
        collection.description = item.get("description")
        collection.position = item.get("position", 0)
        collection.status = PublicationStatus.published
        collection.is_demo = True
        collections[item["slug"]] = collection
        report.collections += 1
    session.flush()

    seen_slugs: set[str] = set()
    for item in data["products"]:
        seen_slugs.add(item["slug"])
        product = session.scalar(
            select(Product).where(Product.tenant_id == tenant.id, Product.slug == item["slug"])
        )
        if product is None:
            product = Product(tenant_id=tenant.id, slug=item["slug"])
            session.add(product)
        status = PublicationStatus(item["status"])
        product.name = item["name"]
        product.category = item["category"]
        product.description = item.get("description")
        product.status = status
        product.is_demo = True
        product.published_at = (
            datetime.fromisoformat(item["published_at"]) if item.get("published_at") else None
        )
        session.flush()
        report.products += 1

        _upsert_listing(session, tenant, product, None, _price(item.get("price")), status)

        for position, v in enumerate(item["variants"]):
            variant = session.scalar(
                select(Variant).where(Variant.tenant_id == tenant.id, Variant.sku == v["sku"])
            )
            if variant is None:
                variant = Variant(tenant_id=tenant.id, sku=v["sku"], product_id=product.id)
                session.add(variant)
            elif variant.product_id != product.id:
                raise SeedError(f"SKU {v['sku']} ya pertenece a otro producto")
            variant.size = v.get("size")
            variant.color = v.get("color")
            variant.status = VariantStatus.active
            variant.position = position
            session.flush()
            report.variants += 1
            if "price" in v:
                _upsert_listing(session, tenant, product, variant, _price(v["price"]), status)

        session.execute(
            delete(CollectionProduct).where(
                CollectionProduct.tenant_id == tenant.id,
                CollectionProduct.product_id == product.id,
            )
        )
        for position, slug in enumerate(item.get("collections", [])):
            if slug not in collections:
                raise SeedError(f"Colección desconocida '{slug}' en {item['slug']}")
            session.add(
                CollectionProduct(
                    tenant_id=tenant.id,
                    collection_id=collections[slug].id,
                    product_id=product.id,
                    position=position,
                )
            )

        _sync_images(session, tenant, product, item.get("images", []))

    stale = session.scalars(
        select(Product).where(
            Product.tenant_id == tenant.id,
            Product.is_demo.is_(True),
            Product.slug.not_in(seen_slugs),
            Product.status != PublicationStatus.archived,
        )
    ).all()
    for product in stale:
        product.status = PublicationStatus.archived
        report.archived += 1

    session.flush()
    return report
