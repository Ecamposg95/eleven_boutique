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
    PLACEHOLDER_BRAND,
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
    make_brand(db, "Otra", slug="nueva-casa")
    sync_brands(db, [_brand("b1", "Nueva Casa")])
    new = db.get(Brand, _row(db, "b1").brand_id)
    assert new.slug != "nueva-casa" and new.slug.startswith("nueva-casa")


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
    row.category_id = cat.id
    db.flush()
    counts = sync_departments(db, [_dept("d9", "Otro")])
    assert counts["desligadas"] == 1
    assert row.category_id is None


def test_vanished_brand_keeps_link(db):
    sync_brands(db, [_brand("b1", "Cosa Rara")])
    sync_brands(db, [])
    assert _row(db, "b1").brand_id is not None


def test_brand_rename_keeps_link_updates_name(db):
    casa = make_brand(db, "Nike")
    sync_brands(db, [_brand("b1", "Nike")])
    sync_brands(db, [_brand("b1", "Nike Inc")])
    row = _row(db, "b1")
    assert row.brand_id == casa.id and row.atlas_name == "Nike Inc"


def test_blank_brand_name_skipped(db):
    sync_brands(db, [_brand("b1", "  ")])
    assert _row(db, "b1") is None


def test_archived_house_reason(db):
    from app.models import STATUS_ARCHIVED

    casa = make_brand(db, "Vieja", status=STATUS_ARCHIVED)
    db.add(AtlasBrandMap(atlas_brand_id="b1", atlas_name="Vieja", brand_id=casa.id))
    db.flush()
    assert resolve_brand(db, "b1") == (None, "casa archivada: Vieja")


def test_resolver_constant_queries(db):
    from sqlalchemy import event

    from app.services.atlas.links import Resolver

    casa = make_brand(db, "Fija")
    db.add(AtlasBrandMap(atlas_brand_id="b1", atlas_name="Fija", brand_id=casa.id))
    db.flush()
    resolver = Resolver(db)
    seen = []
    engine = db.get_bind()

    def listener(*args):
        seen.append(1)

    event.listen(engine, "before_cursor_execute", listener)
    try:
        for _ in range(50):
            assert resolver.brand("b1") == (casa, None)
            resolver.category("d1")
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    assert len(seen) == 0


def test_empty_or_tombstone_list_does_not_wipe_links(db):
    uno, dos = make_category(db, "Uno"), make_category(db, "Dos")
    db.add(
        AtlasCategoryMap(atlas_department_id="d1", atlas_name="Uno", category_id=uno.id)
    )
    db.add(
        AtlasCategoryMap(atlas_department_id="d2", atlas_name="Dos", category_id=dos.id)
    )
    db.flush()
    assert sync_departments(db, [])["desligadas"] == 0
    counts = sync_departments(db, [_dept("d1", "Uno", deleted=True)])
    assert counts["desligadas"] == 1
    rows = {r.atlas_department_id: r for r in db.scalars(select(AtlasCategoryMap))}
    assert rows["d1"].category_id is None and rows["d2"].category_id == dos.id


def test_resolver_category_paths(db):
    from app.services.atlas.links import Resolver

    cat = make_category(db, "Ropa")
    db.add(
        AtlasCategoryMap(
            atlas_department_id="d1", atlas_name="Ropa", category_id=cat.id
        )
    )
    db.add(AtlasCategoryMap(atlas_department_id="d2", atlas_name="Sueltos"))
    db.flush()
    resolver = Resolver(db)
    assert resolver.category("d1") == (cat, None)
    assert resolver.category("d2") == (None, "categoría sin ligar: Sueltos")


def test_brand_without_name_skipped(db):
    sync_brands(db, [{"id": "b1", "deleted": False}])
    assert _row(db, "b1") is None


def test_auto_link_ignores_classifications_and_placeholder(db):
    generic = make_brand(db, "Genérica", kind=KIND_CLASSIFICATION)
    placeholder = make_brand(db, PLACEHOLDER_BRAND, status=STATUS_DRAFT)
    gucci = make_brand(db, "Gucci")
    make_alias(db, make_brand(db, "Otra clasificación", kind=KIND_CLASSIFICATION), "Gucci")
    counts = sync_brands(
        db, [_brand("b1", "Genérica"), _brand("b2", PLACEHOLDER_BRAND), _brand("b3", "Gucci")]
    )
    assert counts == {"ligadas": 1, "creadas_borrador": 2}
    assert _row(db, "b3").brand_id == gucci.id
    for atlas_id in ("b1", "b2"):
        linked = db.get(Brand, _row(db, atlas_id).brand_id)
        assert linked.id not in (generic.id, placeholder.id)
        assert linked.kind == "brand" and linked.status == STATUS_DRAFT


def test_atlas_sin_marca_links_to_the_classification_even_in_draft(db):
    sm = make_brand(db, "Sin marca", kind=KIND_CLASSIFICATION, status=STATUS_DRAFT)
    counts = sync_brands(db, [_brand("b1", "SIN MARCA")])
    assert counts == {"ligadas": 1, "creadas_borrador": 0}
    assert _row(db, "b1").brand_id == sm.id
    assert db.scalar(select(Brand).where(Brand.kind == "brand")) is None
    # Igual que una pieza sin marca: se usa la clasificación aunque esté en borrador.
    assert resolve_brand(db, "b1") == (sm, None)


def test_atlas_sin_marca_without_classification_waits_without_creating_a_house(db):
    counts = sync_brands(db, [_brand("b1", "Sin marca")])
    assert counts == {"ligadas": 0, "creadas_borrador": 0}
    assert _row(db, "b1").brand_id is None
    assert db.scalar(select(Brand)) is None
    assert resolve_brand(db, "b1") == (None, "No existe la clasificación Sin marca")
    sm = make_brand(db, "Sin marca", kind=KIND_CLASSIFICATION)
    sync_brands(db, [_brand("b1", "Sin marca")])
    assert _row(db, "b1").brand_id == sm.id


def test_unlinked_reason_names_a_classification_that_owns_the_name(db):
    generic = make_brand(db, "Genérica", kind=KIND_CLASSIFICATION)
    db.add(AtlasBrandMap(atlas_brand_id="b1", atlas_name="Genérica"))
    db.flush()
    assert generic.id
    assert resolve_brand(db, "b1") == (
        None,
        "casa sin ligar: Genérica (el nombre es de una clasificación)",
    )
