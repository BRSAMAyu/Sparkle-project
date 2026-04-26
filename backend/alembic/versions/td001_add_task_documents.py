"""add task document links

Revision ID: td001_task_documents
Revises: gnd001_node_documents
Create Date: 2026-04-26 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

import app.models.base


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'task_documents';"
#   backfill_plan: "n/a"
#   owner: "backend"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = "td001_task_documents"
down_revision: str | None = "gnd001_node_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_documents",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("task_id", app.models.base.GUID(), nullable=False),
        sa.Column("file_id", app.models.base.GUID(), nullable=False),
        sa.Column("linked_by", sa.String(length=16), nullable=False, server_default="user"),
        sa.ForeignKeyConstraint(["file_id"], ["stored_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "file_id", name="uq_task_documents_task_file"),
    )
    op.create_index("ix_task_documents_deleted_at", "task_documents", ["deleted_at"], unique=False)
    op.create_index("ix_task_documents_file_id", "task_documents", ["file_id"], unique=False)
    op.create_index("ix_task_documents_task_id", "task_documents", ["task_id"], unique=False)
    op.create_index("idx_task_documents_task_created", "task_documents", ["task_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_task_documents_task_created", table_name="task_documents")
    op.drop_index("ix_task_documents_task_id", table_name="task_documents")
    op.drop_index("ix_task_documents_file_id", table_name="task_documents")
    op.drop_index("ix_task_documents_deleted_at", table_name="task_documents")
    op.drop_table("task_documents")
