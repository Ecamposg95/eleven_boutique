"""Admin API. Routes hang from `protected` unless they are the login itself, so a new route
requires a session by default; tests/test_admin_security.py walks the router to confirm it."""

from fastapi import APIRouter, Depends

from app.api.v1.admin import auth, catalog, content, imports, media
from app.api.v1.admin.deps import check_origin, current_user

protected = APIRouter(dependencies=[Depends(current_user)])
protected.include_router(auth.protected)
protected.include_router(catalog.router)
protected.include_router(media.router)
protected.include_router(content.router)
protected.include_router(imports.router)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(check_origin)])
router.include_router(auth.public)
router.include_router(protected)
