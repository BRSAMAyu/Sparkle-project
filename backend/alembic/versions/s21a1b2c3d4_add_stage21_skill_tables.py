"""add stage21 skill tables

Revision ID: s21a1b2c3d4
Revises: s20a1b2c3d4
Create Date: 2026-04-21 21:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "s21a1b2c3d4"
down_revision = "s20a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("forked_from_share_id", sa.String(length=36), nullable=True),
        sa.Column("shared_catalog_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("pattern_template", sa.String(length=4000), nullable=False),
        sa.Column("activation_conditions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("examples", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("privacy_level", sa.String(length=16), nullable=False, server_default="private"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activated_at", sa.DateTime(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("forked_at", sa.DateTime(), nullable=True),
        sa.Column("schema_version", sa.String(length=16), nullable=False, server_default="skill.v1"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_skills_user_active", "user_skills", ["user_id", "active"], unique=False)
    op.create_index("idx_user_skills_user_updated", "user_skills", ["user_id", "updated_at"], unique=False)
    op.create_index("ix_user_skills_forked_from_share_id", "user_skills", ["forked_from_share_id"], unique=False)
    op.create_index("ix_user_skills_shared_catalog_id", "user_skills", ["shared_catalog_id"], unique=False)

    op.create_table(
        "shared_skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("share_slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("pattern_template", sa.String(length=4000), nullable=False),
        sa.Column("activation_conditions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("examples", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("author_label", sa.String(length=32), nullable=False, server_default="anonymous"),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("source_schema_version", sa.String(length=16), nullable=False, server_default="skill.v1"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_shared_skills_published", "shared_skills", ["published_at"], unique=False)
    op.create_index("ix_shared_skills_share_slug", "shared_skills", ["share_slug"], unique=True)

    op.create_table(
        "skill_share_moderation_queue",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("user_skill_id", sa.String(length=36), nullable=False),
        sa.Column("staged_name", sa.String(length=40), nullable=False),
        sa.Column("staged_pattern_template", sa.String(length=4000), nullable=False),
        sa.Column("staged_activation_conditions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("staged_examples", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("pii_scan_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("injection_scan_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("moderation_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("reviewer_label", sa.String(length=64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("published_shared_skill_id", sa.String(length=36), nullable=True),
        sa.Column("rejection_reason", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_skill_share_queue_owner_created",
        "skill_share_moderation_queue",
        ["owner_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_skill_share_moderation_queue_user_skill_id",
        "skill_share_moderation_queue",
        ["user_skill_id"],
        unique=False,
    )

    op.add_column("routing_decision_log", sa.Column("skills_injected", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("routing_decision_log", "skills_injected")
    op.drop_index("ix_skill_share_moderation_queue_user_skill_id", table_name="skill_share_moderation_queue")
    op.drop_index("idx_skill_share_queue_owner_created", table_name="skill_share_moderation_queue")
    op.drop_table("skill_share_moderation_queue")
    op.drop_index("ix_shared_skills_share_slug", table_name="shared_skills")
    op.drop_index("idx_shared_skills_published", table_name="shared_skills")
    op.drop_table("shared_skills")
    op.drop_index("ix_user_skills_shared_catalog_id", table_name="user_skills")
    op.drop_index("ix_user_skills_forked_from_share_id", table_name="user_skills")
    op.drop_index("idx_user_skills_user_updated", table_name="user_skills")
    op.drop_index("idx_user_skills_user_active", table_name="user_skills")
    op.drop_table("user_skills")
