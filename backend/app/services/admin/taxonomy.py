"""Brands and categories."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import ApiError
from app.models import AdminUser, Brand, BrandAlias, Category, Product
from app.schemas import admin as schemas
from app.services.admin import audit
from app.services.admin.common import (
    asset_or_error,
    get_or_404,
    invalid_reference,
    set_asset,
    unique_slug,
)
from app.services.catalog import _public_aliases
from app.services.text import normalize, slugify

BRAND_FIELDS = (
    "name",
    "slug",
    "logo_asset_id",
    "editorial_asset_id",
    "description",
    "display_order",
    "is_featured",
    "status",
    "validation_status",
)
_PLAIN_BRAND_FIELDS = (
    "name",
    "description",
    "display_order",
    "is_featured",
    "status",
    "validation_status",
)
_BRAND_MISSING = "Marca no encontrada"
_CATEGORY_MISSING = "Categoría no encontrada"


def _counts(db: Session, column) -> dict:
    return dict(db.execute(select(column, func.count()).group_by(column)).all())


def _brand_out(brand: Brand, count: int) -> schemas.AdminBrand:
    return schemas.AdminBrand(
        id=brand.id,
        name=brand.name,
        slug=brand.slug,
        kind=brand.kind,
        logo_asset_id=brand.logo_asset_id,
        logo_url=brand.logo_url,
        editorial_asset_id=brand.editorial_asset_id,
        editorial_image_url=brand.editorial_image_url,
        description=brand.description,
        display_order=brand.display_order,
        is_featured=brand.is_featured,
        status=brand.status,
        validation_status=brand.validation_status,
        aliases=_public_aliases(brand),
        product_count=count,
    )


def _load_brand(db: Session, brand_id: uuid.UUID) -> Brand:
    brand = db.scalar(
        select(Brand).options(selectinload(Brand.aliases)).where(Brand.id == brand_id)
    )
    if brand is None:
        raise ApiError(404, "not_found", _BRAND_MISSING)
    return brand


def _single_out(db: Session, brand: Brand) -> schemas.AdminBrand:
    count = db.scalar(select(func.count()).where(Product.brand_id == brand.id)) or 0
    return _brand_out(brand, count)


def list_brands(
    db: Session, *, q: str | None, status: str | None, page: int, page_size: int
) -> schemas.Page[schemas.AdminBrand]:
    stmt = select(Brand).options(selectinload(Brand.aliases))
    if status:
        stmt = stmt.where(Brand.status == status)
    brands = list(db.scalars(stmt))
    query = normalize(q) if q else ""
    if query:
        brands = [
            brand
            for brand in brands
            if query in brand.search_text
            or any(query in alias.search_text for alias in brand.aliases)
        ]
    # Sorted here because SQL collations disagree on accents across databases.
    brands.sort(key=lambda brand: normalize(brand.name))
    counts = _counts(db, Product.brand_id)
    start = (page - 1) * page_size
    return schemas.Page[schemas.AdminBrand](
        items=[_brand_out(b, counts.get(b.id, 0)) for b in brands[start : start + page_size]],
        total=len(brands),
        page=page,
        page_size=page_size,
    )


def get_brand(db: Session, brand_id: uuid.UUID) -> schemas.AdminBrand:
    return _single_out(db, _load_brand(db, brand_id))


def _check_brand_slug(db: Session, slug: str, own_id: uuid.UUID | None) -> None:
    """A brand slug must not shadow another brand's slug or alias: public URLs resolve both."""
    other_brand = db.scalar(select(Brand.id).where(Brand.slug == slug, Brand.id != own_id))
    other_alias = db.scalar(
        select(BrandAlias.brand_id).where(BrandAlias.slug == slug, BrandAlias.brand_id != own_id)
    )
    if other_brand or other_alias:
        raise ApiError(409, "slug_taken", "Ese slug ya está en uso por otra marca")


