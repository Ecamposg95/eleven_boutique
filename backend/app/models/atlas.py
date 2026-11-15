import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import UTCDateTime
from app.models.base import Base, IdMixin, TimestampMixin, utcnow


class AtlasSyncState(Base):
    """Fila única (id=1): hasta dónde llegó la última corrida buena contra Atlas ONE."""

    __tablename__ = "atlas_sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    products_since: Mapped[datetime | None] = mapped_column(UTCDateTime)
    availability_since: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_full_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_ok_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    # Texto corto, sin secretos.
    last_error: Mapped[str | None] = mapped_column(Text)


class AtlasSyncRun(Base):
    __tablename__ = "atlas_sync_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    kind: Mapped[str] = mapped_column(String(16))  # incremental | full | manual
    status: Mapped[str] = mapped_column(String(16))  # ok | error
    counts: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    error: Mapped[str | None] = mapped_column(Text)


class AtlasBrandMap(IdMixin, TimestampMixin, Base):
    __tablename__ = "atlas_brand_map"

    atlas_brand_id: Mapped[str] = mapped_column(String(100), unique=True)
    atlas_name: Mapped[str] = mapped_column(String(300))
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"), index=True
    )


class AtlasCategoryMap(IdMixin, TimestampMixin, Base):
    __tablename__ = "atlas_category_map"

    atlas_department_id: Mapped[str] = mapped_column(String(100), unique=True)
    atlas_name: Mapped[str] = mapped_column(String(300))
    atlas_parent_id: Mapped[str | None] = mapped_column(String(100))
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
