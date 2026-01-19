"""user_memory_settings

Revision ID: e4b6c7d8f9a0
Revises: d1e2f3a4b5c6
Create Date: 2026-02-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = "e4b6c7d8f9a0"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_memory_settings",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_preferences", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_goals", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_episodic", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "capture_level",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'medium'"),
        ),
        sa.Column(
            "blocked_pref_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "blocked_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_memory_settings_user"),
    )
    op.create_index(
        "ix_user_memory_settings_user",
        "user_memory_settings",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "ix_user_memory_settings_deleted_at",
        "user_memory_settings",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_memory_settings_deleted_at", table_name="user_memory_settings")
    op.drop_index("ix_user_memory_settings_user", table_name="user_memory_settings")
    op.drop_table("user_memory_settings")
