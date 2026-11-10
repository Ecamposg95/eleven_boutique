"""Collections, lookbooks, site settings, dashboard and the audit listing."""

import uuid
from datetime import timedelta

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.config import Settings
from app.models import (
    BLOCK_TEXT,
    KIND_BRAND,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    AdminUser,
    AuditLog,
    Brand,
    CatalogEvent,
    Collection,
    CollectionProduct,
    Lookbook,
    LookbookBlock,
    LookbookProduct,
    Product,
    ProductMedia,
    SiteSettings,
)
from app.models.base import utcnow
from app.schemas import admin as schemas
from app.services.admin import audit
from app.services.admin.common import (
    asset_or_error,
    get_or_404,
    invalid_reference,
    paginate,
    set_asset,
    unique_slug,
)
from app.services.catalog import effective_whatsapp_digits
from app.services.text import escape_like
from app.services.whatsapp import normalize_number

CONTENT_FIELDS = ("title", "slug", "summary", "cover_asset_id", "status", "display_order")
_PLAIN_FIELDS = ("title", "summary", "status", "display_order")


class _Kind:
    def __init__(self, model, link_model, owner_field: str, entity: str, missing: str) -> None:
        self.model = model
        self.link_model = link_model
        self.owner_field = owner_field
        self.entity = entity
        self.missing = missing

    @property
    def owner_column(self):
        return getattr(self.link_model, self.owner_field)


COLLECTIONS = _Kind(
    Collection, CollectionProduct, "collection_id", "collection", "Colección no encontrada"
)
LOOKBOOKS = _Kind(Lookbook, LookbookProduct, "lookbook_id", "lookbook", "Lookbook no encontrado")


def _product_ids(db: Session, kind: _Kind, owner_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(kind.link_model.product_id)
            .where(kind.owner_column == owner_id)
            .order_by(kind.link_model.position)
        )
    )


def _set_products(db: Session, kind: _Kind, owner_id: uuid.UUID, product_ids: list[uuid.UUID]) -> None:
    if len(product_ids) != len(set(product_ids)):
        raise ApiError(422, "invalid_reference", "product_ids contiene piezas repetidas")
    if product_ids:
        found = set(db.scalars(select(Product.id).where(Product.id.in_(product_ids))))
        if found != set(product_ids):
            raise invalid_reference("product_ids contiene piezas que no existen")
    for link in db.scalars(select(kind.link_model).where(kind.owner_column == owner_id)):
        db.delete(link)
    db.flush()
    for position, product_id in enumerate(product_ids):
        db.add(
            kind.link_model(
                **{kind.owner_field: owner_id}, product_id=product_id, position=position
            )
        )
    db.flush()


def _base_fields(db: Session, kind: _Kind, record) -> dict:
    return {
        "id": record.id,
        "title": record.title,
        "slug": record.slug,
        "summary": record.summary,
        "cover_asset_id": record.cover_asset_id,
        "cover_url": record.cover_url,
        "status": record.status,
        "is_demo": record.is_demo,
        "display_order": record.display_order,
        "product_ids": _product_ids(db, kind, record.id),
    }


def _block_out(block: LookbookBlock) -> dict:
    content = block.content
    if block.type == BLOCK_TEXT:
        fields = {"heading": content.get("heading"), "body": content["body"]}
    else:
        fields = {
            "url": content["url"],
            "alt": content["alt"],
            "layout": content.get("layout", "full"),
        }
    return {"type": block.type, "position": block.position, **fields}


def _out(db: Session, kind: _Kind, record):
    fields = _base_fields(db, kind, record)
    if kind is LOOKBOOKS:
        blocks = db.scalars(
            select(LookbookBlock)
            .where(LookbookBlock.lookbook_id == record.id)
            .order_by(LookbookBlock.position)
        )
        return schemas.AdminLookbook(**fields, blocks=[_block_out(block) for block in blocks])
    return schemas.AdminCollection(**fields)


