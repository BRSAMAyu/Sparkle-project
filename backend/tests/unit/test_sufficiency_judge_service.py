import json
from pathlib import Path
from uuid import uuid4

from app.services.sufficiency_judge_schema import CurrentTurnParseResult
from app.services.sufficiency_judge_service import SufficiencyJudgeService
from app.state_aggregator.schema import (
    CommitmentSummaryValue,
    EngagementStateValue,
    RecentPersonMentionsValue,
    SocialMentionValue,
    StateFieldEnvelope,
    UserStateV1,
    WorkingMemorySnapshotValue,
    WorkingMemorySnapshotValueItem,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "stage20_sufficiency_judge_cold_dataset.json"


def _label(value: float) -> str:
    if value >= 0.8:
        return "high"
    if value >= 0.45:
        return "medium"
    return "low"


def _build_state(case: dict) -> UserStateV1:
    user_id = uuid4()
    state = UserStateV1(user_id=user_id)
    if case["has_commitment"]:
        state = UserStateV1(
            user_id=user_id,
            commitment_summary=StateFieldEnvelope(
                value=CommitmentSummaryValue(overdue_count=1, next_due_at=None, pending_commitment_ids=("c1",)),
                computed_at=FIXTURE_NOW,
                source_snapshot_ids=("episodic:c1",),
                freshness_seconds=0,
            ),
            engagement_state=state.engagement_state,
            recent_person_mentions=state.recent_person_mentions,
            learning_state=state.learning_state,
            working_memory_snapshot=state.working_memory_snapshot,
            emotion_hint=state.emotion_hint,
        )
    if case["has_working_memory"]:
        state = UserStateV1(
            user_id=user_id,
            commitment_summary=state.commitment_summary,
            engagement_state=state.engagement_state,
            recent_person_mentions=state.recent_person_mentions,
            learning_state=state.learning_state,
            working_memory_snapshot=StateFieldEnvelope(
                value=WorkingMemorySnapshotValue(
                    active_session_id="session-1",
                    items=(
                        WorkingMemorySnapshotValueItem(
                            summary="复习数学真题",
                            subject_type="commitment",
                            mention_count=3,
                            consolidated=False,
                            last_seen_at=FIXTURE_NOW,
                        ),
                    ),
                ),
                computed_at=FIXTURE_NOW,
                source_snapshot_ids=("wm:1",),
                freshness_seconds=0,
            ),
            emotion_hint=state.emotion_hint,
        )
    if case["has_engagement"]:
        state = UserStateV1(
            user_id=user_id,
            commitment_summary=state.commitment_summary,
            engagement_state=StateFieldEnvelope(
                value=EngagementStateValue(last_active_at=FIXTURE_NOW, session_count_7d=3, streak=2),
                computed_at=FIXTURE_NOW,
                source_snapshot_ids=("focus:1",),
                freshness_seconds=0,
            ),
            recent_person_mentions=state.recent_person_mentions,
            learning_state=state.learning_state,
            working_memory_snapshot=state.working_memory_snapshot,
            emotion_hint=state.emotion_hint,
        )
    if case["has_social"]:
        state = UserStateV1(
            user_id=user_id,
            commitment_summary=state.commitment_summary,
            engagement_state=state.engagement_state,
            recent_person_mentions=StateFieldEnvelope(
                value=RecentPersonMentionsValue(
                    mentions=(SocialMentionValue(summary="和同学讨论复习计划", occurred_at=FIXTURE_NOW),),
                    relationship_count=1,
                ),
                computed_at=FIXTURE_NOW,
                source_snapshot_ids=("episodic:social",),
                freshness_seconds=0,
            ),
            learning_state=state.learning_state,
            working_memory_snapshot=state.working_memory_snapshot,
            emotion_hint=state.emotion_hint,
        )
    return state


FIXTURE_NOW = __import__("datetime").datetime(2026, 4, 21, 12, 0, 0)


def test_sufficiency_judge_returns_explainable_missing_dimensions() -> None:
    service = SufficiencyJudgeService()
    judgment = service.evaluate(
        user_state=UserStateV1(user_id=uuid4()),
        current_turn=CurrentTurnParseResult(
            intent="plan",
            intent_confidence=0.42,
            information_sufficient=False,
            target_object_resolved=False,
            constraint_explicit=False,
        ),
    )

    assert judgment.task_sufficiency.score < 0.45
    assert "intent_clarity" in judgment.task_sufficiency.missing_dimensions
    assert "target_object_resolved" in judgment.task_sufficiency.missing_dimensions
    assert "relevant_memory_present" in judgment.context_sufficiency.missing_dimensions


def test_sufficiency_judge_cold_dataset_meets_split_accuracy_threshold() -> None:
    service = SufficiencyJudgeService()
    dataset = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    total = len(dataset)
    task_matches = 0
    context_matches = 0

    for case in dataset:
        judgment = service.evaluate(
            user_state=_build_state(case),
            current_turn=CurrentTurnParseResult(
                intent="plan",
                intent_confidence=case["intent_confidence"],
                information_sufficient=case["information_sufficient"],
                target_object_resolved=case["target_object_resolved"],
                constraint_explicit=case["constraint_explicit"],
            ),
        )
        if _label(judgment.task_sufficiency.score) == case["expected_task"]:
            task_matches += 1
        if _label(judgment.context_sufficiency.score) == case["expected_context"]:
            context_matches += 1

    task_accuracy = task_matches / total
    context_accuracy = context_matches / total

    assert total >= 40
    assert task_accuracy >= 0.8
    assert context_accuracy >= 0.8


def test_sufficiency_summary_for_aggregator_keeps_top_three_missing_dimensions() -> None:
    service = SufficiencyJudgeService()
    judgment = service.evaluate(
        user_state=UserStateV1(user_id=uuid4()),
        current_turn=CurrentTurnParseResult(
            intent="plan",
            intent_confidence=0.1,
            information_sufficient=False,
            target_object_resolved=False,
            constraint_explicit=False,
        ),
    )

    summary = service.summarize_for_aggregator(judgment)
    assert summary["task_sufficiency_summary"]["score"] == judgment.task_sufficiency.score
    assert len(summary["task_sufficiency_summary"]["top_missing_dimensions"]) <= 3
