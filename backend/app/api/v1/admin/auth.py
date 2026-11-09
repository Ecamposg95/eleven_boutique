from fastapi import APIRouter, Response

from app.api.v1.admin.deps import CurrentUser, SessionDep
from app.api.v1.deps import DbDep, SettingsDep
from app.config import Settings
from app.models import AdminUser
from app.schemas import admin as schemas
from app.services.admin import auth as auth_service

public = APIRouter(prefix="/auth")
protected = APIRouter(prefix="/auth")


def _me(user: AdminUser) -> schemas.Me:
    return schemas.Me(id=user.id, email=user.email, role=user.role)


def _cookie_options(settings: Settings) -> dict:
    return {
        "key": auth_service.COOKIE_NAME,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.secure_cookies,
        "path": "/",
    }


@public.post("/login", response_model=schemas.Me)
def login(body: schemas.LoginIn, response: Response, db: DbDep, settings: SettingsDep):
    user, token = auth_service.login(db, body.email, body.password)
    response.set_cookie(
        value=token,
        max_age=int(auth_service.SESSION_TTL.total_seconds()),
        **_cookie_options(settings),
    )
    return _me(user)


@protected.post("/logout", status_code=204, response_class=Response)
def logout(session: SessionDep, response: Response, db: DbDep, settings: SettingsDep) -> None:
    auth_service.logout(db, session)
    response.delete_cookie(**_cookie_options(settings))


@protected.get("/me", response_model=schemas.Me)
def me(user: CurrentUser):
    return _me(user)
