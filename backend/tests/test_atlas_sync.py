"""Sincronización de piezas y disponibilidad contra un Atlas ONE falso en memoria."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import make_engine, make_session_factory
from app.models import (
    KIND_CLASSIFICATION,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    AtlasCategoryMap,
    Brand,
    AtlasSyncRun,
    AtlasSyncState,
    MediaAsset,
    Product,
    ProductMedia,
    ProductVariant,
)
from app.schemas.admin import AtlasBrandMapPatch, AtlasCategoryMapPatch, BrandPatch
from app.services.admin.atlas import patch_brand_map, patch_category_map
from app.services.admin.taxonomy import update_brand
from app.services.atlas.client import AtlasClient, fmt_since
from app.services.atlas.sync import is_nightly_due, run_sync, with_lock
from tests.admin_helpers import make_user
from tests.factories import make_brand, make_category, make_product

# 12:00 en Ciudad de México.
NOW = datetime(2026, 11, 14, 18, 0, tzinfo=UTC)
WEB_PUBLISHED = datetime(2026, 11, 10, 9, 30, tzinfo=UTC)


class FakeAtlas:
    """Canal de Atlas en memoria: páginas con cursor, filtro updated_since y fallas por ruta."""

    def __init__(self) -> None:
        self.now = NOW
        self.page_size = 50
        self.brands: list[dict] = []
        self.departments: list[dict] = []
        self.products: dict[str, dict] = {}
        self.availability: dict[str, dict] = {}
        self.requests: list[tuple[str, dict]] = []
        # ruta -> cursor desde el que responde 500
        self.fail: dict[str, int] = {}

    def tick(self, minutes: int = 60) -> None:
        self.now += timedelta(minutes=minutes)

    def brand(self, id: str, name: str) -> None:
        self.brands.append({"id": id, "name": name, "logo_url": None, "is_premium": False,
                            "updated_at": fmt_since(self.now), "deleted": False})

    def department(self, id: str, name: str) -> None:
        self.departments.append({"id": id, "name": name, "parent_id": None,
                                 "updated_at": fmt_since(self.now), "deleted": False})

    def put(self, id: str, **fields) -> dict:
        current = self.products.get(id)
        if current is None or current.get("deleted"):
            current = {
                "id": id,
                "name": f"Pieza {id}",
                "description": "Descripción de Atlas",
                "brand_id": "b1",
                "department_id": "d1",
                "gender": "Mujer",
                "model": None,
                "material": "Piel",
                "available": True,
                "images": [
                    {"url": f"https://res.cloudinary.com/x/{id}-1.jpg", "alt": "frente", "position": 0, "is_primary": False},
                    {"url": f"https://res.cloudinary.com/x/{id}-2.jpg", "alt": None, "position": 1, "is_primary": True},
                ],
                "variants": [
                    {"id": f"{id}-v1", "sku": f"{id.upper()}-NEG", "color": "Negro", "size": "UNI", "available": True},
                ],
                "web_published_at": fmt_since(WEB_PUBLISHED),
            }
        current = {**current, **fields, "updated_at": fmt_since(self.now), "deleted": False}
        self.products[id] = current
        return current

    def delete(self, id: str) -> None:
        self.products[id] = {"id": id, "updated_at": fmt_since(self.now), "deleted": True}

    def set_available(self, product_id: str, variant_id: str, available: bool) -> None:
        self.availability[variant_id] = {"product_id": product_id, "variant_id": variant_id,
                                         "available": available, "changed_at": fmt_since(self.now)}

    def _items(self, path: str, since: str | None) -> list[dict]:
        if path == "/brands":
            return self.brands
        if path == "/departments":
            return self.departments
        if path == "/products":
            items, key = list(self.products.values()), "updated_at"
        elif path == "/availability":
            items, key = list(self.availability.values()), "changed_at"
        else:
            raise AssertionError(path)
        if since is None:
            return [item for item in items if path != "/products" or not item.get("deleted")]
        return [item for item in items if item[key] >= since]

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = dict(request.url.params)
        self.requests.append((path, params))
        cursor = int(params.get("cursor", 0))
        if path in self.fail and cursor >= self.fail[path]:
            return httpx.Response(500, json={"detail": "boom"})
        items = self._items(path, params.get("updated_since"))
        page = items[cursor : cursor + self.page_size]
        more = cursor + self.page_size < len(items)
        return httpx.Response(200, json={
            "items": page,
            "next_cursor": str(cursor + self.page_size) if more else None,
            "server_time": fmt_since(self.now),
        })

    def client(self) -> AtlasClient:
        return AtlasClient("https://atlas.test", "llave-secreta",
                           transport=httpx.MockTransport(self.handler), sleep=lambda s: None)

    def params(self, path: str) -> list[dict]:
        return [params for p, params in self.requests if p == path]


@pytest.fixture
def factory(database_url: str) -> Iterator[sessionmaker[Session]]:
    engine = make_engine(database_url)
    yield make_session_factory(engine)
    engine.dispose()


@pytest.fixture
def atlas(factory) -> FakeAtlas:
    """Hermès publicada y ligada; Bolsos ligada a d1."""
    fake = FakeAtlas()
    fake.brand("b1", "Hermès")
    fake.department("d1", "Bolsos")
    with factory() as s:
        make_brand(s, "Hermès")
        category = make_category(s, "Bolsos")
        s.add(AtlasCategoryMap(atlas_department_id="d1", atlas_name="Bolsos", category_id=category.id))
        s.commit()
    return fake


def sync(factory, atlas: FakeAtlas, kind="incremental", now=NOW) -> AtlasSyncRun | None:
    client = atlas.client()
    try:
        return run_sync(factory, client, kind=kind, now=lambda: now)
    finally:
        client.close()


def piece(factory, ext: str) -> Product:
    with factory() as s:
        product = s.scalar(select(Product).where(Product.external_inventory_id == ext))
        assert product is not None
        # Carga lo que las pruebas inspeccionan fuera de la sesión.
        product.variants, product.media, product.brand, product.category  # noqa: B018
        return product


def state(factory) -> AtlasSyncState | None:
    with factory() as s:
        return s.get(AtlasSyncState, 1)


def changes(run: AtlasSyncRun) -> dict[str, int]:
    keys = ("creadas", "actualizadas", "bajas", "borradores", "disponibilidad")
    return {key: run.counts[key] for key in keys}


# --- Alta y publicación --------------------------------------------------------------------


def test_new_piece_with_linked_house_and_category_is_published(factory, atlas):
    atlas.put("p1", name="Birkin 30", model="BIRKIN-30", variants=[
        {"id": "v1", "sku": "B30-NEG", "color": "Negro", "size": "UNI", "available": True},
        {"id": "v2", "sku": "B30-ORO", "color": "Oro", "size": "UNI", "available": False},
    ])
    run = sync(factory, atlas)
    assert run.status == "ok"
    assert run.counts["creadas"] == 1
    p = piece(factory, "p1")
    assert p.status == STATUS_PUBLISHED
    assert p.atlas_missing is None
    assert p.published_at == WEB_PUBLISHED
    assert p.commercial_added_at == WEB_PUBLISHED
    assert p.name == "Birkin 30"
    assert p.sku == "BIRKIN-30"
    assert p.slug == "hermes-birkin-30"
    assert p.brand.name == "Hermès" and p.category.name == "Bolsos"
    assert (p.gender, p.model, p.material) == ("Mujer", "BIRKIN-30", "Piel")
    assert p.available is True
    assert {(v.external_inventory_id, v.sku, v.color, v.available) for v in p.variants} == {
        ("v1", "B30-NEG", "Negro", True), ("v2", "B30-ORO", "Oro", False)}
    assert [(m.url, m.alt, m.is_primary, m.media_asset_id) for m in p.media] == [
        ("https://res.cloudinary.com/x/p1-1.jpg", "frente", False, None),
        ("https://res.cloudinary.com/x/p1-2.jpg", "Birkin 30", True, None),
    ]
    assert p.hidden_on_web is False


def test_unlinked_category_drafts_then_publishes_once_linked(factory, atlas):
    atlas.department("d2", "Zapatos")
    atlas.put("p1", department_id="d2")
    run = sync(factory, atlas)
    p = piece(factory, "p1")
    assert p.status == STATUS_DRAFT
    assert p.atlas_missing == "categoría sin ligar: Zapatos"
    assert p.published_at is None
    assert run.counts["borradores"] == 1

    with factory() as s:
        zapatos = make_category(s, "Zapatos")
        s.scalar(select(AtlasCategoryMap).where(AtlasCategoryMap.atlas_department_id == "d2")).category_id = zapatos.id
        s.commit()
    sync(factory, atlas)
    p = piece(factory, "p1")
    assert p.status == STATUS_PUBLISHED
    assert p.atlas_missing is None
    assert p.category.name == "Zapatos"
    assert p.published_at == WEB_PUBLISHED


def test_house_in_draft_keeps_piece_in_draft(factory, atlas):
    atlas.brand("b2", "Casa Nueva")
    atlas.put("p1", brand_id="b2")
    sync(factory, atlas)
    p = piece(factory, "p1")
    assert p.status == STATUS_DRAFT
    assert p.atlas_missing == "casa en borrador: Casa Nueva"
    # La pieza queda ligada a la casa en borrador para que publicarla la destrabe.
    assert p.brand.name == "Casa Nueva"


def test_missing_house_and_category_join_reasons(factory, atlas):
    atlas.brand("b2", "Casa Nueva")
    atlas.department("d2", "Zapatos")
    atlas.put("p1", brand_id="b2", department_id="d2")
    sync(factory, atlas)
    p = piece(factory, "p1")
    assert p.status == STATUS_DRAFT
    assert p.atlas_missing == "casa en borrador: Casa Nueva; categoría sin ligar: Zapatos"


def test_piece_without_brand_goes_to_sin_marca(factory, atlas):
    with factory() as s:
        make_brand(s, "Sin marca", kind=KIND_CLASSIFICATION)
        s.commit()
    atlas.put("p1", brand_id=None, name="Cinturón")
    sync(factory, atlas)
    p = piece(factory, "p1")
    assert p.status == STATUS_PUBLISHED
    assert p.brand.name == "Sin marca"
    assert p.slug == "cinturon"


# --- Lo editorial -------------------------------------------------------------------------


def test_sync_never_touches_editorial_fields(factory, atlas):
    atlas.put("p1", name="Birkin")
    sync(factory, atlas)
    with factory() as s:
        p = s.scalar(select(Product).where(Product.external_inventory_id == "p1"))
        p.is_featured = True
        p.display_order = 7
        p.seo_title = "SEO propio"
        p.seo_description = "Descripción SEO"
        p.internal_notes = "nota"
        p.hidden_on_web = True
        asset = MediaAsset(storage_key="k/1.jpg", url="/media/k/1.jpg", filename="1.jpg",
                           content_type="image/jpeg", width=10, height=10, size_bytes=1)
        s.add(asset)
        s.flush()
        s.add(ProductMedia(product_id=p.id, url=asset.url, alt="panel", position=5,
                           is_primary=True, media_asset_id=asset.id))
        s.commit()

    atlas.tick()
    atlas.put("p1", name="Birkin 25")
    run = sync(factory, atlas, now=NOW + timedelta(hours=1))
    assert run.counts["actualizadas"] == 1
    p = piece(factory, "p1")
    assert p.name == "Birkin 25"
    assert p.search_text.startswith("birkin 25")
    assert (p.is_featured, p.display_order, p.seo_title, p.seo_description, p.internal_notes, p.hidden_on_web) == (
        True, 7, "SEO propio", "Descripción SEO", "nota", True)
    panel = [m for m in p.media if m.media_asset_id is not None]
    assert [(m.url, m.position, m.is_primary) for m in panel] == [("/media/k/1.jpg", 5, True)]
    atlas_media = [m for m in p.media if m.media_asset_id is None]
    assert len(atlas_media) == 2
    # La foto del panel ya es la principal: ninguna de Atlas lo es.
    assert not any(m.is_primary for m in atlas_media)
    assert p.status == STATUS_PUBLISHED


def test_photos_are_replaced_and_avoid_panel_positions(factory, atlas):
    atlas.put("p1")
    sync(factory, atlas)
    with factory() as s:
        p = s.scalar(select(Product).where(Product.external_inventory_id == "p1"))
        asset = MediaAsset(storage_key="k/2.jpg", url="/media/k/2.jpg", filename="2.jpg",
                           content_type="image/jpeg", width=10, height=10, size_bytes=1)
        s.add(asset)
        s.flush()
        s.add(ProductMedia(product_id=p.id, url=asset.url, alt="panel", position=2, media_asset_id=asset.id))
        s.commit()
    atlas.put("p1", images=[
        {"url": f"https://res.cloudinary.com/x/n{i}.jpg", "alt": f"n{i}", "position": i, "is_primary": False}
        for i in range(3)
    ])
    sync(factory, atlas)
    p = piece(factory, "p1")
    assert [(m.url, m.position, m.is_primary) for m in p.media] == [
        ("https://res.cloudinary.com/x/n0.jpg", 0, True),
        ("https://res.cloudinary.com/x/n1.jpg", 1, False),
        ("/media/k/2.jpg", 2, False),
        ("https://res.cloudinary.com/x/n2.jpg", 3, False),
    ]


# --- SKU, slug y variantes ------------------------------------------------------------------


def test_sku_from_model_then_first_variant_then_suffix_and_never_changes(factory, atlas):
    with factory() as s:
        make_product(s, make_brand(s, "Otra"), make_category(s, "Otra"), "Web", sku="BIRKIN")
        s.commit()
    atlas.put("p1", model="BIRKIN", variants=[
        {"id": "a", "sku": "Z-1", "color": None, "size": "M", "available": True},
        {"id": "b", "sku": "A-1", "color": None, "size": "G", "available": True},
    ])
    atlas.put("p2", model="BIRKIN", variants=[
        {"id": "c", "sku": "A-1", "color": None, "size": "M", "available": True},
    ])
    atlas.put("p3", model="KELLY", variants=[
        {"id": "d", "sku": None, "color": None, "size": "M", "available": True},
    ])
    sync(factory, atlas)
    assert piece(factory, "p1").sku == "A-1"
    assert piece(factory, "p2").sku == "A-1-2"
    p3 = piece(factory, "p3")
    assert p3.sku == "KELLY"
    assert p3.variants[0].sku == "ATL-d"
    # El SKU de variante choca con el de p1: también lleva sufijo.
    assert piece(factory, "p2").variants[0].sku == "A-1-2"

    slug = p3.slug
    atlas.put("p3", model="KELLY-28", name="Kelly 28")
    sync(factory, atlas)
    p3 = piece(factory, "p3")
    assert (p3.sku, p3.slug, p3.model, p3.name) == ("KELLY", slug, "KELLY-28", "Kelly 28")


def test_vanished_variant_is_deleted_and_new_one_added(factory, atlas):
    atlas.put("p1", variants=[
        {"id": "v1", "sku": "S-1", "color": None, "size": "Ch", "available": True},
        {"id": "v2", "sku": "S-2", "color": None, "size": "M", "available": True},
    ])
    sync(factory, atlas)
    keep = {v.external_inventory_id: v.id for v in piece(factory, "p1").variants}
    atlas.put("p1", variants=[
        {"id": "v1", "sku": "S-1", "color": None, "size": "Ch", "available": True},
        {"id": "v3", "sku": "S-2", "color": None, "size": "G", "available": True},
    ])
    sync(factory, atlas)
    variants = {v.external_inventory_id: v for v in piece(factory, "p1").variants}
    assert set(variants) == {"v1", "v3"}
    assert variants["v1"].id == keep["v1"]
    # El SKU liberado por v2 se reutiliza sin sufijo.
    assert variants["v3"].sku == "S-2" and variants["v3"].size == "G"


def test_tombstone_archives_and_revival_republishes_with_same_slug(factory, atlas):
    atlas.put("p1")
    sync(factory, atlas)
    slug = piece(factory, "p1").slug
    atlas.delete("p1")
    run = sync(factory, atlas)
    assert run.counts["bajas"] == 1
    assert piece(factory, "p1").status == STATUS_ARCHIVED
    atlas.put("p1", name="Otra vez")
    sync(factory, atlas)
    p = piece(factory, "p1")
    assert (p.status, p.slug, p.name) == (STATUS_PUBLISHED, slug, "Otra vez")


# --- Disponibilidad -------------------------------------------------------------------------


def test_availability_by_variant_and_piece(factory, atlas):
    atlas.put("p1", variants=[
        {"id": "v1", "sku": "S-1", "color": None, "size": "Ch", "available": True},
        {"id": "v2", "sku": "S-2", "color": None, "size": "M", "available": True},
    ])
    sync(factory, atlas)

    def step(variant: str, available: bool, hours: int) -> tuple[dict, bool]:
        atlas.tick()
        atlas.set_available("p1", variant, available)
        run = sync(factory, atlas, now=NOW + timedelta(hours=hours))
        assert run.status == "ok"
        p = piece(factory, "p1")
        return {v.external_inventory_id: v.available for v in p.variants}, p.available

    assert step("v1", False, 1) == ({"v1": False, "v2": True}, True)
    assert step("v2", False, 2) == ({"v1": False, "v2": False}, False)
    assert step("v1", True, 3) == ({"v1": True, "v2": False}, True)


def test_availability_ignores_unknown_variants(factory, atlas):
    atlas.put("p1")
    sync(factory, atlas)
    atlas.tick()
    atlas.set_available("zz", "no-existe", False)
    run = sync(factory, atlas, now=NOW + timedelta(hours=1))
    assert run.status == "ok"
    assert run.counts["disponibilidad"] == 0


# --- Idempotencia, fallas y estado ----------------------------------------------------------


def snapshot(factory) -> list:
    with factory() as s:
        rows = []
        for model in (Product, ProductVariant, ProductMedia):
            for row in s.scalars(select(model).order_by(model.id)):
                rows.append({c.key: getattr(row, c.key) for c in model.__table__.columns if c.key != "updated_at"})
        return rows


def test_two_runs_without_changes_are_idempotent(factory, atlas):
    atlas.department("d2", "Zapatos")
    atlas.put("p1")
    atlas.put("p2", department_id="d2")
    first = sync(factory, atlas)
    assert first.counts["creadas"] == 2
    before = snapshot(factory)
    second = sync(factory, atlas)
    assert second.status == "ok"
    assert snapshot(factory) == before
    assert changes(second) == {"creadas": 0, "actualizadas": 0, "bajas": 0, "borradores": 0, "disponibilidad": 0}


def test_updated_since_is_products_since_minus_ten_minutes(factory, atlas):
    atlas.put("p1")
    sync(factory, atlas)
    assert "updated_since" not in atlas.params("/products")[0]
    assert state(factory).products_since == NOW
    atlas.tick()
    sync(factory, atlas, now=NOW + timedelta(hours=1))
    assert atlas.params("/products")[-1]["updated_since"] == "2026-11-14T17:50:00Z"
    assert atlas.params("/availability")[-1]["updated_since"] == "2026-11-14T17:50:00Z"
    assert state(factory).products_since == NOW + timedelta(hours=1)
    assert state(factory).availability_since == NOW + timedelta(hours=1)


def test_products_500_marks_error_and_keeps_state(factory, atlas):
    atlas.put("p1", name="Original")
    sync(factory, atlas)
    before = state(factory)
    atlas.tick()
    atlas.put("p1", name="Cambiado")
    atlas.fail["/products"] = 0
    run = sync(factory, atlas, now=NOW + timedelta(hours=1))
    assert run.status == "error"
    assert "500" in run.error
    assert "llave-secreta" not in run.error
    after = state(factory)
    assert after.products_since == before.products_since
    assert after.availability_since == before.availability_since
    assert after.last_ok_at == NOW
    assert after.last_run_at == NOW + timedelta(hours=1)
    assert after.last_error and "500" in after.last_error
    p = piece(factory, "p1")
    assert (p.name, p.status) == ("Original", STATUS_PUBLISHED)


def test_old_runs_are_purged(factory, atlas):
    with factory() as s:
        s.add(AtlasSyncRun(kind="incremental", status="ok", started_at=NOW - timedelta(days=31), counts={}))
        s.add(AtlasSyncRun(kind="incremental", status="ok", started_at=NOW - timedelta(days=29), counts={}))
        s.commit()
    sync(factory, atlas)
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(AtlasSyncRun)) == 2


# --- Nocturna -------------------------------------------------------------------------------

MX = timedelta(hours=6)  # America/Mexico_City es UTC-6 en noviembre.


def mx(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=UTC) + MX


def test_is_nightly_due():
    assert is_nightly_due(AtlasSyncState(last_full_at=None), mx(14, 3, 1)) is True
    assert is_nightly_due(AtlasSyncState(last_full_at=mx(13, 3, 5)), mx(14, 2, 59)) is False
    assert is_nightly_due(AtlasSyncState(last_full_at=mx(13, 3, 5)), mx(14, 3, 0)) is True
    assert is_nightly_due(AtlasSyncState(last_full_at=mx(14, 3, 5)), mx(14, 9, 0)) is False
    # 00:30 de México: el último full de ayer a las 03:05 sigue valiendo.
    assert is_nightly_due(AtlasSyncState(last_full_at=mx(13, 3, 5)), mx(15, 0, 30)) is False


def stale_piece(factory) -> None:
    """Pieza de Atlas que ya no viene publicada; el estado simula una corrida buena de ayer."""
    with factory() as s:
        brand = s.scalar(select(Product.brand_id).limit(1))
        category = s.scalar(select(Product.category_id).limit(1))
        s.add(Product(sku="GONE", slug="gone", name="Se fue", brand_id=brand, category_id=category,
                      status=STATUS_PUBLISHED, external_inventory_id="gone"))
        st = s.get(AtlasSyncState, 1)
        st.last_full_at = mx(13, 3, 5)
        s.commit()


def test_nightly_full_load_archives_pieces_atlas_no_longer_returns(factory, atlas):
    atlas.put("p1")
    sync(factory, atlas, now=mx(13, 12))
    stale_piece(factory)
    run = sync(factory, atlas, now=mx(14, 3, 30))
    assert run.status == "ok"
    assert run.kind == "full"
    assert "updated_since" not in atlas.params("/products")[-1]
    assert piece(factory, "gone").status == STATUS_ARCHIVED
    assert piece(factory, "p1").status == STATUS_PUBLISHED
    assert run.counts["bajas"] == 1
    assert state(factory).last_full_at == mx(14, 3, 30)


def test_nightly_with_failure_mid_load_archives_nothing(factory, atlas):
    atlas.page_size = 1
    atlas.put("p1")
    atlas.put("p2")
    sync(factory, atlas, now=mx(13, 12))
    stale_piece(factory)
    atlas.fail["/products"] = 1
    run = sync(factory, atlas, now=mx(14, 3, 30))
    assert run.status == "error"
    assert piece(factory, "gone").status == STATUS_PUBLISHED
    assert state(factory).last_full_at == mx(13, 3, 5)


def _load_twenty(factory, atlas) -> None:
    for i in range(20):
        atlas.put(f"p{i:02d}")
    assert sync(factory, atlas).counts["creadas"] == 20


def test_empty_full_load_archives_nothing(factory, atlas):
    atlas.put("p1")
    sync(factory, atlas)
    atlas.products.clear()
    run = sync(factory, atlas, kind="full")
    assert run.status == "ok"
    assert run.counts["bajas"] == 0
    assert run.counts["archivado_omitido"] == 1
    assert "archivado omitido" in run.error
    assert piece(factory, "p1").status == STATUS_PUBLISHED
    assert state(factory).last_error is None


def test_full_load_missing_half_of_twenty_archives_nothing(factory, atlas):
    _load_twenty(factory, atlas)
    for i in range(10):
        del atlas.products[f"p{i:02d}"]
    run = sync(factory, atlas, kind="full")
    assert run.status == "ok"
    assert run.counts["bajas"] == 0
    assert run.counts["archivado_omitido"] == 1
    assert "10 de 20" in run.error
    assert all(piece(factory, f"p{i:02d}").status == STATUS_PUBLISHED for i in range(20))


def test_full_load_missing_two_of_twenty_archives_them(factory, atlas):
    _load_twenty(factory, atlas)
    del atlas.products["p00"], atlas.products["p01"]
    run = sync(factory, atlas, kind="full")
    assert run.status == "ok"
    assert run.counts["bajas"] == 2
    assert run.counts["archivado_omitido"] == 0
    assert run.error is None
    assert piece(factory, "p00").status == STATUS_ARCHIVED
    assert piece(factory, "p01").status == STATUS_ARCHIVED
    assert piece(factory, "p02").status == STATUS_PUBLISHED


def test_explicit_full_kind_reloads_everything(factory, atlas):
    atlas.put("p1")
    sync(factory, atlas)
    run = sync(factory, atlas, kind="full")
    assert run.kind == "full"
    assert "updated_since" not in atlas.params("/products")[-1]


# --- Candado --------------------------------------------------------------------------------


def test_busy_lock_returns_none_without_writing_a_run(factory, atlas):
    with factory() as s, with_lock(s) as acquired:
        assert acquired is True
        assert sync(factory, atlas) is None
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(AtlasSyncRun)) == 0
    assert atlas.requests == []
    # Liberado al salir: la siguiente corrida sí entra.
    assert sync(factory, atlas).status == "ok"


def test_lock_is_released_after_a_failed_run(factory, atlas):
    atlas.fail["/brands"] = 0
    assert sync(factory, atlas).status == "error"
    atlas.fail.clear()
    assert sync(factory, atlas).status == "ok"


# --- Script ---------------------------------------------------------------------------------


def test_script_exits_zero_without_doing_anything_when_disabled(monkeypatch, make_settings):
    from scripts import sync_atlas

    monkeypatch.setattr(sync_atlas, "get_settings", lambda: make_settings(atlas_sync_enabled=False))
    monkeypatch.setattr(sync_atlas, "AtlasClient", lambda *a, **k: pytest.fail("no debe conectarse"))
    assert sync_atlas.main([]) == 0
    monkeypatch.setattr(sync_atlas, "get_settings", lambda: make_settings(
        atlas_sync_enabled=True, atlas_api_url="", atlas_api_key="k"))
    assert sync_atlas.main([]) == 0


def test_script_exit_code_follows_run_status(monkeypatch, make_settings, atlas, factory):
    from scripts import sync_atlas

    monkeypatch.setattr(sync_atlas, "get_settings", lambda: make_settings(
        atlas_sync_enabled=True, atlas_api_url="https://atlas.test", atlas_api_key="llave-secreta"))
    monkeypatch.setattr(sync_atlas, "AtlasClient", lambda *a, **k: atlas.client())
    atlas.put("p1")
    assert sync_atlas.main(["--full"]) == 0
    with factory() as s:
        assert s.scalar(select(AtlasSyncRun.kind)) == "full"
    atlas.fail["/products"] = 0
    assert sync_atlas.main([]) == 1


# --- Reevaluación de borradores tras arreglar la causa en el panel ---------------------------


def test_linking_category_in_panel_republishes_on_next_incremental(factory, atlas):
    atlas.department("d2", "Zapatos")
    atlas.put("p1", department_id="d2")
    atlas.tick(120)
    sync(factory, atlas, now=atlas.now)
    assert piece(factory, "p1").status == STATUS_DRAFT

    with factory() as s:
        zapatos = make_category(s, "Zapatos")
        patch_category_map(s, AtlasCategoryMapPatch(atlas_department_id="d2", category_id=zapatos.id), make_user(s))
    assert state(factory).products_since is None
    atlas.tick(120)
    run = sync(factory, atlas, now=atlas.now)
    assert "updated_since" not in atlas.params("/products")[-1]
    assert run.kind == "full"
    p = piece(factory, "p1")
    assert p.status == STATUS_PUBLISHED and p.atlas_missing is None


def test_repointing_brand_in_panel_republishes_on_next_incremental(factory, atlas):
    atlas.brand("b2", "Casa Nueva")
    atlas.put("p1", brand_id="b2")
    atlas.tick(120)
    sync(factory, atlas, now=atlas.now)
    assert piece(factory, "p1").atlas_missing == "casa en borrador: Casa Nueva"

    with factory() as s:
        hermes = next(b for b in s.scalars(select(Brand)) if b.name == "Hermès")
        patch_brand_map(s, AtlasBrandMapPatch(atlas_brand_id="b2", brand_id=hermes.id), make_user(s))
    atlas.tick(120)
    sync(factory, atlas, now=atlas.now)
    p = piece(factory, "p1")
    assert p.status == STATUS_PUBLISHED and p.brand.name == "Hermès"


def test_publishing_draft_house_republishes_its_pieces_on_next_incremental(factory, atlas):
    atlas.brand("b2", "Casa Nueva")
    atlas.put("p1", brand_id="b2")
    atlas.tick(120)
    sync(factory, atlas, now=atlas.now)
    assert piece(factory, "p1").status == STATUS_DRAFT

    with factory() as s:
        casa = next(b for b in s.scalars(select(Brand)) if b.name == "Casa Nueva")
        update_brand(s, casa.id, BrandPatch(status=STATUS_PUBLISHED), make_user(s))
    atlas.tick(120)
    sync(factory, atlas, now=atlas.now)
    assert piece(factory, "p1").status == STATUS_PUBLISHED


def test_manual_run_is_a_full_product_load(factory, atlas):
    atlas.department("d2", "Zapatos")
    atlas.put("p1", department_id="d2")
    atlas.tick(120)
    sync(factory, atlas, now=atlas.now)
    with factory() as s:
        zapatos = make_category(s, "Zapatos")
        s.scalar(select(AtlasCategoryMap).where(AtlasCategoryMap.atlas_department_id == "d2")).category_id = zapatos.id
        s.commit()
    atlas.tick(120)
    run = sync(factory, atlas, kind="manual", now=atlas.now)
    assert run.kind == "manual" and run.status == "ok"
    assert "updated_since" not in atlas.params("/products")[-1]
    assert piece(factory, "p1").status == STATUS_PUBLISHED
    # La disponibilidad sigue incremental.
    assert "updated_since" in atlas.params("/availability")[-1]
