"""adaptive_interventions

Revision ID: 8ccc1db58856
Revises: 8b3f2f5a9c1b
Create Date: 2026-01-19 10:38:54.725704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app.models.base


# Migration Contract:
#   type: reversible|forward_only|destructive
#   rollback_plan: "alembic downgrade -1" | "forward_fix_only"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "team-name"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = '8ccc1db58856'
down_revision: Union[str, None] = '8b3f2f5a9c1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scaffolding_states",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("capability_level", sa.Float(), nullable=False),
        sa.Column("current_zone", sa.String(length=20), nullable=False),
        sa.Column("support_level", sa.Integer(), nullable=False),
        sa.Column("template_variant_id", sa.String(length=100), nullable=True),
        sa.Column("consecutive_successes", sa.Integer(), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("last_intervention_timestamp", sa.DateTime(), nullable=True),
        sa.Column("history", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    with op.batch_alter_table("scaffolding_states", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_scaffolding_states_deleted_at"), ["deleted_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_scaffolding_states_user_id"), ["user_id"], unique=True)

    op.create_table(
        "passive_signals",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("signal_type", sa.String(length=50), nullable=False),
        sa.Column("intervention_id", app.models.base.GUID(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["intervention_id"], ["intervention_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("passive_signals", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_passive_signals_deleted_at"), ["deleted_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_passive_signals_user_id"), ["user_id"], unique=False)

    op.create_table(
        "behavioral_outcomes",
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("intervention_id", app.models.base.GUID(), nullable=False),
        sa.Column("outcome_type", sa.String(length=50), nullable=False),
        sa.Column("time_to_outcome", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["intervention_id"], ["intervention_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("behavioral_outcomes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_behavioral_outcomes_deleted_at"), ["deleted_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_behavioral_outcomes_intervention_id"), ["intervention_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_behavioral_outcomes_user_id"), ["user_id"], unique=False)

    op.create_table(
        "intervention_templates",
        sa.Column("template_id", sa.String(length=100), nullable=False),
        sa.Column("intent_type", sa.String(length=50), nullable=False),
        sa.Column("support_level", sa.Integer(), nullable=False),
        sa.Column("variants", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id"),
    )
    with op.batch_alter_table("intervention_templates", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_intervention_templates_deleted_at"), ["deleted_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_intervention_templates_intent_type"), ["intent_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_intervention_templates_template_id"), ["template_id"], unique=True)

    with op.batch_alter_table("intervention_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("delivery_method", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("template_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("template_variant_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("scaffolding_level", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("intent_type", sa.String(length=50), nullable=True))

    with op.batch_alter_table("response_feedback", schema=None) as batch_op:
        batch_op.add_column(sa.Column("intervention_id", app.models.base.GUID(), nullable=True))
        batch_op.add_column(sa.Column("scaffolding_level", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("template_variant_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("time_to_response", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("action_taken", sa.String(length=40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("response_feedback", schema=None) as batch_op:
        batch_op.drop_column("action_taken")
        batch_op.drop_column("time_to_response")
        batch_op.drop_column("template_variant_id")
        batch_op.drop_column("scaffolding_level")
        batch_op.drop_column("intervention_id")

    with op.batch_alter_table("intervention_requests", schema=None) as batch_op:
        batch_op.drop_column("intent_type")
        batch_op.drop_column("scaffolding_level")
        batch_op.drop_column("template_variant_id")
        batch_op.drop_column("template_id")
        batch_op.drop_column("delivery_method")

    with op.batch_alter_table("intervention_templates", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_intervention_templates_template_id"))
        batch_op.drop_index(batch_op.f("ix_intervention_templates_intent_type"))
        batch_op.drop_index(batch_op.f("ix_intervention_templates_deleted_at"))
    op.drop_table("intervention_templates")

    with op.batch_alter_table("behavioral_outcomes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_behavioral_outcomes_user_id"))
        batch_op.drop_index(batch_op.f("ix_behavioral_outcomes_intervention_id"))
        batch_op.drop_index(batch_op.f("ix_behavioral_outcomes_deleted_at"))
    op.drop_table("behavioral_outcomes")

    with op.batch_alter_table("passive_signals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_passive_signals_user_id"))
        batch_op.drop_index(batch_op.f("ix_passive_signals_deleted_at"))
    op.drop_table("passive_signals")

    with op.batch_alter_table("scaffolding_states", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_scaffolding_states_user_id"))
        batch_op.drop_index(batch_op.f("ix_scaffolding_states_deleted_at"))
    op.drop_table("scaffolding_states")
