from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.cache import cache_service
from app.services.companion_state_service import (
    COMPANION_SESSION_WRITE_FIELDS,
    CompanionStateService,
)
from app.tools.base import BaseTool, ToolCategory, ToolResult, get_tool_runtime_context


class _CompanionEvidence(BaseModel):
    source: str = Field(default="conversation", description="Evidence source, usually conversation")
    message_id: str | None = Field(default=None, description="Related message id when available")
    snippet: str = Field(..., min_length=1, max_length=280, description="Short evidence snippet")
    measurable_effect: bool = Field(
        default=False,
        description="Whether this change measurably improved the user's interaction",
    )


class GetCompanionStateParams(BaseModel):
    session_id: str | None = Field(default=None, description="Optional session override")
    plan_id: str | None = Field(default=None, description="Optional plan override")
    include_relationship_profile: bool = Field(default=True)
    include_recent_revisions: bool = Field(default=True)


class AdjustCompanionStateParams(BaseModel):
    field: str = Field(..., description="One of the allowed session companion fields")
    value: Any = Field(..., description="New value for the companion field")
    reason: str = Field(..., min_length=4, max_length=240, description="Why Sparkle is adjusting this")
    evidence: _CompanionEvidence
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    session_id: str | None = Field(default=None, description="Optional session override")
    plan_id: str | None = Field(default=None, description="Optional plan override")


class WriteCompanionGrowthNoteParams(BaseModel):
    note: str = Field(..., min_length=4, max_length=320)
    reason: str = Field(..., min_length=4, max_length=240)
    evidence: _CompanionEvidence
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    session_id: str | None = Field(default=None)
    plan_id: str | None = Field(default=None)


class WriteRelationshipNoteParams(BaseModel):
    note: str = Field(..., min_length=4, max_length=320)
    note_kind: str = Field(default="milestone", description="milestone, boundary, trust, repair, or growth")
    reason: str = Field(..., min_length=4, max_length=240)
    evidence: _CompanionEvidence
    confidence: float = Field(default=0.78, ge=0.0, le=1.0)
    session_id: str | None = Field(default=None)
    plan_id: str | None = Field(default=None)


class GetSelfRevisionHistoryParams(BaseModel):
    session_id: str | None = Field(default=None)
    plan_id: str | None = Field(default=None)
    limit: int = Field(default=10, ge=1, le=20)


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


def _runtime_redis(db_session: Any):
    runtime_context = get_tool_runtime_context(db_session)
    return runtime_context.get("redis_client") or cache_service.redis


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


class GetCompanionStateTool(BaseTool):
    name = "get_companion_state"
    description = "Read Sparkle's effective companion state and recent self-revision history."
    category = ToolCategory.QUERY
    parameters_schema = GetCompanionStateParams

    async def execute(
        self,
        params: GetCompanionStateParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        user_uuid = UUID(user_id)
        identifiers = _resolve_runtime_identifiers(db_session, params.session_id, params.plan_id)
        service = CompanionStateService(db_session, redis=_runtime_redis(db_session))

        data = {
            "effective_companion_state": await service.get_effective_state(
                user_uuid,
                plan_id=identifiers["plan_id"],
                session_id=identifiers["session_id"],
            ),
        }
        if params.include_relationship_profile:
            data["relationship_profile"] = await service.get_relationship_profile(user_uuid)
        if params.include_recent_revisions:
            data["recent_revisions"] = await service.get_self_revision_history(
                user_uuid,
                plan_id=identifiers["plan_id"],
                session_id=identifiers["session_id"],
            )
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data=data)


