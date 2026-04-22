from dataclasses import FrozenInstanceError
from datetime import datetime
from uuid import uuid4

import pytest

from app.state_aggregator.schema import (
    ActiveSkillSummaryItemValue,
    ActiveSkillsSummaryValue,
    AchievementSummaryValue,
    CalendarContextValue,
    CommitmentSummaryValue,
    PendingPoliciesSummaryValue,
    RecentReflectionsSummaryValue,
    SocialSignalsSummaryValue,
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

    assert state.schema_version == "user_state.v1.13"
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


def test_user_state_v1_4_exposes_achievement_and_calendar_contracts() -> None:
    state = UserStateV1(
        user_id=uuid4(),
        achievement_summary=StateFieldEnvelope(
            value=AchievementSummaryValue(
                recent_unlocks=(),
                in_progress_achievements=(),
                total_achievement_score=4.5,
            ),
            computed_at=datetime(2026, 4, 21, 10, 0, 0),
            source_snapshot_ids=("achievement:streak_7",),
            freshness_seconds=0,
        ),
        calendar_context=StateFieldEnvelope(
            value=CalendarContextValue(
                upcoming_deadlines=(),
                time_blocks_today=(),
                workload_density="medium",
                exam_urgency={"days_left": 12, "urgent": True},
            ),
            computed_at=datetime(2026, 4, 21, 10, 0, 0),
            source_snapshot_ids=("calendar_event:1",),
            freshness_seconds=0,
        ),
    )

    assert state.achievement_summary is not None
    assert state.achievement_summary.value.total_achievement_score == 4.5
    assert state.calendar_context is not None
    assert state.calendar_context.value.workload_density == "medium"


def test_user_state_v1_5_exposes_pending_policies_contract() -> None:
    state = UserStateV1(
        user_id=uuid4(),
        pending_policies=StateFieldEnvelope(
            value=PendingPoliciesSummaryValue(
                count=2,
                next_trigger_at=datetime(2026, 4, 22, 9, 0, 0),
                policy_ids=("policy-1", "policy-2"),
            ),
            computed_at=datetime(2026, 4, 21, 10, 0, 0),
            source_snapshot_ids=("policy:policy-1",),
            freshness_seconds=0,
        ),
    )

    assert state.pending_policies is not None
    assert state.pending_policies.value.count == 2
    assert state.pending_policies.value.policy_ids == ("policy-1", "policy-2")


def test_user_state_v1_6_exposes_recent_reflections_contract() -> None:
    state = UserStateV1(
        user_id=uuid4(),
        recent_reflections=StateFieldEnvelope(
            value=RecentReflectionsSummaryValue(
                count=3,
                last_category="plan_stall",
                last_at=datetime(2026, 4, 21, 13, 0, 0),
            ),
            computed_at=datetime(2026, 4, 21, 13, 5, 0),
            source_snapshot_ids=("episodic:r1",),
            freshness_seconds=0,
        ),
    )

    assert state.recent_reflections is not None
    assert state.recent_reflections.value.count == 3
    assert state.recent_reflections.value.last_category == "plan_stall"


def test_user_state_v1_13_exposes_social_signals_summary_contract() -> None:
    state = UserStateV1(
        user_id=uuid4(),
        social_signals_summary=StateFieldEnvelope(
            value=SocialSignalsSummaryValue(
                summary_text="最近 7 天提到过 2 位学习相关人物；目前有 1 条到期承诺待跟进。",
                mention_count=2,
                relationship_count=1,
                pending_commitments_count=1,
                community_engagement_level="medium",
                social_learning_preference=0.74,
                content_contribution_rate=0.22,
            ),
            computed_at=datetime(2026, 4, 22, 10, 0, 0),
            source_snapshot_ids=("social_signals:u-1",),
            freshness_seconds=0,
        ),
    )

    assert state.social_signals_summary is not None
    assert state.social_signals_summary.value.mention_count == 2
    assert state.social_signals_summary.value.relationship_count == 1
    assert "到期承诺" in state.social_signals_summary.value.summary_text