def list_records(
    db: Session, kind: _Kind, *, q: str | None, status: str | None, page: int, page_size: int
):
    stmt = select(kind.model)
    if q and q.strip():
        pattern = f"%{escape_like(q.strip())}%"
        stmt = stmt.where(
            or_(
                kind.model.title.ilike(pattern, escape="\\"),
                kind.model.slug.ilike(pattern, escape="\\"),
            )
        )
    if status:
        stmt = stmt.where(kind.model.status == status)
    records, total = paginate(
        db, stmt.order_by(kind.model.display_order, kind.model.slug), page, page_size
    )
    return {
        "items": [_out(db, kind, record) for record in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_record(db: Session, kind: _Kind, record_id: uuid.UUID):
    return _out(db, kind, get_or_404(db, kind.model, record_id, kind.missing))


def _check_slug(db: Session, kind: _Kind, slug: str, own_id: uuid.UUID | None) -> None:
    if db.scalar(select(kind.model.id).where(kind.model.slug == slug, kind.model.id != own_id)):
        raise ApiError(409, "slug_taken", "Ese slug ya está en uso")


def _replace_blocks(db: Session, lookbook_id: uuid.UUID, blocks: list) -> None:
    for existing in db.scalars(select(LookbookBlock).where(LookbookBlock.lookbook_id == lookbook_id)):
        db.delete(existing)
    db.flush()
    for index, block in enumerate(blocks):
        content = block.model_dump(exclude={"type", "position"})
        position = block.position if block.position is not None else index
        db.add(
            LookbookBlock(lookbook_id=lookbook_id, type=block.type, position=position, content=content)
        )
    db.flush()


def create_record(db: Session, kind: _Kind, data, user: AdminUser):
    if data.slug:
        _check_slug(db, kind, data.slug, None)
        slug = data.slug
    else:
        slug = unique_slug(data.title, set(db.scalars(select(kind.model.slug))))
    record = kind.model(
        title=data.title,
        slug=slug,
        summary=data.summary,
        status=data.status,
        display_order=data.display_order,
        is_demo=False,
    )
    set_asset(record, "cover_asset_id", "cover_url", asset_or_error(db, data.cover_asset_id))
    db.add(record)
    db.flush()
    _set_products(db, kind, record.id, data.product_ids)
    if kind is LOOKBOOKS:
        _replace_blocks(db, record.id, data.blocks)
    audit.record(
        db,
        user,
        "create",
        kind.entity,
        record.id,
        audit.diff({}, audit.snapshot(record, CONTENT_FIELDS))
        | {"product_ids": [None, data.product_ids]},
    )
    db.commit()
    return _out(db, kind, record)


def update_record(db: Session, kind: _Kind, record_id: uuid.UUID, data, user: AdminUser):
    record = get_or_404(db, kind.model, record_id, kind.missing)
    before = audit.snapshot(record, CONTENT_FIELDS)
    fields = data.model_fields_set
    extra_changes: dict = {}
    if data.slug:
        _check_slug(db, kind, data.slug, record.id)
        record.slug = data.slug
    for field in _PLAIN_FIELDS:
        if field in fields:
            setattr(record, field, getattr(data, field))
    if "cover_asset_id" in fields:
        set_asset(record, "cover_asset_id", "cover_url", asset_or_error(db, data.cover_asset_id))
    if data.product_ids is not None:
        previous = _product_ids(db, kind, record.id)
        if previous != data.product_ids:
            _set_products(db, kind, record.id, data.product_ids)
            extra_changes["product_ids"] = [previous, data.product_ids]
    if kind is LOOKBOOKS and data.blocks is not None:
        _replace_blocks(db, record.id, data.blocks)
        extra_changes["blocks"] = [None, len(data.blocks)]
    changes = audit.diff(before, audit.snapshot(record, CONTENT_FIELDS)) | extra_changes
    if changes:
        audit.record(db, user, "update", kind.entity, record.id, changes)
    db.commit()
    return _out(db, kind, record)


def archive_record(db: Session, kind: _Kind, record_id: uuid.UUID, user: AdminUser):
    record = get_or_404(db, kind.model, record_id, kind.missing)
    if record.status != STATUS_ARCHIVED:
        audit.record(
            db, user, "archive", kind.entity, record.id, {"status": [record.status, STATUS_ARCHIVED]}
        )
        record.status = STATUS_ARCHIVED
    db.commit()
    return _out(db, kind, record)


# --- Settings --------------------------------------------------------------------------

_TEXT_SETTINGS = ("hero_headline", "hero_subhead", "intro", "boutique_body", "contact_body")
_AUDITED_SETTINGS = (
    "whatsapp_number",
    "whatsapp_premium_number",
    "hero_asset_id",
    "hero_mobile_asset_id",
    "hero_gallery",
    *_TEXT_SETTINGS,
)


def _real_settings(db: Session) -> SiteSettings | None:
    return db.scalar(select(SiteSettings).where(SiteSettings.is_demo.is_(False)))


def _settings_out(row: SiteSettings | None) -> schemas.AdminSettings:
    return schemas.AdminSettings(
        whatsapp_number=row.whatsapp_number if row else None,
        whatsapp_premium_number=row.whatsapp_premium_number if row else None,
        hero_asset_id=row.hero_asset_id if row else None,
        hero_image_url=row.hero_image_url if row else None,
        hero_mobile_asset_id=row.hero_mobile_asset_id if row else None,
        hero_mobile_image_url=row.hero_mobile_image_url if row else None,
        hero_gallery=[schemas.HeroSlide(**slide) for slide in (row.hero_gallery or [])] if row else [],
        hero_headline=row.hero_headline if row else None,
        hero_subhead=row.hero_subhead if row else None,
        intro=row.intro if row else None,
        boutique_body=row.boutique_body if row else None,
        contact_body=row.contact_body if row else None,
    )


def _hero_gallery(db: Session, asset_ids: list[uuid.UUID]) -> list[dict[str, str]]:
    """Ordered, without repeats. Stores the URL next to the id, like the other asset fields."""
    slides: list[dict[str, str]] = []
    for asset_id in dict.fromkeys(asset_ids):
        asset = asset_or_error(db, asset_id)
        assert asset is not None
        slides.append({"asset_id": str(asset.id), "url": asset.url})
    return slides


def get_settings(db: Session) -> schemas.AdminSettings:
    return _settings_out(_real_settings(db))


def update_settings(db: Session, data: schemas.SettingsPatch, user: AdminUser) -> schemas.AdminSettings:
    row = _real_settings(db)
    if row is None:
        row = SiteSettings(is_demo=False)
        db.add(row)
        db.flush()
    before = audit.snapshot(row, _AUDITED_SETTINGS)
    fields = data.model_fields_set
    for field in ("whatsapp_number", "whatsapp_premium_number"):
        if field in fields:
            number = getattr(data, field) or None
            if number is not None and normalize_number(number) is None:
                raise ApiError(422, "invalid_whatsapp_number", "El número debe tener formato E.164")
            setattr(row, field, number)
    if "hero_asset_id" in fields:
        set_asset(row, "hero_asset_id", "hero_image_url", asset_or_error(db, data.hero_asset_id))
    if "hero_mobile_asset_id" in fields:
        set_asset(
            row,
            "hero_mobile_asset_id",
            "hero_mobile_image_url",
            asset_or_error(db, data.hero_mobile_asset_id),
        )
    if "hero_gallery_asset_ids" in fields:
        row.hero_gallery = _hero_gallery(db, data.hero_gallery_asset_ids or [])
    for field in _TEXT_SETTINGS:
        if field in fields:
            setattr(row, field, getattr(data, field))
    changes = audit.diff(before, audit.snapshot(row, _AUDITED_SETTINGS))
    if changes:
        audit.record(db, user, "update", "site_settings", row.id, changes)
    db.commit()
    return _settings_out(row)


# --- Dashboard and audit ---------------------------------------------------------------


def dashboard(db: Session, settings: Settings) -> schemas.Dashboard:
    by_status = dict(
        db.execute(select(Product.status, func.count()).group_by(Product.status)).all()
    )
    brands = dict(
        db.execute(
            select(Brand.status, func.count())
            .where(Brand.kind == KIND_BRAND)
            .group_by(Brand.status)
        )
        .all()
    )
    without_photo = db.scalar(
        select(func.count())
        .select_from(Product)
        .where(~exists().where(ProductMedia.product_id == Product.id))
    )
    clicks = db.scalar(
        select(func.count())
        .select_from(CatalogEvent)
        .where(
            CatalogEvent.type == "whatsapp_click",
            CatalogEvent.occurred_at >= utcnow() - timedelta(days=30),
        )
    )
    return schemas.Dashboard(
        products=schemas.DashboardProducts(
            draft=by_status.get(STATUS_DRAFT, 0),
            published=by_status.get(STATUS_PUBLISHED, 0),
            archived=by_status.get(STATUS_ARCHIVED, 0),
            without_photo=without_photo or 0,
        ),
        brands=schemas.DashboardBrands(
            draft=brands.get(STATUS_DRAFT, 0), published=brands.get(STATUS_PUBLISHED, 0)
        ),
        consult_clicks_30d=clicks or 0,
        whatsapp_configured=effective_whatsapp_digits(db, settings) is not None,
    )


def list_audit(
    db: Session, *, entity: str | None, entity_id: str | None, page: int, page_size: int
) -> schemas.Page[schemas.AuditEntry]:
    stmt = select(AuditLog)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    rows, total = paginate(db, stmt.order_by(AuditLog.created_at.desc(), AuditLog.id), page, page_size)
    return schemas.Page[schemas.AuditEntry](
        items=[
            schemas.AuditEntry(
                id=row.id,
                user_id=row.user_id,
                user_email=row.user_email,
                operation=row.operation,
                entity=row.entity,
                entity_id=row.entity_id,
                changes=row.changes,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
