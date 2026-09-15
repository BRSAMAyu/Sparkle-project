"""add marketplace production tables

Revision ID: c15_20260502
Revises: c13_20260502, c14_20260502
Create Date: 2026-05-02 15:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base


revision: str = "c15_20260502"
down_revision: Union[str, tuple[str, str], None] = ("c13_20260502", "c14_20260502")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "marketplace_skills",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("skill_id", sa.String(length=64), nullable=False),
        sa.Column("source_skill_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("goal_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("domain", sa.String(length=96), nullable=False, server_default=""),
        sa.Column("author_id", app.models.base.GUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("trigger_condition", sa.Text(), nullable=False, server_default=""),
        sa.Column("action_template", sa.Text(), nullable=False, server_default=""),
        sa.Column("expected_outcome", sa.Text(), nullable=False, server_default=""),
        sa.Column("prerequisites", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("contraindications", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("context_signatures", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("evidence_grade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("episode_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("negative_feedback_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("revoke_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("adoption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("privacy_report", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("governance", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("previous_versions", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rollback_of_id", app.models.base.GUID(), nullable=True),
        sa.Column("auto_deprecation_reason", sa.String(length=128), nullable=True),
        sa.Column("listed_at", sa.DateTime(), nullable=True),
        sa.Column("deprecated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rollback_of_id"], ["marketplace_skills.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("skill_id"),
    )
    op.create_index(op.f("ix_marketplace_skills_deleted_at"), "marketplace_skills", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_marketplace_skills_skill_id"), "marketplace_skills", ["skill_id"], unique=True)
    op.create_index(op.f("ix_marketplace_skills_source_skill_id"), "marketplace_skills", ["source_skill_id"], unique=False)
    op.create_index(op.f("ix_marketplace_skills_domain"), "marketplace_skills", ["domain"], unique=False)
    op.create_index(op.f("ix_marketplace_skills_author_id"), "marketplace_skills", ["author_id"], unique=False)
    op.create_index(op.f("ix_marketplace_skills_status"), "marketplace_skills", ["status"], unique=False)
    op.create_index(op.f("ix_marketplace_skills_evidence_grade"), "marketplace_skills", ["evidence_grade"], unique=False)
    op.create_index("ix_marketplace_skills_status_domain", "marketplace_skills", ["status", "domain"], unique=False)
    op.create_index("ix_marketplace_skills_quality", "marketplace_skills", ["status", "quality_score"], unique=False)

    op.create_table(
        "marketplace_packs",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("pack_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("domain", sa.String(length=96), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(length=128), nullable=False, server_default="system"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("node_schema", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("task_templates", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("risk_rules", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("skill_ids", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("quality_evidence", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("negative_feedback_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("revoke_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("adoption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("privacy_report", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("governance", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("previous_versions", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rollback_of_id", app.models.base.GUID(), nullable=True),
        sa.Column("auto_deprecation_reason", sa.String(length=128), nullable=True),
        sa.Column("listed_at", sa.DateTime(), nullable=True),
        sa.Column("deprecated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["rollback_of_id"], ["marketplace_packs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pack_id"),
    )
    op.create_index(op.f("ix_marketplace_packs_deleted_at"), "marketplace_packs", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_marketplace_packs_pack_id"), "marketplace_packs", ["pack_id"], unique=True)
    op.create_index(op.f("ix_marketplace_packs_domain"), "marketplace_packs", ["domain"], unique=False)
    op.create_index(op.f("ix_marketplace_packs_status"), "marketplace_packs", ["status"], unique=False)
    op.create_index("ix_marketplace_packs_status_domain", "marketplace_packs", ["status", "domain"], unique=False)
    op.create_index("ix_marketplace_packs_quality", "marketplace_packs", ["status", "quality_score"], unique=False)

    op.create_table(
        "user_skill_adoptions",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("asset_type", sa.String(length=24), nullable=False),
        sa.Column("asset_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("explicit_confirm", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("context_signature", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("preview_snapshot", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "asset_type", "asset_id", name="uq_user_marketplace_asset_adoption"),
    )
    op.create_index(op.f("ix_user_skill_adoptions_deleted_at"), "user_skill_adoptions", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_user_skill_adoptions_user_id"), "user_skill_adoptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_skill_adoptions_asset_id"), "user_skill_adoptions", ["asset_id"], unique=False)
    op.create_index(op.f("ix_user_skill_adoptions_asset_type"), "user_skill_adoptions", ["asset_type"], unique=False)
    op.create_index(op.f("ix_user_skill_adoptions_status"), "user_skill_adoptions", ["status"], unique=False)
    op.create_index(op.f("ix_user_skill_adoptions_trace_id"), "user_skill_adoptions", ["trace_id"], unique=False)
    op.create_index("ix_user_skill_adoptions_user_asset", "user_skill_adoptions", ["user_id", "asset_type", "asset_id"], unique=False)

    op.create_table(
        "pack_adoption_history",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("adoption_id", app.models.base.GUID(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("asset_type", sa.String(length=24), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("impact_type", sa.String(length=32), nullable=False),
        sa.Column("impact_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("before_snapshot", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("after_snapshot", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("outcome", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["adoption_id"], ["user_skill_adoptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pack_adoption_history_deleted_at"), "pack_adoption_history", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_pack_adoption_history_adoption_id"), "pack_adoption_history", ["adoption_id"], unique=False)
    op.create_index(op.f("ix_pack_adoption_history_user_id"), "pack_adoption_history", ["user_id"], unique=False)
    op.create_index(op.f("ix_pack_adoption_history_asset_id"), "pack_adoption_history", ["asset_id"], unique=False)
    op.create_index(op.f("ix_pack_adoption_history_asset_type"), "pack_adoption_history", ["asset_type"], unique=False)
    op.create_index(op.f("ix_pack_adoption_history_trace_id"), "pack_adoption_history", ["trace_id"], unique=False)
    op.create_index(op.f("ix_pack_adoption_history_impact_type"), "pack_adoption_history", ["impact_type"], unique=False)
    op.create_index(op.f("ix_pack_adoption_history_outcome"), "pack_adoption_history", ["outcome"], unique=False)
    op.create_index("ix_pack_adoption_history_asset_trace", "pack_adoption_history", ["asset_type", "asset_id", "trace_id"], unique=False)
    op.create_index("ix_pack_adoption_history_user_created", "pack_adoption_history", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pack_adoption_history_user_created", table_name="pack_adoption_history")
    op.drop_index("ix_pack_adoption_history_asset_trace", table_name="pack_adoption_history")
    op.drop_index(op.f("ix_pack_adoption_history_outcome"), table_name="pack_adoption_history")
    op.drop_index(op.f("ix_pack_adoption_history_impact_type"), table_name="pack_adoption_history")
    op.drop_index(op.f("ix_pack_adoption_history_trace_id"), table_name="pack_adoption_history")
    op.drop_index(op.f("ix_pack_adoption_history_asset_type"), table_name="pack_adoption_history")
    op.drop_index(op.f("ix_pack_adoption_history_asset_id"), table_name="pack_adoption_history")
    op.drop_index(op.f("ix_pack_adoption_history_user_id"), table_name="pack_adoption_history")
    op.drop_index(op.f("ix_pack_adoption_history_adoption_id"), table_name="pack_adoption_history")
    op.drop_index(op.f("ix_pack_adoption_history_deleted_at"), table_name="pack_adoption_history")
    op.drop_table("pack_adoption_history")

    op.drop_index("ix_user_skill_adoptions_user_asset", table_name="user_skill_adoptions")
    op.drop_index(op.f("ix_user_skill_adoptions_trace_id"), table_name="user_skill_adoptions")
    op.drop_index(op.f("ix_user_skill_adoptions_status"), table_name="user_skill_adoptions")
    op.drop_index(op.f("ix_user_skill_adoptions_asset_type"), table_name="user_skill_adoptions")
    op.drop_index(op.f("ix_user_skill_adoptions_asset_id"), table_name="user_skill_adoptions")
    op.drop_index(op.f("ix_user_skill_adoptions_user_id"), table_name="user_skill_adoptions")
    op.drop_index(op.f("ix_user_skill_adoptions_deleted_at"), table_name="user_skill_adoptions")
    op.drop_table("user_skill_adoptions")

    op.drop_index("ix_marketplace_packs_quality", table_name="marketplace_packs")
    op.drop_index("ix_marketplace_packs_status_domain", table_name="marketplace_packs")
    op.drop_index(op.f("ix_marketplace_packs_status"), table_name="marketplace_packs")
    op.drop_index(op.f("ix_marketplace_packs_domain"), table_name="marketplace_packs")
    op.drop_index(op.f("ix_marketplace_packs_pack_id"), table_name="marketplace_packs")
    op.drop_index(op.f("ix_marketplace_packs_deleted_at"), table_name="marketplace_packs")
    op.drop_table("marketplace_packs")

    op.drop_index("ix_marketplace_skills_quality", table_name="marketplace_skills")
    op.drop_index("ix_marketplace_skills_status_domain", table_name="marketplace_skills")
    op.drop_index(op.f("ix_marketplace_skills_evidence_grade"), table_name="marketplace_skills")
    op.drop_index(op.f("ix_marketplace_skills_status"), table_name="marketplace_skills")
    op.drop_index(op.f("ix_marketplace_skills_author_id"), table_name="marketplace_skills")
    op.drop_index(op.f("ix_marketplace_skills_domain"), table_name="marketplace_skills")
    op.drop_index(op.f("ix_marketplace_skills_source_skill_id"), table_name="marketplace_skills")
    op.drop_index(op.f("ix_marketplace_skills_skill_id"), table_name="marketplace_skills")
    op.drop_index(op.f("ix_marketplace_skills_deleted_at"), table_name="marketplace_skills")
    op.drop_table("marketplace_skills")
