"""Collections, lookbooks, settings, dashboard and audit."""

import uuid

from fastapi import APIRouter

from app.api.v1.admin.deps import AdminOnly, AdminPageSize, CurrentUser
from app.api.v1.deps import DbDep, PageParam, SearchParam, SettingsDep
from app.schemas import admin as schemas
from app.services.admin import content
from app.services.admin.content import COLLECTIONS, LOOKBOOKS

router = APIRouter()


@router.get("/dashboard", response_model=schemas.Dashboard)
def dashboard(db: DbDep, settings: SettingsDep):
    return content.dashboard(db, settings)


@router.get("/collections", response_model=schemas.Page[schemas.AdminCollection])
def list_collections(
    db: DbDep,
    q: SearchParam = None,
    status: schemas.Status | None = None,
    page: PageParam = 1,
    page_size: AdminPageSize = 24,
):
    return content.list_records(db, COLLECTIONS, q=q, status=status, page=page, page_size=page_size)


@router.post("/collections", response_model=schemas.AdminCollection, status_code=201)
def create_collection(body: schemas.CollectionCreate, db: DbDep, user: CurrentUser):
    return content.create_record(db, COLLECTIONS, body, user)


@router.get("/collections/{record_id}", response_model=schemas.AdminCollection)
def get_collection(record_id: uuid.UUID, db: DbDep):
    return content.get_record(db, COLLECTIONS, record_id)


@router.patch("/collections/{record_id}", response_model=schemas.AdminCollection)
def update_collection(
    record_id: uuid.UUID, body: schemas.CollectionPatch, db: DbDep, user: CurrentUser
):
    return content.update_record(db, COLLECTIONS, record_id, body, user)


@router.delete("/collections/{record_id}", response_model=schemas.AdminCollection)
def archive_collection(record_id: uuid.UUID, db: DbDep, user: CurrentUser):
    return content.archive_record(db, COLLECTIONS, record_id, user)


@router.get("/lookbooks", response_model=schemas.Page[schemas.AdminLookbook])
def list_lookbooks(
    db: DbDep,
    q: SearchParam = None,
    status: schemas.Status | None = None,
    page: PageParam = 1,
    page_size: AdminPageSize = 24,
):
    return content.list_records(db, LOOKBOOKS, q=q, status=status, page=page, page_size=page_size)


@router.post("/lookbooks", response_model=schemas.AdminLookbook, status_code=201)
def create_lookbook(body: schemas.LookbookCreate, db: DbDep, user: CurrentUser):
    return content.create_record(db, LOOKBOOKS, body, user)


@router.get("/lookbooks/{record_id}", response_model=schemas.AdminLookbook)
def get_lookbook(record_id: uuid.UUID, db: DbDep):
    return content.get_record(db, LOOKBOOKS, record_id)


@router.patch("/lookbooks/{record_id}", response_model=schemas.AdminLookbook)
def update_lookbook(record_id: uuid.UUID, body: schemas.LookbookPatch, db: DbDep, user: CurrentUser):
    return content.update_record(db, LOOKBOOKS, record_id, body, user)


@router.delete("/lookbooks/{record_id}", response_model=schemas.AdminLookbook)
def archive_lookbook(record_id: uuid.UUID, db: DbDep, user: CurrentUser):
    return content.archive_record(db, LOOKBOOKS, record_id, user)


@router.get("/settings", response_model=schemas.AdminSettings)
def get_settings(db: DbDep, _user: AdminOnly):
    return content.get_settings(db)


@router.patch("/settings", response_model=schemas.AdminSettings)
def update_settings(body: schemas.SettingsPatch, db: DbDep, user: AdminOnly):
    return content.update_settings(db, body, user)


@router.get("/audit", response_model=schemas.Page[schemas.AuditEntry])
def list_audit(
    db: DbDep,
    _user: AdminOnly,
    entity: str | None = None,
    entity_id: str | None = None,
    page: PageParam = 1,
    page_size: AdminPageSize = 24,
):
    return content.list_audit(db, entity=entity, entity_id=entity_id, page=page, page_size=page_size)
