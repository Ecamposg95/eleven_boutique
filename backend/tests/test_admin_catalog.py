"""Publishing rules, product/brand/category/collection/lookbook CRUD, settings and dashboard."""

import json
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import (
    ROLE_EDITOR,
    STATUS_DRAFT,
    AuditLog,
    Brand,
    BrandAlias,
    CatalogEvent,
    Product,
)
from app.models.base import utcnow
from app.services.base_seed import seed_categories
from app.services.brand_import import run_import
from tests.admin_helpers import BASE, ORIGIN, login, make_user, upload_one
from tests.factories import make_alias, make_brand, make_category, make_product
from tests.test_public_scan import FORBIDDEN_KEY_PARTS, walk_keys

SECRET = "NOTA-INTERNA-SECRETA"


@pytest.fixture
def client(db, public_client):
    login(public_client, make_user(db))
    return public_client


@pytest.fixture
def refs(db):
    published = make_brand(db, "Publicada")
    draft = make_brand(db, "Borrador", status=STATUS_DRAFT)
    no_brand = make_brand(db, "Sin marca", kind="classification", status=STATUS_DRAFT)
    category = make_category(db, "Bolsas")
    db.commit()
    return {"published": published, "draft": draft, "no_brand": no_brand, "category": category}


def post(client, path, body):
    return client.post(BASE + path, json=body, headers=ORIGIN)


def patch(client, path, body):
    return client.patch(BASE + path, json=body, headers=ORIGIN)


