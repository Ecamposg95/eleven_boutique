import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.api.errors import ApiError
from app.api.v1.admin.deps import AdminOnly, require_admin
from app.api.v1.deps import DbDep
from app.schemas import admin as schemas
from app.services.admin import catalog_import

router = APIRouter(prefix="/imports", dependencies=[Depends(require_admin)])

MULTIPART_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {"file": {"type": "string", "format": "binary"}},
                }
            }
        },
    }
}


def _csv_response(body: str, filename: str) -> Response:
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/products/preview", response_model=schemas.ImportPreview, openapi_extra=MULTIPART_BODY
)
async def preview(request: Request, db: DbDep, user: AdminOnly):
    # Parsed here so the role check runs before the upload is read. See upload_media.
    async with request.form(max_files=1, max_fields=5) as form:
        upload = next(
            (value for _, value in form.multi_items() if isinstance(value, UploadFile)), None
        )
        if upload is None:
            raise ApiError(422, "no_files", "No se recibió ningún archivo")
        filename = upload.filename
        data = await upload.read(catalog_import.MAX_FILE_BYTES + 1)
    return await run_in_threadpool(catalog_import.create_preview, db, filename, data, user)


@router.post("/products", response_model=schemas.ImportResult)
def commit(body: schemas.ImportCommit, db: DbDep, user: AdminOnly):
    return catalog_import.commit_import(db, body.preview_id, body.update_existing, user)


@router.get("/template")
def template() -> Response:
    return _csv_response(catalog_import.template_csv(), "plantilla_catalogo.csv")


@router.get("/{import_id}/report")
def report(import_id: uuid.UUID, db: DbDep) -> Response:
    return _csv_response(catalog_import.report_csv(db, import_id), f"importacion_{import_id}.csv")
