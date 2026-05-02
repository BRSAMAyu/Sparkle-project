"""add source lifecycle fields to stored files

Revision ID: fv17_20260502
Revises: wp18_20260502
Create Date: 2026-05-02 14:20:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "fv17_20260502"
down_revision: str | None = "wp18_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "stored_files",
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="active"),
    )
    op.add_column("stored_files", sa.Column("lifecycle_reason", sa.String(length=255), nullable=True))
    op.add_column("stored_files", sa.Column("lifecycle_updated_at", sa.DateTime(), nullable=True))
    op.add_column("stored_files", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("stored_files", sa.Column("revoked_at", sa.DateTime(), nullable=True))
    op.add_column("stored_files", sa.Column("orphaned_at", sa.DateTime(), nullable=True))
    op.add_column("stored_files", sa.Column("archive_review_due_at", sa.DateTime(), nullable=True))
    op.add_column("stored_files", sa.Column("erased_at", sa.DateTime(), nullable=True))
    op.add_column("stored_files", sa.Column("erasure_receipt", sa.String(length=255), nullable=True))

    op.create_index("ix_stored_files_lifecycle_status", "stored_files", ["lifecycle_status"])
    op.create_index("ix_stored_files_archived_at", "stored_files", ["archived_at"])
    op.create_index("ix_stored_files_revoked_at", "stored_files", ["revoked_at"])
    op.create_index("ix_stored_files_orphaned_at", "stored_files", ["orphaned_at"])
    op.create_index("ix_stored_files_archive_review_due_at", "stored_files", ["archive_review_due_at"])
    op.create_check_constraint(
        "chk_stored_files_lifecycle_status",
        "stored_files",
        "lifecycle_status IN ('active', 'archived', 'revoked', 'orphaned')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_stored_files_lifecycle_status", "stored_files", type_="check")
    op.drop_index("ix_stored_files_archive_review_due_at", table_name="stored_files")
    op.drop_index("ix_stored_files_orphaned_at", table_name="stored_files")
    op.drop_index("ix_stored_files_revoked_at", table_name="stored_files")
    op.drop_index("ix_stored_files_archived_at", table_name="stored_files")
    op.drop_index("ix_stored_files_lifecycle_status", table_name="stored_files")
    op.drop_column("stored_files", "erasure_receipt")
    op.drop_column("stored_files", "erased_at")
    op.drop_column("stored_files", "archive_review_due_at")
    op.drop_column("stored_files", "orphaned_at")
    op.drop_column("stored_files", "revoked_at")
    op.drop_column("stored_files", "archived_at")
    op.drop_column("stored_files", "lifecycle_updated_at")
    op.drop_column("stored_files", "lifecycle_reason")
    op.drop_column("stored_files", "lifecycle_status")
