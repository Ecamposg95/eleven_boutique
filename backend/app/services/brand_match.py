"""Índice de casas por nombre y alias normalizados, compartido por importadores y la sincronización."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KIND_CLASSIFICATION, Brand, BrandAlias
from app.services.text import normalize

NO_BRAND = "sin marca"


def brand_index(
    db: Session,
) -> tuple[dict[str, set[uuid.UUID]], dict[uuid.UUID, Brand]]:
    brands = {brand.id: brand for brand in db.scalars(select(Brand))}
    index: dict[str, set[uuid.UUID]] = {}
    for brand in brands.values():
        index.setdefault(normalize(brand.name), set()).add(brand.id)
    for alias, brand_id in db.execute(select(BrandAlias.alias, BrandAlias.brand_id)):
        index.setdefault(normalize(alias), set()).add(brand_id)
    return index, brands


def no_brand_classification(brands: dict[uuid.UUID, Brand]) -> Brand | None:
    return next(
        (
            brand
            for brand in brands.values()
            if brand.kind == KIND_CLASSIFICATION and normalize(brand.name) == NO_BRAND
        ),
        None,
    )
