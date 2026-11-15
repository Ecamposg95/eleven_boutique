"""Pantalla Atlas ONE de la API y piezas de solo lectura."""

import uuid

import pytest

from app.models import ROLE_EDITOR, AtlasBrandMap, AtlasCategoryMap, AtlasSyncRun, AtlasSyncState, ProductMedia
from app.models.base import utcnow
from app.services.admin import atlas as atlas_service
from app.services.atlas.sync import with_lock
from app.services.atlas.sync_products import PLACEHOLDER_BRAND
from tests.admin_helpers import BASE, ORIGIN, login, make_user
from tests.factories import make_brand, make_category, make_product

CONFIG = {"atlas_sync_enabled": True, "atlas_api_url": "https://atlas.example", "atlas_api_key": "k"}


@pytest.fixture
def launched(monkeypatch):
    calls = []
    monkeypatch.setattr(atlas_service, "launch_sync", lambda settings, factory: calls.append(1))
    return calls


@pytest.fixture
def client(db, make_client):
    client = make_client(**CONFIG)
    login(client, make_user(db))
    return client


@pytest.fixture
def editor(db, make_client):
    client = make_client(**CONFIG)
    login(client, make_user(db, ROLE_EDITOR))
    return client


def patch(client, path, body):
    return client.patch(BASE + path, json=body, headers=ORIGIN)


def atlas_piece(db, **fields):
    brand = make_brand(db, "Casa")
    category = make_category(db, "Bolsas")
    product = make_product(db, brand, category, "Pieza Atlas", external_inventory_id="inv-1", **fields)
    db.add(ProductMedia(product_id=product.id, url="https://atlas/x.jpg", alt="x", position=5))
    db.commit()
    return product


def test_editor_is_refused_everywhere(editor):
    assert editor.get(f"{BASE}/atlas/status").status_code == 403
    assert editor.post(f"{BASE}/atlas/sync", headers=ORIGIN).status_code == 403
    assert editor.get(f"{BASE}/atlas/brand-map").status_code == 403
    assert patch(editor, "/atlas/brand-map", {"atlas_brand_id": "a", "brand_id": None}).status_code == 403
    assert patch(editor, "/atlas/category-map", {"atlas_department_id": "a", "category_id": None}).status_code == 403


def test_status_reflects_last_run_and_drafts(db, client):
    body = client.get(f"{BASE}/atlas/status").json()
    assert body["enabled"] is True and body["last_run"] is None and body["drafts"] == []
    now = utcnow()
    db.add(AtlasSyncRun(started_at=now, finished_at=now, kind="manual", status="ok", counts={"creadas": 2}))
    db.add(AtlasSyncState(id=1, last_ok_at=now))
    atlas_piece(db, status="draft", atlas_missing="foto")
    db.commit()
    body = client.get(f"{BASE}/atlas/status").json()
    assert body["last_run"]["status"] == "ok" and body["last_run"]["counts"] == {"creadas": 2}
    assert body["last_ok_at"] is not None
    assert [(d["name"], d["atlas_missing"]) for d in body["drafts"]] == [("Pieza Atlas", "foto")]


def test_status_disabled_without_config(db, make_client):
    client = make_client()
    login(client, make_user(db))
    assert client.get(f"{BASE}/atlas/status").json()["enabled"] is False


def test_sync_starts(client, launched):
    response = client.post(f"{BASE}/atlas/sync", headers=ORIGIN)
    assert response.status_code == 202 and response.json() == {"started": True}
    assert launched == [1]


def test_sync_busy_is_409(db, client, launched):
    with with_lock(db) as acquired:
        assert acquired
        response = client.post(f"{BASE}/atlas/sync", headers=ORIGIN)
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Ya hay una sincronización en curso"
    assert launched == []


def test_sync_unconfigured_is_409(db, make_client, launched):
    client = make_client()
    login(client, make_user(db))
    response = client.post(f"{BASE}/atlas/sync", headers=ORIGIN)
    assert response.status_code == 409 and "no está configurada" in response.json()["error"]["message"]
    assert launched == []


