"""tienda nueva: department covers, detail and attention banners, Instagram link

Revision ID: 0006
Revises: 0005

Same SQLite rules as 0002: upgrade adds asset columns inline (no table rebuild); downgrade has
to rebuild because SQLite cannot drop a column that has a foreign key, so it turns enforcement
off first and refuses to continue if that did not take effect.
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

INSTAGRAM_URL = "https://www.instagram.com/eleven.fashionboutique/"

# (table, column) in creation order; downgrade drops them in reverse.
ASSET_COLUMNS = (
    ("categories", "cover_asset_id"),
    ("site_settings", "detail_asset_id"),
    ("site_settings", "detail_mobile_asset_id"),
    ("site_settings", "attention_asset_id"),
    ("site_settings", "attention_mobile_asset_id"),
)
PLAIN_COLUMNS = (
    ("categories", "cover_url", sa.String(500)),
    ("site_settings", "instagram_url", sa.String(500)),
    ("site_settings", "detail_image_url", sa.String(500)),
    ("site_settings", "detail_mobile_image_url", sa.String(500)),
    ("site_settings", "detail_caption", sa.Text()),
    ("site_settings", "attention_image_url", sa.String(500)),
    ("site_settings", "attention_mobile_image_url", sa.String(500)),
    ("site_settings", "attention_headline", sa.Text()),
    ("site_settings", "attention_subhead", sa.Text()),
)


def _add_asset_column(table: str, column: str) -> None:
    constraint = f"fk_{table}_{column}_media_assets"
    if op.get_context().dialect.name == "sqlite":
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} CHAR(32) CONSTRAINT {constraint} "
            "REFERENCES media_assets (id) ON DELETE RESTRICT"
        )
        return
    op.add_column(table, sa.Column(column, sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f(constraint), table, "media_assets", [column], ["id"], ondelete="RESTRICT"
    )


def _disable_sqlite_foreign_keys() -> None:
    """Must run before any write: SQLite ignores this pragma inside a transaction."""
    if op.get_context().dialect.name != "sqlite":
        return
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    if bind.exec_driver_sql("PRAGMA foreign_keys").scalar() != 0:
        raise RuntimeError(
            "No se pudieron desactivar las llaves foráneas de SQLite; "
            "reconstruir las tablas borraría datos. Baja 0005 en una ejecución aparte."
        )


def upgrade() -> None:
    for table, column, type_ in PLAIN_COLUMNS:
        op.add_column(table, sa.Column(column, type_))
    for table, column in ASSET_COLUMNS:
        _add_asset_column(table, column)
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column])
    op.execute(
        sa.text("UPDATE site_settings SET instagram_url = :url WHERE instagram_url IS NULL").bindparams(
            url=INSTAGRAM_URL
        )
    )


def downgrade() -> None:
    _disable_sqlite_foreign_keys()

    for table, column in reversed(ASSET_COLUMNS):
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
    for table in ("site_settings", "categories"):
        asset_columns = [c for owner, c in reversed(ASSET_COLUMNS) if owner == table]
        plain_columns = [c for owner, c, _ in reversed(PLAIN_COLUMNS) if owner == table]
        with op.batch_alter_table(table) as batch_op:
            if op.get_context().dialect.name != "sqlite":
                for column in asset_columns:
                    batch_op.drop_constraint(
                        op.f(f"fk_{table}_{column}_media_assets"), type_="foreignkey"
                    )
            for column in asset_columns + plain_columns:
                batch_op.drop_column(column)
