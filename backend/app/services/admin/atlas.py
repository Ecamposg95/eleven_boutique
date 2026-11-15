"""Pantalla Atlas ONE del panel: estado, sincronización a pedido y mapas de casas y categorías."""

import logging
import threading
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.config import Settings
from app.models import (
    KIND_BRAND,
    STATUS_DRAFT,
    AdminUser,
    AtlasBrandMap,
    AtlasCategoryMap,
    AtlasSyncRun,
    AtlasSyncState,
    Brand,
    Category,
    Product,
)
from app.schemas import admin as schemas
from app.services.admin import audit
from app.services.admin.common import invalid_reference, not_found
from app.services.atlas.client import AtlasClient
from app.services.atlas.links import PLACEHOLDER_BRAND
from app.services.atlas.sync import request_full_load, run_sync, with_lock
from app.services.brand_match import is_no_brand_classification

logger = logging.getLogger(__name__)

MAX_DRAFTS = 200


def is_configured(settings: Settings) -> bool:
    return bool(
        settings.atlas_sync_enabled
        and settings.atlas_api_url.strip()
        and settings.atlas_api_key.strip()
    )


def status(db: Session, settings: Settings) -> schemas.AtlasStatus:
    run = db.scalar(select(AtlasSyncRun).order_by(AtlasSyncRun.started_at.desc()).limit(1))
    state = db.get(AtlasSyncState, 1)
    drafts = db.execute(
        select(Product.id, Product.name, Product.atlas_missing)
        .where(Product.external_inventory_id.is_not(None), Product.status == STATUS_DRAFT)
        .order_by(Product.name, Product.id)
        .limit(MAX_DRAFTS)
    ).all()
    return schemas.AtlasStatus(
        enabled=is_configured(settings),
        last_run=(
            schemas.AtlasRun(
                kind=run.kind,
                status=run.status,
                started_at=run.started_at,
                finished_at=run.finished_at,
                counts=run.counts or {},
                error=run.error if run.status == "error" else None,
                note=run.error if run.status == "ok" else None,
            )
            if run
            else None
        ),
        last_ok_at=state.last_ok_at if state else None,
        last_error=state.last_error if state else None,
        drafts=[schemas.AtlasDraft(id=row.id, name=row.name, atlas_missing=row.atlas_missing) for row in drafts],
    )


def lock_busy(session_factory: Callable[[], Session]) -> bool:
    """Sondea el candado de sincronización y lo suelta enseguida."""
    with session_factory() as db, with_lock(db) as acquired:
        return not acquired


# Guardia de este proceso: el sondeo del candado se suelta antes de que el hilo lo tome, y dos
# clics seguidos pasarían ambos. El candado de la base sigue cubriendo al cron de otro proceso.
_launching = threading.Lock()


def _run_manual(settings: Settings, session_factory: Callable[[], Session]) -> None:
    try:
        _run_manual_inner(settings, session_factory)
    finally:
        _launching.release()


def _run_manual_inner(settings: Settings, session_factory: Callable[[], Session]) -> None:
    client = AtlasClient(settings.atlas_api_url.strip(), settings.atlas_api_key.strip())
    try:
        run_sync(session_factory, client, kind="manual")
    except Exception:
        logger.exception("Falló la sincronización manual con Atlas ONE")
    finally:
        client.close()


def launch_sync(settings: Settings, session_factory: Callable[[], Session]) -> None:
    """Arranca la corrida en un hilo propio con su propia sesión; no espera el resultado."""
    threading.Thread(
        target=_run_manual, args=(settings, session_factory), name="atlas-sync-manual", daemon=True
    ).start()


def start_sync(settings: Settings, session_factory: Callable[[], Session]) -> None:
    if not is_configured(settings):
        raise ApiError(409, "atlas_not_configured", "La sincronización con Atlas ONE no está configurada")
    if not _launching.acquire(blocking=False):
        raise ApiError(409, "sync_running", "Ya hay una sincronización en curso")
    try:
        if lock_busy(session_factory):
            raise ApiError(409, "sync_running", "Ya hay una sincronización en curso")
        launch_sync(settings, session_factory)
    except BaseException:
        _launching.release()
        raise


def list_brand_map(db: Session) -> list[schemas.AtlasBrandMapOut]:
    rows = db.scalars(select(AtlasBrandMap).order_by(AtlasBrandMap.atlas_name, AtlasBrandMap.id))
    return [schemas.AtlasBrandMapOut.model_validate(row, from_attributes=True) for row in rows]


def patch_brand_map(
    db: Session, data: schemas.AtlasBrandMapPatch, user: AdminUser
) -> schemas.AtlasBrandMapOut:
    row = db.scalar(select(AtlasBrandMap).where(AtlasBrandMap.atlas_brand_id == data.atlas_brand_id))
    if row is None:
        raise not_found("Casa de Atlas ONE no encontrada")
    brand = db.get(Brand, data.brand_id)
    if brand is None:
        raise invalid_reference("La marca indicada no existe")
    if brand.name == PLACEHOLDER_BRAND:
        raise invalid_reference("Casa interna de sincronización")
    if brand.kind != KIND_BRAND and not is_no_brand_classification(brand):
        raise invalid_reference("Solo se puede enlazar a una marca o a «Sin marca», no a otra clasificación")
    if row.brand_id != data.brand_id:
        audit.record(
            db, user, "update", "atlas_brand_map", row.id, {"brand_id": [row.brand_id, data.brand_id]}
        )
        row.brand_id = data.brand_id
        request_full_load(db)
        db.commit()
    return schemas.AtlasBrandMapOut.model_validate(row, from_attributes=True)


def list_category_map(db: Session) -> list[schemas.AtlasCategoryMapOut]:
    rows = db.scalars(select(AtlasCategoryMap).order_by(AtlasCategoryMap.atlas_name, AtlasCategoryMap.id))
    return [schemas.AtlasCategoryMapOut.model_validate(row, from_attributes=True) for row in rows]


def patch_category_map(
    db: Session, data: schemas.AtlasCategoryMapPatch, user: AdminUser
) -> schemas.AtlasCategoryMapOut:
    row = db.scalar(
        select(AtlasCategoryMap).where(AtlasCategoryMap.atlas_department_id == data.atlas_department_id)
    )
    if row is None:
        raise not_found("Departamento de Atlas ONE no encontrado")
    if data.category_id is not None and db.get(Category, data.category_id) is None:
        raise invalid_reference("La categoría indicada no existe")
    if row.category_id != data.category_id:
        audit.record(
            db,
            user,
            "update",
            "atlas_category_map",
            row.id,
            {"category_id": [row.category_id, data.category_id]},
        )
        row.category_id = data.category_id
        request_full_load(db)
        db.commit()
    return schemas.AtlasCategoryMapOut.model_validate(row, from_attributes=True)
