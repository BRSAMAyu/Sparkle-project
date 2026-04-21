from dataclasses import FrozenInstanceError
from datetime import datetime
from uuid import uuid4

import pytest

from app.state_aggregator.schema import (
    ActiveSkillSummaryItemValue,
    ActiveSkillsSummaryValue,
    CommitmentSummaryValue,
    StateFieldEnvelope,
    SufficiencySummaryValue,
    UserStateV1,
)


def test_user_state_v1_schema_is_frozen() -> None:
    state = UserStateV1(user_id=uuid4())

    with pytest.raises(FrozenInstanceError):
        state.schema_version = "user_state.v2"


def test_user_state_v1_uses_expected_schema_version() -> None:
    state = UserStateV1(
        user_id=uuid4(),
        commitment_summary=StateFieldEnvelope(
            value=CommitmentSummaryValue(
                overdue_count=1,
                next_due_at=None,
                pending_commitment_ids=("c1",),
            ),
            computed_at=datetime(2026, 4, 21, 10, 0, 0),
            source_snapshot_ids=("episodic:c1",),
            freshness_seconds=0,
        ),
    )

    assert state.schema_version == "user_state.v1.3"
    assert state.commitment_summary is not None
    assert state.commitment_summary.value.overdue_count == 1


def test_user_state_v1_2_exposes_sufficiency_summary_contract() -> None:
    state = UserStateV1(
        user_id=uuid4(),
        task_sufficiency_summary=StateFieldEnvelope(
            value=SufficiencySummaryValue(score=0.6, top_missing_dimensions=("constraint_explicit",)),
            computed_at=datetime(2026, 4, 21, 10, 0, 0),
            source_snapshot_ids=("sufficiency:task",),
            freshness_seconds=0,
        ),
    )

    assert state.task_sufficiency_summary is not None
    assert state.task_sufficiency_summary.value.score == 0.6
    assert state.task_sufficiency_summary.value.top_missing_dimensions == ("constraint_explicit",)


def test_user_state_v1_3_exposes_active_skills_summary_contract() -> None:
    state = UserStateV1(
        user_id=uuid4(),
        active_skills_summary=StateFieldEnvelope(
            value=ActiveSkillsSummaryValue(
                items=(
                    ActiveSkillSummaryItemValue(
                        skill_id="skill-1",
                        name="Exam Triage",
                        activation_match_score=1.0,
                    ),
                )
            ),
            computed_at=datetime(2026, 4, 21, 10, 0, 0),
            source_snapshot_ids=("user_skill:skill-1",),
            freshness_seconds=0,
        ),
    )

    assert state.active_skills_summary is not None
    assert state.active_skills_summary.value.items[0].skill_id == "skill-1"
    assert state.active_skills_summary.value.items[0].activation_match_score == 1.0
