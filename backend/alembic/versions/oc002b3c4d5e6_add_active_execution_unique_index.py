"""add active execution unique index

Revision ID: oc002b3c4d5e6
Revises: oc001a2b3c4d5
Create Date: 2026-03-27 22:10:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "oc002b3c4d5e6"
down_revision = "oc001a2b3c4d5"
branch_labels = None
depends_on = None


INDEX_NAME = "uq_execution_intents_active_task"
ACTIVE_STATUSES = "'draft','ready','dispatched','running','waiting_approval'"


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
            ON execution_intents (user_id, task_id)
            WHERE deleted_at IS NULL
              AND status IN ({ACTIVE_STATUSES})
            """
        )
        return

    if dialect == "sqlite":
        op.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
            ON execution_intents (user_id, task_id)
            WHERE deleted_at IS NULL
              AND status IN ({ACTIVE_STATUSES})
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect in {"postgresql", "sqlite"}:
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
