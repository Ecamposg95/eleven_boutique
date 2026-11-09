import pytest
from sqlalchemy import select, update

from app.models import STATUS_DRAFT, STATUS_PUBLISHED, Brand
from app.services.brand_import import run_import
from tests.factories import make_alias, make_brand, make_category, make_product


@pytest.fixture
def imported(db):
    run_import(db)
    db.commit()
    return db


@pytest.fixture
def published(imported):
    imported.execute(update(Brand).values(status=STATUS_PUBLISHED))
    imported.commit()
    return imported


@pytest.mark.parametrize(
    ("query", "slug"),
    [
        ("BAPE", "a-bathing-ape"),
        ("bape", "a-bathing-ape"),
        ("A Bathing Ape", "a-bathing-ape"),
        ("canada", "canada-goose"),
        ("Canadá", "canada-goose"),
        ("hermes", "hermes"),
        ("HERMÈS", "hermes"),
        ("levis", "levis"),
        ("Levi's", "levis"),
        ("offwhite", "off-white"),
        ("off white", "off-white"),
        ("off-white", "off-white"),
        ("salvatore", "ferragamo"),
    ],
)
@pytest.mark.parametrize("client_fixture", ["public_client", "demo_client"])
def test_search_finds_a_single_brand(published, request, client_fixture, query, slug):
    client = request.getfixturevalue(client_fixture)
    search = client.get("/api/v1/search", params={"q": query}).json()
    assert [brand["slug"] for brand in search["brands"]] == [slug]
    listing = client.get("/api/v1/brands", params={"q": query}).json()
    assert [brand["slug"] for brand in listing["items"]] == [slug]


def test_unpublished_brands_are_not_searchable_without_demo_mode(imported, public_client):
    assert public_client.get("/api/v1/search", params={"q": "bape"}).json()["brands"] == []


def test_draft_brands_are_searchable_in_demo_mode(imported, demo_client):
    brands = demo_client.get("/api/v1/search", params={"q": "bape"}).json()["brands"]
    assert [brand["slug"] for brand in brands] == ["a-bathing-ape"]


def test_sin_marca_is_never_a_search_result(published, public_client, demo_client):
    for client in (public_client, demo_client):
        assert client.get("/api/v1/search", params={"q": "sin marca"}).json()["brands"] == []
        assert client.get("/api/v1/brands", params={"q": "sin marca"}).json()["items"] == []


@pytest.mark.parametrize("wildcard", ["%", "_", "a%e", "pr_da", "\\"])
def test_like_wildcards_are_literal(published, public_client, wildcard):
    search = public_client.get("/api/v1/search", params={"q": wildcard}).json()
    assert search == {"brands": [], "products": []}
    assert public_client.get("/api/v1/brands", params={"q": wildcard}).json()["items"] == []


@pytest.mark.parametrize("empty", ["", "   ", "-", "..."])
def test_blank_search_returns_nothing(published, public_client, empty):
    assert public_client.get("/api/v1/search", params={"q": empty}).json() == {
        "brands": [],
        "products": [],
    }


def test_missing_q_returns_nothing(published, public_client):
    assert public_client.get("/api/v1/search").json() == {"brands": [], "products": []}


def test_product_search_by_name_brand_alias_and_category(db, public_client):
    ropa = make_category(db, "Ropa")
    camisas = make_category(db, "Camisas", parent=ropa)
    calzado = make_category(db, "Calzado")
    brand = make_brand(db, "Hermès")
    other = make_brand(db, "Prada")
    make_alias(db, brand, "Maison H")
    make_product(db, brand, camisas, "Camisa Lúcida")
    make_product(db, other, calzado, "Bota Noche")
    db.commit()

    def found(query):
        response = public_client.get("/api/v1/search", params={"q": query}).json()
        return [product["slug"] for product in response["products"]]

    assert found("lucida") == ["camisa-lucida"]
    assert found("HERMES") == ["camisa-lucida"]
    assert found("maison h") == ["camisa-lucida"]
    assert found("camisas") == ["camisa-lucida"]
    assert found("ropa") == ["camisa-lucida"]
    assert found("calzado") == ["bota-noche"]
    assert found("inexistente") == []


def test_draft_product_is_absent_from_search(db, public_client):
    brand = make_brand(db, "Loewe")
    category = make_category(db)
    make_product(db, brand, category, "Bolso Borrador", status=STATUS_DRAFT)
    db.commit()
    assert public_client.get("/api/v1/search", params={"q": "borrador"}).json()["products"] == []
    assert public_client.get("/api/v1/search", params={"q": "loewe"}).json()["products"] == []


def test_sin_marca_does_not_match_its_products_by_classification_name(db, public_client):
    run_import(db)
    sin_marca = db.scalar(select(Brand).where(Brand.slug == "sin-marca"))
    make_product(db, sin_marca, make_category(db), "Pañuelo Azul")
    db.commit()
    assert public_client.get("/api/v1/search", params={"q": "sin marca"}).json()["products"] == []
    found = public_client.get("/api/v1/search", params={"q": "panuelo"}).json()["products"]
    assert [product["slug"] for product in found] == ["panuelo-azul"]
