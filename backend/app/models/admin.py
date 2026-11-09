import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Uuid,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import UTCDateTime
from app.models.base import Base, IdMixin, TimestampMixin, in_values, utcnow

ROLE_SUPERADMIN = "superadmin"
ROLE_ADMIN = "admin"
ROLE_EDITOR = "editor"
ROLES = (ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_EDITOR)

IMPORT_PREVIEW = "preview"
IMPORT_COMPLETED = "completed"
IMPORT_EXPIRED = "expired"
IMPORT_STATUSES = (IMPORT_PREVIEW, IMPORT_COMPLETED, IMPORT_EXPIRED)


class AdminUser(IdMixin, TimestampMixin, Base):
    __tablename__ = "admin_users"
    __table_args__ = (CheckConstraint(in_values("role", ROLES), name="role"),)

    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class AdminSession(IdMixin, Base):
    """Only the token's hash is stored: a database leak does not expose live sessions."""

    __tablename__ = "admin_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    user: Mapped[AdminUser] = relationship()


class LoginAttempt(IdMixin, Base):
    """Keyed by a hash of the email: people sometimes type a password in the email field."""

    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_key_time", "email_key", "attempted_at"),)

    email_key: Mapped[str] = mapped_column(String(64))
    succeeded: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), index=True
    )
    # Snapshot, so the entry stays readable if the user goes away.
    user_email: Mapped[str | None] = mapped_column(String(254))
    operation: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    # {field: [before, after]}, without secrets or hashes.
    changes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)


class ImportRun(IdMixin, TimestampMixin, Base):
    """Never holds the uploaded file. `payload` is only the allow-listed columns of each row
    and is cleared on commit or expiry."""

    __tablename__ = "import_runs"
    __table_args__ = (CheckConstraint(in_values("status", IMPORT_STATUSES), name="status"),)

    status: Mapped[str] = mapped_column(String(16), default=IMPORT_PREVIEW, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    update_existing: Mapped[bool | None] = mapped_column(Boolean)
    # none_as_null: otherwise None is stored as the JSON value `null`, not as SQL NULL.
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True))
    # {created, updated, skipped, errors}, set on commit.
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True))
    # [{row, sku, result, message}], set on commit; feeds the CSV report.
    results: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON(none_as_null=True))
