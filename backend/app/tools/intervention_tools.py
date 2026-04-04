from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.card_protocol import InterventionRecord
from app.services.intervention_feedback_binding_service import InterventionFeedbackBindingService
from app.services.intervention_record_service import InterventionRecordService
from app.services.intervention_strategy_learner import InterventionStrategyLearner
from app.tools.base import BaseTool, ToolCategory, ToolResult, get_tool_runtime_context

_ALLOWED_FEEDBACK_SENTIMENTS = {"helped", "accepted", "dismissed", "not_helped", "mixed", "snoozed"}


class GetInterventionTrackRecordParams(BaseModel):
    days: int = Field(default=30, ge=1, le=90)
    limit: int = Field(default=10, ge=1, le=20)


class RecordInterventionFeedbackParams(BaseModel):
    intervention_id: str | None = Field(default=None, description="Optional explicit intervention override")
    sentiment: str | None = Field(
        default=None,
        description="One of: helped, accepted, dismissed, not_helped, mixed, snoozed",
    )
    user_words: str | None = Field(
        default=None,
        max_length=600,
        description="Raw user words or a faithful short quote from the user",
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    message_id: str | None = Field(default=None, max_length=120)
    source: str = Field(default="conversation", max_length=60)
    snooze_hours: int = Field(default=24, ge=1, le=168)

    # Backward-compatible aliases retained from Bridge 3.
    feedback_kind: str | None = Field(default=None, exclude=True)
    summary: str | None = Field(default=None, exclude=True)
    detail: str | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _normalize(self) -> "RecordInterventionFeedbackParams":
        normalized_sentiment = str(self.sentiment or self.feedback_kind or "").strip().lower()
        normalized_words = " ".join(str(self.user_words or self.detail or self.summary or "").split())
        if normalized_sentiment not in _ALLOWED_FEEDBACK_SENTIMENTS:
            raise ValueError(
                "sentiment must be one of: helped, accepted, dismissed, not_helped, mixed, snoozed"
            )
        if not normalized_words:
            raise ValueError("user_words is required")
        self.sentiment = normalized_sentiment
        self.user_words = normalized_words
        return self


def _format_record(record: InterventionRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "trigger_type": record.trigger_type.value if record.trigger_type else None,
        "delivery_strategy": record.delivery_strategy.value if record.delivery_strategy else None,
        "delivery_channel": record.delivery_channel.value if record.delivery_channel else None,
        "acceptance_status": record.acceptance_status.value if record.acceptance_status else None,
        "outcome_status": record.outcome_status.value if record.outcome_status else None,
        "action_payload": dict(record.action_payload or {}),
        "evidence_payload": dict(record.evidence_payload or {}),
    }


class GetInterventionTrackRecordTool(BaseTool):
    name = "get_intervention_track_record"
    description = "Inspect Sparkle's recent intervention history and response profile for this user."
    category = ToolCategory.GROWTH
    parameters_schema = GetInterventionTrackRecordParams

    async def execute(
        self,
        params: GetInterventionTrackRecordParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        user_uuid = UUID(user_id)
        record_service = InterventionRecordService(db_session)
        learner = InterventionStrategyLearner(db_session)

        recent_records = await record_service.get_recent_for_user(user_uuid, days=params.days, limit=params.limit)
        acceptance_stats = await record_service.get_acceptance_stats(user_uuid, days=params.days)
        outcome_stats = await record_service.get_outcome_stats(user_uuid)
        response_profile = await learner.get_user_response_profile(user_uuid)

        runtime_context = get_tool_runtime_context(db_session)
        binding_service = InterventionFeedbackBindingService(
            db_session,
            redis=runtime_context.get("redis_client"),
        )
        active_interventions = await binding_service.resolve_active_interventions(
            user_id=user_uuid,
            session_id=str(runtime_context.get("session_id") or "").strip() or None,
            runtime_active_interventions=(
                runtime_context.get("active_interventions")
                if isinstance(runtime_context.get("active_interventions"), list)
                else None
            ),
        )
        last_feedback_binding = await binding_service.get_last_feedback_binding(
            str(runtime_context.get("session_id") or "").strip() or None
        )

        data = {
            "acceptance_stats": acceptance_stats,
            "outcome_stats": outcome_stats,
            "response_profile": {
                "user_id": str(response_profile.user_id),
                "total_samples": response_profile.total_samples,
                "preferred_strategy": response_profile.preferred_strategy.value if response_profile.preferred_strategy else None,
                "preferred_channel": response_profile.preferred_channel.value if response_profile.preferred_channel else None,
                "acted_rate_by_strategy": response_profile.acted_rate_by_strategy,
                "effective_rate_by_strategy": response_profile.effective_rate_by_strategy,
            },
            "recent_records": [_format_record(record) for record in recent_records],
            "active_interventions": active_interventions,
        }
        if last_feedback_binding:
            data["last_feedback_binding"] = last_feedback_binding
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data=data)


class RecordInterventionFeedbackTool(BaseTool):
    name = "record_intervention_feedback"
    description = "Bind free-text conversational feedback onto the active or specified intervention."
    category = ToolCategory.GROWTH
    parameters_schema = RecordInterventionFeedbackParams

    async def execute(
        self,
        params: RecordInterventionFeedbackParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        runtime_context = get_tool_runtime_context(db_session)
        binding_service = InterventionFeedbackBindingService(
            db_session,
            redis=runtime_context.get("redis_client"),
        )
        data = await binding_service.bind_feedback(
            user_id=UUID(user_id),
            session_id=str(runtime_context.get("session_id") or "").strip() or None,
            sentiment=str(params.sentiment or "").strip(),
            user_words=str(params.user_words or "").strip(),
            confidence=params.confidence,
            intervention_id=params.intervention_id,
            message_id=params.message_id,
            source=params.source,
            runtime_active_interventions=(
                runtime_context.get("active_interventions")
                if isinstance(runtime_context.get("active_interventions"), list)
                else None
            ),
            snooze_hours=params.snooze_hours,
        )
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data=data)
