"""Media library: upload, usage tracking, deletion and photo-to-product matching."""

import re
import uuid
from pathlib import PurePosixPath

from sqlalchemy import or_, select, union_all
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.config import Settings
from app.models import (
    BLOCK_IMAGE,
    STATUS_ARCHIVED,
    AdminUser,
    Brand,
    Collection,
    Lookbook,
    LookbookBlock,
    MediaAsset,
    Product,
    ProductMedia,
    ProductVariant,
    SiteSettings,
)
from app.schemas import admin as schemas
from app.services.admin import audit, products
from app.services.admin.common import get_or_404, paginate
from app.services.admin.images import ImageRejected, process_image, sanitize_filename
from app.services.admin.storage import get_storage
from app.services.text import escape_like

_URL_COLUMNS = (
    ProductMedia.url,
    Brand.logo_url,
    Brand.editorial_image_url,
    Collection.cover_url,
    Lookbook.cover_url,
    SiteSettings.hero_image_url,
    SiteSettings.hero_mobile_image_url,
)
_MISSING = "Imagen no encontrada"


def _referenced_urls_query():
    return union_all(*(select(column.label("url")).where(column.is_not(None)) for column in _URL_COLUMNS))


def _block_urls(db: Session) -> set[str]:
    """Lookbook image blocks keep their URL in JSON, which SQL cannot compare portably."""
    contents = db.scalars(select(LookbookBlock.content).where(LookbookBlock.type == BLOCK_IMAGE))
    return {content["url"] for content in contents if content.get("url")}


def _gallery_urls(db: Session) -> set[str]:
    """The portada gallery keeps its URLs in JSON too."""
    galleries = db.scalars(select(SiteSettings.hero_gallery))
    return {slide["url"] for gallery in galleries for slide in (gallery or []) if slide.get("url")}


def _used_urls(db: Session) -> set[str]:
    return set(db.scalars(_referenced_urls_query())) | _block_urls(db) | _gallery_urls(db)


def _asset_out(asset: MediaAsset, used: set[str]) -> schemas.AdminMedia:
    return schemas.AdminMedia(
        id=asset.id,
        url=asset.url,
        filename=asset.filename,
        alt=asset.alt,
        content_type=asset.content_type,
        width=asset.width,
        height=asset.height,
        size_bytes=asset.size_bytes,
        in_use=asset.url in used,
        created_at=asset.created_at,
    )


def list_media(
    db: Session, *, q: str | None, unused: bool | None, page: int, page_size: int
) -> schemas.Page[schemas.AdminMedia]:
    stmt = select(MediaAsset)
    if q and q.strip():
        pattern = f"%{escape_like(q.strip())}%"
        stmt = stmt.where(
            or_(
                MediaAsset.filename.ilike(pattern, escape="\\"),
                MediaAsset.alt.ilike(pattern, escape="\\"),
            )
        )
    if unused is not None:
        referenced = select(_referenced_urls_query().subquery().c.url)
        blocks = _block_urls(db) | _gallery_urls(db)
        if unused:
            stmt = stmt.where(MediaAsset.url.not_in(referenced), MediaAsset.url.not_in(blocks))
        else:
            stmt = stmt.where(or_(MediaAsset.url.in_(referenced), MediaAsset.url.in_(blocks)))
    assets, total = paginate(
        db, stmt.order_by(MediaAsset.created_at.desc(), MediaAsset.id), page, page_size
    )
    used = _used_urls(db)
    return schemas.Page[schemas.AdminMedia](
        items=[_asset_out(asset, used) for asset in assets],
        total=total,
        page=page,
        page_size=page_size,
    )


def store_upload(
    db: Session, settings: Settings, filename: str | None, data: bytes, user: AdminUser
) -> schemas.AdminMedia:
    """Raises ImageRejected if the content is not an acceptable image."""
    processed = process_image(data)
    storage = get_storage(settings)
    storage.save(processed.key, processed.data, processed.content_type)
    try:
        asset = MediaAsset(
            storage_key=processed.key,
            url=storage.url(processed.key),
            filename=sanitize_filename(filename),
            alt="",
            content_type=processed.content_type,
            width=processed.width,
            height=processed.height,
            size_bytes=len(processed.data),
            uploaded_by_id=user.id,
        )
        db.add(asset)
        db.flush()
        audit.record(db, user, "upload", "media_asset", asset.id, {"filename": [None, asset.filename]})
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(processed.key)
        raise
    return _asset_out(asset, set())


def upload_many(
    db: Session, settings: Settings, files: list[tuple[str | None, bytes]], user: AdminUser
) -> schemas.MediaUploadOut:
    """Stores what it can. A request where nothing could be stored is an error."""
    items: list[schemas.AdminMedia] = []
    rejected: list[tuple[str, ImageRejected]] = []
    for filename, data in files:
        try:
            items.append(store_upload(db, settings, filename, data, user))
        except ImageRejected as error:
            rejected.append((sanitize_filename(filename), error))
    if not items:
        first = rejected[0][1]
        raise ApiError(first.status, first.code, first.message)
    return schemas.MediaUploadOut(
        items=items,
        errors=[
            schemas.UploadError(filename=name, code=error.code, message=error.message)
            for name, error in rejected
        ],
    )


