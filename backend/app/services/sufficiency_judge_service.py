from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aurora_stage20 import AuroraJudgmentRecord
from app.services.sufficiency_judge_schema import (
    CurrentTurnParseResult,
    ScoreBucket,
    SufficiencyJudgment,
    SufficiencyScore,
)
from app.state_aggregator.schema import UserStateV1


class SufficiencyJudgeService:
    """Deterministic Stage 20 sufficiency judge."""

    JUDGE_VERSION = "v1"
    TASK_WEIGHTS = {
        "intent_clarity": 0.40,
        "target_object_resolved": 0.35,
        "constraint_explicit": 0.25,
    }

    def evaluate(
        self,
        *,
        user_state: UserStateV1,
        current_turn: CurrentTurnParseResult,
    ) -> SufficiencyJudgment:
        task_dimensions = {
            "intent_clarity": self._intent_clarity_bucket(current_turn.intent_confidence),
            "target_object_resolved": self._bool_bucket(current_turn.target_object_resolved),
            "constraint_explicit": self._constraint_bucket(current_turn),
        }
        task_missing = tuple(name for name, value in task_dimensions.items() if value < 1.0)
        task_score = round(
            sum(float(task_dimensions[name]) * weight for name, weight in self.TASK_WEIGHTS.items()),
            4,
        )

        context_dimensions = {
            "relevant_memory_present": self._relevant_memory_bucket(user_state),
            "recent_user_state_known": self._recent_user_state_bucket(user_state),
            "social_context_loaded": self._social_context_bucket(user_state),
        }
        context_missing = tuple(name for name, value in context_dimensions.items() if value < 1.0)
        context_score = round(sum(float(value) for value in context_dimensions.values()) / 3.0, 4)

        return SufficiencyJudgment(
            task_sufficiency=SufficiencyScore(score=task_score, missing_dimensions=task_missing),
            context_sufficiency=SufficiencyScore(score=context_score, missing_dimensions=context_missing),
            judge_version=self.JUDGE_VERSION,
        )

    @staticmethod
    def summarize_for_aggregator(judgment: SufficiencyJudgment) -> dict[str, dict[str, object]]:
        return {
            "task_sufficiency_summary": {
                "score": judgment.task_sufficiency.score,
                "top_missing_dimensions": judgment.task_sufficiency.missing_dimensions[:3],
            },
            "context_sufficiency_summary": {
                "score": judgment.context_sufficiency.score,
                "top_missing_dimensions": judgment.context_sufficiency.missing_dimensions[:3],
            },
        }

    @staticmethod
    def _intent_clarity_bucket(confidence: float) -> ScoreBucket:
        if confidence >= 0.8:
            return 1.0
        if confidence >= 0.55:
            return 0.5
        return 0.0

    @staticmethod
    def _constraint_bucket(current_turn: CurrentTurnParseResult) -> ScoreBucket:
        if current_turn.constraint_explicit:
            return 1.0
        return 0.0

    @staticmethod
    def _bool_bucket(value: bool) -> ScoreBucket:
        return 1.0 if value else 0.0

    @staticmethod
    def _relevant_memory_bucket(user_state: UserStateV1) -> ScoreBucket:
        working_memory = getattr(user_state, "working_memory_snapshot", None)
        if working_memory is not None and working_memory.value.items:
            return 1.0
        commitment = getattr(user_state, "commitment_summary", None)
        if commitment is not None and (
            commitment.value.pending_commitment_ids or commitment.value.next_due_at is not None
        ):
            return 1.0
        if working_memory is not None or commitment is not None:
            return 0.5
        return 0.0

    @staticmethod
    def _recent_user_state_bucket(user_state: UserStateV1) -> ScoreBucket:
        engagement = getattr(user_state, "engagement_state", None)
        if engagement is None:
            return 0.5
        if engagement.value.last_active_at is not None:
            return 1.0
        if engagement.value.session_count_7d > 0 or engagement.value.streak > 0:
            return 0.5
        return 0.5

    @staticmethod
    def _social_context_bucket(user_state: UserStateV1) -> ScoreBucket:
        social = getattr(user_state, "recent_person_mentions", None)
        if social is None:
            return 0.5
        return 1.0

    @staticmethod
    async def persist_judgment(
        db: AsyncSession,
        *,
        user_state: UserStateV1,
        judgment: SufficiencyJudgment,
    ) -> str:
        record = AuroraJudgmentRecord(
            user_id=user_state.user_id,
            task_sufficiency_score=judgment.task_sufficiency.score,
            task_missing_dimensions=list(judgment.task_sufficiency.missing_dimensions),
            context_sufficiency_score=judgment.context_sufficiency.score,
            context_missing_dimensions=list(judgment.context_sufficiency.missing_dimensions),
            judge_version=judgment.judge_version,
            computed_at=judgment.computed_at,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return str(record.id)
