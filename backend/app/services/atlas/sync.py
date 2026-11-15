"""Corrida de sincronización con Atlas ONE: casas, categorías, piezas, disponibilidad y eventos.

Orden (§3.3 del diseño): marcas y departamentos en su propia transacción; una transacción por
página de piezas; disponibilidad; reenvío de eventos; al final el estado y la bitácora. Una falla
marca la corrida como `error`, conserva las páginas ya confirmadas (son idempotentes) y no avanza
`products_since` / `availability_since`.
"""

import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, delete, text
from sqlalchemy.orm import Session

from app.models import AtlasSyncRun, AtlasSyncState
from app.models.base import utcnow
from app.services.atlas.client import AtlasClient, AtlasError
from app.services.atlas.events import forward_events
from app.services.atlas.links import Resolver, sync_brands, sync_departments
from app.services.atlas.sync_products import (
    ProductSync,
    apply_availability,
    archive_missing,
    parse_time,
)

logger = logging.getLogger(__name__)

OVERLAP = timedelta(minutes=10)
RUN_RETENTION = timedelta(days=30)
NIGHTLY_TZ = ZoneInfo("America/Mexico_City")
NIGHTLY_AT = time(3, 0)
LOCK_KEY = "atlas_sync"
MAX_ERROR = 500

SyncKind = Literal["incremental", "full", "manual"]

# SQLite (pruebas y local): candado de proceso. En Postgres, advisory lock de sesión.
_process_lock = threading.Lock()


@contextmanager
def with_lock(db: Session) -> Iterator[bool]:
    """True si obtuvo el candado; lo libera al salir, pase lo que pase."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        acquired = _process_lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                _process_lock.release()
        return

    # Conexión propia: la sesión devuelve la suya al pool en cada commit y el candado es por conexión.
    engine = bind.engine if isinstance(bind, Connection) else bind
    conn = engine.connect()
    try:
        acquired = bool(
            conn.scalar(text("SELECT pg_try_advisory_lock(hashtext(:key))"), {"key": LOCK_KEY})
        )
        conn.commit()
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    conn.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": LOCK_KEY})
                    conn.commit()
                except Exception:
                    # Sin poder liberar, la conexión se descarta: cerrar la sesión de Postgres suelta el candado.
                    logger.exception("No se pudo liberar el candado de sincronización")
                    conn.invalidate()
    finally:
        conn.close()


def is_nightly_due(state: AtlasSyncState | None, now: datetime) -> bool:
    """Primera corrida después de las 03:00 (Ciudad de México) de un día sin carga completa desde esa hora."""
    local = now.astimezone(NIGHTLY_TZ)
    if local.time() < NIGHTLY_AT:
        return False
    cutoff = datetime.combine(local.date(), NIGHTLY_AT, tzinfo=NIGHTLY_TZ)
    return state is None or state.last_full_at is None or state.last_full_at < cutoff


def _describe(exc: Exception) -> str:
    """Texto corto para la bitácora. AtlasError ya viene sin la llave."""
    if isinstance(exc, AtlasError):
        message = str(exc)
    else:
        message = f"{type(exc).__name__}: {exc}"
    return message[:MAX_ERROR]


def _counts() -> dict[str, int]:
    return {
        "creadas": 0,
        "actualizadas": 0,
        "bajas": 0,
        "borradores": 0,
        "disponibilidad": 0,
        "casas_borrador": 0,
        "departamentos_nuevos": 0,
        "eventos_enviados": 0,
        "eventos_descartados": 0,
        "eventos_error": 0,
    }


def _all_items(client: AtlasClient, path: str) -> list[dict]:
    items: list[dict] = []
    for page, _ in client.iter_pages(path, None):
        items.extend(page)
    return items


def _execute(db: Session, client: AtlasClient, kind: SyncKind, now: Callable[[], datetime]) -> AtlasSyncRun:
    started = now()
    counts = _counts()
    state = db.get(AtlasSyncState, 1)
    full = kind == "full" or state is None or state.products_since is None or is_nightly_due(state, started)
    products_since = None if full else state.products_since - OVERLAP
    availability_since = (
        state.availability_since - OVERLAP if state is not None and state.availability_since else None
    )
    products_time: str | None = None
    availability_time: str | None = None
    error: str | None = None
    try:
        brands = sync_brands(db, _all_items(client, "/brands"))
        departments = sync_departments(db, _all_items(client, "/departments"))
        counts["casas_borrador"] = brands["creadas_borrador"]
        counts["departamentos_nuevos"] = departments["nuevas"]
        db.commit()

        products = ProductSync(db, Resolver(db), counts, started)
        seen: set[str] = set()
        for items, server_time in client.iter_pages("/products", products_since):
            seen |= products.apply_page(items)
            db.commit()
            products_time = server_time
        if full:
            # Solo se llega aquí si se recorrieron todas las páginas sin error.
            counts["bajas"] += archive_missing(db, seen)
            db.commit()

        for items, server_time in client.iter_pages("/availability", availability_since):
            counts["disponibilidad"] += apply_availability(db, items)
            db.commit()
            availability_time = server_time

        events = forward_events(db, client, now())
        counts["eventos_enviados"] = events["enviados"]
        counts["eventos_descartados"] = events["descartados"]
        counts["eventos_error"] = events["error"]
    except Exception as exc:
        db.rollback()
        error = _describe(exc)
        if not isinstance(exc, AtlasError):
            logger.exception("Falló la sincronización con Atlas ONE")

    state = db.get(AtlasSyncState, 1)
    if state is None:
        state = AtlasSyncState(id=1)
        db.add(state)
    state.last_run_at = started
    if error is None:
        state.products_since = parse_time(products_time)
        state.availability_since = parse_time(availability_time)
        if full:
            state.last_full_at = started
        state.last_ok_at = started
        state.last_error = None
    else:
        state.last_error = error
    run = AtlasSyncRun(
        started_at=started,
        finished_at=now(),
        kind="full" if full and kind == "incremental" else kind,
        status="ok" if error is None else "error",
        counts=counts,
        error=error,
    )
    db.add(run)
    db.execute(delete(AtlasSyncRun).where(AtlasSyncRun.started_at < started - RUN_RETENTION))
    db.commit()
    return run


def run_sync(
    db_factory: Callable[[], Session],
    client: AtlasClient,
    *,
    kind: SyncKind = "incremental",
    now: Callable[[], datetime] = utcnow,
) -> AtlasSyncRun | None:
    """Una corrida completa. None si otra corrida tiene el candado (no escribe nada)."""
    with db_factory() as db, with_lock(db) as acquired:
        if not acquired:
            return None
        return _execute(db, client, kind, now)
