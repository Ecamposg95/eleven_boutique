"""Ligas entre marcas/departamentos de Atlas ONE y las casas/categorías de Eleven."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    KIND_BRAND,
    STATUS_ARCHIVED,
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
from app.services.brand_match import NO_BRAND, brand_index, no_brand_classification
from app.services.text import normalize

PLACEHOLDER_BRAND = "Pendiente de ligar (Atlas ONE)"


def linkable_index(
    db: Session,
) -> tuple[dict[str, set[uuid.UUID]], dict[uuid.UUID, Brand]]:
    """Como `brand_index`, pero el índice solo apunta a casas a las que se puede ligar una marca de
    Atlas: ni clasificaciones ni la casa interna de respaldo (el panel tampoco lo permite).
    `brands` sigue trayendo todas, para resolver «Sin marca» y mapas ya ligados.
    """
    index, brands = brand_index(db)
    linkable = {
        brand_id
        for brand_id, brand in brands.items()
        if brand.kind == KIND_BRAND and brand.name != PLACEHOLDER_BRAND
    }
    filtered = {key: owners & linkable for key, owners in index.items()}
    return {key: owners for key, owners in filtered.items() if owners}, brands


def sync_brands(db: Session, atlas_brands: list[dict]) -> dict[str, int]:
    """Liga marcas de Atlas a casas por nombre/alias; sin coincidencia crea una casa en borrador.

    Nunca modifica una casa existente. Un mapa ya ligado gana sobre el nombre. La marca «Sin marca»
    de Atlas va a la clasificación «Sin marca» (como una pieza sin marca); si esa clasificación no
    existe, la fila espera sin ligar en vez de crear una casa con ese nombre.
    """
    index, brands = linkable_index(db)
    no_brand = no_brand_classification(brands)
    taken = set(db.scalars(select(Brand.slug))) | set(
        db.scalars(select(BrandAlias.slug))
    )
    maps = {row.atlas_brand_id: row for row in db.scalars(select(AtlasBrandMap))}
    counts = {"ligadas": 0, "creadas_borrador": 0}
    for item in atlas_brands:
        if item.get("deleted") or not normalize(item.get("name") or ""):
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
        if normalize(item["name"]) == NO_BRAND:
            if no_brand is not None:
                row.brand_id = no_brand.id
                counts["ligadas"] += 1
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
    incoming = {item["id"] for item in atlas_departments}
    # Una respuesta sin departamentos vivos (vacía o solo lápidas) no prueba ausencia.
    live = any(not item.get("deleted") for item in atlas_departments)
    for dept_id, row in maps.items():
        if live and dept_id not in incoming and row.category_id is not None:
            row.category_id = None
            counts["desligadas"] += 1
    db.flush()
    return counts


class Resolver:
    """Resuelve casas y categorías de Atlas con todo precargado: úsalo una vez por corrida."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.index, self.brands = linkable_index(db)
        self.full_index, _ = brand_index(db)
        self.no_brand = no_brand_classification(self.brands)
        self.brand_maps = {
            r.atlas_brand_id: r for r in db.scalars(select(AtlasBrandMap))
        }
        self.category_maps = {
            r.atlas_department_id: r for r in db.scalars(select(AtlasCategoryMap))
        }
        self.categories = {c.id: c for c in db.scalars(select(Category))}

    def brand(self, atlas_brand_id: str | None) -> tuple[Brand | None, str | None]:
        """Casa para un producto de Atlas, o el motivo por el que no se puede usar."""
        if atlas_brand_id is None:
            if self.no_brand:
                return self.no_brand, None
            return None, "No existe la clasificación Sin marca"
        row = self.brand_maps.get(atlas_brand_id)
        if row is None:
            return None, f"casa sin ligar: {atlas_brand_id}"
        brand = self.brands.get(row.brand_id) if row.brand_id else None
        if brand is None:
            key = normalize(row.atlas_name)
            if key == NO_BRAND:
                return None, "No existe la clasificación Sin marca"
            owners = self.index.get(key, set())
            if len(owners) > 1:
                return None, f"casa ambigua: {row.atlas_name}"
            if any(self.brands[i].kind != KIND_BRAND for i in self.full_index.get(key, set()) if i in self.brands):
                return None, f"casa sin ligar: {row.atlas_name} (el nombre es de una clasificación)"
            return None, f"casa sin ligar: {row.atlas_name}"
        if brand is self.no_brand:
            # Como una pieza sin marca: la clasificación se usa aunque esté en borrador.
            return brand, None
        if brand.status == STATUS_ARCHIVED:
            return None, f"casa archivada: {brand.name}"
        if brand.status != STATUS_PUBLISHED:
            return None, f"casa en borrador: {brand.name}"
        return brand, None

    def category(
        self, atlas_department_id: str | None
    ) -> tuple[Category | None, str | None]:
        row = (
            self.category_maps.get(atlas_department_id) if atlas_department_id else None
        )
        category = (
            self.categories.get(row.category_id) if row and row.category_id else None
        )
        if category is None:
            return (
                None,
                f"categoría sin ligar: {row.atlas_name if row else atlas_department_id}",
            )
        return category, None


def resolve_brand(
    db: Session, atlas_brand_id: str | None
) -> tuple[Brand | None, str | None]:
    return Resolver(db).brand(atlas_brand_id)


def resolve_category(
    db: Session, atlas_department_id: str | None
) -> tuple[Category | None, str | None]:
    return Resolver(db).category(atlas_department_id)
