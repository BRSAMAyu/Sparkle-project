"""add phase3 intervention strategy outcomes

Revision ID: ps003_phase3_strategy_outcomes
Revises: z1a2b3c4d5e6
Create Date: 2026-04-03 13:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.models.base


# revision identifiers, used by Alembic.
revision: str = "ps003_phase3_strategy_outcomes"
down_revision: Union[str, None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    trigger_enum = postgresql.ENUM(
        "CONCEPT_GAP",
        "PLAN_RISK",
        "STALL_PATTERN",
        "OVERLOAD",
        "MISALIGNMENT",
        name="intervention_trigger_enum",
        create_type=False,
    )
    strategy_enum = postgresql.ENUM(
        "CURIOUS",
        "SUPPORTIVE",
        "DIRECT",
        "MICRO_RESTART",
        name="delivery_strategy_enum",
        create_type=False,
    )
    channel_enum = postgresql.ENUM(
        "CHAT",
        "PUSH",
        "IN_APP",
        "FOCUS_MODE",
        name="delivery_channel_enum",
        create_type=False,
    )
    acceptance_enum = postgresql.ENUM(
        "CREATED",
        "DELIVERED",
        "SEEN",
        "DISMISSED",
        "SNOOZED",
        "ACCEPTED",
        "ACTED",
        name="intervention_acceptance_enum",
        create_type=False,
    )
    outcome_enum = postgresql.ENUM(
        "PENDING",
        "EFFECTIVE",
        "INEFFECTIVE",
        "UNKNOWN",
        name="intervention_outcome_enum",
        create_type=False,
    )

    # Create enum types explicitly so they exist before table creation
    trigger_enum.create(bind, checkfirst=True)
    strategy_enum.create(bind, checkfirst=True)
    channel_enum.create(bind, checkfirst=True)
    acceptance_enum.create(bind, checkfirst=True)
    outcome_enum.create(bind, checkfirst=True)

    if not _table_exists(inspector, "intervention_strategy_outcomes"):
        op.create_table(
            "intervention_strategy_outcomes",
            sa.Column("id", app.models.base.GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("user_id", app.models.base.GUID(), nullable=False),
            sa.Column("intervention_id", app.models.base.GUID(), nullable=False),
            sa.Column("trigger_type", trigger_enum, nullable=False),
            sa.Column("delivery_tone", strategy_enum, nullable=False),
            sa.Column("delivery_channel", channel_enum, nullable=False),
            sa.Column("acceptance_status", acceptance_enum, nullable=False),
            sa.Column("outcome", outcome_enum, nullable=False),
            sa.Column("time_to_action_seconds", sa.Integer(), nullable=True),
            sa.Column("context_snapshot", sa.JSON(), nullable=False, server_default="{}"),
            sa.ForeignKeyConstraint(["intervention_id"], ["intervention_records.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("intervention_id", name="uq_strategy_outcome_intervention"),
        )

    if not _index_exists(inspector, "intervention_strategy_outcomes", "ix_intervention_strategy_outcomes_user_id"):
        op.create_index("ix_intervention_strategy_outcomes_user_id", "intervention_strategy_outcomes", ["user_id"], unique=False)
    if not _index_exists(inspector, "intervention_strategy_outcomes", "ix_intervention_strategy_outcomes_intervention_id"):
        op.create_index("ix_intervention_strategy_outcomes_intervention_id", "intervention_strategy_outcomes", ["intervention_id"], unique=False)
    if not _index_exists(inspector, "intervention_strategy_outcomes", "ix_intervention_strategy_outcomes_trigger_type"):
        op.create_index("ix_intervention_strategy_outcomes_trigger_type", "intervention_strategy_outcomes", ["trigger_type"], unique=False)
    if not _index_exists(inspector, "intervention_strategy_outcomes", "ix_intervention_strategy_outcomes_outcome"):
        op.create_index("ix_intervention_strategy_outcomes_outcome", "intervention_strategy_outcomes", ["outcome"], unique=False)
    if not _index_exists(inspector, "intervention_strategy_outcomes", "ix_strategy_outcomes_user_trigger"):
        op.create_index("ix_strategy_outcomes_user_trigger", "intervention_strategy_outcomes", ["user_id", "trigger_type"], unique=False)
    if not _index_exists(inspector, "intervention_strategy_outcomes", "ix_strategy_outcomes_user_trigger_tone"):
        op.create_index(
            "ix_strategy_outcomes_user_trigger_tone",
            "intervention_strategy_outcomes",
            ["user_id", "trigger_type", "delivery_tone"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _table_exists(inspector, "intervention_strategy_outcomes"):
        op.drop_table("intervention_strategy_outcomes")

    postgresql.ENUM(name="intervention_outcome_enum", create_type=False).drop(bind, checkfirst=True)
    postgresql.ENUM(name="intervention_acceptance_enum", create_type=False).drop(bind, checkfirst=True)
    postgresql.ENUM(name="delivery_channel_enum", create_type=False).drop(bind, checkfirst=True)
    postgresql.ENUM(name="delivery_strategy_enum", create_type=False).drop(bind, checkfirst=True)
    postgresql.ENUM(name="intervention_trigger_enum", create_type=False).drop(bind, checkfirst=True)