def create(client, refs, brand="published", **fields):
    response = post(
        client,
        "/products",
        {
            "name": fields.pop("name", "Pieza"),
            "brand_id": str(refs[brand].id),
            "category_id": str(refs["category"].id),
            **fields,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_photo(client, product):
    response = post(
        client, f"/products/{product['id']}/media", {"media_asset_id": upload_one(client)["id"]}
    )
    assert response.status_code == 201, response.text
    return response.json()


def public_slugs(client):
    return [item["slug"] for item in client.get("/api/v1/products?page_size=60").json()["items"]]


def error_code(response):
    return response.json()["error"]["code"]


# --- Publishing ------------------------------------------------------------------------


def test_create_defaults_to_draft_with_generated_fields(client, refs):
    product = create(client, refs, name="Bolsa Roja")
    assert product["status"] == "draft"
    assert product["slug"] == "publicada-bolsa-roja"
    assert product["sku"].startswith("ELV-")
    assert product["published_at"] is None
    assert (product["media"], product["variants"], product["photo_refs"]) == ([], [], [])


def test_publishing_without_a_photo_is_rejected(client, refs):
    product = create(client, refs)
    response = patch(client, f"/products/{product['id']}", {"status": "published"})
    assert response.status_code == 409
    assert error_code(response) == "photo_required"
    assert client.get(f"{BASE}/products/{product['id']}").json()["status"] == "draft"


def test_creating_as_published_without_a_photo_is_rejected_and_rolled_back(db, client, refs):
    response = post(
        client,
        "/products",
        {
            "name": "Directa",
            "brand_id": str(refs["published"].id),
            "category_id": str(refs["category"].id),
            "status": "published",
        },
    )
    assert response.status_code == 409
    assert db.scalar(select(Product).where(Product.name == "Directa")) is None


def test_unpublished_brand_gives_409_then_publish_brand_publishes_both(db, client, refs):
    product = add_photo(client, create(client, refs, brand="draft"))
    path = f"/products/{product['id']}"
    response = patch(client, path, {"status": "published"})
    assert response.status_code == 409
    assert error_code(response) == "brand_unpublished"
    db.expire_all()
    assert db.get(Brand, refs["draft"].id).status == "draft"
    assert public_slugs(client) == []

    response = patch(client, path, {"status": "published", "publish_brand": True})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "published"
    db.expire_all()
    assert db.get(Brand, refs["draft"].id).status == "published"
    assert public_slugs(client) == [product["slug"]]
    rows = db.scalars(select(AuditLog).where(AuditLog.operation == "publish_brand")).all()
    assert len(rows) == 1 and rows[0].entity_id == str(refs["draft"].id)


def test_editor_cannot_publish_a_brand_through_a_product(db, make_client, refs):
    client = make_client()
    login(client, make_user(db, ROLE_EDITOR))
    product = add_photo(client, create(client, refs, brand="draft"))
    response = patch(
        client, f"/products/{product['id']}", {"status": "published", "publish_brand": True}
    )
    assert response.status_code == 403
    db.expire_all()
    assert db.get(Brand, refs["draft"].id).status == "draft"


def test_editor_can_publish_under_a_published_brand(db, make_client, refs):
    client = make_client()
    login(client, make_user(db, ROLE_EDITOR))
    product = add_photo(client, create(client, refs))
    assert patch(client, f"/products/{product['id']}", {"status": "published"}).status_code == 200


def test_classification_needs_no_published_brand(client, refs):
    product = add_photo(client, create(client, refs, brand="no_brand", name="Sola"))
    assert product["slug"] == "sola"
    response = patch(client, f"/products/{product['id']}", {"status": "published"})
    assert response.status_code == 200
    card = client.get("/api/v1/products").json()["items"][0]
    assert card["brand"] == {"slug": None, "name": None}


def test_moving_a_published_product_to_an_unpublished_brand_is_rejected(client, refs):
    product = add_photo(client, create(client, refs))
    patch(client, f"/products/{product['id']}", {"status": "published"})
    response = patch(client, f"/products/{product['id']}", {"brand_id": str(refs["draft"].id)})
    assert response.status_code == 409
    assert error_code(response) == "brand_unpublished"


def test_published_at_is_set_only_the_first_time(client, refs):
    product = add_photo(client, create(client, refs))
    path = f"/products/{product['id']}"
    first = patch(client, path, {"status": "published"}).json()["published_at"]
    assert first is not None
    patch(client, path, {"status": "draft"})
    assert patch(client, path, {"status": "published"}).json()["published_at"] == first


def test_product_appears_after_publishing_and_vanishes_after_unpublish(client, refs):
    product = add_photo(client, create(client, refs))
    path = f"/products/{product['id']}"
    assert public_slugs(client) == []
    patch(client, path, {"status": "published"})
    assert public_slugs(client) == [product["slug"]]
    detail = client.get(f"/api/v1/products/{product['slug']}")
    assert detail.status_code == 200
    assert detail.json()["gallery"][0]["url"].startswith("/media/")

    patch(client, path, {"status": "draft"})
    assert public_slugs(client) == []
    assert client.get(f"/api/v1/products/{product['slug']}").status_code == 404


def test_delete_archives_and_the_product_vanishes(db, client, refs):
    product = add_photo(client, create(client, refs))
    patch(client, f"/products/{product['id']}", {"status": "published"})
    response = client.delete(f"{BASE}/products/{product['id']}", headers=ORIGIN)
    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    assert public_slugs(client) == []
    db.expire_all()
    assert db.get(Product, uuid.UUID(product["id"])) is not None


def test_removing_the_last_photo_of_a_published_product_is_409(client, refs):
    product = add_photo(client, create(client, refs))
    patch(client, f"/products/{product['id']}", {"status": "published"})
    link = product["media"][0]["id"]
    response = client.delete(f"{BASE}/products/{product['id']}/media/{link}", headers=ORIGIN)
    assert response.status_code == 409
    assert error_code(response) == "last_photo"


def test_removing_the_last_photo_of_a_draft_is_allowed(client, refs):
    product = add_photo(client, create(client, refs))
    link = product["media"][0]["id"]
    response = client.delete(f"{BASE}/products/{product['id']}/media/{link}", headers=ORIGIN)
    assert response.status_code == 200


def test_brands_endpoint_hides_drafts_when_demo_mode_is_off(client, refs):
    slugs = {item["slug"] for item in client.get("/api/v1/brands").json()["items"]}
    assert "publicada" in slugs
    assert "borrador" not in slugs
    assert client.get("/api/v1/brands/borrador").status_code == 404


def test_published_brand_gets_public_when_published_through_a_product(client, refs):
    product = add_photo(client, create(client, refs, brand="draft"))
    patch(client, f"/products/{product['id']}", {"status": "published", "publish_brand": True})
    assert client.get("/api/v1/brands/borrador").status_code == 200


# --- Product fields and listing --------------------------------------------------------


def test_invalid_references_are_rejected(client, refs):
    response = post(
        client,
        "/products",
        {"name": "X", "brand_id": str(uuid.uuid4()), "category_id": str(refs["category"].id)},
    )
    assert response.status_code == 422
    assert error_code(response) == "invalid_reference"


def test_slug_uniqueness_and_format(client, refs):
    first = create(client, refs, name="Igual")
    second = create(client, refs, name="Igual")
    assert second["slug"] == f"{first['slug']}-2"
    response = patch(client, f"/products/{second['id']}", {"slug": first["slug"]})
    assert response.status_code == 409 and error_code(response) == "slug_taken"
    assert patch(client, f"/products/{second['id']}", {"slug": "No Valido"}).status_code == 422


def test_sku_collision_is_409(client, refs):
    create(client, refs, sku="UNICO-1")
    response = post(
        client,
        "/products",
        {
            "name": "Otra",
            "sku": "UNICO-1",
            "brand_id": str(refs["published"].id),
            "category_id": str(refs["category"].id),
        },
    )
    assert response.status_code == 409 and error_code(response) == "sku_taken"


def test_patch_rejects_null_for_required_fields_but_clears_optional_ones(client, refs):
    product = create(client, refs, seo_title="Título")
    path = f"/products/{product['id']}"
    assert patch(client, path, {"name": None}).status_code == 422
    assert patch(client, path, {"seo_title": None}).json()["seo_title"] is None


def test_naive_date_is_accepted_as_utc(client, refs):
    product = create(client, refs)
    response = patch(client, f"/products/{product['id']}", {"commercial_added_at": "2026-03-01T10:00:00"})
    assert response.status_code == 200
    assert response.json()["commercial_added_at"].startswith("2026-03-01T10:00:00")


def test_list_filters(db, client, refs):
    with_photo = add_photo(client, create(client, refs, name="Con Foto", sku="AAA-1"))
    create(client, refs, brand="draft", name="Sin Foto", sku="BBB-2")

    def skus(query):
        response = client.get(f"{BASE}/products{query}")
        assert response.status_code == 200, response.text
        return {item["sku"] for item in response.json()["items"]}

    assert skus("") == {"AAA-1", "BBB-2"}
    assert skus("?q=con foto") == {"AAA-1"}
    assert skus("?q=bbb") == {"BBB-2"}
    assert skus("?has_photo=true") == {"AAA-1"}
    assert skus("?has_photo=false") == {"BBB-2"}
    assert skus("?brand=borrador") == {"BBB-2"}
    assert skus(f"?brand={refs['published'].id}") == {"AAA-1"}
    assert skus("?category=bolsas") == {"AAA-1", "BBB-2"}
    assert skus("?status=published") == set()
    assert skus("?sort=name&page=1&page_size=1") <= {"AAA-1", "BBB-2"}
    assert with_photo["media"]
    assert client.get(f"{BASE}/products?status=otro").status_code == 422
    assert client.get(f"{BASE}/products?sort=otro").status_code == 422


def test_bulk_reports_per_id_without_failing_the_batch(client, refs):
    good = add_photo(client, create(client, refs, name="Buena"))
    no_photo = create(client, refs, name="Sin Foto")
    draft_brand = add_photo(client, create(client, refs, brand="draft", name="Marca Borrador"))
    missing = str(uuid.uuid4())
    response = post(
        client,
        "/products/bulk",
        {
            "ids": [good["id"], no_photo["id"], draft_brand["id"], missing],
            "action": "publish",
        },
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["ok"] for r in results] == [True, False, False, False]
    assert [r["error"]["code"] for r in results[1:]] == [
        "photo_required",
        "brand_unpublished",
        "not_found",
    ]
    assert public_slugs(client) == [good["slug"]]


def test_bulk_publish_brand_and_other_actions(client, refs):
    product = add_photo(client, create(client, refs, brand="draft"))
    ids = [product["id"]]
    body = {"ids": ids, "action": "publish", "publish_brand": True}
    assert post(client, "/products/bulk", body).json()["results"][0]["ok"]
    assert public_slugs(client) == [product["slug"]]

    post(client, "/products/bulk", {"ids": ids, "action": "feature"})
    assert client.get(f"{BASE}/products/{product['id']}").json()["is_featured"] is True
    post(client, "/products/bulk", {"ids": ids, "action": "unfeature"})
    assert client.get(f"{BASE}/products/{product['id']}").json()["is_featured"] is False
    post(client, "/products/bulk", {"ids": ids, "action": "unpublish"})
    assert public_slugs(client) == []
    post(client, "/products/bulk", {"ids": ids, "action": "archive"})
    assert client.get(f"{BASE}/products/{product['id']}").json()["status"] == "archived"
    assert post(client, "/products/bulk", {"ids": ids, "action": "otro"}).status_code == 422


# --- Public scan -----------------------------------------------------------------------


def test_internal_fields_never_reach_public_responses(db, client, refs):
    product = add_photo(client, create(client, refs, internal_notes=SECRET, sku="SKU-OCULTO"))
    patch(client, f"/products/{product['id']}", {"status": "published"})
    item = upload_one(client)
    patch(client, f"/brands/{refs['published'].id}", {"logo_asset_id": item["id"]})
    post(client, "/collections", {"title": "Col", "status": "published", "product_ids": [product["id"]]})
    post(
        client,
        "/lookbooks",
        {
            "title": "Look",
            "status": "published",
            "product_ids": [product["id"]],
            "blocks": [{"type": "text", "body": "Texto"}],
        },
    )
    patch(client, "/settings", {"hero_asset_id": item["id"], "hero_mobile_asset_id": item["id"]})

    paths = (
        "/brands",
        "/brands/publicada",
        "/products",
        f"/products/{product['slug']}",
        "/collections",
        "/collections/col",
        "/lookbooks",
        "/lookbooks/look",
        "/search?q=pieza",
        "/site-settings/public",
    )
    for path in paths:
        response = client.get(f"/api/v1{path}")
        assert response.status_code == 200, path
        body = response.json()
        for key, location in walk_keys(body):
            lowered = key.casefold()
            assert not any(part in lowered for part in FORBIDDEN_KEY_PARTS), location
            assert "asset_id" not in lowered, location
            assert lowered not in {"photo_refs", "variants", "storage_key", "uploaded_by_id"}
        dumped = json.dumps(body)
        assert SECRET not in dumped
        assert "SKU-OCULTO" not in dumped


def test_admin_product_never_exposes_other_internal_columns(db, client, refs):
    product = make_product(
        db,
        refs["published"],
        refs["category"],
        "Interna",
        external_inventory_id="INV-OCULTO",
        supplier_ref="PROV-OCULTO",
        admin_description="DESC-OCULTA",
    )
    db.commit()
    dumped = client.get(f"{BASE}/products/{product.id}").text
    for hidden in ("INV-OCULTO", "PROV-OCULTO", "DESC-OCULTA"):
        assert hidden not in dumped


# --- Brands ----------------------------------------------------------------------------


def test_brand_create_and_read(client):
    response = post(client, "/brands", {"name": "Nueva Casa", "aliases": ["Casa Nueva"]})
    assert response.status_code == 201, response.text
    brand = response.json()
    assert brand["slug"] == "nueva-casa"
    assert brand["status"] == "draft"
    assert brand["aliases"] == ["Casa Nueva"]
    assert client.get(f"{BASE}/brands/{brand['id']}").json() == brand
    assert client.get(f"{BASE}/brands?q=casa nueva").json()["total"] == 1


def test_brand_slug_change_keeps_the_old_slug_resolving(db, client, refs):
    brand = refs["published"]
    response = patch(client, f"/brands/{brand.id}", {"slug": "publicada-nueva"})
    assert response.status_code == 200, response.text
    assert response.json()["slug"] == "publicada-nueva"
    # The retained slug is routing data, not a name to show.
    assert response.json()["aliases"] == []
    old = client.get("/api/v1/brands/publicada")
    assert old.status_code == 200
    assert old.json()["slug"] == "publicada-nueva"
    assert old.json()["aliases"] == []
    assert client.get("/api/v1/brands/publicada-nueva").status_code == 200
    assert db.scalar(select(BrandAlias).where(BrandAlias.slug == "publicada")) is not None


def test_retained_slug_survives_an_alias_list_update(client, refs):
    path = f"/brands/{refs['published'].id}"
    patch(client, path, {"slug": "publicada-nueva"})
    patch(client, path, {"aliases": []})
    assert client.get("/api/v1/brands/publicada").status_code == 200


def test_brand_slug_cannot_take_another_brands_slug_or_alias(db, client, refs):
    make_alias(db, refs["draft"], "Otro Nombre")
    db.commit()
    path = f"/brands/{refs['published'].id}"
    assert patch(client, path, {"slug": "borrador"}).status_code == 409
    assert patch(client, path, {"slug": "otro-nombre"}).status_code == 409


def test_aliases_can_be_added_and_removed_but_not_stolen(db, client, refs):
    make_alias(db, refs["draft"], "Ajeno")
    db.commit()
    path = f"/brands/{refs['published'].id}"
    assert patch(client, path, {"aliases": ["Uno", "Dos"]}).json()["aliases"] == ["Dos", "Uno"]
    assert patch(client, path, {"aliases": ["Dos"]}).json()["aliases"] == ["Dos"]
    response = patch(client, path, {"aliases": ["Ajeno"]})
    assert response.status_code == 409 and error_code(response) == "alias_taken"


def test_source_aliases_are_protected(db, client):
    run_import(db)
    db.commit()
    brand = db.scalar(select(Brand).where(Brand.slug == "a-bathing-ape"))
    response = patch(client, f"/brands/{brand.id}", {"aliases": []})
    assert response.status_code == 409 and error_code(response) == "alias_protected"


def test_brand_asset_sets_the_public_url(client, refs):
    item = upload_one(client)
    path = f"/brands/{refs['published'].id}"
    body = patch(client, path, {"editorial_asset_id": item["id"]}).json()
    assert body["editorial_image_url"] == item["url"]
    public = client.get("/api/v1/brands/publicada").json()
    assert public["editorial_image_url"] == item["url"]
    assert patch(client, path, {"editorial_asset_id": None}).json()["editorial_image_url"] is None


def test_brand_list_is_paginated_and_counts_products(db, client, refs):
    make_product(db, refs["published"], refs["category"], "Una")
    db.commit()
    page = client.get(f"{BASE}/brands?page_size=2").json()
    assert (page["total"], page["page_size"], len(page["items"])) == (3, 2, 2)
    by_slug = {item["slug"]: item for item in client.get(f"{BASE}/brands").json()["items"]}
    assert by_slug["publicada"]["product_count"] == 1
    assert by_slug["sin-marca"]["kind"] == "classification"


def test_there_is_no_brand_delete_route(client, refs):
    response = client.delete(f"{BASE}/brands/{refs['draft'].id}", headers=ORIGIN)
    assert response.status_code == 405


# --- Categories ------------------------------------------------------------------------


def test_category_crud(client):
    parent = post(client, "/categories", {"name": "Raíz Nueva"}).json()
    child = post(client, "/categories", {"name": "Hija", "parent_id": parent["id"]})
    assert child.status_code == 201
    child = child.json()
    assert child["parent_id"] == parent["id"]
    assert patch(client, f"/categories/{child['id']}", {"name": "Hija 2"}).json()["name"] == "Hija 2"
    assert client.get(f"{BASE}/categories").json()["total"] == 2
    public = {c["slug"]: c["parent_slug"] for c in client.get("/api/v1/categories").json()["items"]}
    assert public["hija"] == "raiz-nueva"


def test_category_delete_is_409_with_children_or_products(db, client, refs):
    parent = post(client, "/categories", {"name": "Padre"}).json()
    child = post(client, "/categories", {"name": "Hija", "parent_id": parent["id"]}).json()
    response = client.delete(f"{BASE}/categories/{parent['id']}", headers=ORIGIN)
    assert response.status_code == 409 and error_code(response) == "category_in_use"

    create(client, {**refs, "category": type("C", (), {"id": child["id"]})}, name="En Hija")
    assert client.delete(f"{BASE}/categories/{child['id']}", headers=ORIGIN).status_code == 409


def test_empty_category_is_really_deleted(client):
    category = post(client, "/categories", {"name": "Vacía"}).json()
    assert client.delete(f"{BASE}/categories/{category['id']}", headers=ORIGIN).status_code == 204
    assert client.get(f"{BASE}/categories").json()["total"] == 0


def test_category_cannot_become_its_own_ancestor(client):
    parent = post(client, "/categories", {"name": "A"}).json()
    child = post(client, "/categories", {"name": "B", "parent_id": parent["id"]}).json()
    assert patch(client, f"/categories/{parent['id']}", {"parent_id": parent["id"]}).status_code == 422
    assert patch(client, f"/categories/{parent['id']}", {"parent_id": child["id"]}).status_code == 422


# --- Collections and lookbooks ---------------------------------------------------------


@pytest.mark.parametrize("path", ["/collections", "/lookbooks"])
def test_collection_like_crud_keeps_product_order(client, refs, path):
    first = create(client, refs, name="Primera")["id"]
    second = create(client, refs, name="Segunda")["id"]
    cover = upload_one(client)
    response = post(
        client,
        path,
        {"title": "Título", "summary": "Resumen", "cover_asset_id": cover["id"], "product_ids": [second, first]},
    )
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["slug"] == "titulo"
    assert record["cover_url"] == cover["url"]
    assert record["product_ids"] == [second, first]

    item = f"{path}/{record['id']}"
    assert patch(client, item, {"product_ids": [first, second]}).json()["product_ids"] == [first, second]
    assert client.get(BASE + item).json()["product_ids"] == [first, second]
    assert client.get(f"{BASE}{path}?q=tit").json()["total"] == 1

    assert post(client, path, {"title": "Otro", "slug": "titulo"}).status_code == 409
    assert patch(client, item, {"product_ids": [str(uuid.uuid4())]}).status_code == 422
    assert patch(client, item, {"product_ids": [first, first]}).status_code == 422

    archived = client.delete(BASE + item, headers=ORIGIN)
    assert archived.status_code == 200 and archived.json()["status"] == "archived"
    assert client.get(BASE + item).status_code == 200


def test_lookbook_blocks_match_the_public_shape(client):
    blocks = [
        {"type": "text", "heading": "Encabezado", "body": "Cuerpo"},
        {"type": "image", "url": "/media/abc.jpg", "alt": "Foto", "layout": "left"},
    ]
    response = post(client, "/lookbooks", {"title": "Look", "status": "published", "blocks": blocks})
    assert response.status_code == 201, response.text
    assert [b["position"] for b in response.json()["blocks"]] == [0, 1]
    public = client.get("/api/v1/lookbooks/look").json()["blocks"]
    assert public == response.json()["blocks"]
    assert public[1]["layout"] == "left"

    item = f"/lookbooks/{response.json()['id']}"
    assert patch(client, item, {"blocks": blocks[:1]}).json()["blocks"][0]["type"] == "text"
    assert len(client.get("/api/v1/lookbooks/look").json()["blocks"]) == 1


@pytest.mark.parametrize(
    "block",
    [
        {"type": "image", "url": "javascript:alert(1)", "alt": "a"},
        {"type": "image", "url": "//evil.example/a.jpg", "alt": "a"},
        {"type": "image", "url": "http://evil.example/a.jpg", "alt": "a"},
        {"type": "video", "url": "/a.mp4"},
        {"type": "text"},
    ],
)
def test_lookbook_rejects_bad_blocks(client, block):
    assert post(client, "/lookbooks", {"title": "L", "blocks": [block]}).status_code == 422


def test_published_collection_appears_publicly(client):
    post(client, "/collections", {"title": "Visible", "status": "published"})
    post(client, "/collections", {"title": "Oculta"})
    assert [c["slug"] for c in client.get("/api/v1/collections").json()["items"]] == ["visible"]


# --- Settings --------------------------------------------------------------------------


def test_settings_round_trip_and_public_mobile_hero(client):
    desktop, mobile = upload_one(client), upload_one(client)
    response = patch(
        client,
        "/settings",
        {
            "whatsapp_number": "+52 55 1234 5678",
            "hero_asset_id": desktop["id"],
            "hero_mobile_asset_id": mobile["id"],
            "hero_headline": "Titular",
            "hero_subhead": "Sub",
            "intro": "Intro",
            "boutique_body": "Boutique",
            "contact_body": "Contacto",
        },
    )
    assert response.status_code == 200, response.text
    assert client.get(f"{BASE}/settings").json() == response.json()

    public = client.get("/api/v1/site-settings/public").json()
    assert public["hero"] == {
        "image_url": desktop["url"],
        "mobile_image_url": mobile["url"],
        "headline": "Titular",
        "subhead": "Sub",
        "gallery": [],
    }
    assert public["whatsapp_enabled"] is True
    assert "whatsapp_number" not in public

    cleared = patch(client, "/settings", {"hero_mobile_asset_id": None}).json()
    assert cleared["hero_mobile_image_url"] is None
    assert client.get("/api/v1/site-settings/public").json()["hero"]["mobile_image_url"] is None


def test_settings_hero_gallery_round_trip_order_and_clear(client):
    first, second = upload_one(client), upload_one(client)
    saved = patch(client, "/settings", {"hero_gallery_asset_ids": [second["id"], first["id"]]})
    assert saved.status_code == 200, saved.text
    assert saved.json()["hero_gallery"] == [
        {"asset_id": second["id"], "url": second["url"]},
        {"asset_id": first["id"], "url": first["url"]},
    ]
    assert client.get(f"{BASE}/settings").json() == saved.json()
    public = client.get("/api/v1/site-settings/public").json()
    assert public["hero"]["gallery"] == [second["url"], first["url"]]

    # Repeated ids collapse; an unrelated patch keeps the gallery.
    again = patch(client, "/settings", {"hero_gallery_asset_ids": [first["id"], first["id"]]}).json()
    assert [slide["asset_id"] for slide in again["hero_gallery"]] == [first["id"]]
    assert patch(client, "/settings", {"intro": "x"}).json()["hero_gallery"] == again["hero_gallery"]

    assert patch(client, "/settings", {"hero_gallery_asset_ids": []}).json()["hero_gallery"] == []
    assert client.get("/api/v1/site-settings/public").json()["hero"]["gallery"] == []


def test_settings_hero_gallery_rejects_unknown_and_too_many(client):
    missing = patch(client, "/settings", {"hero_gallery_asset_ids": [str(uuid.uuid4())]})
    assert missing.status_code == 422
    item = upload_one(client)
    too_many = patch(client, "/settings", {"hero_gallery_asset_ids": [item["id"]] * 9})
    assert too_many.status_code == 422


def test_settings_reject_a_bad_number_and_unknown_fields(client):
    response = patch(client, "/settings", {"whatsapp_number": "no es numero"})
    assert response.status_code == 422 and error_code(response) == "invalid_whatsapp_number"
    assert patch(client, "/settings", {"precio": 1}).status_code == 422
    assert patch(client, "/settings", {"whatsapp_number": ""}).json()["whatsapp_number"] is None


def test_settings_premium_number_round_trip_and_validation(client):
    saved = patch(client, "/settings", {"whatsapp_premium_number": "+52 55 9999 0000"}).json()
    assert saved["whatsapp_premium_number"] == "+52 55 9999 0000"
    response = patch(client, "/settings", {"whatsapp_premium_number": "123"})
    assert response.status_code == 422 and error_code(response) == "invalid_whatsapp_number"
    assert patch(client, "/settings", {"whatsapp_premium_number": None}).json()["whatsapp_premium_number"] is None


def test_brand_premium_flag_round_trip(client):
    brand = post(client, "/brands", {"name": "Hermès", "is_premium": True}).json()
    assert brand["is_premium"] is True
    updated = patch(client, f"/brands/{brand['id']}", {"is_premium": False}).json()
    assert updated["is_premium"] is False
    assert patch(client, f"/brands/{brand['id']}", {"is_premium": None}).status_code == 422


def test_settings_edits_show_publicly_in_demo_mode_too(db, make_client, make_settings):
    from app.services.demo_seed import seed_demo

    seed_demo(db, make_settings(demo_mode=True))
    db.commit()
    client = make_client(demo_mode=True)
    login(client, make_user(db))
    demo_headline = client.get("/api/v1/site-settings/public").json()["hero"]["headline"]
    assert demo_headline
    patch(client, "/settings", {"hero_headline": "Titular real"})
    assert client.get("/api/v1/site-settings/public").json()["hero"]["headline"] == "Titular real"


# --- Dashboard -------------------------------------------------------------------------


def test_dashboard(db, client, refs):
    published = add_photo(client, create(client, refs, name="Publicada Una"))
    patch(client, f"/products/{published['id']}", {"status": "published"})
    create(client, refs, name="Borrador Una")
    archived = create(client, refs, name="Archivada Una")
    client.delete(f"{BASE}/products/{archived['id']}", headers=ORIGIN)

    product_id = uuid.UUID(published["id"])
    db.add_all(
        [
            CatalogEvent(type="whatsapp_click", product_id=product_id),
            CatalogEvent(
                type="whatsapp_click",
                product_id=product_id,
                occurred_at=utcnow() - timedelta(days=31),
            ),
        ]
    )
    db.commit()
    assert client.get(f"{BASE}/dashboard").json() == {
        "products": {"draft": 1, "published": 1, "archived": 1, "without_photo": 2},
        "brands": {"draft": 1, "published": 1},
        "consult_clicks_30d": 1,
        "whatsapp_configured": False,
    }


def test_operations_are_audited_with_field_changes(db, client, refs):
    product = create(client, refs, name="Antes")
    patch(client, f"/products/{product['id']}", {"name": "Después"})
    row = db.scalar(
        select(AuditLog).where(AuditLog.operation == "update", AuditLog.entity == "product")
    )
    assert row.entity_id == product["id"]
    assert row.changes == {"name": ["Antes", "Después"]}


def test_seeded_categories_work_with_the_admin_list(db, client):
    seed_categories(db)
    db.commit()
    body = client.get(f"{BASE}/categories").json()
    assert body["total"] == len(body["items"]) > 20
