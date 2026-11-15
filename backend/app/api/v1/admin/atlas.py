"""Pantalla Atlas ONE: estado de la sincronización, sincronizar ahora y mapas de casas y categorías.
Solo el rol admin; el editor no la ve."""

from fastapi import APIRouter, Depends, Request

from app.api.v1.admin.deps import AdminOnly, require_admin
from app.api.v1.deps import DbDep, SettingsDep
from app.schemas import admin as schemas
from app.services.admin import atlas as service

router = APIRouter(prefix="/atlas", dependencies=[Depends(require_admin)])


@router.get("/status", response_model=schemas.AtlasStatus)
def get_status(db: DbDep, settings: SettingsDep):
    return service.status(db, settings)


@router.post("/sync", response_model=schemas.AtlasSyncStarted, status_code=202)
def sync_now(settings: SettingsDep, request: Request):
    service.start_sync(settings, request.app.state.session_factory)
    return schemas.AtlasSyncStarted(started=True)


@router.get("/brand-map", response_model=list[schemas.AtlasBrandMapOut])
def get_brand_map(db: DbDep):
    return service.list_brand_map(db)


@router.patch("/brand-map", response_model=schemas.AtlasBrandMapOut)
def patch_brand_map(body: schemas.AtlasBrandMapPatch, db: DbDep, user: AdminOnly):
    return service.patch_brand_map(db, body, user)


@router.get("/category-map", response_model=list[schemas.AtlasCategoryMapOut])
def get_category_map(db: DbDep):
    return service.list_category_map(db)


@router.patch("/category-map", response_model=schemas.AtlasCategoryMapOut)
def patch_category_map(body: schemas.AtlasCategoryMapPatch, db: DbDep, user: AdminOnly):
    return service.patch_category_map(db, body, user)
