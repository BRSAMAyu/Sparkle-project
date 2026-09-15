"""add release approval requests

Revision ID: c20_20260502
Revises: c12_20260502
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base
from alembic import op

revision: str = "c20_20260502"
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
        "release_approval_requests",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payload", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("requested_by_id", app.models.base.GUID(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("required_approvals", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approvals", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rejections", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("reviewer_ids", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("applied_by_id", app.models.base.GUID(), nullable=True),
        sa.Column("apply_result", json_type, nullable=True),
        sa.Column("notification_state", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("needs_admin_attention", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint(
            "status IN ('draft','pending_review','approved','rejected','applied')",
            name="chk_release_approval_status",
        ),
        sa.CheckConstraint(
            "category IN ('policy_publish','experiment_promote','skill_systemize','domain_pack_release','kill_switch_promote','high_risk_config')",
            name="chk_release_approval_category",
        ),
        sa.CheckConstraint("required_approvals >= 1", name="chk_release_approval_required_positive"),
        sa.ForeignKeyConstraint(["applied_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_release_approval_requests_deleted_at"), "release_approval_requests", ["deleted_at"])
    op.create_index(op.f("ix_release_approval_requests_category"), "release_approval_requests", ["category"])
    op.create_index(op.f("ix_release_approval_requests_object_type"), "release_approval_requests", ["object_type"])
    op.create_index(op.f("ix_release_approval_requests_object_id"), "release_approval_requests", ["object_id"])
    op.create_index(op.f("ix_release_approval_requests_status"), "release_approval_requests", ["status"])
    op.create_index(op.f("ix_release_approval_requests_requested_by_id"), "release_approval_requests", ["requested_by_id"])
    op.create_index(op.f("ix_release_approval_requests_submitted_at"), "release_approval_requests", ["submitted_at"])
    op.create_index(op.f("ix_release_approval_requests_applied_at"), "release_approval_requests", ["applied_at"])
    op.create_index(op.f("ix_release_approval_requests_applied_by_id"), "release_approval_requests", ["applied_by_id"])
    op.create_index(
        op.f("ix_release_approval_requests_needs_admin_attention"),
        "release_approval_requests",
        ["needs_admin_attention"],
    )
    op.create_index(
        "idx_release_approval_category_status_created",
        "release_approval_requests",
        ["category", "status", "created_at"],
    )
    op.create_index(
        "idx_release_approval_object_status",
        "release_approval_requests",
        ["object_type", "object_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_release_approval_object_status", table_name="release_approval_requests")
    op.drop_index("idx_release_approval_category_status_created", table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_needs_admin_attention"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_applied_by_id"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_applied_at"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_submitted_at"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_requested_by_id"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_status"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_object_id"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_object_type"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_category"), table_name="release_approval_requests")
    op.drop_index(op.f("ix_release_approval_requests_deleted_at"), table_name="release_approval_requests")
    op.drop_table("release_approval_requests")
