"""sincronización con Atlas ONE: estado, mapas, disponibilidad y reenvío de eventos

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

NOT_NULL = "external_inventory_id IS NOT NULL"


def upgrade() -> None:
    op.create_table(
        "atlas_sync_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("products_since", sa.DateTime(timezone=True)),
        sa.Column("availability_since", sa.DateTime(timezone=True)),
        sa.Column("last_full_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_ok_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.PrimaryKeyConstraint("id", name="pk_atlas_sync_state"),
    )
    op.create_table(
        "atlas_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error", sa.Text()),
        sa.PrimaryKeyConstraint("id", name="pk_atlas_sync_runs"),
    )
    op.create_index("ix_atlas_sync_runs_started_at", "atlas_sync_runs", ["started_at"])
    op.create_table(
        "atlas_brand_map",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atlas_brand_id", sa.String(length=100), nullable=False),
        sa.Column("atlas_name", sa.String(length=300), nullable=False),
        sa.Column("brand_id", sa.Uuid()),
        sa.ForeignKeyConstraint(
            ["brand_id"], ["brands.id"], name="fk_atlas_brand_map_brand_id_brands", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_atlas_brand_map"),
        sa.UniqueConstraint("atlas_brand_id", name="uq_atlas_brand_map_atlas_brand_id"),
    )
    op.create_index("ix_atlas_brand_map_brand_id", "atlas_brand_map", ["brand_id"])
    op.create_table(
        "atlas_category_map",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atlas_department_id", sa.String(length=100), nullable=False),
        sa.Column("atlas_name", sa.String(length=300), nullable=False),
        sa.Column("atlas_parent_id", sa.String(length=100)),
        sa.Column("category_id", sa.Uuid()),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_atlas_category_map_category_id_categories",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_atlas_category_map"),
        sa.UniqueConstraint("atlas_department_id", name="uq_atlas_category_map_atlas_department_id"),
    )
    op.create_index("ix_atlas_category_map_category_id", "atlas_category_map", ["category_id"])

    # Columnas simples (sin llaves): SQLite las agrega sin reconstruir la tabla.
    op.add_column(
        "products",
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("products", sa.Column("atlas_missing", sa.String(length=300)))
    op.add_column(
        "products",
        sa.Column("hidden_on_web", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("products", sa.Column("gender", sa.String(length=50)))
    op.add_column("products", sa.Column("model", sa.String(length=200)))
    op.add_column("products", sa.Column("material", sa.String(length=200)))
    op.add_column("product_variants", sa.Column("external_inventory_id", sa.String(length=200)))
    op.add_column(
        "product_variants",
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("catalog_events", sa.Column("forwarded_at", sa.DateTime(timezone=True)))

    # No se manda historia vieja a Atlas: todo evento existente queda como reenviado.
    op.execute("UPDATE catalog_events SET forwarded_at = CURRENT_TIMESTAMP")

    for table in ("products", "product_variants"):
        op.create_index(
            f"uq_{table}_external_inventory_id",
            table,
            ["external_inventory_id"],
            unique=True,
            sqlite_where=sa.text(NOT_NULL),
            postgresql_where=sa.text(NOT_NULL),
        )


def downgrade() -> None:
    for table in ("product_variants", "products"):
        op.drop_index(f"uq_{table}_external_inventory_id", table_name=table)
    op.drop_column("catalog_events", "forwarded_at")
    op.drop_column("product_variants", "available")
    op.drop_column("product_variants", "external_inventory_id")
    for column in ("material", "model", "gender", "hidden_on_web", "atlas_missing", "available"):
        op.drop_column("products", column)
    op.drop_table("atlas_category_map")
    op.drop_table("atlas_brand_map")
    op.drop_table("atlas_sync_runs")
    op.drop_table("atlas_sync_state")
