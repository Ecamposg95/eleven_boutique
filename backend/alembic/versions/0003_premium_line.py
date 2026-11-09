"""premium consult line: brands.is_premium and site_settings.whatsapp_premium_number

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "brands",
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("site_settings", sa.Column("whatsapp_premium_number", sa.String(length=40)))


def downgrade() -> None:
    # Plain columns without keys or indexes: SQLite drops them without rebuilding the table.
    op.drop_column("site_settings", "whatsapp_premium_number")
    op.drop_column("brands", "is_premium")
