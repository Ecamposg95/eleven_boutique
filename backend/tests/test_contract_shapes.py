"""Exact field sets from docs/api-contract.md."""

import pytest

from app.services.demo_seed import seed_demo

MEDIA = {"url", "alt", "is_primary", "position"}
BRAND_SUMMARY = {"slug", "name", "logo_url", "is_featured", "aliases", "product_count"}
BRAND_DETAIL = BRAND_SUMMARY | {"description", "editorial_image_url"}
CARD = {"slug", "name", "brand", "category", "primary_image", "secondary_image"}
DETAIL = CARD | {"gallery", "consult_url", "seo_title", "seo_description", "published_at"}
COLLECTION = {"slug", "title", "summary", "cover_url", "product_count"}
LOOKBOOK = {"slug", "title", "summary", "cover_url"}


@pytest.fixture
def client(db, make_settings, demo_client):
    seed_demo(db, make_settings(demo_mode=True))
    db.commit()
    return demo_client


def assert_card(card: dict) -> None:
    assert set(card) == CARD
    assert set(card["brand"]) == {"slug", "name"}
    assert set(card["category"]) == {"slug", "name"}
    assert set(card["primary_image"]) == MEDIA


def test_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_brands(client):
    listing = client.get("/api/v1/brands").json()
    assert set(listing) == {"items"}
    assert set(listing["items"][0]) == BRAND_SUMMARY
    assert set(client.get("/api/v1/brands/prada").json()) == BRAND_DETAIL


def test_categories(client):
    listing = client.get("/api/v1/categories").json()
    assert set(listing) == {"items"}
    assert set(listing["items"][0]) == {"slug", "name", "parent_slug", "product_count"}


@pytest.mark.parametrize("path", ["/api/v1/products", "/api/v1/novedades"])
def test_paginated_cards(client, path):
    page = client.get(path).json()
    assert set(page) == {"items", "total", "page", "page_size"}
    assert_card(page["items"][0])


def test_product_detail(client):
    detail = client.get("/api/v1/products/pieza-demostracion-01").json()
    assert set(detail) == DETAIL
    assert set(detail["gallery"][0]) == MEDIA


def test_collections(client):
    listing = client.get("/api/v1/collections").json()
    assert set(listing) == {"items"}
    assert set(listing["items"][0]) == COLLECTION
    detail = client.get("/api/v1/collections/seleccion-demostracion-a").json()
    assert set(detail) == COLLECTION | {"products"}
    assert_card(detail["products"][0])


def test_lookbooks(client):
    listing = client.get("/api/v1/lookbooks").json()
    assert set(listing) == {"items"}
    assert set(listing["items"][0]) == LOOKBOOK
    detail = client.get("/api/v1/lookbooks/lookbook-demostracion").json()
    assert set(detail) == LOOKBOOK | {"blocks", "products"}
    assert_card(detail["products"][0])
    shapes = {block["type"]: set(block) for block in detail["blocks"]}
    assert shapes["text"] == {"type", "position", "heading", "body"}
    assert shapes["image"] == {"type", "position", "url", "alt", "layout"}
    positions = [block["position"] for block in detail["blocks"]]
    assert positions == sorted(positions)


def test_search(client):
    result = client.get("/api/v1/search", params={"q": "prada"}).json()
    assert set(result) == {"brands", "products"}
    assert set(result["brands"][0]) == BRAND_SUMMARY
    assert_card(result["products"][0])


def test_site_settings(client):
    settings = client.get("/api/v1/site-settings/public").json()
    assert set(settings) == {
        "demo_mode",
        "whatsapp_enabled",
        "site_name",
        "hero",
        "intro",
        "boutique",
        "contact",
    }
    assert set(settings["hero"]) == {"image_url", "mobile_image_url", "headline", "subhead", "gallery"}
    assert set(settings["boutique"]) == {"body"}
    assert set(settings["contact"]) == {"body"}


def test_cors_allows_the_configured_origin(client):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    other = client.get("/api/v1/health", headers={"Origin": "https://otro.example"})
    assert "access-control-allow-origin" not in other.headers
