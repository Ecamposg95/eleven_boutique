"""Public visibility is computed here and only here; queries never mutate status."""

from sqlalchemy import ColumnElement, and_, or_

from app.models import (
    KIND_BRAND,
    KIND_CLASSIFICATION,
    STATUS_ARCHIVED,
    STATUS_PUBLISHED,
    Brand,
    Product,
)


def record_visible(model, demo_mode: bool) -> ColumnElement[bool]:
    """For models with status and is_demo: products, collections and lookbooks."""
    if demo_mode:
        return and_(
            or_(model.status == STATUS_PUBLISHED, model.is_demo.is_(True)),
            model.status != STATUS_ARCHIVED,
        )
    return and_(model.status == STATUS_PUBLISHED, model.is_demo.is_(False))


def brand_visible(demo_mode: bool) -> ColumnElement[bool]:
    """Classifications are never a public brand, in any mode."""
    status = Brand.status != STATUS_ARCHIVED if demo_mode else Brand.status == STATUS_PUBLISHED
    return and_(Brand.kind == KIND_BRAND, status)


def product_visible(demo_mode: bool) -> ColumnElement[bool]:
    """Requires Product joined to Brand. A hidden brand hides its products: no dead links."""
    return and_(
        record_visible(Product, demo_mode),
        or_(Brand.kind == KIND_CLASSIFICATION, brand_visible(demo_mode)),
    )
