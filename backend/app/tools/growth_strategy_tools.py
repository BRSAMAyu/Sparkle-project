from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.cache import cache_service
from app.orchestration.situation_brief import SituationBriefBuilder
from app.services.user_strategy_state_service import UserStrategyStateService
from app.tools.base import BaseTool, ToolCategory, ToolResult, get_tool_runtime_context


class _StrategyEvidence(BaseModel):
    source: str = Field(default="conversation", description="Evidence source, usually conversation")
    message_id: str | None = Field(default=None, description="Related message id when available")
    snippet: str = Field(..., min_length=1, max_length=280, description="Short evidence snippet")


class GetSituationBriefParams(BaseModel):
    include_source_trace: bool = Field(default=True, description="Whether to include source-trace details")


class GetUserStrategyStateParams(BaseModel):
    session_id: str | None = Field(default=None, description="Optional session override")
    plan_id: str | None = Field(default=None, description="Optional plan override")
    include_recent_changes: bool = Field(default=True)
    recent_change_limit: int = Field(default=8, ge=1, le=20)


class AdjustUserStrategyStateParams(BaseModel):
    layer: str = Field(..., description="One of: session, episode, profile")
    changes: dict[str, Any] = Field(
        ...,
        description=(
            "Field updates. Allowed fields: difficulty_level, push_vs_support, session_mode, "
            "intervention_intensity, explanation_style, retrieval_emphasis, current_episode_note"
        ),
    )
    reason: str = Field(..., min_length=4, max_length=180)
    evidence: _StrategyEvidence
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    session_id: str | None = Field(default=None, description="Optional session override")
    plan_id: str | None = Field(default=None, description="Optional plan override")
    ttl_seconds: int | None = Field(default=None, ge=60, le=7 * 24 * 60 * 60)


class WriteEpisodeNoteParams(BaseModel):
    note: str = Field(..., min_length=4, max_length=240)
    reason: str = Field(..., min_length=4, max_length=180)
    evidence: _StrategyEvidence
    confidence: float = Field(default=0.82, ge=0.0, le=1.0)
    session_id: str | None = Field(default=None, description="Optional session override")
    plan_id: str | None = Field(default=None, description="Optional plan override")
    ttl_seconds: int | None = Field(default=None, ge=60, le=30 * 24 * 60 * 60)


def _runtime_redis(db_session: Any):
    runtime_context = get_tool_runtime_context(db_session)
    return runtime_context.get("redis_client") or cache_service.redis


def _resolve_runtime_ids(
    db_session: Any, session_id: str | None, plan_id: str | None
) -> tuple[str | None, UUID | None]:
    runtime_context = get_tool_runtime_context(db_session)
    resolved_session_id = str(session_id or runtime_context.get("session_id") or "").strip() or None
    raw_plan_id = str(plan_id or runtime_context.get("plan_id") or "").strip()
    resolved_plan_id: UUID | None = None
    if raw_plan_id:
        try:
            resolved_plan_id = UUID(raw_plan_id)
        except (TypeError, ValueError):
            resolved_plan_id = None
    return resolved_session_id, resolved_plan_id


def _compact_dict(value: dict[str, Any], *, include_source_trace: bool) -> dict[str, Any]:
    payload = dict(value)
    if not include_source_trace:
        payload.pop("source_trace", None)
    return payload


