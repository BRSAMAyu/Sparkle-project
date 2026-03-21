"""add acceptance runtime tables

Revision ID: f7a9c3e2d1b4
Revises: f3c1d9a7b6e5
Create Date: 2026-03-21 19:50:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base

# revision identifiers, used by Alembic.
revision: str = "f7a9c3e2d1b4"
down_revision: Union[str, None] = "f3c1d9a7b6e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "learning_assets"):
        op.create_table(
            "learning_assets",
            sa.Column("id", app.models.base.GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("user_id", app.models.base.GUID(), nullable=False),
            sa.Column("source_file_id", app.models.base.GUID(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="INBOX"),
            sa.Column("asset_kind", sa.String(length=20), nullable=False, server_default="WORD"),
            sa.Column("headword", sa.String(length=255), nullable=False),
            sa.Column("definition", sa.Text(), nullable=True),
            sa.Column("translation", sa.Text(), nullable=True),
            sa.Column("example", sa.Text(), nullable=True),
            sa.Column("language_code", sa.String(length=10), nullable=False, server_default="en"),
            sa.Column("inbox_expires_at", sa.DateTime(), nullable=True),
            sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("snapshot_schema_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("provenance_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
            sa.Column("provenance_updated_at", sa.DateTime(), nullable=True),
            sa.Column("selection_fp", sa.String(length=64), nullable=True),
            sa.Column("anchor_fp", sa.String(length=64), nullable=True),
            sa.Column("doc_fp", sa.String(length=64), nullable=True),
            sa.Column("norm_version", sa.String(length=20), nullable=False, server_default="v1"),
            sa.Column("match_profile", sa.String(length=50), nullable=True),
            sa.Column("review_due_at", sa.DateTime(), nullable=True),
            sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("review_success_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
            sa.Column("lookup_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("star_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ignored_count", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_file_id"], ["stored_files.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "learning_assets", "idx_learning_assets_user_status"):
        op.create_index("idx_learning_assets_user_status", "learning_assets", ["user_id", "status"], unique=False)
    if not _index_exists(inspector, "learning_assets", "idx_learning_assets_selection_fp"):
        op.create_index("idx_learning_assets_selection_fp", "learning_assets", ["user_id", "selection_fp"], unique=False)
    if not _index_exists(inspector, "learning_assets", "idx_learning_assets_headword"):
        op.create_index("idx_learning_assets_headword", "learning_assets", ["headword"], unique=False)
    if not _index_exists(inspector, "learning_assets", "idx_learning_assets_inbox_expires"):
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_learning_assets_inbox_expires
            ON learning_assets (inbox_expires_at)
            WHERE status = 'INBOX'
            """
        )
    if not _index_exists(inspector, "learning_assets", "idx_learning_assets_review_due"):
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_learning_assets_review_due
            ON learning_assets (user_id, review_due_at)
            WHERE status = 'ACTIVE' AND review_due_at IS NOT NULL
            """
        )

    if not _table_exists(inspector, "asset_suggestion_logs"):
        op.create_table(
            "asset_suggestion_logs",
            sa.Column("id", app.models.base.GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("user_id", app.models.base.GUID(), nullable=False),
            sa.Column("session_id", sa.String(length=64), nullable=True),
            sa.Column("policy_id", sa.String(length=50), nullable=False),
            sa.Column("trigger_event", sa.String(length=100), nullable=False),
            sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("decision", sa.String(length=20), nullable=False),
            sa.Column("decision_reason", sa.String(length=255), nullable=True),
            sa.Column("user_response", sa.String(length=20), nullable=True, server_default="PENDING"),
            sa.Column("response_at", sa.DateTime(), nullable=True),
            sa.Column("cooldown_until", sa.DateTime(), nullable=True),
            sa.Column("asset_id", app.models.base.GUID(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["asset_id"], ["learning_assets.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "asset_suggestion_logs", "idx_suggestion_log_user_created"):
        op.create_index("idx_suggestion_log_user_created", "asset_suggestion_logs", ["user_id", "created_at"], unique=False)
    if not _index_exists(inspector, "asset_suggestion_logs", "idx_suggestion_log_policy"):
        op.create_index("idx_suggestion_log_policy", "asset_suggestion_logs", ["policy_id"], unique=False)

    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE backgroundtasktype AS ENUM (
                'AI_GENERATION', 'DATA_SYNC', 'PLAN_GENERATION', 'GALAXY_EXPANSION', 'TASK_BATCH'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE backgroundtaskstatus AS ENUM (
                'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    background_task_type = postgresql.ENUM(
        "AI_GENERATION",
        "DATA_SYNC",
        "PLAN_GENERATION",
        "GALAXY_EXPANSION",
        "TASK_BATCH",
        name="backgroundtasktype",
        create_type=False,
    )
    background_task_status = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        name="backgroundtaskstatus",
        create_type=False,
    )

    if not _table_exists(inspector, "background_tasks"):
        op.create_table(
            "background_tasks",
            sa.Column("id", app.models.base.GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("user_id", app.models.base.GUID(), nullable=False),
            sa.Column("task_type", background_task_type, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("status", background_task_status, nullable=False, server_default="PENDING"),
            sa.Column("progress", sa.Float(), nullable=True, server_default="0"),
            sa.Column("progress_message", sa.Text(), nullable=True),
            sa.Column("result_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("related_entity_id", app.models.base.GUID(), nullable=True),
            sa.Column("related_entity_type", sa.String(length=50), nullable=True),
            sa.Column("external_task_id", sa.String(length=255), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "background_tasks", "idx_background_tasks_user_status"):
        op.create_index("idx_background_tasks_user_status", "background_tasks", ["user_id", "status"], unique=False)
    if not _index_exists(inspector, "background_tasks", "idx_background_tasks_type"):
        op.create_index("idx_background_tasks_type", "background_tasks", ["task_type"], unique=False)
    if not _index_exists(inspector, "background_tasks", "ix_background_tasks_external_task_id"):
        op.create_index("ix_background_tasks_external_task_id", "background_tasks", ["external_task_id"], unique=False)

    if not _table_exists(inspector, "agent_execution_stats"):
        op.create_table(
            "agent_execution_stats",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", app.models.base.GUID(), nullable=False),
            sa.Column("session_id", sa.String(length=255), nullable=False),
            sa.Column("request_id", sa.String(length=255), nullable=False),
            sa.Column("agent_type", sa.String(length=50), nullable=False),
            sa.Column("agent_name", sa.String(length=100), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("tool_name", sa.String(length=100), nullable=True),
            sa.Column("operation", sa.String(length=255), nullable=True),
            sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    if not _index_exists(inspector, "agent_execution_stats", "ix_agent_execution_stats_user_id"):
        op.create_index("ix_agent_execution_stats_user_id", "agent_execution_stats", ["user_id"], unique=False)
    if not _index_exists(inspector, "agent_execution_stats", "ix_agent_execution_stats_agent_type"):
        op.create_index("ix_agent_execution_stats_agent_type", "agent_execution_stats", ["agent_type"], unique=False)
    if not _index_exists(inspector, "agent_execution_stats", "ix_agent_execution_stats_created_at"):
        op.create_index("ix_agent_execution_stats_created_at", "agent_execution_stats", ["created_at"], unique=False)
    if not _index_exists(inspector, "agent_execution_stats", "ix_agent_execution_stats_session_id"):
        op.create_index("ix_agent_execution_stats_session_id", "agent_execution_stats", ["session_id"], unique=False)
    if not _index_exists(inspector, "agent_execution_stats", "ix_agent_stats_user_agent_type"):
        op.create_index("ix_agent_stats_user_agent_type", "agent_execution_stats", ["user_id", "agent_type"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_agent_stats_user_agent_type", table_name="agent_execution_stats", if_exists=True)
    op.drop_index("ix_agent_execution_stats_session_id", table_name="agent_execution_stats", if_exists=True)
    op.drop_index("ix_agent_execution_stats_created_at", table_name="agent_execution_stats", if_exists=True)
    op.drop_index("ix_agent_execution_stats_agent_type", table_name="agent_execution_stats", if_exists=True)
    op.drop_index("ix_agent_execution_stats_user_id", table_name="agent_execution_stats", if_exists=True)
    op.drop_table("agent_execution_stats", if_exists=True)

    op.drop_index("ix_background_tasks_external_task_id", table_name="background_tasks", if_exists=True)
    op.drop_index("idx_background_tasks_type", table_name="background_tasks", if_exists=True)
    op.drop_index("idx_background_tasks_user_status", table_name="background_tasks", if_exists=True)
    op.drop_table("background_tasks", if_exists=True)

    background_task_status = postgresql.ENUM(name="backgroundtaskstatus")
    background_task_type = postgresql.ENUM(name="backgroundtasktype")
    background_task_status.drop(bind, checkfirst=True)
    background_task_type.drop(bind, checkfirst=True)

    op.drop_index("idx_suggestion_log_policy", table_name="asset_suggestion_logs", if_exists=True)
    op.drop_index("idx_suggestion_log_user_created", table_name="asset_suggestion_logs", if_exists=True)
    op.drop_table("asset_suggestion_logs", if_exists=True)

    op.execute("DROP INDEX IF EXISTS idx_learning_assets_review_due")
    op.execute("DROP INDEX IF EXISTS idx_learning_assets_inbox_expires")
    op.drop_index("idx_learning_assets_headword", table_name="learning_assets", if_exists=True)
    op.drop_index("idx_learning_assets_selection_fp", table_name="learning_assets", if_exists=True)
    op.drop_index("idx_learning_assets_user_status", table_name="learning_assets", if_exists=True)
    op.drop_table("learning_assets", if_exists=True)
