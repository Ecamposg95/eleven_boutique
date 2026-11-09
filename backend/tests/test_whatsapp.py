from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from app.models import KIND_CLASSIFICATION, SiteSettings
from app.services.base_seed import seed_site_settings
from app.services.whatsapp import build_consult_url, normalize_number
from tests.factories import make_brand, make_category, make_product

FAKE_NUMBER = "+52 55 0000 0000"
FAKE_DIGITS = "525500000000"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (FAKE_NUMBER, FAKE_DIGITS),
        ("+52 (55) 0000-0000", FAKE_DIGITS),
        (FAKE_DIGITS, FAKE_DIGITS),
        ("12345678", "12345678"),
        ("123456789012345", "123456789012345"),
        ("1234567", None),
        ("1234567890123456", None),
        ("+05 55 0000 0000", None),
        ("55-CALL-NOW", None),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalize_number(raw, expected):
    assert normalize_number(raw) == expected


def message_of(url: str) -> str:
    return parse_qs(urlsplit(url).query, strict_parsing=True)["text"][0]


def test_exact_template_and_encoding(db, make_client):
    brand = make_brand(db, "Dolce & Gabbana")
    make_product(db, brand, make_category(db), "Camisa Línea Ñ", slug="camisa", sku="DG-001")
    db.commit()
    client = make_client(whatsapp_number=FAKE_NUMBER)
    url = client.get("/api/v1/products/camisa").json()["consult_url"]
    assert url == (
        "https://wa.me/525500000000?text="
        "Hola%2C%20me%20interesa%20conocer%20m%C3%A1s%20sobre%20esta%20pieza%20de%20Eleven%20Boutique"
        "%3A%20Dolce%20%26%20Gabbana%20%E2%80%94%20Camisa%20L%C3%ADnea%20%C3%91."
        "%20Referencia%3A%20DG-001."
        "%20Enlace%3A%20https%3A%2F%2Feleven.example%2Fmarcas%2Fdolce-gabbana%2Fcamisa."
        "%20%C2%BFPodr%C3%ADan%20brindarme%20atenci%C3%B3n%20personalizada%3F"
    )
    assert message_of(url) == (
        "Hola, me interesa conocer más sobre esta pieza de Eleven Boutique: "
        "Dolce & Gabbana — Camisa Línea Ñ. Referencia: DG-001. "
        "Enlace: https://eleven.example/marcas/dolce-gabbana/camisa. "
        "¿Podrían brindarme atención personalizada?"
    )


def test_sin_marca_variant(db, make_client):
    classification = make_brand(db, "Sin marca", kind=KIND_CLASSIFICATION)
    make_product(db, classification, make_category(db), "Pañuelo", slug="panuelo", sku="X-1")
    db.commit()
    url = make_client(whatsapp_number=FAKE_NUMBER).get("/api/v1/products/panuelo").json()["consult_url"]
    assert message_of(url) == (
        "Hola, me interesa conocer más sobre esta pieza de Eleven Boutique: Pañuelo. "
        "Referencia: X-1. Enlace: https://eleven.example/piezas/panuelo. "
        "¿Podrían brindarme atención personalizada?"
    )


def test_trailing_slash_in_site_url_is_ignored():
    url = build_consult_url(
        digits=FAKE_DIGITS,
        site_url="https://eleven.example/",
        brand_slug="prada",
        brand_name="Prada",
        name="Bolso",
        slug="bolso",
        sku="P-1",
    )
    assert "https://eleven.example/marcas/prada/bolso." in message_of(url)


@pytest.mark.parametrize("number", ["", "123", "+05 55 0000 0000", "no-es-numero"])
def test_null_when_number_missing_or_invalid(db, make_client, number):
    make_product(db, make_brand(db), make_category(db), "Pieza")
    db.commit()
    client = make_client(whatsapp_number=number)
    assert client.get("/api/v1/products/pieza").json()["consult_url"] is None
    assert client.get("/api/v1/site-settings/public").json()["whatsapp_enabled"] is False


def test_site_settings_number_is_seeded_from_env_and_wins_afterwards(db, make_client, make_settings):
    make_product(db, make_brand(db), make_category(db), "Pieza")
    seed_site_settings(db, make_settings(whatsapp_number=FAKE_NUMBER))
    db.commit()
    row = db.scalar(select(SiteSettings).where(SiteSettings.is_demo.is_(False)))
    assert row.whatsapp_number == FAKE_NUMBER

    # The stored number works without the env var, and an operator's edit survives a re-seed.
    client = make_client(whatsapp_number="")
    assert FAKE_DIGITS in client.get("/api/v1/products/pieza").json()["consult_url"]
    row.whatsapp_number = "+52 55 0000 0001"
    seed_site_settings(db, make_settings(whatsapp_number=FAKE_NUMBER))
    db.commit()
    assert db.scalar(select(SiteSettings.whatsapp_number)) == "+52 55 0000 0001"


def test_invalid_stored_number_does_not_fall_back_to_env(db, make_client):
    make_product(db, make_brand(db), make_category(db), "Pieza")
    db.add(SiteSettings(is_demo=False, whatsapp_number="invalido"))
    db.commit()
    client = make_client(whatsapp_number=FAKE_NUMBER)
    assert client.get("/api/v1/products/pieza").json()["consult_url"] is None


def test_number_is_not_exposed_in_settings(make_client):
    body = make_client(whatsapp_number=FAKE_NUMBER).get("/api/v1/site-settings/public")
    assert body.json()["whatsapp_enabled"] is True
    assert FAKE_DIGITS not in body.text and "0000" not in body.text
