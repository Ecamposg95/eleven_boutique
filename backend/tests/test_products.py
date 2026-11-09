import pytest

from app.models import (
    KIND_CLASSIFICATION,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
)
from tests.factories import at, make_alias, make_brand, make_category, make_product


def slugs(response) -> list[str]:
    return [item["slug"] for item in response.json()["items"]]


def test_draft_product_is_hidden_until_published(db, public_client):
    brand = make_brand(db, "Prada")
    category = make_category(db)
    product = make_product(db, brand, category, "Bolso Nuevo", status=STATUS_DRAFT)
    db.commit()

    assert public_client.get("/api/v1/products/bolso-nuevo").status_code == 404
    assert slugs(public_client.get("/api/v1/products")) == []
    assert slugs(public_client.get("/api/v1/products", params={"brand": "prada"})) == []
    assert public_client.get("/api/v1/brands/prada").json()["product_count"] == 0

    product.status = STATUS_PUBLISHED
    db.commit()

    assert public_client.get("/api/v1/products/bolso-nuevo").status_code == 200
    assert slugs(public_client.get("/api/v1/products", params={"brand": "prada"})) == ["bolso-nuevo"]
    assert public_client.get("/api/v1/brands/prada").json()["product_count"] == 1
    assert public_client.get("/api/v1/products/bolso-nuevo").json()["brand"] == {
        "slug": "prada",
        "name": "Prada",
    }


def test_archived_product_is_hidden(db, public_client, demo_client):
    make_product(
        db, make_brand(db), make_category(db), "Viejo", status=STATUS_ARCHIVED, is_demo=True
    )
    db.commit()
    assert public_client.get("/api/v1/products/viejo").status_code == 404
    assert demo_client.get("/api/v1/products/viejo").status_code == 404


def test_published_product_of_an_unpublished_brand_is_hidden(db, public_client):
    brand = make_brand(db, "Sin Revisar", status=STATUS_DRAFT)
    make_product(db, brand, make_category(db), "Pieza")
    db.commit()
    assert public_client.get("/api/v1/products/pieza").status_code == 404
    assert slugs(public_client.get("/api/v1/products")) == []


def test_filters_and_pagination(db, public_client):
    ropa = make_category(db, "Ropa")
    camisas = make_category(db, "Camisas", parent=ropa)
    calzado = make_category(db, "Calzado")
    prada = make_brand(db, "Prada")
    make_alias(db, prada, "Prada Milano")
    loewe = make_brand(db, "Loewe")
    make_product(db, prada, camisas, "Uno", is_featured=True, display_order=3)
    make_product(db, prada, calzado, "Dos", display_order=1)
    make_product(db, loewe, calzado, "Tres", display_order=2)
    db.commit()

    get = lambda **params: public_client.get("/api/v1/products", params=params)  # noqa: E731
    assert slugs(get()) == ["dos", "tres", "uno"]
    assert slugs(get(sort="name")) == ["dos", "tres", "uno"]
    assert slugs(get(brand="prada")) == ["dos", "uno"]
    assert slugs(get(brand="prada-milano")) == ["dos", "uno"]
    assert slugs(get(brand="no-existe")) == []
    assert slugs(get(category="camisas")) == ["uno"]
    assert slugs(get(category="ropa")) == ["uno"]
    assert slugs(get(featured="true")) == ["uno"]
    page = get(page=2, page_size=2).json()
    assert page["total"] == 3 and page["page"] == 2 and page["page_size"] == 2
    assert [item["slug"] for item in page["items"]] == ["uno"]
    default = get().json()
    assert default["page"] == 1 and default["page_size"] == 24


def test_recent_sort_puts_undated_products_last(db, public_client):
    brand = make_brand(db)
    category = make_category(db)
    make_product(db, brand, category, "Sin Fecha")
    make_product(db, brand, category, "Antigua", commercial_added_at=at(2024))
    make_product(db, brand, category, "Nueva", commercial_added_at=at(2026))
    db.commit()
    response = public_client.get("/api/v1/products", params={"sort": "recent"})
    assert slugs(response) == ["nueva", "antigua", "sin-fecha"]


def test_novedades_uses_commercial_date_not_load_date(db, public_client):
    brand = make_brand(db)
    category = make_category(db)
    # Loaded recently but commercially old, and the other way around.
    make_product(db, brand, category, "Recien Cargada", commercial_added_at=at(2020), created_at=at(2026))
    make_product(db, brand, category, "Novedad Real", commercial_added_at=at(2026), created_at=at(2020))
    make_product(db, brand, category, "Sin Fecha Comercial", created_at=at(2026, 6))
    make_product(
        db, brand, category, "Borrador", commercial_added_at=at(2027), status=STATUS_DRAFT
    )
    db.commit()
    response = public_client.get("/api/v1/novedades")
    assert slugs(response) == ["novedad-real", "recien-cargada"]
    assert response.json()["total"] == 2


def test_sin_marca_product_is_public_with_null_brand(db, public_client):
    classification = make_brand(
        db, "Sin marca", kind=KIND_CLASSIFICATION, status=STATUS_DRAFT
    )
    make_product(db, classification, make_category(db), "Pieza Libre")
    db.commit()
    detail = public_client.get("/api/v1/products/pieza-libre").json()
    assert detail["brand"] == {"slug": None, "name": None}
    assert slugs(public_client.get("/api/v1/products")) == ["pieza-libre"]
    assert slugs(public_client.get("/api/v1/products", params={"brand": "sin-marca"})) == []


@pytest.mark.parametrize("status", [STATUS_DRAFT, STATUS_PUBLISHED])
def test_sin_marca_is_never_a_public_brand(db, public_client, demo_client, status):
    make_brand(db, "Sin marca", kind=KIND_CLASSIFICATION, status=status)
    db.commit()
    for client in (public_client, demo_client):
        assert client.get("/api/v1/brands/sin-marca").status_code == 404
        assert client.get("/api/v1/brands").json()["items"] == []


def test_card_images_and_gallery(db, public_client):
    make_product(db, make_brand(db), make_category(db), "Pieza")
    db.commit()
    detail = public_client.get("/api/v1/products/pieza").json()
    assert detail["primary_image"] == {
        "url": "/media/pieza-a.jpg",
        "alt": "Pieza frente",
        "is_primary": True,
        "position": 0,
    }
    assert detail["secondary_image"]["url"] == "/media/pieza-b.jpg"
    assert [media["position"] for media in detail["gallery"]] == [0, 1]


def test_published_at_is_utc_iso(db, public_client):
    make_product(db, make_brand(db), make_category(db), "Pieza", published_at=at(2026, 3, 2))
    db.commit()
    assert public_client.get("/api/v1/products/pieza").json()["published_at"] == "2026-03-02T00:00:00Z"
