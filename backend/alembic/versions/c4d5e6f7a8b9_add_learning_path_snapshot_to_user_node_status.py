"""add learning_path_snapshot to user_node_status

Revision ID: c4d5e6f7a8b9
Revises: a4b5c6d7e8f9
Create Date: 2026-03-23 18:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "user_node_status", "learning_path_snapshot"):
        op.add_column(
            "user_node_status",
            sa.Column("learning_path_snapshot", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_column(bind, "user_node_status", "learning_path_snapshot"):
        op.drop_column("user_node_status", "learning_path_snapshot")
