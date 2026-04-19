from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.cache import cache_service
from app.orchestration.situation_brief import SituationBriefBuilder
from app.services.graph_reasoning_service import GraphReasoningService
from app.services.profile_front_door_service import ProfileFrontDoorService
from app.services.profile_insight_control_service import ProfileInsightControlService
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


class GetProfileFrontDoorParams(BaseModel):
    include_actions: bool = Field(
        default=True,
        description="Whether to include chat-native correction prompts for directly correctable claims.",
    )
    highlighted_claim_id: str | None = Field(
        default=None,
        description="Optional claim id to highlight in the payload when the user is asking about a specific belief.",
    )


class ApplyProfileCorrectionParams(BaseModel):
    target_id: str = Field(..., min_length=1, description="Canonical claim id from the profile front door payload.")
    action: str = Field(
        ...,
        description="One of: wrong, used_to_be_true, exam_mode_only, reset_override.",
    )
    reason: str | None = Field(
        default=None,
        max_length=240,
        description="Optional short user rationale for why the current claim is inaccurate.",
    )
    value: Any | None = Field(
        default=None,
        description="Optional explicit replacement value when correcting an adjustable inferred field.",
    )


class GetGraphDiagnosticSurfaceParams(BaseModel):
    limit: int = Field(default=3, ge=1, le=5, description="Max items per weak / at-risk section.")


def _runtime_redis(db_session: Any):
    runtime_context = get_tool_runtime_context(db_session)
    return runtime_context.get("redis_client") or cache_service.redis


def _resolve_runtime_identifiers(db_session: Any, session_id: str | None, plan_id: str | None) -> dict[str, Any]:
    runtime_context = get_tool_runtime_context(db_session)
    raw_session_id = str(session_id if session_id is not None else runtime_context.get("session_id") or "").strip()
    raw_plan_id = str(plan_id if plan_id is not None else runtime_context.get("plan_id") or "").strip()
    resolved_plan_id: UUID | None = None
    invalid_plan_id = False
    if raw_plan_id:
        try:
            resolved_plan_id = UUID(raw_plan_id)
        except (TypeError, ValueError):
            invalid_plan_id = True
    return {
        "session_id": raw_session_id or None,
        "plan_id": resolved_plan_id,
        "raw_plan_id": raw_plan_id,
        "invalid_plan_id": invalid_plan_id,
    }


