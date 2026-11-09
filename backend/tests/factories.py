from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import (
    KIND_BRAND,
    STATUS_PUBLISHED,
    Brand,
    BrandAlias,
    Category,
    Product,
    ProductMedia,
)
from app.services.text import slugify


def make_brand(db: Session, name: str = "Marca Prueba", **fields) -> Brand:
    values = {
        "name": name,
        "original_name": name,
        "slug": slugify(name),
        "kind": KIND_BRAND,
        "status": STATUS_PUBLISHED,
    }
    brand = Brand(**{**values, **fields})
    db.add(brand)
    db.flush()
    return brand


def make_alias(db: Session, brand: Brand, alias: str, **fields) -> BrandAlias:
    row = BrandAlias(brand_id=brand.id, alias=alias, slug=slugify(alias), **fields)
    db.add(row)
    db.flush()
    return row


def make_category(db: Session, name: str = "Categoría Prueba", parent: Category | None = None):
    category = Category(name=name, slug=slugify(name), parent_id=parent.id if parent else None)
    db.add(category)
    db.flush()
    return category


def make_product(
    db: Session, brand: Brand, category: Category, name: str = "Pieza Prueba", **fields
) -> Product:
    slug = fields.pop("slug", slugify(name))
    values = {
        "sku": f"SKU-{slug}".upper(),
        "slug": slug,
        "name": name,
        "brand_id": brand.id,
        "category_id": category.id,
        "status": STATUS_PUBLISHED,
    }
    product = Product(**{**values, **fields})
    db.add(product)
    db.flush()
    db.add_all(
        [
            ProductMedia(
                product_id=product.id,
                url=f"/media/{slug}-a.jpg",
                alt=f"{name} frente",
                is_primary=True,
                position=0,
            ),
            ProductMedia(
                product_id=product.id,
                url=f"/media/{slug}-b.jpg",
                alt=f"{name} detalle",
                is_primary=False,
                position=1,
            ),
        ]
    )
    db.flush()
    return product


def at(year: int, month: int = 1, day: int = 1) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)

