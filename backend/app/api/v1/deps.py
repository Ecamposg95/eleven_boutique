from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config import Settings


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SettingsDep = Annotated[Settings, Depends(_settings)]
DbDep = Annotated[Session, Depends(_db)]
PageParam = Annotated[int, Query(ge=1)]
PageSizeParam = Annotated[int, Query(ge=1, le=60)]
SearchParam = Annotated[str | None, Query(max_length=200)]


def found[T](value: T | None, message: str) -> T:
    if value is None:
        raise HTTPException(status_code=404, detail=message)
    return value