class AdjustCompanionStateTool(BaseTool):
    name = "adjust_companion_state"
    description = "Adjust Sparkle's session-level companion stance with evidence and audit logging."
    category = ToolCategory.QUERY
    parameters_schema = AdjustCompanionStateParams

    async def execute(
        self,
        params: AdjustCompanionStateParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        if params.field not in COMPANION_SESSION_WRITE_FIELDS:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=f"Unsupported companion field: {params.field}",
                error_type="invalid_field",
            )
        try:
            identifiers = _resolve_runtime_identifiers(db_session, params.session_id, params.plan_id)
            if not identifiers["session_id"]:
                return _identifier_error_result(
                    self.name,
                    message="Companion session writes require a valid session_id in params or runtime context.",
                    error_type="missing_identifier",
                    tool_call_id=tool_call_id,
                )
            if identifiers["invalid_plan_id"]:
                return _identifier_error_result(
                    self.name,
                    message=f"Companion writes require a UUID plan_id when provided, got: {identifiers['raw_plan_id']}",
                    error_type="invalid_identifier",
                    tool_call_id=tool_call_id,
                )
            service = CompanionStateService(db_session, redis=_runtime_redis(db_session))
            data = await service.write_session_state(
                user_id=UUID(user_id),
                session_id=identifiers["session_id"],
                field=params.field,
                value=params.value,
                reason=params.reason,
                evidence=params.evidence.model_dump(),
                confidence=params.confidence,
                plan_id=identifiers["plan_id"],
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


class WriteCompanionGrowthNoteTool(BaseTool):
    name = "write_companion_growth_note"
    description = "Write a short audited growth note about Sparkle's current relational stance."
    category = ToolCategory.QUERY
    parameters_schema = WriteCompanionGrowthNoteParams

    async def execute(
        self,
        params: WriteCompanionGrowthNoteParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            identifiers = _resolve_runtime_identifiers(db_session, params.session_id, params.plan_id)
            if not identifiers["session_id"]:
                return _identifier_error_result(
                    self.name,
                    message="Companion growth notes require a valid session_id in params or runtime context.",
                    error_type="missing_identifier",
                    tool_call_id=tool_call_id,
                )
            if identifiers["invalid_plan_id"]:
                return _identifier_error_result(
                    self.name,
                    message=f"Companion growth notes require a UUID plan_id when provided, got: {identifiers['raw_plan_id']}",
                    error_type="invalid_identifier",
                    tool_call_id=tool_call_id,
                )
            service = CompanionStateService(db_session, redis=_runtime_redis(db_session))
            data = await service.write_companion_growth_note(
                user_id=UUID(user_id),
                session_id=identifiers["session_id"],
                note=params.note,
                reason=params.reason,
                evidence=params.evidence.model_dump(),
                confidence=params.confidence,
                plan_id=identifiers["plan_id"],
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


class WriteRelationshipNoteTool(BaseTool):
    name = "write_relationship_note"
    description = "Record an audited relationship note and promote it only when repeated evidence justifies it."
    category = ToolCategory.QUERY
    parameters_schema = WriteRelationshipNoteParams

    async def execute(
        self,
        params: WriteRelationshipNoteParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            identifiers = _resolve_runtime_identifiers(db_session, params.session_id, params.plan_id)
            if not identifiers["session_id"]:
                return _identifier_error_result(
                    self.name,
                    message="Relationship notes require a valid session_id in params or runtime context.",
                    error_type="missing_identifier",
                    tool_call_id=tool_call_id,
                )
            if identifiers["invalid_plan_id"]:
                return _identifier_error_result(
                    self.name,
                    message=f"Relationship notes require a UUID plan_id when provided, got: {identifiers['raw_plan_id']}",
                    error_type="invalid_identifier",
                    tool_call_id=tool_call_id,
                )
            service = CompanionStateService(db_session, redis=_runtime_redis(db_session))
            data = await service.write_relationship_note(
                user_id=UUID(user_id),
                session_id=identifiers["session_id"],
                note=params.note,
                note_kind=params.note_kind,
                reason=params.reason,
                evidence=params.evidence.model_dump(),
                confidence=params.confidence,
                plan_id=identifiers["plan_id"],
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


class GetSelfRevisionHistoryTool(BaseTool):
    name = "get_self_revision_history"
    description = "Read Sparkle's recent self-revision ledger across session, episode, and profile layers."
    category = ToolCategory.QUERY
    parameters_schema = GetSelfRevisionHistoryParams

    async def execute(
        self,
        params: GetSelfRevisionHistoryParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        identifiers = _resolve_runtime_identifiers(db_session, params.session_id, params.plan_id)
        service = CompanionStateService(db_session, redis=_runtime_redis(db_session))
        data = {
            "recent_revisions": await service.get_self_revision_history(
                UUID(user_id),
                plan_id=identifiers["plan_id"],
                session_id=identifiers["session_id"],
                limit=params.limit,
            )
        }
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data=data)
