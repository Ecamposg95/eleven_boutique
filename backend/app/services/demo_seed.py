"""Demo catalog. Everything here is explicit placeholder content: no real claims of any kind."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import (
    BLOCK_IMAGE,
    BLOCK_TEXT,
    Brand,
    Category,
    Collection,
    CollectionProduct,
    Lookbook,
    LookbookBlock,
    LookbookProduct,
    Product,
    ProductMedia,
    SiteSettings,
)
from app.services.base_seed import seed_categories, seed_site_settings
from app.services.brand_import import run_import

FEATURED_BRANDS = (
    "acne-studios",
    "balenciaga",
    "loewe",
    "prada",
    "common-projects",
    "rick-owens",
)

# number, brand slug, category slug, is_featured, commercial_added_at
DEMO_PRODUCTS: tuple[tuple[int, str, str, bool, datetime | None], ...] = (
    (1, "acne-studios", "camisetas", True, datetime(2026, 4, 12, tzinfo=UTC)),
    (2, "acne-studios", "chamarras", False, datetime(2026, 4, 5, tzinfo=UTC)),
    (3, "balenciaga", "sneakers", True, datetime(2026, 3, 28, tzinfo=UTC)),
    (4, "balenciaga", "bolsas", False, datetime(2026, 3, 21, tzinfo=UTC)),
    (5, "loewe", "carteras", True, datetime(2026, 3, 14, tzinfo=UTC)),
    (6, "loewe", "panuelos", False, None),
    (7, "prada", "mochilas", False, datetime(2026, 3, 7, tzinfo=UTC)),
    (8, "prada", "lentes", True, None),
    (9, "common-projects", "sneakers", False, datetime(2026, 2, 28, tzinfo=UTC)),
    (10, "common-projects", "botas", False, None),
    (11, "rick-owens", "pantalones", False, datetime(2026, 2, 21, tzinfo=UTC)),
    (12, "sin-marca", "coleccionables", False, None),
)

DEMO_COLLECTIONS = (
    {
        "slug": "seleccion-demostracion-a",
        "title": "Selección de demostración A",
        "summary": "Texto de demostración: resumen de una selección de ejemplo.",
        "cover_url": "/demo/editorial-1.jpg",
        "products": (1, 3, 5, 7, 9, 11),
    },
    {
        "slug": "seleccion-demostracion-b",
        "title": "Selección de demostración B",
        "summary": "Texto de demostración: resumen de otra selección de ejemplo.",
        "cover_url": "/demo/editorial-2.jpg",
        "products": (2, 4, 6, 8, 10, 12),
    },
)

DEMO_LOOKBOOK = {
    "slug": "lookbook-demostracion",
    "title": "Lookbook de demostración",
    "summary": "Texto de demostración: resumen de un lookbook de ejemplo.",
    "cover_url": "/demo/editorial-3.jpg",
    "products": (1, 5, 8, 11),
}
DEMO_BLOCKS: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        BLOCK_TEXT,
        {
            "heading": "Texto de demostración",
            "body": "Texto de demostración: este párrafo muestra un bloque de texto editorial.",
        },
    ),
    (
        BLOCK_IMAGE,
        {
            "url": "/demo/editorial-1.jpg",
            "alt": "Imagen de demostración: composición editorial 1",
            "layout": "full",
        },
    ),
    (
        BLOCK_TEXT,
        {
            "heading": None,
            "body": "Texto de demostración: este párrafo no tiene encabezado.",
        },
    ),
    (
        BLOCK_IMAGE,
        {
            "url": "/demo/editorial-2.jpg",
            "alt": "Imagen de demostración: composición editorial 2",
            "layout": "left",
        },
    ),
    (
        BLOCK_IMAGE,
        {
            "url": "/demo/editorial-3.jpg",
            "alt": "Imagen de demostración: composición editorial 3",
            "layout": "right",
        },
    ),
)

DEMO_SETTINGS = {
    "hero_image_url": "/demo/editorial-1.jpg",
    # Demo slides have no media asset: public reads only use the URL.
    "hero_gallery": [{"url": "/demo/editorial-2.jpg"}, {"url": "/demo/editorial-3.jpg"}],
    "hero_headline": "Texto de demostración: titular de portada",
    "hero_subhead": "Texto de demostración: subtítulo de portada",
    "intro": "Texto de demostración: introducción del sitio.",
    "boutique_body": "Texto de demostración: descripción de la boutique.",
    "contact_body": "Texto de demostración: información de contacto.",
}


class DemoModeRequired(RuntimeError):
    pass


class DemoSlugConflict(RuntimeError):
    pass


def _upsert(db: Session, model, lookup: dict[str, Any], values: dict[str, Any]):
    row = db.scalar(select(model).filter_by(**lookup))
    if row is None:
        row = model(**lookup)
        db.add(row)
    elif getattr(row, "is_demo", True) is False:
        raise DemoSlugConflict(f"{model.__tablename__} {lookup} ya existe y no es demo")
    for name, value in values.items():
        setattr(row, name, value)
    db.flush()
    return row


def seed_demo(db: Session, settings: Settings) -> dict[str, int]:
    if not settings.demo_mode:
        raise DemoModeRequired("seed_demo solo corre con DEMO_MODE=true")

    # Prerequisites are idempotent, so the demo works on a freshly migrated database.
    run_import(db)
    seed_categories(db)
    seed_site_settings(db, settings)

    brands = {brand.slug: brand for brand in db.scalars(select(Brand)).all()}
    categories = {category.slug: category for category in db.scalars(select(Category)).all()}
    for slug in FEATURED_BRANDS:
        brands[slug].is_featured = True

    products: dict[int, Product] = {}
    for number, brand_slug, category_slug, is_featured, added_at in DEMO_PRODUCTS:
        label = f"{number:02d}"
        name = f"Pieza de demostración {label}"
        product = _upsert(
            db,
            Product,
            {"sku": f"DEMO-{number:03d}"},
            {
                "slug": f"pieza-demostracion-{label}",
                "name": name,
                "brand_id": brands[brand_slug].id,
                "category_id": categories[category_slug].id,
                "is_featured": is_featured,
                "display_order": number,
                "commercial_added_at": added_at,
                "is_demo": True,
            },
        )
        products[number] = product
        for position, (view, is_primary) in enumerate((("a", True), ("b", False))):
            _upsert(
                db,
                ProductMedia,
                {"product_id": product.id, "position": position},
                {
                    "url": f"/demo/pieza-{label}-{view}.jpg",
                    "alt": f"Imagen de demostración: {name}, vista {view.upper()}",
                    "is_primary": is_primary,
                },
            )

    for order, definition in enumerate(DEMO_COLLECTIONS, start=1):
        collection = _upsert(
            db,
            Collection,
            {"slug": definition["slug"]},
            {
                "title": definition["title"],
                "summary": definition["summary"],
                "cover_url": definition["cover_url"],
                "display_order": order,
                "is_demo": True,
            },
        )
        for position, number in enumerate(definition["products"]):
            _upsert(
                db,
                CollectionProduct,
                {"collection_id": collection.id, "product_id": products[number].id},
                {"position": position},
            )

    lookbook = _upsert(
        db,
        Lookbook,
        {"slug": DEMO_LOOKBOOK["slug"]},
        {
            "title": DEMO_LOOKBOOK["title"],
            "summary": DEMO_LOOKBOOK["summary"],
            "cover_url": DEMO_LOOKBOOK["cover_url"],
            "is_demo": True,
        },
    )
    for position, (block_type, content) in enumerate(DEMO_BLOCKS):
        _upsert(
            db,
            LookbookBlock,
            {"lookbook_id": lookbook.id, "position": position},
            {"type": block_type, "content": content},
        )
    for position, number in enumerate(DEMO_LOOKBOOK["products"]):
        _upsert(
            db,
            LookbookProduct,
            {"lookbook_id": lookbook.id, "product_id": products[number].id},
            {"position": position},
        )

    _upsert(db, SiteSettings, {"is_demo": True}, DEMO_SETTINGS)
    return {
        "products": len(products),
        "featured_brands": len(FEATURED_BRANDS),
        "collections": len(DEMO_COLLECTIONS),
        "lookbooks": 1,
    }