def _add_alias(db: Session, brand: Brand, text: str) -> None:
    slug = slugify(text)
    if not slug:
        raise ApiError(422, "invalid_alias", "El alias debe contener letras o números")
    existing = db.scalar(select(BrandAlias).where(BrandAlias.slug == slug))
    taken_by_brand = db.scalar(select(Brand.id).where(Brand.slug == slug, Brand.id != brand.id))
    if taken_by_brand or (existing is not None and existing.brand_id != brand.id):
        raise ApiError(409, "alias_taken", f"El alias {text} ya pertenece a otra marca")
    if existing is None:
        brand.aliases.append(BrandAlias(brand_id=brand.id, alias=text, slug=slug))
        db.flush()


def _sync_aliases(db: Session, brand: Brand, wanted: list[str]) -> None:
    """`wanted` is the list the API exposes. Rows it hides, such as retained slugs, are untouched."""
    canonical = normalize(brand.name)
    wanted_slugs = {slugify(text) for text in wanted}
    for alias in list(brand.aliases):
        if normalize(alias.alias) == canonical or alias.slug in wanted_slugs:
            continue
        if alias.is_original:
            raise ApiError(
                409, "alias_protected", f"El alias {alias.alias} viene de la lista original de marcas"
            )
        brand.aliases.remove(alias)
    db.flush()
    for text in wanted:
        _add_alias(db, brand, text)


def _retain_old_slug(db: Session, brand: Brand, old_slug: str) -> None:
    if db.scalar(select(BrandAlias.id).where(BrandAlias.slug == old_slug)) is None:
        # The alias text equals the brand's name, so the public alias list does not show it.
        brand.aliases.append(BrandAlias(brand_id=brand.id, alias=brand.name, slug=old_slug))
        db.flush()


def create_brand(db: Session, data: schemas.BrandCreate, user: AdminUser) -> schemas.AdminBrand:
    if data.slug:
        _check_brand_slug(db, data.slug, None)
        slug = data.slug
    else:
        taken = set(db.scalars(select(Brand.slug))) | set(db.scalars(select(BrandAlias.slug)))
        slug = unique_slug(data.name, taken, fallback="marca")
    brand = Brand(
        name=data.name,
        original_name=data.name,
        slug=slug,
        description=data.description,
        display_order=data.display_order,
        is_featured=data.is_featured,
        status=data.status,
        validation_status=data.validation_status,
    )
    set_asset(brand, "logo_asset_id", "logo_url", asset_or_error(db, data.logo_asset_id))
    set_asset(
        brand,
        "editorial_asset_id",
        "editorial_image_url",
        asset_or_error(db, data.editorial_asset_id),
    )
    db.add(brand)
    db.flush()
    for text in data.aliases:
        _add_alias(db, brand, text)
    audit.record(
        db,
        user,
        "create",
        "brand",
        brand.id,
        audit.diff({}, audit.snapshot(brand, BRAND_FIELDS)) | {"aliases": [None, data.aliases]},
    )
    db.commit()
    return get_brand(db, brand.id)


def update_brand(
    db: Session, brand_id: uuid.UUID, data: schemas.BrandPatch, user: AdminUser
) -> schemas.AdminBrand:
    brand = _load_brand(db, brand_id)
    before = audit.snapshot(brand, BRAND_FIELDS)
    aliases_before = _public_aliases(brand)
    fields = data.model_fields_set
    old_slug = brand.slug

    for field in _PLAIN_BRAND_FIELDS:
        if field in fields:
            setattr(brand, field, getattr(data, field))
    if "logo_asset_id" in fields:
        set_asset(brand, "logo_asset_id", "logo_url", asset_or_error(db, data.logo_asset_id))
    if "editorial_asset_id" in fields:
        set_asset(
            brand,
            "editorial_asset_id",
            "editorial_image_url",
            asset_or_error(db, data.editorial_asset_id),
        )
    if data.slug and data.slug != old_slug:
        _check_brand_slug(db, data.slug, brand.id)
        brand.slug = data.slug
        db.flush()
        _retain_old_slug(db, brand, old_slug)
    if data.aliases is not None:
        _sync_aliases(db, brand, data.aliases)

    changes = audit.diff(before, audit.snapshot(brand, BRAND_FIELDS))
    aliases_after = _public_aliases(brand)
    if aliases_after != aliases_before:
        changes["aliases"] = [aliases_before, aliases_after]
    if changes:
        audit.record(db, user, "update", "brand", brand.id, changes)
    db.commit()
    return get_brand(db, brand.id)


