"""Product administration and the publishing rules."""

import uuid
from typing import Literal

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.errors import ApiError
from app.models import (
    KIND_BRAND,
    ROLE_EDITOR,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    AdminUser,
    Brand,
    Category,
    MediaAsset,
    Product,
    ProductMedia,
    ProductVariant,
)
from app.models.base import utcnow
from app.schemas import admin as schemas
from app.services.admin import audit
from app.services.admin.common import invalid_reference, not_found, paginate, unique_slug
from app.services.text import escape_like, normalize

ProductSort = Literal["updated", "recent", "name", "display", "sku"]
AUDITED_FIELDS = (
    "name",
    "slug",
    "sku",
    "brand_id",
    "category_id",
    "status",
    "is_featured",
    "display_order",
    "commercial_added_at",
    "published_at",
    "seo_title",
    "seo_description",
    "internal_notes",
)
_EDITABLE = tuple(field for field in AUDITED_FIELDS if field not in ("sku", "published_at", "status"))


def product_out(product: Product) -> schemas.AdminProduct:
    brand, category = product.brand, product.category
    return schemas.AdminProduct(
        id=product.id,
        sku=product.sku,
        name=product.name,
        slug=product.slug,
        brand_id=product.brand_id,
        category_id=product.category_id,
        brand=schemas.ProductBrandRef(
            id=brand.id, slug=brand.slug, name=brand.name, kind=brand.kind, status=brand.status
        ),
        category=schemas.ProductCategoryRef(id=category.id, slug=category.slug, name=category.name),
        status=product.status,
        is_featured=product.is_featured,
        is_demo=product.is_demo,
        display_order=product.display_order,
        published_at=product.published_at,
        commercial_added_at=product.commercial_added_at,
        seo_title=product.seo_title,
        seo_description=product.seo_description,
        internal_notes=product.internal_notes,
        photo_refs=product.photo_refs or [],
        media=[
            schemas.ProductMediaOut(
                id=item.id,
                media_asset_id=item.media_asset_id,
                url=item.url,
                alt=item.alt,
                is_primary=item.is_primary,
                position=item.position,
            )
            for item in product.media
        ],
        variants=[
            schemas.VariantOut(id=item.id, sku=item.sku, color=item.color, size=item.size)
            for item in product.variants
        ],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _loaded():
    return select(Product).options(
        joinedload(Product.brand),
        joinedload(Product.category),
        selectinload(Product.media),
        selectinload(Product.variants),
    )


def get_product(db: Session, product_id: uuid.UUID) -> Product:
    product = db.scalar(_loaded().where(Product.id == product_id))
    if product is None:
        raise not_found("Pieza no encontrada")
    return product


def _refreshed(db: Session, product_id: uuid.UUID) -> schemas.AdminProduct:
    db.expire_all()
    return product_out(get_product(db, product_id))


def _by_id_or_slug(db: Session, model, value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return db.scalar(select(model.id).where(model.slug == value))


def list_products(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    brand: str | None,
    category: str | None,
    has_photo: bool | None,
    sort: ProductSort,
    page: int,
    page_size: int,
) -> schemas.Page[schemas.AdminProduct]:
    stmt = _loaded()
    if q and q.strip():
        normalized = escape_like(normalize(q))
        raw = escape_like(q.strip().casefold())
        variant_match = select(ProductVariant.product_id).where(
            func.lower(ProductVariant.sku).like(f"%{raw}%", escape="\\")
        )
        stmt = stmt.where(
            or_(
                Product.search_text.like(f"%{normalized}%", escape="\\"),
                func.lower(Product.sku).like(f"%{raw}%", escape="\\"),
                Product.id.in_(variant_match),
            )
        )
    if status:
        stmt = stmt.where(Product.status == status)
    if brand:
        stmt = stmt.where(Product.brand_id == _by_id_or_slug(db, Brand, brand))
    if category:
        category_id = _by_id_or_slug(db, Category, category)
        children = select(Category.id).where(Category.parent_id == category_id)
        stmt = stmt.where(or_(Product.category_id == category_id, Product.category_id.in_(children)))
    has_media = exists().where(ProductMedia.product_id == Product.id)
    if has_photo is True:
        stmt = stmt.where(has_media)
    elif has_photo is False:
        stmt = stmt.where(~has_media)

    order = {
        "updated": (Product.updated_at.desc(),),
        "recent": (Product.commercial_added_at.desc().nulls_last(),),
        "name": (Product.search_text,),
        "display": (Product.display_order,),
        "sku": (Product.sku,),
    }[sort]
    products, total = paginate(db, stmt.order_by(*order, Product.slug), page, page_size)
    return schemas.Page[schemas.AdminProduct](
        items=[product_out(product) for product in products],
        total=total,
        page=page,
        page_size=page_size,
    )


def _prepare_publication(db: Session, product: Product, publish_brand: bool, user: AdminUser) -> None:
    """Raises unless the product can go public. Also applies publish_brand."""
    if not product.name.strip():
        raise ApiError(409, "publish_requirements", "La pieza necesita nombre para publicarse")
    has_photo = db.scalar(select(exists().where(ProductMedia.product_id == product.id)))
    if not has_photo:
        raise ApiError(409, "photo_required", "La pieza necesita al menos una foto para publicarse")
    brand = db.get(Brand, product.brand_id)
    if brand.kind == KIND_BRAND and brand.status != STATUS_PUBLISHED:
        if not publish_brand:
            raise ApiError(
                409,
                "brand_unpublished",
                f"La marca {brand.name} no está publicada; reenvía con publish_brand para publicar ambas",
            )
        if user.role == ROLE_EDITOR:
            raise ApiError(403, "forbidden", "Publicar una marca exige rol admin")
        audit.record(
            db,
            user,
            "publish_brand",
            "brand",
            brand.id,
            {"status": [brand.status, STATUS_PUBLISHED], "product_id": [None, str(product.id)]},
        )
        brand.status = STATUS_PUBLISHED


def _publish_stamp(product: Product) -> None:
    if product.published_at is None:
        product.published_at = utcnow()


def _check_references(db: Session, brand_id: uuid.UUID | None, category_id: uuid.UUID | None) -> None:
    if brand_id is not None and db.get(Brand, brand_id) is None:
        raise invalid_reference("La marca indicada no existe")
    if category_id is not None and db.get(Category, category_id) is None:
        raise invalid_reference("La categoría indicada no existe")


def _check_slug_free(db: Session, slug: str, own_id: uuid.UUID | None = None) -> None:
    stmt = select(Product.id).where(Product.slug == slug)
    if own_id is not None:
        stmt = stmt.where(Product.id != own_id)
    if db.scalar(stmt) is not None:
        raise ApiError(409, "slug_taken", "Ese slug ya está en uso")


def create_product(db: Session, data: schemas.ProductCreate, user: AdminUser) -> schemas.AdminProduct:
    _check_references(db, data.brand_id, data.category_id)
    brand = db.get(Brand, data.brand_id)
    if data.slug:
        _check_slug_free(db, data.slug)
        slug = data.slug
    else:
        taken = set(db.scalars(select(Product.slug)))
        base = data.name if brand.kind != KIND_BRAND else f"{brand.name} {data.name}"
        slug = unique_slug(base, taken, fallback="pieza")
    sku = data.sku or f"ELV-{uuid.uuid4().hex[:10].upper()}"
    if db.scalar(select(Product.id).where(Product.sku == sku)) is not None:
        raise ApiError(409, "sku_taken", "Ese SKU ya está en uso")

    product = Product(
        sku=sku,
        slug=slug,
        name=data.name,
        brand_id=data.brand_id,
        category_id=data.category_id,
        status=STATUS_DRAFT,
        is_featured=data.is_featured,
        display_order=data.display_order,
        commercial_added_at=data.commercial_added_at,
        seo_title=data.seo_title,
        seo_description=data.seo_description,
        internal_notes=data.internal_notes,
        is_demo=False,
        photo_refs=[],
    )
    db.add(product)
    db.flush()
    if data.status == STATUS_PUBLISHED:
        _prepare_publication(db, product, data.publish_brand, user)
        _publish_stamp(product)
    product.status = data.status
    audit.record(
        db, user, "create", "product", product.id, audit.diff({}, audit.snapshot(product, AUDITED_FIELDS))
    )
    db.commit()
    return _refreshed(db, product.id)


def update_product(
    db: Session, product_id: uuid.UUID, data: schemas.ProductPatch, user: AdminUser
) -> schemas.AdminProduct:
    product = get_product(db, product_id)
    before = audit.snapshot(product, AUDITED_FIELDS)
    fields = data.model_fields_set
    _check_references(db, data.brand_id, data.category_id)
    if data.slug and data.slug != product.slug:
        _check_slug_free(db, data.slug, product.id)

    brand_changed = "brand_id" in fields and data.brand_id != product.brand_id
    for field in _EDITABLE:
        if field in fields:
            setattr(product, field, getattr(data, field))

    target = data.status if "status" in fields else product.status
    if target == STATUS_PUBLISHED and (product.status != STATUS_PUBLISHED or brand_changed):
        db.flush()
        _prepare_publication(db, product, bool(data.publish_brand), user)
        _publish_stamp(product)
    product.status = target

    changes = audit.diff(before, audit.snapshot(product, AUDITED_FIELDS))
    if changes:
        audit.record(db, user, "update", "product", product.id, changes)
    db.commit()
    return _refreshed(db, product.id)


def archive_product(db: Session, product_id: uuid.UUID, user: AdminUser) -> schemas.AdminProduct:
    product = get_product(db, product_id)
    if product.status != STATUS_ARCHIVED:
        audit.record(
            db, user, "archive", "product", product.id, {"status": [product.status, STATUS_ARCHIVED]}
        )
        product.status = STATUS_ARCHIVED
    db.commit()
    return _refreshed(db, product.id)


def _apply_bulk_action(
    db: Session, product: Product, action: str, publish_brand: bool, user: AdminUser
) -> None:
    before = audit.snapshot(product, AUDITED_FIELDS)
    if action == "publish":
        if product.status != STATUS_PUBLISHED:
            _prepare_publication(db, product, publish_brand, user)
            _publish_stamp(product)
            product.status = STATUS_PUBLISHED
    elif action == "unpublish":
        if product.status == STATUS_PUBLISHED:
            product.status = STATUS_DRAFT
    elif action == "archive":
        product.status = STATUS_ARCHIVED
    else:
        product.is_featured = action == "feature"
    changes = audit.diff(before, audit.snapshot(product, AUDITED_FIELDS))
    if changes:
        audit.record(db, user, f"bulk_{action}", "product", product.id, changes)


def bulk_action(db: Session, data: schemas.ProductBulkIn, user: AdminUser) -> schemas.ProductBulkOut:
    results = []
    for product_id in dict.fromkeys(data.ids):
        try:
            product = get_product(db, product_id)
            _apply_bulk_action(db, product, data.action, data.publish_brand, user)
            db.commit()  # Per product: one failure leaves the rest of the batch intact.
            results.append(schemas.ProductBulkResult(id=product_id, ok=True, error=None))
        except ApiError as error:
            db.rollback()
            results.append(
                schemas.ProductBulkResult(
                    id=product_id,
                    ok=False,
                    error=schemas.ItemError(code=error.code, message=str(error.detail)),
                )
            )
    return schemas.ProductBulkOut(results=results)


# --- Gallery ---------------------------------------------------------------------------


def link_asset(
    db: Session, product: Product, asset: MediaAsset, alt: str | None, user: AdminUser
) -> ProductMedia:
    """Appends to the gallery. The first photo becomes the primary one."""
    position = (
        db.scalar(
            select(func.max(ProductMedia.position)).where(ProductMedia.product_id == product.id)
        )
        or 0
    )
    has_media = db.scalar(select(exists().where(ProductMedia.product_id == product.id)))
    link = ProductMedia(
        product_id=product.id,
        media_asset_id=asset.id,
        url=asset.url,
        alt=alt if alt else (asset.alt or product.name),
        is_primary=not has_media,
        position=position + 1 if has_media else 0,
    )
    db.add(link)
    db.flush()
    audit.record(
        db, user, "link_media", "product", product.id, {"media_asset_id": [None, str(asset.id)]}
    )
    return link


def is_linked(db: Session, product_id: uuid.UUID, asset_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(ProductMedia.id).where(
                ProductMedia.product_id == product_id, ProductMedia.media_asset_id == asset_id
            )
        )
        is not None
    )


def add_media(
    db: Session, product_id: uuid.UUID, data: schemas.ProductMediaAdd, user: AdminUser
) -> schemas.AdminProduct:
    product = get_product(db, product_id)
    asset = db.get(MediaAsset, data.media_asset_id)
    if asset is None:
        raise invalid_reference("La imagen indicada no existe")
    if is_linked(db, product.id, asset.id):
        raise ApiError(409, "already_linked", "La imagen ya está en la galería de esta pieza")
    link_asset(db, product, asset, data.alt, user)
    db.commit()
    return _refreshed(db, product.id)


def reorder_media(
    db: Session, product_id: uuid.UUID, data: schemas.ProductMediaOrder, user: AdminUser
) -> schemas.AdminProduct:
    product = get_product(db, product_id)
    links = {link.id: link for link in product.media}
    if len(data.order) != len(set(data.order)) or set(data.order) != set(links):
        raise ApiError(422, "invalid_order", "El orden debe incluir cada foto de la pieza una vez")
    if data.primary_id is not None and data.primary_id not in links:
        raise ApiError(422, "invalid_order", "La foto principal no pertenece a esta pieza")

    before = [str(link.id) for link in product.media]
    # Two steps, because (product_id, position) is unique at every point.
    for offset, link in enumerate(product.media):
        link.position = -1 - offset
    db.flush()
    for position, link_id in enumerate(data.order):
        links[link_id].position = position
    if data.primary_id is not None:
        for link in links.values():
            link.is_primary = link.id == data.primary_id
    audit.record(
        db,
        user,
        "reorder_media",
        "product",
        product.id,
        {"order": [before, [str(item) for item in data.order]], "primary_id": [None, data.primary_id]},
    )
    db.commit()
    return _refreshed(db, product.id)


def update_media_alt(
    db: Session, product_id: uuid.UUID, media_id: uuid.UUID, alt: str, user: AdminUser
) -> schemas.AdminProduct:
    product = get_product(db, product_id)
    link = next((item for item in product.media if item.id == media_id), None)
    if link is None:
        raise not_found("Foto no encontrada en esta pieza")
    if link.alt != alt:
        audit.record(db, user, "update_media_alt", "product", product.id, {"alt": [link.alt, alt]})
        link.alt = alt
        db.commit()
    return _refreshed(db, product.id)


def remove_media(
    db: Session, product_id: uuid.UUID, media_id: uuid.UUID, user: AdminUser
) -> schemas.AdminProduct:
    product = get_product(db, product_id)
    link = next((item for item in product.media if item.id == media_id), None)
    if link is None:
        raise not_found("Foto no encontrada en esta pieza")
    remaining = [item for item in product.media if item.id != media_id]
    if not remaining and product.status == STATUS_PUBLISHED:
        raise ApiError(
            409, "last_photo", "Una pieza publicada debe conservar al menos una foto"
        )
    if link.is_primary and remaining:
        remaining[0].is_primary = True
    audit.record(
        db,
        user,
        "unlink_media",
        "product",
        product.id,
        {"media": [{"id": link.id, "url": link.url}, None]},
    )
    product.media.remove(link)  # The file and its asset stay; only the link goes.
    db.commit()
    return _refreshed(db, product.id)

