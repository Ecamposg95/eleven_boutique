import re
from urllib.parse import parse_qs, urlsplit

from app.models import KIND_CLASSIFICATION, STATUS_DRAFT, SiteSettings
from tests.factories import make_brand, make_category, make_product

NUMBER, DIGITS = "+52 55 0000 0000", "525500000000"
PREMIUM, PREMIUM_DIGITS = "+52 55 9999 0000", "525599990000"
GENERAL_MESSAGE = "Hola, me gustaría recibir atención personalizada de Eleven Boutique."


def settings_of(client) -> dict:
    return client.get("/api/v1/site-settings/public").json()


def test_attention_defaults_and_links(make_client):
    attention = settings_of(make_client(whatsapp_number=NUMBER))["attention"]
    assert attention["headline"] == "Escríbenos. Te asesoramos."
    assert attention["subhead"] is None
    assert attention["whatsapp_url"].startswith(f"https://wa.me/{DIGITS}?")
    assert parse_qs(urlsplit(attention["whatsapp_url"]).query)["text"] == [GENERAL_MESSAGE]
    assert attention["boutique_whatsapp_url"] is None

    both = settings_of(make_client(whatsapp_number=NUMBER, whatsapp_premium_number=PREMIUM))
    assert both["attention"]["boutique_whatsapp_url"].startswith(f"https://wa.me/{PREMIUM_DIGITS}?")

    same = settings_of(make_client(whatsapp_number=NUMBER, whatsapp_premium_number=NUMBER))
    assert same["attention"]["boutique_whatsapp_url"] is None

    none = settings_of(make_client())["attention"]
    assert none["whatsapp_url"] is None and none["boutique_whatsapp_url"] is None


def test_attention_never_exposes_the_number_outside_links(make_client):
    client = make_client(whatsapp_number=NUMBER, whatsapp_premium_number=PREMIUM)
    body = client.get("/api/v1/site-settings/public").text
    assert DIGITS in body  # inside the wa.me link
    stripped = re.sub(r"https://wa\.me/[^\"]*", "", body)
    for needle in (DIGITS, PREMIUM_DIGITS, "0000 0000", "9999 0000"):
        assert needle not in stripped


def test_stored_attention_detail_and_instagram_are_public(db, make_client):
    db.add(
        SiteSettings(
            is_demo=False,
            instagram_url="https://instagram.com/eleven",
            detail_image_url="/media/d.jpg",
            detail_mobile_image_url="/media/dm.jpg",
            detail_caption="Hecho a mano",
            attention_image_url="/media/a.jpg",
            attention_mobile_image_url="/media/am.jpg",
            attention_headline="Hablemos",
            attention_subhead="Con gusto",
        )
    )
    db.commit()
    body = settings_of(make_client())
    assert body["instagram_url"] == "https://instagram.com/eleven"
    assert body["detail"] == {
        "image_url": "/media/d.jpg",
        "mobile_image_url": "/media/dm.jpg",
        "caption": "Hecho a mano",
    }
    attention = body["attention"]
    assert (attention["headline"], attention["subhead"]) == ("Hablemos", "Con gusto")
    assert (attention["image_url"], attention["mobile_image_url"]) == ("/media/a.jpg", "/media/am.jpg")


def test_category_cover_url_is_public(db, public_client):
    category = make_category(db, "Ropa")
    category.cover_url = "/media/ropa.jpg"
    make_category(db, "Calzado")
    db.commit()
    items = public_client.get("/api/v1/categories").json()["items"]
    assert {c["slug"]: c["cover_url"] for c in items} == {"ropa": "/media/ropa.jpg", "calzado": None}


def test_brand_facets_follow_category_and_children(db, public_client):
    ropa = make_category(db, "Ropa")
    camisas = make_category(db, "Camisas", parent=ropa)
    calzado = make_category(db, "Calzado")
    a = make_brand(db, "Alfa")
    b = make_brand(db, "Beta")
    make_product(db, a, camisas, "Camisa", slug="camisa")
    make_product(db, a, camisas, "Borrador", slug="borrador", status=STATUS_DRAFT)
    make_product(db, b, calzado, "Zapato", slug="zapato")
    unbranded = make_brand(db, "Sin marca", kind=KIND_CLASSIFICATION)
    make_product(db, unbranded, camisas, "Pañuelo", slug="panuelo")
    db.commit()

    def facets(**params):
        return public_client.get("/api/v1/brand-facets", params=params).json()["items"]

    assert facets(category="ropa") == [{"slug": "alfa", "name": "Alfa", "product_count": 1}]
    assert facets() == [
        {"slug": "alfa", "name": "Alfa", "product_count": 1},
        {"slug": "beta", "name": "Beta", "product_count": 1},
    ]
    assert facets(category="inexistente") == []


def test_attention_with_only_the_boutique_line(make_client):
    attention = settings_of(make_client(whatsapp_premium_number=PREMIUM))["attention"]
    assert attention["whatsapp_url"] is None
    assert attention["boutique_whatsapp_url"].startswith(f"https://wa.me/{PREMIUM_DIGITS}?")


def test_cleared_instagram_is_null(db, make_client):
    db.add(SiteSettings(is_demo=False, instagram_url=None))
    db.commit()
    assert settings_of(make_client())["instagram_url"] is None


def test_brand_facets_in_demo_mode_include_demo_pieces_only_there(db, make_client):
    ropa = make_category(db, "Ropa")
    brand = make_brand(db, "Demo Marca", status=STATUS_DRAFT)
    make_product(
        db, brand, ropa, "Pieza Demo", slug="pieza-demo", status=STATUS_DRAFT, is_demo=True
    )
    db.commit()

    def facets(client):
        return client.get("/api/v1/brand-facets", params={"category": "ropa"}).json()["items"]

    expected = [{"slug": "demo-marca", "name": "Demo Marca", "product_count": 1}]
    assert facets(make_client(demo_mode=True)) == expected
    assert facets(make_client(demo_mode=False)) == []
