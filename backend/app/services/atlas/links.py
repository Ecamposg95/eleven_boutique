"""Ligas entre marcas/departamentos de Atlas ONE y las casas/categorías de Eleven."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    KIND_BRAND,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    VALIDATION_PENDING,
    AtlasBrandMap,
    AtlasCategoryMap,
    Brand,
    BrandAlias,
    Category,
)
from app.services.admin.common import unique_slug
from app.services.brand_match import brand_index, no_brand_classification
from app.services.text import normalize


def sync_brands(db: Session, atlas_brands: list[dict]) -> dict[str, int]:
    """Liga marcas de Atlas a casas por nombre/alias; sin coincidencia crea una casa en borrador.

    Nunca modifica una casa existente. Un mapa ya ligado gana sobre el nombre.
    """
    index, brands = brand_index(db)
    taken = set(db.scalars(select(Brand.slug))) | set(
        db.scalars(select(BrandAlias.slug))
    )
    maps = {row.atlas_brand_id: row for row in db.scalars(select(AtlasBrandMap))}
    counts = {"ligadas": 0, "creadas_borrador": 0}
    for item in atlas_brands:
        if item.get("deleted"):
            continue
        row = maps.get(item["id"])
        if row is None:
            row = AtlasBrandMap(atlas_brand_id=item["id"], atlas_name=item["name"])
            db.add(row)
            maps[item["id"]] = row
        else:
            row.atlas_name = item["name"]
            if row.brand_id is not None:
                continue
        owners = index.get(normalize(item["name"]), set())
        if len(owners) == 1:
            row.brand_id = next(iter(owners))
            counts["ligadas"] += 1
        elif not owners:
            brand = Brand(
                name=item["name"],
                original_name=item["name"],
                slug=unique_slug(item["name"], taken, fallback="marca"),
                kind=KIND_BRAND,
                status=STATUS_DRAFT,
                validation_status=VALIDATION_PENDING,
            )
            db.add(brand)
            db.flush()
            row.brand_id = brand.id
            index.setdefault(normalize(brand.name), set()).add(brand.id)
            counts["creadas_borrador"] += 1
    db.flush()
    return counts


def sync_departments(db: Session, atlas_departments: list[dict]) -> dict[str, int]:
    """Registra departamentos de Atlas. La liga a una categoría la hace una persona."""
    maps = {
        row.atlas_department_id: row for row in db.scalars(select(AtlasCategoryMap))
    }
    counts = {"nuevas": 0, "actualizadas": 0, "desligadas": 0}
    for item in atlas_departments:
        row = maps.get(item["id"])
        if row is None:
            row = AtlasCategoryMap(
                atlas_department_id=item["id"], atlas_name=item["name"]
            )
            db.add(row)
            maps[item["id"]] = row
            counts["nuevas"] += 1
        else:
            counts["actualizadas"] += 1
        row.atlas_name = item["name"]
        row.atlas_parent_id = item.get("parent_id")
        if item.get("deleted") and row.category_id is not None:
            row.category_id = None
            counts["desligadas"] += 1
    db.flush()
    return counts


def resolve_brand(
    db: Session, atlas_brand_id: str | None
) -> tuple[Brand | None, str | None]:
    """Casa para un producto de Atlas, o el motivo por el que no se puede usar."""
    index, brands = brand_index(db)
    if atlas_brand_id is None:
        brand = no_brand_classification(brands)
        return (
            (brand, None) if brand else (None, "No existe la clasificación Sin marca")
        )
    row = db.scalar(
        select(AtlasBrandMap).where(AtlasBrandMap.atlas_brand_id == atlas_brand_id)
    )
    if row is None:
        return None, f"casa sin ligar: {atlas_brand_id}"
    brand = brands.get(row.brand_id) if row.brand_id else None
    if brand is None:
        owners = index.get(normalize(row.atlas_name), set())
        kind = "ambigua" if len(owners) > 1 else "sin ligar"
        return None, f"casa {kind}: {row.atlas_name}"
    if brand.status != STATUS_PUBLISHED:
        return None, f"casa en borrador: {brand.name}"
    return brand, None


def resolve_category(
    db: Session, atlas_department_id: str | None
) -> tuple[Category | None, str | None]:
    row = None
    if atlas_department_id is not None:
        row = db.scalar(
            select(AtlasCategoryMap).where(
                AtlasCategoryMap.atlas_department_id == atlas_department_id
            )
        )
    if row is None or row.category_id is None:
        return (
            None,
            f"categoría sin ligar: {row.atlas_name if row else atlas_department_id}",
        )
    return db.get(Category, row.category_id), None
