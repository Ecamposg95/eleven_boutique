"""Reenvío a Atlas ONE de los clics de WhatsApp y selecciones anónimos."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KIND_CLASSIFICATION, CatalogEvent
from app.services.atlas.client import AtlasClient, AtlasError, AtlasForbidden, fmt_since

BATCH = 100
# Atlas rechaza (422) fechas de hace más de 7 días; se descarta con 1 h de margen.
MAX_AGE = timedelta(days=7) - timedelta(hours=1)
SOURCES = {"whatsapp_click": "web_whatsapp_click", "selection": "web_selection"}


def _payload(event: CatalogEvent, now: datetime) -> dict | None:
    """None si el evento no se puede enviar (se descarta)."""
    product = event.product
    if product is None or not product.external_inventory_id:
        return None
    if now - event.occurred_at >= MAX_AGE:
        return None
    brand = product.brand
    boutique = brand.is_premium and brand.kind != KIND_CLASSIFICATION
    return {
        "source": SOURCES[event.type],
        "product_ids": [product.external_inventory_id],
        "line": "boutique" if boutique else "general",
        "occurred_at": fmt_since(event.occurred_at),
    }


def forward_events(db: Session, client: AtlasClient, now: datetime) -> dict[str, int]:
    result = {"enviados": 0, "descartados": 0, "error": 0}
    while True:
        batch = db.scalars(
            select(CatalogEvent)
            .where(CatalogEvent.type.in_(SOURCES), CatalogEvent.forwarded_at.is_(None))
            .order_by(CatalogEvent.occurred_at)
            .limit(BATCH)
        ).all()
        if not batch:
            return result
        stop = False
        for event in batch:
            payload = _payload(event, now)
            if payload is None:
                result["descartados"] += 1
            else:
                try:
                    client.post_lead(payload, str(event.id))
                except AtlasForbidden:
                    result["error"] += 1
                    stop = True
                    break
                except AtlasError as exc:
                    # 4xx permanente (salvo auth/límite): el evento envenena la cola, se descarta.
                    if exc.status is not None and 400 <= exc.status < 500 and exc.status not in (401, 403, 429):
                        result["descartados"] += 1
                    else:
                        result["error"] += 1
                        stop = True
                        break
                else:
                    result["enviados"] += 1
            event.forwarded_at = now
        db.commit()
        if stop:
            return result
