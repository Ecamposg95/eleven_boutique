from sqlalchemy import select

from app.models import (
    KIND_CLASSIFICATION,
    STATUS_DRAFT,
    VALIDATION_PENDING,
    AtlasBrandMap,
    AtlasCategoryMap,
    Brand,
)
from app.services.atlas.links import (
    resolve_brand,
    resolve_category,
    sync_brands,
    sync_departments,
)
from tests.factories import make_alias, make_brand, make_category


def _brand(atlas_id, name, deleted=False):
    return {
        "id": atlas_id,
        "name": name,
        "logo_url": None,
        "is_premium": False,
        "updated_at": None,
        "deleted": deleted,
    }


def _dept(atlas_id, name, parent=None, deleted=False):
    return {
        "id": atlas_id,
        "name": name,
        "parent_id": parent,
        "updated_at": None,
        "deleted": deleted,
    }


def _row(db, atlas_id):
    return db.scalar(
        select(AtlasBrandMap).where(AtlasBrandMap.atlas_brand_id == atlas_id)
    )


def test_brand_matching_alias_links_and_stores_map(db):
    casa = make_brand(db, "Louis Vuitton")
    make_alias(db, casa, "LV")
    counts = sync_brands(db, [_brand("b1", "lv")])
    assert counts["ligadas"] == 1 and counts["creadas_borrador"] == 0
    assert _row(db, "b1").brand_id == casa.id
    assert resolve_brand(db, "b1") == (casa, None)


def test_existing_map_wins_over_name(db):
    uno = make_brand(db, "Uno")
    otro = make_brand(db, "Otro")
    db.add(AtlasBrandMap(atlas_brand_id="b1", atlas_name="Otro", brand_id=uno.id))
    db.flush()
    sync_brands(db, [_brand("b1", "Otro")])
    assert _row(db, "b1").brand_id == uno.id
    assert otro.id != uno.id


def test_ambiguous_name_not_linked(db):
    make_brand(db, "Dual A", slug="dual-a")
    b = make_brand(db, "Dual B", slug="dual-b")
    make_alias(db, b, "Dual A")
    sync_brands(db, [_brand("b1", "Dual A")])
    assert _row(db, "b1").brand_id is None
    assert db.scalar(select(Brand).where(Brand.status == STATUS_DRAFT)) is None
    brand, reason = resolve_brand(db, "b1")
    assert brand is None and reason == "casa ambigua: Dual A"


def test_unknown_brand_creates_draft_once(db):
    first = sync_brands(db, [_brand("b1", "Marca Nueva")])
    second = sync_brands(db, [_brand("b1", "Marca Nueva")])
    assert first["creadas_borrador"] == 1 and second["creadas_borrador"] == 0
    drafts = list(db.scalars(select(Brand).where(Brand.name == "Marca Nueva")))
    assert len(drafts) == 1
    assert drafts[0].status == STATUS_DRAFT
    assert drafts[0].validation_status == VALIDATION_PENDING
    assert _row(db, "b1").brand_id == drafts[0].id
    brand, reason = resolve_brand(db, "b1")
    assert brand is None and reason == "casa en borrador: Marca Nueva"


def test_draft_slug_unique(db):
    make_brand(db, "Gucci", slug="gucci-x")
    make_brand(db, "Otra", slug="nueva-casa")
    sync_brands(db, [_brand("b1", "Nueva Casa")])
    assert _row(db, "b1").brand_id is not None


def test_never_modifies_existing_house(db):
    casa = make_brand(db, "Prada", is_premium=False, logo_url=None)
    db.commit()
    cols = {c.name: getattr(casa, c.name) for c in Brand.__table__.columns}
    payload = _brand("b1", "Prada")
    payload["is_premium"] = True
    payload["logo_url"] = "http://x/y.png"
    sync_brands(db, [payload])
    db.commit()
    db.refresh(casa)
    assert {c.name: getattr(casa, c.name) for c in Brand.__table__.columns} == cols


def test_deleted_brand_not_created(db):
    sync_brands(db, [_brand("b1", "Fantasma", deleted=True)])
    assert _row(db, "b1") is None
    assert db.scalar(select(Brand).where(Brand.name == "Fantasma")) is None


def test_resolve_brand_none_is_sin_marca_and_unmapped(db):
    sm = make_brand(db, "Sin marca", kind=KIND_CLASSIFICATION)
    assert resolve_brand(db, None) == (sm, None)
    assert resolve_brand(db, "zzz") == (None, "casa sin ligar: zzz")


def test_departments_new_unlinked_and_resolve(db):
    counts = sync_departments(db, [_dept("d1", "Ropa"), _dept("d2", "Playeras", "d1")])
    assert counts["nuevas"] == 2
    row = db.scalar(
        select(AtlasCategoryMap).where(AtlasCategoryMap.atlas_department_id == "d2")
    )
    assert row.category_id is None and row.atlas_parent_id == "d1"
    assert resolve_category(db, "d2") == (None, "categoría sin ligar: Playeras")
    cat = make_category(db, "Playeras")
    row.category_id = cat.id
    db.flush()
    assert resolve_category(db, "d2") == (cat, None)
    sync_departments(db, [_dept("d2", "Playeras 2", "d1")])
    assert row.category_id == cat.id and row.atlas_name == "Playeras 2"


def test_deleted_or_vanished_department_unlinks(db):
    cat = make_category(db, "Ropa")
    db.add(
        AtlasCategoryMap(
            atlas_department_id="d1", atlas_name="Ropa", category_id=cat.id
        )
    )
    db.flush()
    sync_departments(db, [_dept("d1", "Ropa", deleted=True)])
    row = db.scalar(select(AtlasCategoryMap))
    assert row.category_id is None
