from urllib.parse import parse_qs, urlsplit

from app.models import KIND_CLASSIFICATION, STATUS_DRAFT
from tests.factories import make_brand, make_category, make_product

NUMBER, DIGITS = "+52 55 0000 0000", "525500000000"
PREMIUM, PREMIUM_DIGITS = "+52 55 9999 0000", "525599990000"


def message_of(url: str) -> str:
    return parse_qs(urlsplit(url).query, strict_parsing=True)["text"][0]


def consult(client, *slugs):
    return client.post("/api/v1/selection/consult", json={"product_slugs": list(slugs)})


def test_several_pieces_go_in_one_message_in_the_visitors_order(db, make_client):
    category = make_category(db)
    prada = make_brand(db, "Prada")
    make_product(db, prada, category, "Bolso", slug="bolso", sku="P-1")
    make_product(db, prada, category, "Mocasín", slug="mocasin", sku="P-2")
    unbranded = make_brand(db, "Sin marca", kind=KIND_CLASSIFICATION)
    make_product(db, unbranded, category, "Pañuelo", slug="panuelo", sku="X-1")
    db.commit()
    body = consult(make_client(whatsapp_number=NUMBER), "mocasin", "panuelo", "bolso", "mocasin").json()
    assert body["missing_slugs"] == []
    [line] = body["lines"]
    assert line["product_slugs"] == ["mocasin", "panuelo", "bolso"]
    assert line["url"].startswith(f"https://wa.me/{DIGITS}?text=")
    assert message_of(line["url"]) == (
        "Hola, me interesa conocer más sobre estas piezas de Eleven Boutique:\n\n"
        "1. Prada — Mocasín. Referencia: P-2. Enlace: https://eleven.example/marcas/prada/mocasin\n"
        "2. Pañuelo. Referencia: X-1. Enlace: https://eleven.example/piezas/panuelo\n"
        "3. Prada — Bolso. Referencia: P-1. Enlace: https://eleven.example/marcas/prada/bolso\n\n"
        "¿Podrían brindarme atención personalizada?"
    )


def test_single_piece_uses_the_product_template(db, make_client):
    make_product(db, make_brand(db, "Prada"), make_category(db), "Bolso", slug="bolso", sku="P-1")
    db.commit()
    client = make_client(whatsapp_number=NUMBER)
    [line] = consult(client, "bolso").json()["lines"]
    assert line["url"] == client.get("/api/v1/products/bolso").json()["consult_url"]


def test_premium_pieces_are_split_to_the_boutique_line(db, make_client):
    category = make_category(db)
    make_product(db, make_brand(db, "Hermès", is_premium=True), category, "Bolso", slug="bolso")
    make_product(db, make_brand(db, "Básicos"), category, "Playera", slug="playera")
    db.commit()
    client = make_client(whatsapp_number=NUMBER, whatsapp_premium_number=PREMIUM)
    lines = consult(client, "playera", "bolso").json()["lines"]
    assert [(urlsplit(x["url"]).path, x["product_slugs"], x["boutique"]) for x in lines] == [
        (f"/{DIGITS}", ["playera"], False),
        (f"/{PREMIUM_DIGITS}", ["bolso"], True),
    ]


def test_without_premium_line_everything_shares_one_message(db, make_client):
    category = make_category(db)
    make_product(db, make_brand(db, "Hermès", is_premium=True), category, "Bolso", slug="bolso")
    make_product(db, make_brand(db, "Básicos"), category, "Playera", slug="playera")
    db.commit()
    [line] = consult(make_client(whatsapp_number=NUMBER), "bolso", "playera").json()["lines"]
    assert line["product_slugs"] == ["bolso", "playera"]
    assert line["boutique"] is False


def test_only_premium_line_serves_premium_pieces_and_skips_the_rest(db, make_client):
    category = make_category(db)
    make_product(db, make_brand(db, "Hermès", is_premium=True), category, "Bolso", slug="bolso")
    make_product(db, make_brand(db, "Básicos"), category, "Playera", slug="playera")
    db.commit()
    body = consult(make_client(whatsapp_premium_number=PREMIUM), "bolso", "playera").json()
    assert [(x["product_slugs"], x["boutique"]) for x in body["lines"]] == [(["bolso"], True)]
    assert body["missing_slugs"] == []


def test_hidden_and_unknown_pieces_are_reported_missing(db, make_client):
    category = make_category(db)
    brand = make_brand(db)
    make_product(db, brand, category, "Visible", slug="visible")
    make_product(db, brand, category, "Oculta", slug="oculta", status=STATUS_DRAFT)
    db.commit()
    body = consult(make_client(whatsapp_number=NUMBER), "oculta", "visible", "no-existe").json()
    assert body["missing_slugs"] == ["oculta", "no-existe"]
    assert [line["product_slugs"] for line in body["lines"]] == [["visible"]]


def test_no_number_means_no_lines(db, make_client):
    make_product(db, make_brand(db), make_category(db), "Pieza", slug="pieza")
    db.commit()
    assert consult(make_client(whatsapp_number=""), "pieza").json() == {"lines": [], "missing_slugs": []}


def test_selection_size_is_bounded(make_client):
    client = make_client(whatsapp_number=NUMBER)
    assert consult(client).status_code == 422
    assert consult(client, *[f"p{i}" for i in range(25)]).status_code == 422
