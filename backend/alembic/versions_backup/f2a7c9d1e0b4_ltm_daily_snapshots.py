"""ltm daily snapshots

Revision ID: f2a7c9d1e0b4
Revises: e4b6c7d8f9a0
Create Date: 2025-01-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f2a7c9d1e0b4"
down_revision = "e4b6c7d8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ltm_daily_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_date"),
    )
    op.create_index(
        "idx_ltm_daily_snapshots_date",
        "ltm_daily_snapshots",
        ["snapshot_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_ltm_daily_snapshots_date", table_name="ltm_daily_snapshots")
    op.drop_table("ltm_daily_snapshots")
