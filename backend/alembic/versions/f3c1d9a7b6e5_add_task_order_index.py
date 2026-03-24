"""add task order index

Revision ID: f3c1d9a7b6e5
Revises: c1f4e7a9b2d6
Create Date: 2026-03-21 15:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3c1d9a7b6e5"
down_revision = "c1f4e7a9b2d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("idx_tasks_user_order_index", "tasks", ["user_id", "order_index"], unique=False)
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id
                    ORDER BY created_at DESC, id ASC
                ) AS row_num
            FROM tasks
            WHERE deleted_at IS NULL
        )
        UPDATE tasks
        SET order_index = ranked.row_num * 1000
        FROM ranked
        WHERE tasks.id = ranked.id
        """
    )
    op.alter_column("tasks", "order_index", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_tasks_user_order_index", table_name="tasks")
    op.drop_column("tasks", "order_index")
