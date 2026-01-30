"""add decision records

Revision ID: f5d0a1b2c3d4
Revises: f4c9d1e2a3b5
Create Date: 2026-02-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base

revision = "f5d0a1b2c3d4"
down_revision = "f4c9d1e2a3b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_records",
        sa.Column("user_id", app.models.base.GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("preference_version", sa.Integer(), nullable=False),
        sa.Column("preferences_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("outcome", sa.String(length=500), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_records_user_id", "decision_records", ["user_id"], unique=False)
    op.create_index("ix_decision_records_module", "decision_records", ["module"], unique=False)
    op.create_index("ix_decision_records_created_at", "decision_records", ["created_at"], unique=False)
    op.create_index("ix_decision_records_deleted_at", "decision_records", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_decision_records_deleted_at", table_name="decision_records")
    op.drop_index("ix_decision_records_created_at", table_name="decision_records")
    op.drop_index("ix_decision_records_module", table_name="decision_records")
    op.drop_index("ix_decision_records_user_id", table_name="decision_records")
    op.drop_table("decision_records")
