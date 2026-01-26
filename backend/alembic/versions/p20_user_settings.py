"""add user settings table

Revision ID: p20_user_settings
Revises: p19_review_system_tables
Create Date: 2026-01-27 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.utils.migration_helpers import get_inspector, table_exists

# revision identifiers, used by Alembic.
revision: str = "p20_user_settings"
down_revision: Union[str, None] = "p19_review_system_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = get_inspector()

    if not table_exists(inspector, "user_settings"):
        op.create_table(
            "user_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("transparency_level", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("system_update_level", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("idx_user_settings_user", "user_settings", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("user_settings")