def _identifier_error_result(
    tool_name: str,
    *,
    message: str,
    error_type: str,
    tool_call_id: str | None = None,
) -> ToolResult:
    return ToolResult(
        success=False,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        error_message=message,
        error_type=error_type,
    )


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
                    data={
                        "situation_brief": _compact_dict(
                            embedded_brief, include_source_trace=params.include_source_trace
                        )
                    },
                )

        builder = SituationBriefBuilder()
        brief = builder.build(
            user_context_payload=user_context_payload if isinstance(user_context_payload, dict) else None,
            plan_context=(
                runtime_context.get("plan_context") if isinstance(runtime_context.get("plan_context"), dict) else None
            ),
            focused_memory=(
                runtime_context.get("focused_memory")
                if isinstance(runtime_context.get("focused_memory"), dict)
                else None
            ),
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
        identifiers = _resolve_runtime_identifiers(db_session, params.session_id, params.plan_id)
        service = UserStrategyStateService(db_session, redis=_runtime_redis(db_session))

        data = {
            "effective_state": await service.get_effective_state(
                user_uuid,
                plan_id=identifiers["plan_id"],
                session_id=identifiers["session_id"],
            )
        }
        if params.include_recent_changes:
            data["recent_changes"] = await service.get_recent_changes(
                user_uuid,
                plan_id=identifiers["plan_id"],
                session_id=identifiers["session_id"],
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
            identifiers = _resolve_runtime_identifiers(db_session, params.session_id, params.plan_id)
            normalized_layer = str(params.layer or "").strip().lower()
            if normalized_layer == UserStrategyStateService.SESSION_LAYER and not identifiers["session_id"]:
                return _identifier_error_result(
                    self.name,
                    message="Session-layer strategy writes require a valid session_id in params or runtime context.",
                    error_type="missing_identifier",
                    tool_call_id=tool_call_id,
                )
            if normalized_layer == UserStrategyStateService.EPISODE_LAYER and identifiers["invalid_plan_id"]:
                return _identifier_error_result(
                    self.name,
                    message=f"Episode-layer strategy writes require a UUID plan_id, got: {identifiers['raw_plan_id']}",
                    error_type="invalid_identifier",
                    tool_call_id=tool_call_id,
                )
            if normalized_layer == UserStrategyStateService.EPISODE_LAYER and identifiers["plan_id"] is None:
                return _identifier_error_result(
                    self.name,
                    message="Episode-layer strategy writes require a valid plan_id in params or runtime context.",
                    error_type="missing_identifier",
                    tool_call_id=tool_call_id,
                )
            service = UserStrategyStateService(db_session, redis=_runtime_redis(db_session))
            data = await service.apply_adjustment(
                user_id=UUID(user_id),
                changes=params.changes,
                layer=params.layer,
                reason=params.reason,
                evidence=params.evidence.model_dump(),
                confidence=params.confidence,
                session_id=identifiers["session_id"],
                plan_id=identifiers["plan_id"],
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
            identifiers = _resolve_runtime_identifiers(db_session, params.session_id, params.plan_id)
            if identifiers["invalid_plan_id"]:
                return _identifier_error_result(
                    self.name,
                    message=f"Episode notes require a UUID plan_id, got: {identifiers['raw_plan_id']}",
                    error_type="invalid_identifier",
                    tool_call_id=tool_call_id,
                )
            if identifiers["plan_id"] is None:
                return _identifier_error_result(
                    self.name,
                    message="Episode notes require a valid plan_id in params or runtime context.",
                    error_type="missing_identifier",
                    tool_call_id=tool_call_id,
                )
            service = UserStrategyStateService(db_session, redis=_runtime_redis(db_session))
            data = await service.apply_adjustment(
                user_id=UUID(user_id),
                changes={"current_episode_note": params.note},
                layer=UserStrategyStateService.EPISODE_LAYER,
                reason=params.reason,
                evidence=params.evidence.model_dump(),
                confidence=params.confidence,
                session_id=identifiers["session_id"],
                plan_id=identifiers["plan_id"],
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


class GetProfileFrontDoorTool(BaseTool):
    name = "get_profile_front_door"
    description = (
        "Read Sparkle's canonical current picture of the user for chat-native "
        "questions like 'how do you currently see me' or 'what have you inferred about me'."
    )
    category = ToolCategory.GROWTH
    parameters_schema = GetProfileFrontDoorParams

    async def execute(
        self,
        params: GetProfileFrontDoorParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        runtime_context = get_tool_runtime_context(db_session)
        service = ProfileFrontDoorService(db_session, redis=_runtime_redis(db_session))
        profile_context = await service.load_profile_context(
            user_id=UUID(user_id),
            runtime_context=runtime_context,
        )
        payload = service.build_payload(
            profile_context=profile_context,
            highlighted_claim_id=params.highlighted_claim_id,
            include_actions=params.include_actions,
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            tool_call_id=tool_call_id,
            data={"profile_front_door": payload},
            widget_type="profile_front_door",
            widget_data=payload,
        )


class ApplyProfileCorrectionTool(BaseTool):
    name = "apply_profile_correction"
    description = (
        "Apply a chat-originated profile correction through the User Correction lane only, "
        "then return the refreshed canonical profile front door."
    )
    category = ToolCategory.GROWTH
    parameters_schema = ApplyProfileCorrectionParams

    async def execute(
        self,
        params: ApplyProfileCorrectionParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        runtime_context = get_tool_runtime_context(db_session)
        front_door_service = ProfileFrontDoorService(db_session, redis=_runtime_redis(db_session))
        before_context = await front_door_service.load_profile_context(
            user_id=UUID(user_id),
            runtime_context=runtime_context,
        )
        before_payload = front_door_service.build_payload(
            profile_context=before_context,
            highlighted_claim_id=params.target_id,
            include_actions=True,
        )
        claim_lookup = {
            str(item.get("id") or "").strip(): item
            for item in list(before_payload.get("claims") or [])
            if isinstance(item, dict)
        }
        target_label = str(claim_lookup.get(params.target_id, {}).get("label") or params.target_id).strip()

        control_service = ProfileInsightControlService(db_session, redis=_runtime_redis(db_session))
        try:
            result = await control_service.apply_control(
                user_id=UUID(user_id),
                target_id=params.target_id,
                action=params.action,
                value=params.value,
                reason=params.reason,
                source="chat_profile_correction",
            )
        except (ValueError, LookupError) as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=str(exc),
                error_type=type(exc).__name__,
            )

        after_context = await front_door_service.load_profile_context(
            user_id=UUID(user_id),
            runtime_context={},
        )
        after_payload = front_door_service.build_payload(
            profile_context=after_context,
            highlighted_claim_id=params.target_id,
            include_actions=True,
            confirmation={
                "title": f"已记录「{target_label}」这条纠正",
                "message": (
                    "这次更新走的是 User Correction 独立通道，不经过 Aurora / L3 / strategy lane。"
                    "下面是我按最新 canonical 画像重新读取后的结果。"
                ),
            },
        )

        return ToolResult(
            success=True,
            tool_name=self.name,
            tool_call_id=tool_call_id,
            data={
                "correction_result": {
                    "status": result.status,
                    "target_id": result.target_id,
                    "action": result.action,
                    "preference_version": result.preference_version,
                },
                "profile_front_door": after_payload,
            },
            widget_type="profile_front_door",
            widget_data=after_payload,
        )


class GetGraphDiagnosticSurfaceTool(BaseTool):
    name = "get_graph_diagnostic_surface"
    description = (
        "Read a graph-derived diagnostic surface for questions like "
        "'我哪里弱' or 'which knowledge areas are currently weakest'. "
        "This is a read-only graph / galaxy diagnostic path."
    )
    category = ToolCategory.GROWTH
    parameters_schema = GetGraphDiagnosticSurfaceParams

    async def execute(
        self,
        params: GetGraphDiagnosticSurfaceParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        snapshot = await GraphReasoningService(db_session).build_diagnostic_snapshot(
            UUID(user_id),
            limit=params.limit,
        )
        payload = {
            "title": "你当前最薄弱的知识点",
            "headline": "图谱诊断面",
            **snapshot,
            "read_lane": "graph_diagnostic_surface",
            "binding_note": "这个诊断面只消费现有 graph / mastery 数据，不会直接改写任何用户状态。",
        }
        return ToolResult(
            success=True,
            tool_name=self.name,
            tool_call_id=tool_call_id,
            data={"graph_diagnostic_surface": payload},
            widget_type="graph_diagnostic",
            widget_data=payload,
        )