def test_brand_map_patch_validates_target(db, client):
    house = make_brand(db, "Gucci")
    classification = make_brand(db, "Genérica", kind="classification")
    placeholder = make_brand(db, PLACEHOLDER_BRAND, status="draft")
    db.add(AtlasBrandMap(atlas_brand_id="b1", atlas_name="Gucci"))
    db.commit()
    assert client.get(f"{BASE}/atlas/brand-map").json() == [
        {"atlas_brand_id": "b1", "atlas_name": "Gucci", "brand_id": None}
    ]
    for bad in (uuid.uuid4(), classification.id, placeholder.id):
        assert patch(client, "/atlas/brand-map", {"atlas_brand_id": "b1", "brand_id": str(bad)}).status_code == 422
    assert patch(client, "/atlas/brand-map", {"atlas_brand_id": "zz", "brand_id": None}).status_code == 404
    ok = patch(client, "/atlas/brand-map", {"atlas_brand_id": "b1", "brand_id": str(house.id)})
    assert ok.status_code == 200 and ok.json()["brand_id"] == str(house.id)
    assert patch(client, "/atlas/brand-map", {"atlas_brand_id": "b1", "brand_id": None}).json()["brand_id"] is None


def test_category_map_patch_validates_target(db, client):
    category = make_category(db, "Bolsas")
    db.add(AtlasCategoryMap(atlas_department_id="d1", atlas_name="Bolsos"))
    db.commit()
    bad = patch(client, "/atlas/category-map", {"atlas_department_id": "d1", "category_id": str(uuid.uuid4())})
    assert bad.status_code == 422
    ok = patch(client, "/atlas/category-map", {"atlas_department_id": "d1", "category_id": str(category.id)})
    assert ok.json()["category_id"] == str(category.id)
    assert client.get(f"{BASE}/atlas/category-map").json()[0]["category_id"] == str(category.id)


def test_placeholder_house_is_hidden_and_cannot_be_published(db, client):
    placeholder = make_brand(db, PLACEHOLDER_BRAND, status="draft")
    db.commit()
    names = [b["name"] for b in client.get(f"{BASE}/brands").json()["items"]]
    assert PLACEHOLDER_BRAND not in names
    response = patch(client, f"/brands/{placeholder.id}", {"status": "published"})
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Casa interna de sincronización"


def test_manual_creation_is_gone(db, client):
    brand, category = make_brand(db, "X"), make_category(db, "Y")
    db.commit()
    response = client.post(
        f"{BASE}/products",
        json={"name": "N", "brand_id": str(brand.id), "category_id": str(category.id)},
        headers=ORIGIN,
    )
    assert response.status_code == 410
    assert response.json()["error"]["message"] == "Las piezas se publican desde Atlas ONE"


def test_import_routes_are_gone(client):
    assert client.post(f"{BASE}/imports/products", json={}, headers=ORIGIN).status_code in (404, 405)
    assert client.get(f"{BASE}/imports/template").status_code == 404


def test_atlas_piece_owned_fields_are_422(db, client):
    product = atlas_piece(db)
    for body in ({"name": "Otro"}, {"slug": "otro"}, {"status": "draft"}, {"brand_id": str(uuid.uuid4())}):
        response = patch(client, f"/products/{product.id}", body)
        assert response.status_code == 422, body
        assert "Este campo viene de Atlas ONE" in response.json()["error"]["message"]


def test_atlas_piece_editorial_fields_are_ok(db, client):
    product = atlas_piece(db)
    body = {"hidden_on_web": True, "seo_title": "SEO", "is_featured": True, "internal_notes": "n"}
    response = patch(client, f"/products/{product.id}", body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["hidden_on_web"] is True and data["from_atlas"] is True and data["seo_title"] == "SEO"


def test_atlas_piece_cannot_be_archived_nor_bulk_status_changed(db, client):
    product = atlas_piece(db)
    assert client.delete(f"{BASE}/products/{product.id}", headers=ORIGIN).status_code == 409
    results = client.post(
        f"{BASE}/products/bulk", json={"ids": [str(product.id)], "action": "archive"}, headers=ORIGIN
    ).json()["results"]
    assert results[0]["ok"] is False
    results = client.post(
        f"{BASE}/products/bulk", json={"ids": [str(product.id)], "action": "feature"}, headers=ORIGIN
    ).json()["results"]
    assert results[0]["ok"] is True


def test_non_atlas_piece_still_archives(db, client):
    brand, category = make_brand(db, "Z"), make_category(db, "W")
    product = make_product(db, brand, category, "Vieja")
    db.commit()
    assert client.delete(f"{BASE}/products/{product.id}", headers=ORIGIN).status_code == 200


def test_atlas_media_is_read_only_but_panel_media_is_not(db, client):
    product = atlas_piece(db)
    media = client.get(f"{BASE}/products/{product.id}").json()["media"]
    assert all(m["read_only"] for m in media)
    for m in media:
        path = f"/products/{product.id}/media/{m['id']}"
        assert patch(client, path, {"alt": "x"}).status_code == 422
        assert client.delete(BASE + path, headers=ORIGIN).status_code == 422
