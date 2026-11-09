import io
import re

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.config import BASE_DIR
from app.db import make_engine
from app.models import Base
from tests.conftest import alembic_config

EXPECTED_TABLES = {
    "brands",
    "brand_aliases",
    "categories",
    "products",
    "product_media",
    "collections",
    "collection_products",
    "lookbooks",
    "lookbook_blocks",
    "lookbook_products",
    "site_settings",
    "catalog_events",
    "admin_users",
    "admin_sessions",
    "login_attempts",
    "audit_logs",
    "media_assets",
    "product_variants",
    "import_runs",
}
ADMIN_TABLES = {
    "admin_users",
    "admin_sessions",
    "login_attempts",
    "audit_logs",
    "media_assets",
    "product_variants",
    "import_runs",
}
ASSET_FK_COLUMNS = {
    "brands": {"logo_asset_id", "editorial_asset_id"},
    "product_media": {"media_asset_id"},
    "collections": {"cover_asset_id"},
    "lookbooks": {"cover_asset_id"},
    "site_settings": {"hero_asset_id", "hero_mobile_asset_id"},
}
NEW_COLUMNS = {
    "products": {"photo_refs"},
    "brands": {"logo_asset_id", "editorial_asset_id"},
    "product_media": {"media_asset_id"},
    "collections": {"cover_asset_id"},
    "lookbooks": {"cover_asset_id"},
    "site_settings": {"hero_asset_id", "hero_mobile_asset_id", "hero_mobile_image_url"},
}


def schema_differences(connection) -> list:
    """SQLite does not report the name of a foreign key declared inline in ADD COLUMN (the only
    form that avoids a table rebuild), so those show up as a remove/add pair that differs by name
    alone. Only that exact pair is ignored; test_asset_foreign_keys_are_enforced covers behavior."""
    asset_columns = {column for columns in ASSET_FK_COLUMNS.values() for column in columns}

    def is_unnamed_asset_fk(difference) -> bool:
        kind, constraint = difference[0], difference[1] if len(difference) > 1 else None
        return (
            kind in ("remove_fk", "add_fk")
            and constraint.table.name in ASSET_FK_COLUMNS
            and {column.name for column in constraint.columns} <= asset_columns
            and constraint.referred_table.name == "media_assets"
        )

    context = MigrationContext.configure(connection, opts={"compare_type": True})
    return [d for d in compare_metadata(context, Base.metadata) if not is_unnamed_asset_fk(d)]


def test_upgrade_creates_every_table_and_matches_the_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    command.upgrade(alembic_config(url), "head")
    engine = make_engine(url)
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert schema_differences(connection) == []
    engine.dispose()


def test_downgrade_removes_the_schema(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    engine = make_engine(url)
    assert not EXPECTED_TABLES & set(inspect(engine).get_table_names())
    engine.dispose()


def test_migration_renders_for_postgres_without_sqlite_only_sql():
    config = alembic_config("postgresql+psycopg://user:pass@localhost/eleven")
    config.output_buffer = io.StringIO()
    command.upgrade(config, "head", sql=True)
    ddl = config.output_buffer.getvalue()
    assert "CREATE TABLE brands" in ddl
    assert "UUID" in ddl
    assert "TIMESTAMP WITH TIME ZONE" in ddl
    assert "JSON" in ddl
    assert "BOOLEAN DEFAULT false" in ddl
    assert "BOOLEAN DEFAULT 0" not in ddl
    assert "PRAGMA" not in ddl
    assert "AUTOINCREMENT" not in ddl


def test_foreign_keys_are_enforced_on_sqlite(database_url):
    engine = make_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO product_media (id, product_id, url, alt, created_at, updated_at)"
                    " VALUES ('a', 'missing', 'u', 'a', '2026-01-01', '2026-01-01')"
                )
            )
    engine.dispose()


def test_app_code_never_calls_create_all():
    needle = "create" + "_all"
    for folder in ("app", "scripts", "alembic"):
        for path in (BASE_DIR / folder).rglob("*.py"):
            assert needle not in path.read_text(), path


# --- 0001 -> 0002 with real rows -------------------------------------------------------

BRAND = "b" * 32
CATEGORY = "c" * 32
PRODUCT = "d" * 32
MEDIA = "e" * 32
ALIAS = "f" * 32
COLLECTION = "1" * 32
LOOKBOOK = "2" * 32
BLOCK = "3" * 32
SETTINGS = "4" * 32
STAMP = "2026-01-01 00:00:00"


