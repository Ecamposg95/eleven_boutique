"""portada gallery: site_settings.hero_gallery

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_settings",
        sa.Column("hero_gallery", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    # Plain column without keys or indexes: SQLite drops it without rebuilding the table.
    op.drop_column("site_settings", "hero_gallery")
