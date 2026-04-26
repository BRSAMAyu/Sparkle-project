"""add knowledge node document attachments

Revision ID: gnd001_node_documents
Revises: merge_lane_d_lane_k_2026_04_26
Create Date: 2026-04-26 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

import app.models.base


revision: str = "gnd001_node_documents"
down_revision: str | tuple[str, str] | None = "merge_lane_d_lane_k_2026_04_26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_node_documents",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("node_id", app.models.base.GUID(), nullable=False),
        sa.Column("file_id", app.models.base.GUID(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["file_id"], ["stored_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["knowledge_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "node_id", "file_id", name="uq_knowledge_node_documents_user_node_file"),
    )
    op.create_index("ix_knowledge_node_documents_deleted_at", "knowledge_node_documents", ["deleted_at"], unique=False)
    op.create_index("ix_knowledge_node_documents_file_id", "knowledge_node_documents", ["file_id"], unique=False)
    op.create_index("ix_knowledge_node_documents_is_primary", "knowledge_node_documents", ["is_primary"], unique=False)
    op.create_index("ix_knowledge_node_documents_node_id", "knowledge_node_documents", ["node_id"], unique=False)
    op.create_index("ix_knowledge_node_documents_user_id", "knowledge_node_documents", ["user_id"], unique=False)
    op.create_index(
        "idx_knowledge_node_documents_user_file_primary",
        "knowledge_node_documents",
        ["user_id", "file_id", "is_primary"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_knowledge_node_documents_user_file_primary", table_name="knowledge_node_documents")
    op.drop_index("ix_knowledge_node_documents_user_id", table_name="knowledge_node_documents")
    op.drop_index("ix_knowledge_node_documents_node_id", table_name="knowledge_node_documents")
    op.drop_index("ix_knowledge_node_documents_is_primary", table_name="knowledge_node_documents")
    op.drop_index("ix_knowledge_node_documents_file_id", table_name="knowledge_node_documents")
    op.drop_index("ix_knowledge_node_documents_deleted_at", table_name="knowledge_node_documents")
    op.drop_table("knowledge_node_documents")
