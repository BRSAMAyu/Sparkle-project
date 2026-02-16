"""add seed template v2 tables

Revision ID: b12f4c9e7a31
Revises: 8b2f0b2d9b1a
Create Date: 2026-02-12 17:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b12f4c9e7a31"
down_revision = "8b2f0b2d9b1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seed_template_packs",
        sa.Column("scenario_type", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="private"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="zh"),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("adoption_score", sa.Float(), nullable=True),
        sa.Column("safety_score", sa.Float(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seed_template_packs_name", "seed_template_packs", ["name"], unique=False)
    op.create_index("ix_seed_template_packs_scenario_type", "seed_template_packs", ["scenario_type"], unique=False)
    op.create_index("ix_seed_template_packs_visibility", "seed_template_packs", ["visibility"], unique=False)
    op.create_index("ix_seed_template_packs_status", "seed_template_packs", ["status"], unique=False)
    op.create_index("idx_seed_template_pack_scene_visibility", "seed_template_packs", ["scenario_type", "visibility"], unique=False)
    op.create_index("ix_seed_template_packs_owner_id", "seed_template_packs", ["owner_id"], unique=False)
    op.create_index("ix_seed_template_packs_deleted_at", "seed_template_packs", ["deleted_at"], unique=False)

    op.create_table(
        "seed_templates",
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seed_template_packs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("template_role", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("forked_from_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("forked_from_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seed_templates_pack_id", "seed_templates", ["pack_id"], unique=False)
    op.create_index("ix_seed_templates_name", "seed_templates", ["name"], unique=False)
    op.create_index("ix_seed_templates_template_role", "seed_templates", ["template_role"], unique=False)
    op.create_index("ix_seed_templates_current_version_id", "seed_templates", ["current_version_id"], unique=False)
    op.create_index("ix_seed_templates_forked_from_template_id", "seed_templates", ["forked_from_template_id"], unique=False)
    op.create_index("ix_seed_templates_forked_from_version_id", "seed_templates", ["forked_from_version_id"], unique=False)
    op.create_index("ix_seed_templates_owner_id", "seed_templates", ["owner_id"], unique=False)
    op.create_index("ix_seed_templates_is_official", "seed_templates", ["is_official"], unique=False)
    op.create_index("ix_seed_templates_is_featured", "seed_templates", ["is_featured"], unique=False)
    op.create_index("ix_seed_templates_deleted_at", "seed_templates", ["deleted_at"], unique=False)

    op.create_table(
        "seed_template_versions",
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seed_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("variables_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("change_log", sa.Text(), nullable=True),
        sa.Column("quality_gate_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("moderation_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("moderation_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("promotion_state", sa.String(length=30), nullable=False, server_default="none"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seed_template_versions_template_id", "seed_template_versions", ["template_id"], unique=False)
    op.create_index("ix_seed_template_versions_status", "seed_template_versions", ["status"], unique=False)
    op.create_index("ix_seed_template_versions_moderation_status", "seed_template_versions", ["moderation_status"], unique=False)
    op.create_index("ix_seed_template_versions_promotion_state", "seed_template_versions", ["promotion_state"], unique=False)
    op.create_index("ix_seed_template_versions_created_by", "seed_template_versions", ["created_by"], unique=False)
    op.create_index("idx_seed_template_version_template_version", "seed_template_versions", ["template_id", "version_no"], unique=False)
    op.create_index("ix_seed_template_versions_deleted_at", "seed_template_versions", ["deleted_at"], unique=False)

    op.create_table(
        "seed_template_signals",
        sa.Column("template_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seed_template_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signal_type", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seed_template_signals_template_version_id", "seed_template_signals", ["template_version_id"], unique=False)
    op.create_index("ix_seed_template_signals_user_id", "seed_template_signals", ["user_id"], unique=False)
    op.create_index("ix_seed_template_signals_signal_type", "seed_template_signals", ["signal_type"], unique=False)
    op.create_index("idx_seed_template_signal_version_type", "seed_template_signals", ["template_version_id", "signal_type"], unique=False)
    op.create_index("ix_seed_template_signals_deleted_at", "seed_template_signals", ["deleted_at"], unique=False)

    op.create_table(
        "seed_template_subscriptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seed_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seed_template_subscriptions_user_id", "seed_template_subscriptions", ["user_id"], unique=False)
    op.create_index("ix_seed_template_subscriptions_template_id", "seed_template_subscriptions", ["template_id"], unique=False)
    op.create_index("ix_seed_template_subscriptions_is_enabled", "seed_template_subscriptions", ["is_enabled"], unique=False)
    op.create_index("idx_seed_template_subscription_user_template", "seed_template_subscriptions", ["user_id", "template_id"], unique=False)
    op.create_index("ix_seed_template_subscriptions_deleted_at", "seed_template_subscriptions", ["deleted_at"], unique=False)

    op.create_table(
        "seed_template_rewards_ledger",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seed_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("points_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_signal", sa.String(length=40), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seed_template_rewards_ledger_user_id", "seed_template_rewards_ledger", ["user_id"], unique=False)
    op.create_index("ix_seed_template_rewards_ledger_template_id", "seed_template_rewards_ledger", ["template_id"], unique=False)
    op.create_index("ix_seed_template_rewards_ledger_event_type", "seed_template_rewards_ledger", ["event_type"], unique=False)
    op.create_index("ix_seed_template_rewards_ledger_deleted_at", "seed_template_rewards_ledger", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_seed_template_rewards_ledger_deleted_at", table_name="seed_template_rewards_ledger")
    op.drop_index("ix_seed_template_rewards_ledger_event_type", table_name="seed_template_rewards_ledger")
    op.drop_index("ix_seed_template_rewards_ledger_template_id", table_name="seed_template_rewards_ledger")
    op.drop_index("ix_seed_template_rewards_ledger_user_id", table_name="seed_template_rewards_ledger")
    op.drop_table("seed_template_rewards_ledger")

    op.drop_index("ix_seed_template_subscriptions_deleted_at", table_name="seed_template_subscriptions")
    op.drop_index("idx_seed_template_subscription_user_template", table_name="seed_template_subscriptions")
    op.drop_index("ix_seed_template_subscriptions_is_enabled", table_name="seed_template_subscriptions")
    op.drop_index("ix_seed_template_subscriptions_template_id", table_name="seed_template_subscriptions")
    op.drop_index("ix_seed_template_subscriptions_user_id", table_name="seed_template_subscriptions")
    op.drop_table("seed_template_subscriptions")

    op.drop_index("ix_seed_template_signals_deleted_at", table_name="seed_template_signals")
    op.drop_index("idx_seed_template_signal_version_type", table_name="seed_template_signals")
    op.drop_index("ix_seed_template_signals_signal_type", table_name="seed_template_signals")
    op.drop_index("ix_seed_template_signals_user_id", table_name="seed_template_signals")
    op.drop_index("ix_seed_template_signals_template_version_id", table_name="seed_template_signals")
    op.drop_table("seed_template_signals")

    op.drop_index("ix_seed_template_versions_deleted_at", table_name="seed_template_versions")
    op.drop_index("idx_seed_template_version_template_version", table_name="seed_template_versions")
    op.drop_index("ix_seed_template_versions_created_by", table_name="seed_template_versions")
    op.drop_index("ix_seed_template_versions_promotion_state", table_name="seed_template_versions")
    op.drop_index("ix_seed_template_versions_moderation_status", table_name="seed_template_versions")
    op.drop_index("ix_seed_template_versions_status", table_name="seed_template_versions")
    op.drop_index("ix_seed_template_versions_template_id", table_name="seed_template_versions")
    op.drop_table("seed_template_versions")

    op.drop_index("ix_seed_templates_deleted_at", table_name="seed_templates")
    op.drop_index("ix_seed_templates_is_featured", table_name="seed_templates")
    op.drop_index("ix_seed_templates_is_official", table_name="seed_templates")
    op.drop_index("ix_seed_templates_owner_id", table_name="seed_templates")
    op.drop_index("ix_seed_templates_forked_from_version_id", table_name="seed_templates")
    op.drop_index("ix_seed_templates_forked_from_template_id", table_name="seed_templates")
    op.drop_index("ix_seed_templates_current_version_id", table_name="seed_templates")
    op.drop_index("ix_seed_templates_template_role", table_name="seed_templates")
    op.drop_index("ix_seed_templates_name", table_name="seed_templates")
    op.drop_index("ix_seed_templates_pack_id", table_name="seed_templates")
    op.drop_table("seed_templates")

    op.drop_index("ix_seed_template_packs_deleted_at", table_name="seed_template_packs")
    op.drop_index("ix_seed_template_packs_owner_id", table_name="seed_template_packs")
    op.drop_index("idx_seed_template_pack_scene_visibility", table_name="seed_template_packs")
    op.drop_index("ix_seed_template_packs_status", table_name="seed_template_packs")
    op.drop_index("ix_seed_template_packs_visibility", table_name="seed_template_packs")
    op.drop_index("ix_seed_template_packs_scenario_type", table_name="seed_template_packs")
    op.drop_index("ix_seed_template_packs_name", table_name="seed_template_packs")
    op.drop_table("seed_template_packs")

