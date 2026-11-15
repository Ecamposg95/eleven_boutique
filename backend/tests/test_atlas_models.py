import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    AtlasBrandMap,
    AtlasCategoryMap,
    AtlasSyncRun,
    AtlasSyncState,
    ProductVariant,
)
from tests.factories import make_brand, make_category, make_product


def test_product_defaults_and_nullable_atlas_fields(db):
    product = make_product(db, make_brand(db), make_category(db))
    db.commit()
    assert product.available is True
    assert product.hidden_on_web is False
    assert product.atlas_missing is None
    assert product.gender is None and product.model is None and product.material is None
    assert product.external_inventory_id is None


def test_external_inventory_id_is_unique_when_present(db):
    brand, category = make_brand(db), make_category(db)
    make_product(db, brand, category, name="Uno", external_inventory_id="A-1")
    with pytest.raises(IntegrityError):
        make_product(db, brand, category, name="Dos", external_inventory_id="A-1")
    db.rollback()


def test_external_inventory_id_allows_many_nulls(db):
    brand, category = make_brand(db), make_category(db)
    make_product(db, brand, category, name="Uno")
    make_product(db, brand, category, name="Dos")
    db.commit()


def test_variant_external_id_unique_when_present_and_available_default(db):
    product = make_product(db, make_brand(db), make_category(db))
    first = ProductVariant(product_id=product.id, sku="V-1", external_inventory_id="AV-1")
    db.add_all([first, ProductVariant(product_id=product.id, sku="V-2")])
    db.add(ProductVariant(product_id=product.id, sku="V-3"))
    db.commit()
    assert first.available is True
    db.add(ProductVariant(product_id=product.id, sku="V-4", external_inventory_id="AV-1"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_sync_tables_work(db):
    db.add(AtlasSyncState(id=1))
    run = AtlasSyncRun(kind="full", status="ok", counts={"creadas": 1})
    db.add(run)
    category = make_category(db)
    brand = make_brand(db)
    db.add_all(
        [
            AtlasBrandMap(atlas_brand_id="b1", atlas_name="Marca"),
            AtlasCategoryMap(atlas_department_id="d1", atlas_name="Depto", category_id=category.id),
        ]
    )
    db.commit()
    assert run.started_at is not None and run.id is not None
    assert db.scalar(select(AtlasSyncState)).last_error is None
    assert db.scalar(select(AtlasBrandMap)).brand_id is None
    db.add(AtlasBrandMap(atlas_brand_id="b1", atlas_name="Otra", brand_id=brand.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(AtlasCategoryMap(atlas_department_id="d1", atlas_name="Otra"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_catalog_event_forwarded_at_is_nullable(db):
    from app.models import CatalogEvent

    event = CatalogEvent(type="whatsapp_click")
    db.add(event)
    db.commit()
    assert event.forwarded_at is None
    assert db.execute(text("SELECT count(*) FROM atlas_sync_state")).scalar() == 0
