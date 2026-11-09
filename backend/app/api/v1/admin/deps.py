from typing import Annotated

from fastapi import Depends, Query, Request

from app.api.errors import ApiError
from app.api.v1.deps import DbDep, SettingsDep
from app.models import ROLE_ADMIN, ROLE_EDITOR, ROLE_SUPERADMIN, AdminSession, AdminUser
from app.services.admin import auth as auth_service

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_RANK = {ROLE_EDITOR: 1, ROLE_ADMIN: 2, ROLE_SUPERADMIN: 3}


def check_origin(request: Request, settings: SettingsDep) -> None:
    """A browser always sends Origin on these methods, so its absence is not a pass either."""
    if request.method in _SAFE_METHODS:
        return
    origin = request.headers.get("origin", "").strip().rstrip("/").casefold()
    if origin not in settings.admin_origins:
        raise ApiError(403, "invalid_origin", "Origen no permitido")


def current_session(request: Request, db: DbDep) -> AdminSession:
    session = auth_service.find_session(db, request.cookies.get(auth_service.COOKIE_NAME))
    if session is None:
        raise ApiError(401, "unauthorized", "Inicia sesión para continuar")
    return session


SessionDep = Annotated[AdminSession, Depends(current_session)]


def current_user(session: SessionDep) -> AdminUser:
    return session.user


CurrentUser = Annotated[AdminUser, Depends(current_user)]


def require_admin(user: CurrentUser) -> AdminUser:
    if _RANK[user.role] < _RANK[ROLE_ADMIN]:
        raise ApiError(403, "forbidden", "Tu rol no permite esta operación")
    return user


AdminOnly = Annotated[AdminUser, Depends(require_admin)]
AdminPageSize = Annotated[int, Query(ge=1, le=200)]
