from sqlalchemy import func, inspect, select

from app.db import make_engine
from app.models import STATUS_DRAFT, CatalogEvent, Product
from tests.factories import make_brand, make_category, make_product


def event_count(db) -> int:
    return db.scalar(select(func.count()).select_from(CatalogEvent))


def test_whitelisted_event_is_stored_without_extra_data(db, public_client):
    product = make_product(db, make_brand(db), make_category(db), "Pieza")
    db.commit()
    response = public_client.post(
        "/api/v1/events",
        json={"type": "whatsapp_click", "product_slug": "pieza"},
        headers={"User-Agent": "agente-secreto"},
    )
    assert response.status_code == 204
    assert response.content == b""
    event = db.scalar(select(CatalogEvent))
    assert event.type == "whatsapp_click"
    assert event.product_id == product.id
    assert event.occurred_at is not None


def test_unknown_type_is_rejected(db, public_client):
    make_product(db, make_brand(db), make_category(db), "Pieza")
    db.commit()
    response = public_client.post(
        "/api/v1/events", json={"type": "page_view", "product_slug": "pieza"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert event_count(db) == 0


def test_unknown_slug_is_rejected(db, public_client):
    response = public_client.post(
        "/api/v1/events", json={"type": "whatsapp_click", "product_slug": "no-existe"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert event_count(db) == 0


def test_hidden_product_is_rejected(db, public_client):
    make_product(db, make_brand(db), make_category(db), "Oculta", status=STATUS_DRAFT)
    db.commit()
    response = public_client.post(
        "/api/v1/events", json={"type": "whatsapp_click", "product_slug": "oculta"}
    )
    assert response.status_code == 404
    assert event_count(db) == 0


def test_missing_slug_is_rejected(public_client):
    assert public_client.post("/api/v1/events", json={"type": "whatsapp_click"}).status_code == 422


def test_no_pii_columns(database_url):
    engine = make_engine(database_url)
    columns = {column["name"] for column in inspect(engine).get_columns("catalog_events")}
    engine.dispose()
    assert columns == {"id", "type", "product_id", "occurred_at"}


def test_deleting_a_product_keeps_the_event(db, public_client):
    product = make_product(db, make_brand(db), make_category(db), "Pieza")
    db.commit()
    public_client.post("/api/v1/events", json={"type": "whatsapp_click", "product_slug": "pieza"})
    db.delete(db.get(Product, product.id))
    db.commit()
    db.expire_all()
    assert db.scalar(select(CatalogEvent)).product_id is None
