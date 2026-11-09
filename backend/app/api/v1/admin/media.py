import uuid

from fastapi import APIRouter, Request, Response
from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.api.errors import ApiError
from app.api.v1.admin.deps import AdminPageSize, CurrentUser
from app.api.v1.deps import DbDep, PageParam, SearchParam, SettingsDep
from app.schemas import admin as schemas
from app.services.admin import media
from app.services.admin.images import MAX_FILE_BYTES

router = APIRouter(prefix="/media")

MAX_FILES = 50
MULTIPART_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "files": {"type": "array", "items": {"type": "string", "format": "binary"}}
                    },
                }
            }
        },
    }
}


@router.get("", response_model=schemas.Page[schemas.AdminMedia])
def list_media(
    db: DbDep,
    q: SearchParam = None,
    unused: bool | None = None,
    page: PageParam = 1,
    page_size: AdminPageSize = 24,
):
    return media.list_media(db, q=q, unused=unused, page=page, page_size=page_size)


@router.post(
    "", response_model=schemas.MediaUploadOut, status_code=201, openapi_extra=MULTIPART_BODY
)
async def upload_media(request: Request, db: DbDep, settings: SettingsDep, user: CurrentUser):
    # The form is parsed here rather than declared as a parameter: FastAPI reads declared bodies
    # before running dependencies, which would spool an anonymous upload to disk before the 401.
    async with request.form(max_files=MAX_FILES, max_fields=10) as form:
        uploads = [value for _, value in form.multi_items() if isinstance(value, UploadFile)]
        if not uploads:
            raise ApiError(422, "no_files", "No se recibió ningún archivo")
        files = []
        for upload in uploads:
            # One byte past the limit is enough to know: the pipeline rejects by length.
            files.append((upload.filename, await upload.read(MAX_FILE_BYTES + 1)))
    return await run_in_threadpool(media.upload_many, db, settings, files, user)


@router.post("/bulk-match", response_model=schemas.BulkMatchOut)
def bulk_match(body: schemas.BulkMatchIn, db: DbDep):
    return media.bulk_match(db, body)


@router.post("/bulk-assign", response_model=schemas.BulkAssignOut)
def bulk_assign(body: schemas.BulkAssignIn, db: DbDep, user: CurrentUser):
    return media.bulk_assign(db, body, user)


@router.patch("/{asset_id}", response_model=schemas.AdminMedia)
def update_media(asset_id: uuid.UUID, body: schemas.MediaPatch, db: DbDep, user: CurrentUser):
    return media.update_alt(db, asset_id, body, user)


@router.delete("/{asset_id}", status_code=204, response_class=Response)
def delete_media(asset_id: uuid.UUID, db: DbDep, settings: SettingsDep, user: CurrentUser) -> None:
    media.delete_asset(db, settings, asset_id, user)
