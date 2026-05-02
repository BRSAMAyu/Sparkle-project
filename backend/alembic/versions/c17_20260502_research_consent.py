"""add durable research consent tables

Revision ID: c17_20260502
Revises: c12_20260502
Create Date: 2026-05-02 15:15:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base

revision: str = "c17_20260502"
down_revision: str | None = "c12_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "research_consents",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("consent_type", sa.String(length=64), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("deleted_at", "user_id", "consent_type", "granted", "granted_at", "revoked_at"):
        op.create_index(op.f(f"ix_research_consents_{col}"), "research_consents", [col])
    op.create_index("idx_research_consent_user_type", "research_consents", ["user_id", "consent_type"], unique=True)
    op.create_index("idx_research_consent_granted_type", "research_consents", ["granted", "consent_type"])

    op.create_table(
        "research_export_usages",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("consent_type", sa.String(length=64), nullable=False),
        sa.Column("export_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("exported_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", json_type, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("deleted_at", "user_id", "consent_type", "export_id", "status", "exported_at", "revoked_at"):
        op.create_index(op.f(f"ix_research_export_usages_{col}"), "research_export_usages", [col])
    op.create_index("idx_research_export_user_status", "research_export_usages", ["user_id", "status"])
    op.create_index("idx_research_export_consent_status", "research_export_usages", ["consent_type", "status"])


def downgrade() -> None:
    op.drop_index("idx_research_export_consent_status", table_name="research_export_usages")
    op.drop_index("idx_research_export_user_status", table_name="research_export_usages")
    for col in ("revoked_at", "exported_at", "status", "export_id", "consent_type", "user_id", "deleted_at"):
        op.drop_index(op.f(f"ix_research_export_usages_{col}"), table_name="research_export_usages")
    op.drop_table("research_export_usages")

    op.drop_index("idx_research_consent_granted_type", table_name="research_consents")
    op.drop_index("idx_research_consent_user_type", table_name="research_consents")
    for col in ("revoked_at", "granted_at", "granted", "consent_type", "user_id", "deleted_at"):
        op.drop_index(op.f(f"ix_research_consents_{col}"), table_name="research_consents")
    op.drop_table("research_consents")
