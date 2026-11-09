"""Audit trail. Entries are added to the caller's transaction, so they commit with the change."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AdminUser, AuditLog

_SECRET_PARTS = ("password", "hash", "token", "secret", "cookie")


def _json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _is_secret(field: str) -> bool:
    lowered = field.casefold()
    return any(part in lowered for part in _SECRET_PARTS)


def snapshot(record: Any, fields: tuple[str, ...] | list[str]) -> dict[str, Any]:
    return {field: _json_safe(getattr(record, field)) for field in fields}


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    """{field: [before, after]} for what changed."""
    return {
        field: [before.get(field), after.get(field)]
        for field in after
        if before.get(field) != after.get(field)
    }


def record(
    db: Session,
    user: AdminUser | None,
    operation: str,
    entity: str,
    entity_id: Any = None,
    changes: dict[str, Any] | None = None,
) -> None:
    safe = {
        field: _json_safe(value) for field, value in (changes or {}).items() if not _is_secret(field)
    }
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            operation=operation,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            changes=safe,
        )
    )