def update_alt(
    db: Session, asset_id: uuid.UUID, data: schemas.MediaPatch, user: AdminUser
) -> schemas.AdminMedia:
    asset = get_or_404(db, MediaAsset, asset_id, _MISSING)
    old_alt = asset.alt
    if data.alt != old_alt:
        # Gallery links that inherited the asset's text follow it; custom ones are kept.
        links = db.scalars(
            select(ProductMedia).where(
                ProductMedia.media_asset_id == asset.id, ProductMedia.alt == old_alt
            )
        )
        for link in links:
            link.alt = data.alt
        audit.record(db, user, "update", "media_asset", asset.id, {"alt": [old_alt, data.alt]})
        asset.alt = data.alt
    db.commit()
    return _asset_out(asset, _used_urls(db))


def delete_asset(db: Session, settings: Settings, asset_id: uuid.UUID, user: AdminUser) -> None:
    asset = get_or_404(db, MediaAsset, asset_id, _MISSING)
    in_use = ApiError(409, "media_in_use", "La imagen está en uso y no se puede borrar")
    if asset.url in _used_urls(db):
        raise in_use
    key = asset.storage_key
    audit.record(db, user, "delete", "media_asset", asset.id, {"filename": [asset.filename, None]})
    db.delete(asset)
    try:
        db.commit()
    except IntegrityError as error:  # An asset column the URL check above did not see.
        db.rollback()
        raise in_use from error
    get_storage(settings).delete(key)


# --- Matching --------------------------------------------------------------------------

_COPY_SUFFIX = re.compile(r"(?:\s*\(\d+\)|[-_ ]\d{1,2})$")
_PHOTO_NAME = re.compile(r"^foto[\s_-]*(mujer[\s_-]*)?(\d+(?:\+\d+)*)(?!\d)", re.IGNORECASE)


def _photo_refs_in_filename(stem: str) -> list[str]:
    found = _PHOTO_NAME.match(stem.strip())
    if not found:
        return []
    prefix = "foto mujer" if found.group(1) else "foto"
    return [f"{prefix} {number}" for number in found.group(2).split("+")]


class _MatchIndex:
    def __init__(self, db: Session) -> None:
        self.products: dict[uuid.UUID, tuple[str, str]] = {}
        self.by_sku: dict[str, set[uuid.UUID]] = {}
        self.by_ref: dict[str, set[uuid.UUID]] = {}
        rows = db.execute(
            select(Product.id, Product.sku, Product.name, Product.photo_refs).where(
                Product.status != STATUS_ARCHIVED
            )
        )
        for product_id, sku, name, refs in rows:
            self.products[product_id] = (sku, name)
            self.by_sku.setdefault(sku.casefold(), set()).add(product_id)
            for ref in refs or []:
                self.by_ref.setdefault(ref.casefold(), set()).add(product_id)
        variants = db.execute(select(ProductVariant.sku, ProductVariant.product_id))
        for sku, product_id in variants:
            if product_id in self.products:
                self.by_sku.setdefault(sku.casefold(), set()).add(product_id)

    def sku_candidates(self, stem: str) -> set[uuid.UUID]:
        key = stem.strip().casefold()
        exact = self.by_sku.get(key)
        if exact:
            return exact
        # "ABC-123_2.jpg" or "ABC-123 (2).jpg": a further shot of the same SKU.
        return self.by_sku.get(_COPY_SUFFIX.sub("", key), set())

    def ref_candidates(self, stem: str) -> set[uuid.UUID]:
        found: set[uuid.UUID] = set()
        for ref in _photo_refs_in_filename(stem):
            found |= self.by_ref.get(ref, set())
        return found

    def candidates(self, ids: set[uuid.UUID]) -> list[schemas.MatchCandidate]:
        rows = [
            schemas.MatchCandidate(id=item, sku=self.products[item][0], name=self.products[item][1])
            for item in ids
        ]
        return sorted(rows, key=lambda row: row.sku)


def bulk_match(db: Session, data: schemas.BulkMatchIn) -> schemas.BulkMatchOut:
    """A proposal only: nothing is saved. Anything ambiguous stays unassigned."""
    index = _MatchIndex(db)
    items = []
    for asset_id in dict.fromkeys(data.media_asset_ids):
        asset = get_or_404(db, MediaAsset, asset_id, _MISSING)
        stem = PurePosixPath(asset.filename).stem
        match, found = "none", index.sku_candidates(stem)
        if found:
            match = "sku"
        else:
            found = index.ref_candidates(stem)
            if found:
                match = "photo_ref"
        unique = len(found) == 1
        items.append(
            schemas.BulkMatchItem(
                media_asset_id=asset.id,
                filename=asset.filename,
                product_id=next(iter(found)) if unique else None,
                match=match if unique else "none",
                candidates=index.candidates(found),
            )
        )
    return schemas.BulkMatchOut(items=items)


def bulk_assign(db: Session, data: schemas.BulkAssignIn, user: AdminUser) -> schemas.BulkAssignOut:
    """Per item. Assigning a photo the product already has counts as done."""
    results = []
    for item in data.items:
        error = None
        asset = db.get(MediaAsset, item.media_asset_id)
        product = db.get(Product, item.product_id)
        if asset is None:
            error = schemas.ItemError(code="invalid_reference", message=_MISSING)
        elif product is None:
            error = schemas.ItemError(code="invalid_reference", message="Pieza no encontrada")
        elif not products.is_linked(db, product.id, asset.id):
            products.link_asset(db, product, asset, None, user)
            db.commit()
        results.append(
            schemas.BulkAssignResult(
                media_asset_id=item.media_asset_id,
                product_id=item.product_id,
                ok=error is None,
                error=error,
            )
        )
    return schemas.BulkAssignOut(results=results)
