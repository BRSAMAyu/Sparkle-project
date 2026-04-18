"""add aurora runtime tables

Revision ID: a8b7c6d5e4f3
Revises: f18222fe1c3e
Create Date: 2026-04-18 09:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT 1;"
#   backfill_plan: "n/a"
#   owner: "aurora-foundation"
#   ticket: "stage3-wave0"

# revision identifiers, used by Alembic.
revision = "a8b7c6d5e4f3"
down_revision = "f18222fe1c3e"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    return sa.JSON() if op.get_bind().dialect.name == "sqlite" else postgresql.JSONB(astext_type=sa.Text())


def _uuid_type() -> sa.types.TypeEngine:
    return sa.String(length=36) if op.get_bind().dialect.name == "sqlite" else postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    json_type = _json_type()
    uuid_type = _uuid_type()

    op.create_table(
        "aurora_policy_versions",
        sa.Column("id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("author", sa.String(length=64), nullable=False),
        sa.Column("changelog", json_type, nullable=False),
        sa.Column("persona_invariants", json_type, nullable=False),
        sa.Column("audit_invariants", json_type, nullable=False),
        sa.Column("proactive_policy", json_type, nullable=False),
        sa.Column("reconciliation_policy", json_type, nullable=False),
        sa.Column("continuous_learning_policy", json_type, nullable=False),
        sa.Column("parameter_write_authority", json_type, nullable=False),
        sa.Column("interaction_model_registry", json_type, nullable=False),
        sa.Column("materiality_threshold", sa.Float(), nullable=False),
        sa.Column("default_rollback_anchor_schema", json_type, nullable=False),
    )
    op.create_index("ix_aurora_policy_versions_created_at", "aurora_policy_versions", ["created_at"], unique=False)
    op.create_index("uq_aurora_policy_versions_version", "aurora_policy_versions", ["version"], unique=True)

    op.create_table(
        "focus_contracts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("scenario_pack_id", sa.String(length=128), nullable=False),
        sa.Column("active_node", sa.String(length=255), nullable=False),
        sa.Column("focus_description", sa.Text(), nullable=False),
        sa.Column("desire_hypothesis", sa.Text(), nullable=True),
        sa.Column("commitment_ids", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=32), nullable=False),
        sa.Column("trigger_decision_ref", sa.String(length=36), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False),
        sa.Column("projection_policy", sa.String(length=64), nullable=False),
        sa.Column("write_path", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_focus_contracts_user_id", "focus_contracts", ["user_id"], unique=False)
    op.create_index("ix_focus_contracts_user_version", "focus_contracts", ["user_id", "version"], unique=False)
    op.create_index("ix_focus_contracts_scenario_pack_id", "focus_contracts", ["scenario_pack_id"], unique=False)
    op.create_index("ix_focus_contracts_active_node", "focus_contracts", ["active_node"], unique=False)

    op.create_table(
        "commitments",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("success_criteria", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("deadline", sa.DateTime(), nullable=False),
        sa.Column("milestone_ids", json_type, nullable=False),
        sa.Column("witness_ids", json_type, nullable=False),
        sa.Column("window_override", sa.String(length=32), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False),
        sa.Column("projection_policy", sa.String(length=64), nullable=False),
        sa.Column("write_path", sa.String(length=64), nullable=False),
        sa.Column("shareability", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_commitments_user_id", "commitments", ["user_id"], unique=False)
    op.create_index("ix_commitments_status", "commitments", ["status"], unique=False)
    op.create_index("ix_commitments_deadline", "commitments", ["deadline"], unique=False)
    op.create_index("ix_commitments_node_id", "commitments", ["node_id"], unique=False)
    op.create_index("idx_commitments_user_status_deadline", "commitments", ["user_id", "status", "deadline"], unique=False)

    op.create_table(
        "transition_decision_records",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("proposed_transition", sa.String(length=255), nullable=True),
        sa.Column("initiation_type", sa.String(length=32), nullable=False),
        sa.Column("decision_mechanism", sa.String(length=32), nullable=False),
        sa.Column("decision_basis", sa.String(length=64), nullable=False),
        sa.Column("input_snapshot_ref", sa.String(length=128), nullable=False),
        sa.Column("impact_class", sa.String(length=32), nullable=False),
        sa.Column("inference_knobs", json_type, nullable=True),
        sa.Column("capability_gate", json_type, nullable=True),
        sa.Column("interaction_model_variant", sa.String(length=64), nullable=False),
        sa.Column("rollback_anchor", json_type, nullable=False),
        sa.Column("evidence_refs", json_type, nullable=False),
        sa.Column("policy_version", sa.String(length=128), nullable=False),
        sa.Column("confirmed_by_user", sa.Boolean(), nullable=True),
        sa.Column("user_feedback", sa.Text(), nullable=True),
        sa.Column("ux_intent", sa.String(length=64), nullable=False),
        sa.Column("aurora_presence", sa.String(length=32), nullable=False),
        sa.Column("projection_policy", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tdr_user_id", "transition_decision_records", ["user_id"], unique=False)
    op.create_index("ix_tdr_created_at", "transition_decision_records", ["created_at"], unique=False)
    op.create_index("ix_tdr_input_snapshot_ref", "transition_decision_records", ["input_snapshot_ref"], unique=False)
    op.create_index("ix_tdr_policy_version", "transition_decision_records", ["policy_version"], unique=False)
    op.create_index(
        "idx_tdr_user_created_snapshot",
        "transition_decision_records",
        ["user_id", "created_at", "input_snapshot_ref"],
        unique=False,
    )

    op.create_table(
        "insight_claims",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("claim_type", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("probed_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False),
        sa.Column("probe_outcome_ids", json_type, nullable=False),
        sa.Column("projection_policy", sa.String(length=64), nullable=False),
        sa.Column("write_path", sa.String(length=64), nullable=False),
        sa.Column("shareability", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_insight_claims_user_id", "insight_claims", ["user_id"], unique=False)
    op.create_index("ix_insight_claims_status", "insight_claims", ["status"], unique=False)
    op.create_index("ix_insight_claims_source", "insight_claims", ["source"], unique=False)
    op.create_index("ix_insight_claims_created_at", "insight_claims", ["created_at"], unique=False)
    op.create_index("idx_insight_claims_user_status", "insight_claims", ["user_id", "status"], unique=False)

    op.create_table(
        "probe_outcomes",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("claim_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("probe_type", sa.String(length=64), nullable=False),
        sa.Column("probe_content", sa.Text(), nullable=False),
        sa.Column("result", sa.String(length=64), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence_adjustment", sa.Float(), nullable=False),
        sa.Column("evidence_refs", json_type, nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["insight_claims.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_probe_outcomes_claim_id", "probe_outcomes", ["claim_id"], unique=False)
    op.create_index("ix_probe_outcomes_created_at", "probe_outcomes", ["created_at"], unique=False)

    op.create_table(
        "identity_evidence",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("dimension", sa.String(length=128), nullable=False),
        sa.Column("evidence_type", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("valence", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("evidence_refs", json_type, nullable=False),
        sa.Column("projection_policy", sa.String(length=64), nullable=False),
        sa.Column("shareability", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_identity_evidence_user_id", "identity_evidence", ["user_id"], unique=False)
    op.create_index("ix_identity_evidence_dimension", "identity_evidence", ["dimension"], unique=False)
    op.create_index("ix_identity_evidence_created_at", "identity_evidence", ["created_at"], unique=False)

    op.create_table(
        "window_states",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("global_mode", sa.String(length=32), nullable=False),
        sa.Column("commitment_overrides", json_type, nullable=False),
        sa.Column("set_by", sa.String(length=32), nullable=False),
        sa.Column("trigger_decision_ref", sa.String(length=36), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False),
        sa.Column("projection_policy", sa.String(length=64), nullable=False),
        sa.Column("write_path", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_window_states_user_id", "window_states", ["user_id"], unique=False)
    op.create_index("ix_window_states_created_at", "window_states", ["created_at"], unique=False)
    op.create_index("ix_window_states_trigger_decision_ref", "window_states", ["trigger_decision_ref"], unique=False)

    op.create_table(
        "user_scenario_states",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("pack_id", sa.String(length=128), nullable=False),
        sa.Column("current_node", sa.String(length=255), nullable=False),
        sa.Column("current_focus_contract_id", uuid_type, nullable=False),
        sa.Column("current_focus_contract_version", sa.Integer(), nullable=False),
        sa.Column("drift_from_backbone", sa.Text(), nullable=True),
        sa.Column("is_on_backbone", sa.Boolean(), nullable=False),
        sa.Column("overrides", json_type, nullable=False),
        sa.Column("last_signal", sa.Text(), nullable=True),
        sa.Column("last_signal_at", sa.DateTime(), nullable=True),
        sa.Column("projection_policy", sa.String(length=64), nullable=False),
        sa.Column("write_path", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["current_focus_contract_id"], ["focus_contracts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_scenario_states_user_id", "user_scenario_states", ["user_id"], unique=True)
    op.create_index("ix_user_scenario_states_pack_id", "user_scenario_states", ["pack_id"], unique=False)
    op.create_index("ix_user_scenario_states_current_node", "user_scenario_states", ["current_node"], unique=False)
    op.create_index(
        "idx_user_scenario_states_user_focus",
        "user_scenario_states",
        ["user_id", "current_focus_contract_id", "current_focus_contract_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_user_scenario_states_user_focus", table_name="user_scenario_states")
    op.drop_index("ix_user_scenario_states_current_node", table_name="user_scenario_states")
    op.drop_index("ix_user_scenario_states_pack_id", table_name="user_scenario_states")
    op.drop_index("ix_user_scenario_states_user_id", table_name="user_scenario_states")
    op.drop_table("user_scenario_states")

    op.drop_index("ix_window_states_trigger_decision_ref", table_name="window_states")
    op.drop_index("ix_window_states_created_at", table_name="window_states")
    op.drop_index("ix_window_states_user_id", table_name="window_states")
    op.drop_table("window_states")

    op.drop_index("ix_probe_outcomes_created_at", table_name="probe_outcomes")
    op.drop_index("ix_probe_outcomes_claim_id", table_name="probe_outcomes")
    op.drop_table("probe_outcomes")

    op.drop_index("ix_identity_evidence_created_at", table_name="identity_evidence")
    op.drop_index("ix_identity_evidence_dimension", table_name="identity_evidence")
    op.drop_index("ix_identity_evidence_user_id", table_name="identity_evidence")
    op.drop_table("identity_evidence")

    op.drop_index("idx_insight_claims_user_status", table_name="insight_claims")
    op.drop_index("ix_insight_claims_created_at", table_name="insight_claims")
    op.drop_index("ix_insight_claims_source", table_name="insight_claims")
    op.drop_index("ix_insight_claims_status", table_name="insight_claims")
    op.drop_index("ix_insight_claims_user_id", table_name="insight_claims")
    op.drop_table("insight_claims")

    op.drop_index("idx_tdr_user_created_snapshot", table_name="transition_decision_records")
    op.drop_index("ix_tdr_policy_version", table_name="transition_decision_records")
    op.drop_index("ix_tdr_input_snapshot_ref", table_name="transition_decision_records")
    op.drop_index("ix_tdr_created_at", table_name="transition_decision_records")
    op.drop_index("ix_tdr_user_id", table_name="transition_decision_records")
    op.drop_table("transition_decision_records")

    op.drop_index("idx_commitments_user_status_deadline", table_name="commitments")
    op.drop_index("ix_commitments_node_id", table_name="commitments")
    op.drop_index("ix_commitments_deadline", table_name="commitments")
    op.drop_index("ix_commitments_status", table_name="commitments")
    op.drop_index("ix_commitments_user_id", table_name="commitments")
    op.drop_table("commitments")

    op.drop_index("ix_focus_contracts_active_node", table_name="focus_contracts")
    op.drop_index("ix_focus_contracts_scenario_pack_id", table_name="focus_contracts")
    op.drop_index("ix_focus_contracts_user_version", table_name="focus_contracts")
    op.drop_index("ix_focus_contracts_user_id", table_name="focus_contracts")
    op.drop_table("focus_contracts")

    op.drop_index("uq_aurora_policy_versions_version", table_name="aurora_policy_versions")
    op.drop_index("ix_aurora_policy_versions_created_at", table_name="aurora_policy_versions")
    op.drop_table("aurora_policy_versions")