# --- Categories ------------------------------------------------------------------------

CATEGORY_FIELDS = ("name", "slug", "parent_id", "display_order")


def _category_out(category: Category, count: int) -> schemas.AdminCategory:
    return schemas.AdminCategory(
        id=category.id,
        name=category.name,
        slug=category.slug,
        parent_id=category.parent_id,
        display_order=category.display_order,
        product_count=count,
    )


def list_categories(db: Session) -> schemas.Page[schemas.AdminCategory]:
    """The whole tree: the panel needs it entire to fill selectors."""
    categories = db.scalars(select(Category).order_by(Category.display_order, Category.slug)).all()
    counts = _counts(db, Product.category_id)
    return schemas.Page[schemas.AdminCategory](
        items=[_category_out(item, counts.get(item.id, 0)) for item in categories],
        total=len(categories),
        page=1,
        page_size=max(len(categories), 1),
    )


def _check_category_slug(db: Session, slug: str, own_id: uuid.UUID | None) -> None:
    if db.scalar(select(Category.id).where(Category.slug == slug, Category.id != own_id)):
        raise ApiError(409, "slug_taken", "Ese slug ya está en uso")


def _check_parent(db: Session, parent_id: uuid.UUID | None, own_id: uuid.UUID | None) -> None:
    current = parent_id
    while current is not None:
        if current == own_id:
            raise ApiError(422, "invalid_parent", "Una categoría no puede ser su propia ascendiente")
        parent = db.get(Category, current)
        if parent is None:
            raise invalid_reference("La categoría padre no existe")
        current = parent.parent_id


def create_category(
    db: Session, data: schemas.CategoryCreate, user: AdminUser
) -> schemas.AdminCategory:
    _check_parent(db, data.parent_id, None)
    if data.slug:
        _check_category_slug(db, data.slug, None)
        slug = data.slug
    else:
        slug = unique_slug(data.name, set(db.scalars(select(Category.slug))), fallback="categoria")
    category = Category(
        name=data.name, slug=slug, parent_id=data.parent_id, display_order=data.display_order
    )
    db.add(category)
    db.flush()
    audit.record(
        db,
        user,
        "create",
        "category",
        category.id,
        audit.diff({}, audit.snapshot(category, CATEGORY_FIELDS)),
    )
    db.commit()
    return _category_out(category, 0)


def update_category(
    db: Session, category_id: uuid.UUID, data: schemas.CategoryPatch, user: AdminUser
) -> schemas.AdminCategory:
    category = get_or_404(db, Category, category_id, _CATEGORY_MISSING)
    before = audit.snapshot(category, CATEGORY_FIELDS)
    fields = data.model_fields_set
    if "parent_id" in fields:
        _check_parent(db, data.parent_id, category.id)
    if data.slug:
        _check_category_slug(db, data.slug, category.id)
    for field in CATEGORY_FIELDS:
        if field in fields:
            setattr(category, field, getattr(data, field))
    changes = audit.diff(before, audit.snapshot(category, CATEGORY_FIELDS))
    if changes:
        audit.record(db, user, "update", "category", category.id, changes)
    db.commit()
    count = db.scalar(select(func.count()).where(Product.category_id == category.id)) or 0
    return _category_out(category, count)


def delete_category(db: Session, category_id: uuid.UUID, user: AdminUser) -> None:
    category = get_or_404(db, Category, category_id, _CATEGORY_MISSING)
    if db.scalar(select(Product.id).where(Product.category_id == category.id).limit(1)):
        raise ApiError(409, "category_in_use", "La categoría tiene piezas")
    if db.scalar(select(Category.id).where(Category.parent_id == category.id).limit(1)):
        raise ApiError(409, "category_in_use", "La categoría tiene subcategorías")
    audit.record(db, user, "delete", "category", category.id, {"name": [category.name, None]})
    db.delete(category)
    db.commit()
