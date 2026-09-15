"""add community file copy tracking fields

Revision ID: cf20260426_file_copies
Revises: df1a2b3c4d5e, gnd001_node_documents
Create Date: 2026-04-26 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID


revision: str = "cf20260426_file_copies"
down_revision: str | tuple[str, str] | None = ("df1a2b3c4d5e", "gnd001_node_documents")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "group_files",
        sa.Column("description", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "stored_files",
        sa.Column("source_file_id", GUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_stored_files_source_file_id",
        "stored_files",
        "stored_files",
        ["source_file_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_stored_files_source_file_id", "stored_files", ["source_file_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stored_files_source_file_id", table_name="stored_files")
    op.drop_constraint("fk_stored_files_source_file_id", "stored_files", type_="foreignkey")
    op.drop_column("stored_files", "source_file_id")
    op.drop_column("group_files", "description")
