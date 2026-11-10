import os
import subprocess
import sys

import pytest
from sqlalchemy import func, select, update

from app.config import BASE_DIR
from app.models import (
    STATUS_PUBLISHED,
    Brand,
    BrandAlias,
    Category,
    Collection,
    CollectionProduct,
    Lookbook,
    LookbookBlock,
    Product,
    ProductMedia,
    SiteSettings,
)
from app.services.demo_seed import DemoModeRequired, seed_demo
from tests.factories import make_brand, make_category, make_product


@pytest.fixture
def seeded(db, make_settings):
    seed_demo(db, make_settings(demo_mode=True))
    db.commit()
    return db


def count(db, model, *criteria) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*criteria))


def test_refuses_to_run_without_demo_mode(db, make_settings):
    with pytest.raises(DemoModeRequired):
        seed_demo(db, make_settings(demo_mode=False))
    assert count(db, Product) == 0
    assert count(db, Brand) == 0


def test_script_exits_non_zero_without_demo_mode(database_url):
    result = subprocess.run(
        [sys.executable, "-m", "scripts.seed_demo"],
        cwd=BASE_DIR,
        env={**os.environ, "DEMO_MODE": "false", "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "DEMO_MODE" in result.stderr


def test_exact_contents(seeded):
    db = seeded
    products = db.scalars(select(Product).order_by(Product.sku)).all()
    assert [p.sku for p in products] == [f"DEMO-{n:03d}" for n in range(1, 13)]
    assert [p.slug for p in products] == [f"pieza-demostracion-{n:02d}" for n in range(1, 13)]
    assert [p.name for p in products] == [f"Pieza de demostración {n:02d}" for n in range(1, 13)]
    assert all(p.is_demo for p in products)
    assert sum(p.is_featured for p in products) == 4
    assert sum(p.commercial_added_at is not None for p in products) == 8
    assert len({p.category_id for p in products}) >= 4

    brands = {p.brand.name for p in products}
    assert brands == {
        "Acne Studios",
        "Balenciaga",
        "Loewe",
        "Prada",
        "Common Projects",
        "Rick Owens",
        "Sin marca",
    }
    assert sum(p.brand.slug == "sin-marca" for p in products) == 1
    assert count(db, Brand, Brand.is_featured.is_(True)) == 6

    for number, product in enumerate(products, start=1):
        assert [m.url for m in product.media] == [
            f"/demo/pieza-{number:02d}-a.jpg",
            f"/demo/pieza-{number:02d}-b.jpg",
        ]
        assert all("demostración" in m.alt.casefold() for m in product.media)

    collections = db.scalars(select(Collection).order_by(Collection.title)).all()
    assert [c.title for c in collections] == [
        "Selección de demostración A",
        "Selección de demostración B",
    ]
    assert all(c.is_demo for c in collections)
    lookbook = db.scalar(select(Lookbook))
    assert lookbook.title == "Lookbook de demostración" and lookbook.is_demo
    assert {block.type for block in lookbook.blocks} == {"text", "image"}


def test_import_stays_intact_and_brands_are_not_published(seeded):
    assert count(seeded, Brand) == 86
    assert count(seeded, BrandAlias) == 89
    assert count(seeded, Brand, Brand.status != "draft") == 0
    assert count(seeded, Product, Product.status != "draft") == 0


def test_idempotent(seeded, make_settings):
    db = seeded
    tables = [Brand, BrandAlias, Category, Product, ProductMedia, Collection, Lookbook, LookbookBlock, SiteSettings]
    before = [count(db, table) for table in tables]
    seed_demo(db, make_settings(demo_mode=True))
    db.commit()
    assert [count(db, table) for table in tables] == before


def test_demo_mode_serves_the_catalog(seeded, demo_client):
    brands = demo_client.get("/api/v1/brands").json()["items"]
    assert len(brands) == 85
    assert "sin-marca" not in {brand["slug"] for brand in brands}
    assert len(demo_client.get("/api/v1/brands?featured=true").json()["items"]) == 6
    assert demo_client.get("/api/v1/products").json()["total"] == 12
    assert demo_client.get("/api/v1/products?featured=true").json()["total"] == 4
    assert demo_client.get("/api/v1/novedades").json()["total"] == 8
    assert len(demo_client.get("/api/v1/collections").json()["items"]) == 2
    collection = demo_client.get("/api/v1/collections/seleccion-demostracion-a").json()
    assert collection["product_count"] == len(collection["products"]) > 0
    lookbook = demo_client.get("/api/v1/lookbooks/lookbook-demostracion").json()
    assert {block["type"] for block in lookbook["blocks"]} == {"text", "image"}
    assert lookbook["products"]
    detail = demo_client.get("/api/v1/products/pieza-demostracion-01").json()
    assert detail["consult_url"] is None
    assert detail["gallery"][0]["url"] == "/demo/pieza-01-a.jpg"
    sin_marca = [
        item
        for item in demo_client.get("/api/v1/products?page_size=60").json()["items"]
        if item["brand"]["slug"] is None
    ]
    assert len(sin_marca) == 1 and sin_marca[0]["brand"]["name"] is None


def test_demo_settings_are_visibly_demo_text(seeded, demo_client):
    settings = demo_client.get("/api/v1/site-settings/public").json()
    assert settings["demo_mode"] is True
    assert settings["whatsapp_enabled"] is False
    assert settings["site_name"] == "Eleven Boutique"
    for text in (
        settings["hero"]["headline"],
        settings["hero"]["subhead"],
        settings["intro"],
        settings["boutique"]["body"],
        settings["contact"]["body"],
    ):
        assert text.startswith("Texto de demostración")


def test_demo_seed_never_stores_a_whatsapp_number(seeded):
    assert seeded.scalars(select(SiteSettings.whatsapp_number)).all() in ([None], [None, None])


def test_demo_data_is_hidden_without_demo_mode(seeded, public_client):
    assert public_client.get("/api/v1/brands").json()["items"] == []
    assert public_client.get("/api/v1/products").json()["total"] == 0
    assert public_client.get("/api/v1/novedades").json()["total"] == 0
    assert public_client.get("/api/v1/collections").json()["items"] == []
    assert public_client.get("/api/v1/lookbooks").json()["items"] == []
    assert public_client.get("/api/v1/products/pieza-demostracion-01").status_code == 404
    assert public_client.get("/api/v1/collections/seleccion-demostracion-a").status_code == 404
    assert public_client.get("/api/v1/lookbooks/lookbook-demostracion").status_code == 404
    assert public_client.get("/api/v1/search?q=demostracion").json() == {"brands": [], "products": []}


def test_demo_rows_stay_hidden_even_if_marked_published(seeded, public_client):
    db = seeded
    db.execute(update(Brand).where(Brand.kind == "brand").values(status=STATUS_PUBLISHED))
    db.execute(update(Product).values(status=STATUS_PUBLISHED))
    db.execute(update(Collection).values(status=STATUS_PUBLISHED))
    db.execute(update(Lookbook).values(status=STATUS_PUBLISHED))
    db.commit()
    assert public_client.get("/api/v1/products").json()["total"] == 0
    assert public_client.get("/api/v1/products/pieza-demostracion-01").status_code == 404
    assert public_client.get("/api/v1/novedades").json()["items"] == []
    assert public_client.get("/api/v1/collections").json()["items"] == []
    assert public_client.get("/api/v1/lookbooks").json()["items"] == []
    assert public_client.get("/api/v1/search?q=demostracion").json()["products"] == []
    assert all(b["product_count"] == 0 for b in public_client.get("/api/v1/brands").json()["items"])


def test_public_settings_have_no_copy_without_demo_mode(seeded, public_client):
    assert public_client.get("/api/v1/site-settings/public").json() == {
        "demo_mode": False,
        "whatsapp_enabled": False,
        "site_name": "Eleven Boutique",
        "hero": {
            "image_url": None,
            "mobile_image_url": None,
            "headline": None,
            "subhead": None,
            "gallery": [],
        },
        "intro": None,
        "boutique": {"body": None},
        "contact": {"body": None},
    }


def test_published_collection_hides_demo_products_from_its_list(db, public_client, make_settings):
    brand = make_brand(db)
    category = make_category(db)
    real = make_product(db, brand, category, "Real")
    demo = make_product(db, brand, category, "Demo", is_demo=True)
    collection = Collection(slug="real", title="Real", status=STATUS_PUBLISHED)
    db.add(collection)
    db.flush()
    db.add_all(
        [
            CollectionProduct(collection_id=collection.id, product_id=real.id, position=1),
            CollectionProduct(collection_id=collection.id, product_id=demo.id, position=2),
        ]
    )
    db.commit()
    assert public_client.get("/api/v1/collections").json()["items"][0]["product_count"] == 1
    detail = public_client.get("/api/v1/collections/real").json()
    assert [product["slug"] for product in detail["products"]] == ["real"]
    assert detail["product_count"] == 1
