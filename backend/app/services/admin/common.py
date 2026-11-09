"""Helpers shared by the admin services."""

import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.models import MediaAsset
from app.services.text import slugify

MAX_SLUG = 200


def not_found(message: str) -> ApiError:
    return ApiError(404, "not_found", message)


def invalid_reference(message: str) -> ApiError:
    return ApiError(422, "invalid_reference", message)


def get_or_404[T](db: Session, model: type[T], record_id: uuid.UUID, message: str) -> T:
    record = db.get(model, record_id)
    if record is None:
        raise not_found(message)
    return record


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> tuple[list[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return list(rows), total


def unique_slug(base_text: str, taken: set[str], fallback: str = "registro") -> str:
    """Adds the slug to `taken`, so a batch can call this repeatedly."""
    base = (slugify(base_text) or fallback)[: MAX_SLUG - 8].strip("-")
    slug = base
    suffix = 1
    while slug in taken:
        suffix += 1
        slug = f"{base}-{suffix}"
    taken.add(slug)
    return slug


def set_asset(record: Any, asset_field: str, url_field: str, asset: MediaAsset | None) -> None:
    """Keeps the id and the URL that public reads use in step."""
    setattr(record, asset_field, asset.id if asset else None)
    setattr(record, url_field, asset.url if asset else None)


def asset_or_error(db: Session, asset_id: uuid.UUID | None) -> MediaAsset | None:
    if asset_id is None:
        return None
    asset = db.get(MediaAsset, asset_id)
    if asset is None:
        raise invalid_reference("La imagen indicada no existe")
    return asset