def seed_0001(connection) -> None:
    statements = (
        "INSERT INTO brands (id, name, original_name, slug, search_text, logo_url, created_at, updated_at)"
        f" VALUES ('{BRAND}', 'Marca', 'Marca', 'marca', 'marca', '/demo/logo.jpg', '{STAMP}', '{STAMP}')",
        "INSERT INTO brand_aliases (id, brand_id, alias, slug, search_text, created_at, updated_at)"
        f" VALUES ('{ALIAS}', '{BRAND}', 'Alias', 'alias', 'alias', '{STAMP}', '{STAMP}')",
        "INSERT INTO categories (id, name, slug, search_text, created_at, updated_at)"
        f" VALUES ('{CATEGORY}', 'Cat', 'cat', 'cat', '{STAMP}', '{STAMP}')",
        "INSERT INTO products (id, sku, slug, name, brand_id, category_id, status, search_text,"
        " created_at, updated_at)"
        f" VALUES ('{PRODUCT}', 'S-1', 'pieza', 'Pieza', '{BRAND}', '{CATEGORY}', 'published',"
        f" 'pieza', '{STAMP}', '{STAMP}')",
        "INSERT INTO product_media (id, product_id, url, alt, is_primary, created_at, updated_at)"
        f" VALUES ('{MEDIA}', '{PRODUCT}', '/demo/a.jpg', 'Alt', 1, '{STAMP}', '{STAMP}')",
        "INSERT INTO collections (id, slug, title, status, cover_url, created_at, updated_at)"
        f" VALUES ('{COLLECTION}', 'col', 'Col', 'published', '/demo/c.jpg', '{STAMP}', '{STAMP}')",
        f"INSERT INTO collection_products (collection_id, product_id) VALUES ('{COLLECTION}', '{PRODUCT}')",
        "INSERT INTO lookbooks (id, slug, title, status, created_at, updated_at)"
        f" VALUES ('{LOOKBOOK}', 'look', 'Look', 'published', '{STAMP}', '{STAMP}')",
        f"INSERT INTO lookbook_products (lookbook_id, product_id) VALUES ('{LOOKBOOK}', '{PRODUCT}')",
        "INSERT INTO lookbook_blocks (id, lookbook_id, type, content, created_at, updated_at)"
        f""" VALUES ('{BLOCK}', '{LOOKBOOK}', 'text', '{{"body": "x"}}', '{STAMP}', '{STAMP}')""",
        "INSERT INTO site_settings (id, is_demo, hero_image_url, created_at, updated_at)"
        f" VALUES ('{SETTINGS}', 0, '/demo/h.jpg', '{STAMP}', '{STAMP}')",
    )
    for statement in statements:
        connection.execute(text(statement))


def counts(engine) -> dict[str, int]:
    tables = (
        "brands",
        "brand_aliases",
        "categories",
        "products",
        "product_media",
        "collections",
        "collection_products",
        "lookbooks",
        "lookbook_products",
        "lookbook_blocks",
        "site_settings",
    )
    with engine.connect() as connection:
        return {t: connection.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in tables}


@pytest.fixture
def seeded_0001(tmp_path):
    url = f"sqlite:///{tmp_path / 'data.db'}"
    command.upgrade(alembic_config(url), "0001")
    engine = make_engine(url)
    with engine.begin() as connection:
        seed_0001(connection)
    yield url, engine
    engine.dispose()


def test_upgrade_from_0001_to_head_keeps_data_and_public_reads_work(seeded_0001, make_client):
    url, engine = seeded_0001
    before = counts(engine)
    command.upgrade(alembic_config(url), "head")
    assert counts(engine) == before
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT photo_refs FROM products WHERE id = :id"), {"id": PRODUCT}
        ).scalar()
        media_url = connection.execute(text("SELECT url FROM product_media")).scalar()
        logo = connection.execute(text("SELECT logo_url FROM brands")).scalar()
    assert row == "[]"
    assert media_url == "/demo/a.jpg"
    assert logo == "/demo/logo.jpg"

    client = make_client(database_url=url)
    # The brand is a draft, so it stays hidden; demo mode shows it is intact.
    demo = make_client(database_url=url, demo_mode=True)
    assert client.get("/api/v1/brands/marca").status_code == 404
    assert demo.get("/api/v1/brands/marca").json()["logo_url"] == "/demo/logo.jpg"
    assert demo.get("/api/v1/products/pieza").json()["gallery"][0]["url"] == "/demo/a.jpg"
    assert demo.get("/api/v1/site-settings/public").json()["hero"]["image_url"] == "/demo/h.jpg"


