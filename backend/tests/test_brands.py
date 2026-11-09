from sqlalchemy import update

from app.data.brand_source import SOURCE_BRANDS
from app.models import STATUS_ARCHIVED, STATUS_DRAFT, STATUS_PUBLISHED, Brand
from app.services.brand_import import run_import
from app.services.text import slugify
from tests.factories import make_brand, make_category, make_product


def test_brand_directory_counts_and_order(db, public_client):
    run_import(db)
    db.execute(update(Brand).values(status=STATUS_PUBLISHED))
    db.commit()
    items = public_client.get("/api/v1/brands").json()["items"]
    assert len(items) == 85
    assert "sin-marca" not in {item["slug"] for item in items}
    names = [item["name"] for item in items]
    # Accent-insensitive: Hermès between Hellstar and Human Made.
    assert names.index("Hellstar") < names.index("Hermès") < names.index("Human Made")
    assert names[0] == "A Bathing Ape / BAPE"
    assert names[-1] == "Zegna"


def test_alias_slug_resolves_to_the_brand(db, public_client):
    run_import(db)
    db.execute(update(Brand).values(status=STATUS_PUBLISHED))
    db.commit()
    canonical = public_client.get("/api/v1/brands/a-bathing-ape").json()
    assert public_client.get("/api/v1/brands/bape").json() == canonical
    assert canonical["slug"] == "a-bathing-ape"
    assert canonical["aliases"] == ["A Bathing Ape", "BAPE"]
    ami = public_client.get("/api/v1/brands/ami-alexandre-mattiussi").json()
    assert ami["slug"] == "ami-paris" and ami["aliases"] == ["Ami Alexandre Mattiussi"]
    assert public_client.get("/api/v1/brands/salvatore-ferragamo").json()["slug"] == "ferragamo"


def test_every_source_name_resolves_over_http(db, demo_client):
    run_import(db)
    db.commit()
    for source in SOURCE_BRANDS:
        slug = slugify(source)
        response = demo_client.get(f"/api/v1/brands/{slug}")
        assert response.status_code == (404 if source == "Sin marca" else 200), source


def test_spelling_fix_is_not_shown_as_a_public_alias(db, demo_client):
    run_import(db)
    db.commit()
    assert demo_client.get("/api/v1/brands/canada-goose").json()["aliases"] == []


def test_visibility_of_brand_states(db, public_client, demo_client):
    make_brand(db, "Publicada")
    make_brand(db, "Borrador", status=STATUS_DRAFT)
    make_brand(db, "Archivada", status=STATUS_ARCHIVED)
    db.commit()
    names = lambda client: [b["slug"] for b in client.get("/api/v1/brands").json()["items"]]  # noqa: E731
    assert names(public_client) == ["publicada"]
    assert names(demo_client) == ["borrador", "publicada"]
    assert public_client.get("/api/v1/brands/borrador").status_code == 404
    assert demo_client.get("/api/v1/brands/borrador").status_code == 200
    assert demo_client.get("/api/v1/brands/archivada").status_code == 404


def test_featured_brands_follow_display_order(db, public_client):
    make_brand(db, "Chanel", is_featured=True, display_order=2)
    make_brand(db, "Rolex", is_featured=True, display_order=1)
    make_brand(db, "Hermès", is_featured=True, display_order=1)
    make_brand(db, "Acne Studios", display_order=0)
    db.commit()
    featured = public_client.get("/api/v1/brands", params={"featured": "true"}).json()["items"]
    assert [b["name"] for b in featured] == ["Hermès", "Rolex", "Chanel"]
    everyone = public_client.get("/api/v1/brands").json()["items"]
    assert [b["name"] for b in everyone] == ["Acne Studios", "Chanel", "Hermès", "Rolex"]


def test_featured_filter(db, public_client):
    make_brand(db, "Destacada", is_featured=True)
    make_brand(db, "Normal")
    db.commit()
    items = public_client.get("/api/v1/brands", params={"featured": "true"}).json()["items"]
    assert [item["slug"] for item in items] == ["destacada"]


def test_product_count_only_counts_visible_products(db, public_client, demo_client):
    brand = make_brand(db, "Prada")
    category = make_category(db)
    make_product(db, brand, category, "Visible")
    make_product(db, brand, category, "Borrador", status=STATUS_DRAFT)
    make_product(db, brand, category, "Demo", is_demo=True, status=STATUS_DRAFT)
    make_product(db, brand, category, "Demo Publicada", is_demo=True)
    db.commit()
    assert public_client.get("/api/v1/brands").json()["items"][0]["product_count"] == 1
    assert public_client.get("/api/v1/brands/prada").json()["product_count"] == 1
    assert demo_client.get("/api/v1/brands/prada").json()["product_count"] == 3
