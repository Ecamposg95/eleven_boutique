import pytest

from app.services.text import build_search_text, escape_like, normalize, slugify


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hermès", "hermes"),
        ("Canadá Goose", "canada goose"),
        ("Levi's", "levis"),
        ("Levi’s", "levis"),
        ("Arc'teryx", "arcteryx"),
        ("Off-White", "off white"),
        ("Gallery Dept.", "gallery dept"),
        ("Dolce & Gabbana", "dolce gabbana"),
        ("Comme des Garçons", "comme des garcons"),
        ("A Bathing Ape / BAPE", "a bathing ape bape"),
        ("  BAPE  ", "bape"),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_search_text_includes_compact_form():
    assert build_search_text("Off-White") == "off white offwhite"
    assert build_search_text("Prada") == "prada"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Levi's", "levis"),
        ("Tiffany & Co.", "tiffany-co"),
        ("VSTAR 2", "vstar-2"),
        ("Enfants Riches Déprimés", "enfants-riches-deprimes"),
        ("Pañuelos", "panuelos"),
        ("Artículos de viaje", "articulos-de-viaje"),
    ],
)
def test_slugify(raw, expected):
    assert slugify(raw) == expected


def test_escape_like():
    assert escape_like(r"50%_a\b") == r"50\%\_a\\b"
