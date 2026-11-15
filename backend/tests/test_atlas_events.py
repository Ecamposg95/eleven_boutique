import json
from datetime import UTC, datetime, timedelta

import httpx

from app.models import KIND_CLASSIFICATION, CatalogEvent
from app.services.atlas.client import AtlasClient
from app.services.atlas.events import forward_events
from tests.factories import make_brand, make_category, make_product

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def make(handler):
    return AtlasClient("https://atlas.test", "k", transport=httpx.MockTransport(handler), sleep=lambda s: None)


def recorder(status=201):
    sent = []

    def handler(request):
        sent.append((json.loads(request.content), request.headers["Idempotency-Key"]))
        return httpx.Response(status, json={})

    return sent, handler


def event(db, product, type="whatsapp_click", age=timedelta(hours=1)):
    e = CatalogEvent(type=type, product_id=product.id if product else None, occurred_at=NOW - age)
    db.add(e)
    db.commit()
    return e


def piece(db, brand_name="Hermès", ext="inv-1", **brand):
    brand = make_brand(db, brand_name, **brand)
    return make_product(db, brand, make_category(db, f"Cat {ext}"), "Bolso", slug=f"p-{ext}", external_inventory_id=ext)


def test_premium_click_goes_to_boutique(db):
    e = event(db, piece(db, is_premium=True))
    sent, handler = recorder()
    assert forward_events(db, make(handler), NOW) == {"enviados": 1, "descartados": 0, "error": 0}
    [(payload, key)] = sent
    assert payload == {
        "source": "web_whatsapp_click",
        "product_ids": ["inv-1"],
        "line": "boutique",
        "occurred_at": "2026-11-14T11:00:00Z",
    }
    assert key == str(e.id)
    db.refresh(e)
    assert e.forwarded_at is not None


def test_non_premium_and_unbranded_go_general_and_selection_source(db):
    event(db, piece(db, "Prada", "a"), type="selection")
    event(db, piece(db, "Sin marca", "b", is_premium=True, kind=KIND_CLASSIFICATION))
    sent, handler = recorder()
    forward_events(db, make(handler), NOW)
    assert {p["product_ids"][0]: (p["line"], p["source"]) for p, _ in sent} == {
        "a": ("general", "web_selection"),
        "b": ("general", "web_whatsapp_click"),
    }


def test_old_event_without_external_id_or_product_are_discarded_unsent(db):
    old = event(db, piece(db, "Prada", "a"), age=timedelta(days=7))
    local = event(db, make_product(db, make_brand(db, "Gucci"), make_category(db, "C2"), "L", slug="l"))
    orphan = event(db, None)
    sent, handler = recorder()
    assert forward_events(db, make(handler), NOW) == {"enviados": 0, "descartados": 3, "error": 0}
    assert sent == []
    for e in (old, local, orphan):
        db.refresh(e)
        assert e.forwarded_at is not None


def test_forbidden_leaves_events_unmarked_and_does_not_raise(db):
    e = event(db, piece(db))
    sent, handler = recorder(403)
    assert forward_events(db, make(handler), NOW) == {"enviados": 0, "descartados": 0, "error": 1}
    db.refresh(e)
    assert e.forwarded_at is None


def test_server_error_stops_run_but_keeps_earlier_ones(db):
    first = event(db, piece(db, "Prada", "a"), age=timedelta(hours=3))
    second = event(db, piece(db, "Gucci", "b"), age=timedelta(hours=2))
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(201 if len(calls) == 1 else 400, json={})

    assert forward_events(db, make(handler), NOW) == {"enviados": 1, "descartados": 0, "error": 1}
    db.refresh(first), db.refresh(second)
    assert first.forwarded_at is not None and second.forwarded_at is None


def test_422_discards_the_event(db):
    e = event(db, piece(db))
    sent, handler = recorder(422)
    assert forward_events(db, make(handler), NOW) == {"enviados": 0, "descartados": 1, "error": 0}
    db.refresh(e)
    assert e.forwarded_at is not None


def test_repeat_does_not_resend(db):
    event(db, piece(db))
    sent, handler = recorder()
    client = make(handler)
    forward_events(db, client, NOW)
    assert forward_events(db, client, NOW) == {"enviados": 0, "descartados": 0, "error": 0}
    assert len(sent) == 1