def test_downgrade_keeps_data_and_removes_only_the_new_schema(seeded_0001):
    url, engine = seeded_0001
    config = alembic_config(url)
    before = counts(engine)
    command.upgrade(config, "0002")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO media_assets (id, storage_key, url, filename, alt, content_type, width,"
                " height, size_bytes, created_at, updated_at) VALUES"
                f" ('{'a' * 32}', 'k.jpg', '/media/k.jpg', 'k.jpg', '', 'image/jpeg', 1, 1, 1,"
                f" '{STAMP}', '{STAMP}')"
            )
        )
        connection.execute(text(f"UPDATE product_media SET media_asset_id = '{'a' * 32}'"))
        connection.execute(text(f"UPDATE brands SET logo_asset_id = '{'a' * 32}'"))

    command.downgrade(config, "0001")

    assert counts(engine) == before
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert not ADMIN_TABLES & tables
    for table, columns in NEW_COLUMNS.items():
        assert not columns & {column["name"] for column in inspector.get_columns(table)}, table
    with engine.connect() as connection:
        assert connection.execute(text("SELECT url FROM product_media")).scalar() == "/demo/a.jpg"
        assert connection.execute(text("SELECT status FROM products")).scalar() == "published"
    assert "ix_products_status" in {index["name"] for index in inspector.get_indexes("products")}


def test_constraints_survive_the_downgrade_rebuild(seeded_0001):
    url, engine = seeded_0001
    config = alembic_config(url)
    command.upgrade(config, "0002")
    command.downgrade(config, "0001")
    bad = (
        "UPDATE products SET status = 'otro'",
        "UPDATE brands SET kind = 'otro'",
        f"UPDATE products SET brand_id = '{'9' * 32}'",
        f"INSERT INTO brand_aliases (id, brand_id, alias, slug, search_text, created_at, updated_at)"
        f" VALUES ('{'8' * 32}', '{BRAND}', 'Dup', 'alias', 'dup', '{STAMP}', '{STAMP}')",
    )
    for statement in bad:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(statement))
    # ON DELETE CASCADE still reaches the rebuilt child table.
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM products"))
        assert connection.execute(text("SELECT count(*) FROM product_media")).scalar() == 0


def test_round_trip_returns_to_a_schema_matching_the_models(seeded_0001):
    url, engine = seeded_0001
    config = alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "0001")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert schema_differences(connection) == []
        # Nothing was re-added twice and enforcement is back on a new connection.
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert connection.execute(text("SELECT count(*) FROM products")).scalar() == 1


def test_asset_foreign_keys_are_enforced_after_upgrade(seeded_0001):
    url, engine = seeded_0001
    command.upgrade(alembic_config(url), "0002")
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(f"UPDATE brands SET logo_asset_id = '{'9' * 32}'"))


def test_0002_renders_for_postgres_in_both_directions():
    config = alembic_config("postgresql+psycopg://user:pass@localhost/eleven")
    config.output_buffer = io.StringIO()
    command.upgrade(config, "0001:0002", sql=True)
    ddl = config.output_buffer.getvalue()
    assert "CREATE TABLE admin_users" in ddl
    assert "ADD COLUMN photo_refs JSON DEFAULT '[]' NOT NULL" in ddl
    assert "fk_brands_logo_asset_id_media_assets" in ddl
    assert "ON DELETE RESTRICT" in ddl
    assert "PRAGMA" not in ddl
    assert not re.search(r"\bCHAR\(32\)", ddl)

    config.output_buffer = io.StringIO()
    command.downgrade(config, "0002:0001", sql=True)
    ddl = config.output_buffer.getvalue()
    assert "DROP TABLE admin_users" in ddl
    assert "DROP CONSTRAINT fk_brands_logo_asset_id_media_assets" in ddl
    assert "ALTER TABLE products DROP COLUMN photo_refs" in ddl
    assert "PRAGMA" not in ddl
