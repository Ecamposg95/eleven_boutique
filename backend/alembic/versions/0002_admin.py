"""admin panel: users, sessions, audit, media assets, variants, import runs

Revision ID: 0002
Revises: 0001

SQLite note. `batch_alter_table` rebuilds a table by dropping the original, and with
foreign_keys=ON (see app/db.py) that DROP runs an implicit DELETE: it would cascade into
product_media or fail on RESTRICT. So:
- upgrade never rebuilds: columns go in with ADD COLUMN and an inline named reference.
- downgrade has to rebuild, because SQLite cannot drop a column that has a foreign key, so
  it turns enforcement off first and refuses to continue if that did not take effect.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ASSET_COLUMNS = (
    ("brands", "logo_asset_id"),
    ("brands", "editorial_asset_id"),
    ("product_media", "media_asset_id"),
    ("collections", "cover_asset_id"),
    ("lookbooks", "cover_asset_id"),
    ("site_settings", "hero_asset_id"),
    ("site_settings", "hero_mobile_asset_id"),
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _add_asset_column(table: str, column: str) -> None:
    constraint = f"fk_{table}_{column}_media_assets"
    if op.get_context().dialect.name == "sqlite":
        # The one form that adds a named foreign key to SQLite without rebuilding the table.
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} CHAR(32) CONSTRAINT {constraint} "
            "REFERENCES media_assets (id) ON DELETE RESTRICT"
        )
        return
    op.add_column(table, sa.Column(column, sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f(constraint), table, "media_assets", [column], ["id"], ondelete="RESTRICT"
    )


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "role IN ('superadmin', 'admin', 'editor')", name=op.f("ck_admin_users_role")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_users")),
        sa.UniqueConstraint("email", name=op.f("uq_admin_users_email")),
    )

    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["admin_users.id"],
            name=op.f("fk_admin_sessions_user_id_admin_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_admin_sessions_token_hash")),
    )
    op.create_index(op.f("ix_admin_sessions_user_id"), "admin_sessions", ["user_id"])
    op.create_index(op.f("ix_admin_sessions_expires_at"), "admin_sessions", ["expires_at"])

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_key", sa.String(length=64), nullable=False),
        sa.Column("succeeded", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_attempts")),
    )
    op.create_index("ix_login_attempts_key_time", "login_attempts", ["email_key", "attempted_at"])
    op.create_index(op.f("ix_login_attempts_attempted_at"), "login_attempts", ["attempted_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("user_email", sa.String(length=254), nullable=True),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("entity", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["admin_users.id"],
            name=op.f("fk_audit_logs_user_id_admin_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    for column in ("user_id", "operation", "entity", "entity_id", "created_at"):
        op.create_index(op.f(f"ix_audit_logs_{column}"), "audit_logs", [column])

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("alt", sa.String(length=500), server_default="", nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["admin_users.id"],
            name=op.f("fk_media_assets_uploaded_by_id_admin_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_media_assets_storage_key")),
        sa.UniqueConstraint("url", name=op.f("uq_media_assets_url")),
    )
    op.create_index(op.f("ix_media_assets_filename"), "media_assets", ["filename"])
    op.create_index(op.f("ix_media_assets_uploaded_by_id"), "media_assets", ["uploaded_by_id"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=100), nullable=True),
        sa.Column("size", sa.String(length=50), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_variants_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_variants")),
        sa.UniqueConstraint("sku", name=op.f("uq_product_variants_sku")),
    )
    op.create_index(op.f("ix_product_variants_product_id"), "product_variants", ["product_id"])

    op.create_table(
        "import_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("update_existing", sa.Boolean(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("results", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('preview', 'completed', 'expired')", name=op.f("ck_import_runs_status")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["admin_users.id"],
            name=op.f("fk_import_runs_created_by_id_admin_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_runs")),
    )
    for column in ("status", "created_by_id", "expires_at"):
        op.create_index(op.f(f"ix_import_runs_{column}"), "import_runs", [column])

    # Existing rows keep working: every new column is nullable or has a default.
    op.add_column(
        "products", sa.Column("photo_refs", sa.JSON(), server_default="[]", nullable=False)
    )
    op.add_column("site_settings", sa.Column("hero_mobile_image_url", sa.String(500)))
    for table, column in ASSET_COLUMNS:
        _add_asset_column(table, column)
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column])
    op.create_index(
        "uq_product_media_product_asset",
        "product_media",
        ["product_id", "media_asset_id"],
        unique=True,
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
            "reconstruir las tablas borraría datos. Baja 0002 en una ejecución aparte."
        )


def downgrade() -> None:
    _disable_sqlite_foreign_keys()

    op.drop_index("uq_product_media_product_asset", table_name="product_media")
    for table, column in ASSET_COLUMNS:
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
    for table in ("brands", "product_media", "collections", "lookbooks", "site_settings"):
        columns = [column for owner, column in ASSET_COLUMNS if owner == table]
        with op.batch_alter_table(table) as batch_op:
            if op.get_context().dialect.name != "sqlite":
                for column in columns:
                    batch_op.drop_constraint(
                        op.f(f"fk_{table}_{column}_media_assets"), type_="foreignkey"
                    )
            for column in columns:
                batch_op.drop_column(column)
    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.drop_column("hero_mobile_image_url")
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("photo_refs")

    for table in (
        "import_runs",
        "product_variants",
        "media_assets",
        "audit_logs",
        "login_attempts",
        "admin_sessions",
        "admin_users",
    ):
        op.drop_table(table)
