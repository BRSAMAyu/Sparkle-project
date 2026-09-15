"""add candidate feedback and leaderboard snapshot tables to active head

Revision ID: tp1e2f3a4b5c6
Revises: tp0c1d2e3f4a5
Create Date: 2026-03-31 18:45:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.models.base import GUID


# revision identifiers, used by Alembic.
revision: str = "tp1e2f3a4b5c6"
down_revision: Union[str, None] = "tp0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _existing_indexes(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "candidate_action_feedback"):
        op.create_table(
            "candidate_action_feedback",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("user_id", GUID(), nullable=False),
            sa.Column("candidate_id", sa.String(length=64), nullable=False),
            sa.Column("action_type", sa.String(length=32), nullable=False),
            sa.Column("feedback_type", sa.String(length=16), nullable=False),
            sa.Column("executed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("completion_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    candidate_indexes = _existing_indexes(bind, "candidate_action_feedback")
    if "idx_candidate_feedback_user_type" not in candidate_indexes:
        op.create_index(
            "idx_candidate_feedback_user_type",
            "candidate_action_feedback",
            ["user_id", "action_type"],
            unique=False,
        )
    if "idx_candidate_feedback_created" not in candidate_indexes:
        op.create_index(
            "idx_candidate_feedback_created",
            "candidate_action_feedback",
            ["created_at"],
            unique=False,
        )
    if "idx_candidate_feedback_type" not in candidate_indexes:
        op.create_index(
            "idx_candidate_feedback_type",
            "candidate_action_feedback",
            ["feedback_type"],
            unique=False,
        )
    if "idx_candidate_feedback_action" not in candidate_indexes:
        op.create_index(
            "idx_candidate_feedback_action",
            "candidate_action_feedback",
            ["action_type"],
            unique=False,
        )
    if "ix_candidate_action_feedback_deleted_at" not in candidate_indexes:
        op.create_index(
            op.f("ix_candidate_action_feedback_deleted_at"),
            "candidate_action_feedback",
            ["deleted_at"],
            unique=False,
        )

    if not _has_table(bind, "leaderboard_snapshots"):
        op.create_table(
            "leaderboard_snapshots",
            sa.Column("snapshot_type", sa.String(length=50), nullable=False),
            sa.Column("period", sa.String(length=20), nullable=False),
            sa.Column("subject_id", GUID(), nullable=True),
            sa.Column("snapshot_date", sa.DateTime(), nullable=False),
            sa.Column("snapshot_version", sa.Integer(), nullable=False),
            sa.Column("rankings", sa.JSON(), nullable=False),
            sa.Column("total_participants", sa.Integer(), nullable=False),
            sa.Column("generation_time_ms", sa.Float(), nullable=True),
            sa.Column("id", GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    leaderboard_indexes = _existing_indexes(bind, "leaderboard_snapshots")
    if "idx_leaderboard_snapshot_type_date" not in leaderboard_indexes:
        op.create_index(
            "idx_leaderboard_snapshot_type_date",
            "leaderboard_snapshots",
            ["snapshot_type", "snapshot_date"],
            unique=False,
        )
    if "idx_leaderboard_snapshot_period" not in leaderboard_indexes:
        op.create_index(
            "idx_leaderboard_snapshot_period",
            "leaderboard_snapshots",
            ["period"],
            unique=False,
        )
    if "ix_leaderboard_snapshots_snapshot_type" not in leaderboard_indexes:
        op.create_index(
            op.f("ix_leaderboard_snapshots_snapshot_type"),
            "leaderboard_snapshots",
            ["snapshot_type"],
            unique=False,
        )
    if "ix_leaderboard_snapshots_snapshot_date" not in leaderboard_indexes:
        op.create_index(
            op.f("ix_leaderboard_snapshots_snapshot_date"),
            "leaderboard_snapshots",
            ["snapshot_date"],
            unique=False,
        )
    if "ix_leaderboard_snapshots_deleted_at" not in leaderboard_indexes:
        op.create_index(
            op.f("ix_leaderboard_snapshots_deleted_at"),
            "leaderboard_snapshots",
            ["deleted_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "leaderboard_snapshots"):
        for index_name in [
            "ix_leaderboard_snapshots_deleted_at",
            "ix_leaderboard_snapshots_snapshot_date",
            "ix_leaderboard_snapshots_snapshot_type",
            "idx_leaderboard_snapshot_period",
            "idx_leaderboard_snapshot_type_date",
        ]:
            if index_name in _existing_indexes(bind, "leaderboard_snapshots"):
                op.drop_index(index_name, table_name="leaderboard_snapshots")
        op.drop_table("leaderboard_snapshots")

    if _has_table(bind, "candidate_action_feedback"):
        for index_name in [
            "ix_candidate_action_feedback_deleted_at",
            "idx_candidate_feedback_action",
            "idx_candidate_feedback_type",
            "idx_candidate_feedback_created",
            "idx_candidate_feedback_user_type",
        ]:
            if index_name in _existing_indexes(bind, "candidate_action_feedback"):
                op.drop_index(index_name, table_name="candidate_action_feedback")
        op.drop_table("candidate_action_feedback")
