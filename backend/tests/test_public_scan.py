"""Walks every public response, in both modes, looking for fields that must never leak."""

import json

import pytest

from app.models import STATUS_PUBLISHED, Collection, CollectionProduct, Lookbook, LookbookProduct
from app.services.demo_seed import seed_demo
from tests.factories import make_brand, make_category, make_product

FORBIDDEN_KEY_PARTS = (
    "price",
    "precio",
    "cost",
    "discount",
    "margin",
    "supplier",
    "proveedor",
    "internal",
    "notes",
    "inventory",
    "sku",
    "admin",
    "whatsapp_number",
    "is_demo",
    "search_text",
    "validation_status",
    "original_name",
)
SECRET = "VALOR-INTERNO-SECRETO"
SKU = "SKU-SECRETO-777"


def walk_keys(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, f"{path}.{key}"
            yield from walk_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_keys(child, f"{path}[{index}]")


def walk_strings(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield value, path


@pytest.fixture
def populated(db, make_settings):
    seed_demo(db, make_settings(demo_mode=True))
    brand = make_brand(db, "Publicada", description="Descripción pública")
    category = make_category(db, "Categoría Pública")
    product = make_product(
        db,
        brand,
        category,
        "Pieza Publicada",
        sku=SKU,
        admin_description=SECRET,
        internal_notes=SECRET,
        external_inventory_id=SECRET,
        supplier_ref=SECRET,
    )
    collection = Collection(slug="publica", title="Pública", status=STATUS_PUBLISHED)
    lookbook = Lookbook(slug="publico", title="Público", status=STATUS_PUBLISHED)
    db.add_all([collection, lookbook])
    db.flush()
    db.add(CollectionProduct(collection_id=collection.id, product_id=product.id))
    db.add(LookbookProduct(lookbook_id=lookbook.id, product_id=product.id))
    db.commit()
    return db


PUBLIC_PATHS = (
    "/api/v1/health",
    "/api/v1/brands",
    "/api/v1/brands?featured=true",
    "/api/v1/brands?q=publicada",
    "/api/v1/brands/publicada",
    "/api/v1/brands/prada",
    "/api/v1/categories",
    "/api/v1/products?page_size=60",
    "/api/v1/products/pieza-publicada",
    "/api/v1/products/pieza-demostracion-01",
    "/api/v1/products/pieza-demostracion-12",
    "/api/v1/novedades?page_size=60",
    "/api/v1/collections",
    "/api/v1/collections/publica",
    "/api/v1/collections/seleccion-demostracion-a",
    "/api/v1/lookbooks",
    "/api/v1/lookbooks/publico",
    "/api/v1/lookbooks/lookbook-demostracion",
    "/api/v1/search?q=pieza",
    "/api/v1/search?q=publicada",
    "/api/v1/site-settings/public",
)


@pytest.mark.parametrize("demo_mode", [False, True])
def test_no_forbidden_field_or_value_anywhere(populated, make_client, demo_mode):
    client = make_client(demo_mode=demo_mode, whatsapp_number="+52 55 0000 0000")
    checked = 0
    for path in PUBLIC_PATHS:
        response = client.get(path)
        if response.status_code == 404:
            assert not demo_mode, f"{path} should exist in demo mode"
            continue
        assert response.status_code == 200, path
        body = response.json()
        checked += 1
        for key, location in walk_keys(body):
            lowered = key.casefold()
            assert not any(part in lowered for part in FORBIDDEN_KEY_PARTS), f"{path}: {location}"
        assert SECRET not in json.dumps(body), path
        for text, location in walk_strings(body):
            if SKU in text or "DEMO-0" in text:
                assert location.endswith(".consult_url"), f"{path}: {location}"
    assert checked >= 12


def test_scan_covers_the_whole_public_api(public_client):
    """A new public GET route must be added to PUBLIC_PATHS above."""
    paths = public_client.app.openapi()["paths"]
    routes = {
        path
        for path, operations in paths.items()
        if "get" in operations and not path.startswith("/api/v1/admin")
    }
    assert routes == {
        "/api/v1/health",
        "/api/v1/brands",
        "/api/v1/brands/{slug}",
        "/api/v1/categories",
        "/api/v1/products",
        "/api/v1/products/{slug}",
        "/api/v1/novedades",
        "/api/v1/collections",
        "/api/v1/collections/{slug}",
        "/api/v1/lookbooks",
        "/api/v1/lookbooks/{slug}",
        "/api/v1/search",
        "/api/v1/site-settings/public",
    }


def test_sku_reaches_only_the_consult_url(populated, make_client):
    client = make_client(whatsapp_number="+52 55 0000 0000")
    detail = client.get("/api/v1/products/pieza-publicada")
    assert SKU in detail.json()["consult_url"]
    without_url = {k: v for k, v in detail.json().items() if k != "consult_url"}
    assert SKU not in json.dumps(without_url)
