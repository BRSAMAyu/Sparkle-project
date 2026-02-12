"""create user preferences center

Revision ID: f3b8c1d2e4f5
Revises: f2a7c9d1e0b4
Create Date: 2026-02-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base

revision = "f3b8c1d2e4f5"
down_revision = "f2a7c9d1e0b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_preferences_center",
        sa.Column(
            "user_id",
            app.models.base.GUID(),
            sa.ForeignKey("users.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "explicit",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "inferred",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_explicit_update", sa.DateTime(), nullable=True),
        sa.Column("last_inferred_update", sa.DateTime(), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_preferences_center_user"),
    )
    op.create_index(
        "ix_user_preferences_center_user_id",
        "user_preferences_center",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "ix_user_preferences_center_deleted_at",
        "user_preferences_center",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_preferences_center_deleted_at", table_name="user_preferences_center")
    op.drop_index("ix_user_preferences_center_user_id", table_name="user_preferences_center")
    op.drop_table("user_preferences_center")