class GetSituationBriefTool(BaseTool):
    name = "get_situation_brief"
    description = "Read Sparkle's compact SituationBrief for the current conversation context."
    category = ToolCategory.GROWTH
    parameters_schema = GetSituationBriefParams

    async def execute(
        self,
        params: GetSituationBriefParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        del user_id
        runtime_context = get_tool_runtime_context(db_session)

        direct_brief = runtime_context.get("situation_brief")
        if isinstance(direct_brief, dict) and direct_brief:
            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={"situation_brief": _compact_dict(direct_brief, include_source_trace=params.include_source_trace)},
            )

        user_context_payload = runtime_context.get("user_context_payload")
        if isinstance(user_context_payload, dict):
            embedded_brief = user_context_payload.get("situation_brief")
            if isinstance(embedded_brief, dict) and embedded_brief:
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    tool_call_id=tool_call_id,
                    data={"situation_brief": _compact_dict(embedded_brief, include_source_trace=params.include_source_trace)},
                )

        builder = SituationBriefBuilder()
        brief = builder.build(
            user_context_payload=user_context_payload if isinstance(user_context_payload, dict) else None,
            plan_context=runtime_context.get("plan_context") if isinstance(runtime_context.get("plan_context"), dict) else None,
            focused_memory=runtime_context.get("focused_memory") if isinstance(runtime_context.get("focused_memory"), dict) else None,
            context_briefing_note=str(runtime_context.get("context_briefing_note") or "").strip() or None,
            visible_update_context=(
                runtime_context.get("visible_update_context")
                if isinstance(runtime_context.get("visible_update_context"), dict)
                else None
            ),
            dual_core_snapshot=(
                runtime_context.get("dual_core_snapshot")
                if isinstance(runtime_context.get("dual_core_snapshot"), dict)
                else None
            ),
            session_feedback_signal=(
                runtime_context.get("session_feedback_signal")
                if isinstance(runtime_context.get("session_feedback_signal"), dict)
                else None
            ),
            progress_snapshot=(
                runtime_context.get("progress_snapshot")
                if isinstance(runtime_context.get("progress_snapshot"), dict)
                else None
            ),
            adaptation_records=(
                runtime_context.get("adaptation_records")
                if isinstance(runtime_context.get("adaptation_records"), list)
                else None
            ),
        ).to_dict()

        return ToolResult(
            success=True,
            tool_name=self.name,
            tool_call_id=tool_call_id,
            data={"situation_brief": _compact_dict(brief, include_source_trace=params.include_source_trace)},
        )


class GetUserStrategyStateTool(BaseTool):
    name = "get_user_strategy_state"
    description = "Read Sparkle's effective user strategy state and recent strategy adjustments."
    category = ToolCategory.GROWTH
    parameters_schema = GetUserStrategyStateParams

    async def execute(
        self,
        params: GetUserStrategyStateParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        user_uuid = UUID(user_id)
        session_id, plan_id = _resolve_runtime_ids(db_session, params.session_id, params.plan_id)
        service = UserStrategyStateService(db_session, redis=_runtime_redis(db_session))

        data = {
            "effective_state": await service.get_effective_state(
                user_uuid,
                plan_id=plan_id,
                session_id=session_id,
            )
        }
        if params.include_recent_changes:
            data["recent_changes"] = await service.get_recent_changes(
                user_uuid,
                plan_id=plan_id,
                session_id=session_id,
                limit=params.recent_change_limit,
            )

        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data=data)


class AdjustUserStrategyStateTool(BaseTool):
    name = "adjust_user_strategy_state"
    description = "Write bounded user strategy adjustments to the session, episode, or profile layer."
    category = ToolCategory.GROWTH
    parameters_schema = AdjustUserStrategyStateParams

    async def execute(
        self,
        params: AdjustUserStrategyStateParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            session_id, plan_id = _resolve_runtime_ids(db_session, params.session_id, params.plan_id)
            service = UserStrategyStateService(db_session, redis=_runtime_redis(db_session))
            data = await service.apply_adjustment(
                user_id=UUID(user_id),
                changes=params.changes,
                layer=params.layer,
                reason=params.reason,
                evidence=params.evidence.model_dump(),
                confidence=params.confidence,
                session_id=session_id,
                plan_id=plan_id,
                ttl_seconds=params.ttl_seconds,
            )
            return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data=data)
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=str(exc),
                error_type=type(exc).__name__,
            )


class WriteEpisodeNoteTool(BaseTool):
    name = "write_episode_note"
    description = "Write a short-lived episode note into the episode-layer strategy state."
    category = ToolCategory.GROWTH
    parameters_schema = WriteEpisodeNoteParams

    async def execute(
        self,
        params: WriteEpisodeNoteParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            session_id, plan_id = _resolve_runtime_ids(db_session, params.session_id, params.plan_id)
            service = UserStrategyStateService(db_session, redis=_runtime_redis(db_session))
            data = await service.apply_adjustment(
                user_id=UUID(user_id),
                changes={"current_episode_note": params.note},
                layer=UserStrategyStateService.EPISODE_LAYER,
                reason=params.reason,
                evidence=params.evidence.model_dump(),
                confidence=params.confidence,
                session_id=session_id,
                plan_id=plan_id,
                ttl_seconds=params.ttl_seconds,
            )
            return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data=data)
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=str(exc),
                error_type=type(exc).__name__,
            )
