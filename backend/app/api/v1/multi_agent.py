"""
Multi-Agent API - 多智能体协作API

提供多专家智能体协作服务
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator_agent import create_multi_agent_workflow
from app.api.deps import get_current_user
from app.config import settings
from app.core.agent_capability_registry import (
    get_capability_catalog,
    get_expert_capability_catalog,
)
from app.core.cache import cache_service
from app.db.session import get_db
from app.gen.agent.v1 import agent_service_pb2
from app.models.user import User
from app.orchestration.chat_modes import (
    CHAT_MODE_EXPERT_AUTO,
    CHAT_MODE_EXPERT_PREFIX,
    CHAT_MODE_STANDARD,
    normalize_chat_mode,
)
from app.orchestration.expert_strategy import ExpertStrategyV1, parse_selected_experts
from app.orchestration.expert_strategy_v2 import ExpertStrategyV2
from app.orchestration.orchestrator import ChatOrchestrator
from app.services.expert_policy_report_service import ExpertPolicyReportService

router = APIRouter(prefix="/multi-agent", tags=["multi-agent"])

_http_orchestrator: ChatOrchestrator | None = None


class MultiAgentRequest(BaseModel):
    """多智能体请求"""

    query: str
    session_id: str
    enable_trace: bool = True
    chat_mode: str = CHAT_MODE_EXPERT_AUTO


class MultiAgentResponse(BaseModel):
    """多智能体响应"""

    response_text: str
    agent_role: str
    agent_name: str

    # 可选字段
    reasoning: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] | None = None

    # 追踪信息
    trace: dict[str, Any] | None = None


def _resolve_workflow_id(chat_mode: str) -> str:
    mode = normalize_chat_mode(chat_mode)
    if mode == CHAT_MODE_STANDARD:
        return "standard_chat"
    if mode == "deep_analysis":
        return "deep_analysis_workflow"
    if mode == "study_plan":
        return "study_plan_workflow"
    if mode == "error_diagnosis":
        return "error_diagnosis_workflow"
    if mode == CHAT_MODE_EXPERT_AUTO:
        return "expert_auto_workflow"
    if mode.startswith(CHAT_MODE_EXPERT_PREFIX):
        expert_id = mode[len(CHAT_MODE_EXPERT_PREFIX):].strip() or "unknown"
        return f"expert_{expert_id}_workflow"
    return f"{mode}_workflow"


def _get_http_orchestrator() -> ChatOrchestrator:
    global _http_orchestrator
    if _http_orchestrator is not None:
        return _http_orchestrator
    if cache_service.redis is None:
        raise RuntimeError("redis_client_not_ready")
    _http_orchestrator = ChatOrchestrator(redis_client=cache_service.redis)
    return _http_orchestrator


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None


def _extract_strategy_pack(policy_id: str) -> str:
    value = str(policy_id or "")
    if ":" not in value:
        return "default"
    rest = value.split(":", 1)[1]
    if ":candidate_" in rest:
        return rest.split(":candidate_", 1)[0]
    if ":" in rest:
        return rest.split(":", 1)[0]
    return rest
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_trace_payload(
    *,
    workflow_id: str,
    metadata: dict[str, Any],
    confidence: float | None,
) -> dict[str, Any]:
    selected_experts = parse_selected_experts(metadata.get("selected_experts"))
    return {
        "workflow_type": workflow_id,
        "agents_involved": selected_experts,
        "is_multi_agent": len(selected_experts) > 1,
        "confidence": confidence if confidence is not None else 0.0,
        "routing_strategy": metadata.get("routing_strategy", ""),
        "fallback_reason": metadata.get("fallback_reason", ""),
    }


@router.post("/chat", response_model=MultiAgentResponse)
async def multi_agent_chat(
    request: MultiAgentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Multi-agent chat endpoint with backward-compatible response shape.

    Default path keeps the external API stable while redirecting execution to the
    unified ChatOrchestrator + LangGraph chain.
    """

    logger.info("Multi-agent request from user %s: %s", current_user.id, request.query[:80])

    if not settings.ENABLE_LEGACY_MULTI_AGENT_REDIRECT:
        try:
            workflow = create_multi_agent_workflow()
            result = await workflow.execute(
                user_query=request.query,
                user_id=str(current_user.id),
                session_id=request.session_id,
            )
        except Exception as exc:
            logger.error("Legacy multi-agent error: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Multi-agent processing failed: {exc}") from exc

        trace = None
        if request.enable_trace:
            trace = {
                "workflow_type": "multi_agent_legacy",
                "agents_involved": result.get("metadata", {}).get("agents_involved", [result.get("agent_name", "")]),
                "is_multi_agent": result.get("metadata", {}).get("multi_agent", False),
                "confidence": result.get("confidence", 0.8),
            }
        return MultiAgentResponse(
            response_text=result["response_text"],
            agent_role=result["agent_role"],
            agent_name=result["agent_name"],
            reasoning=result.get("reasoning"),
            confidence=result.get("confidence"),
            metadata=result.get("metadata"),
            trace=trace,
        )

    try:
        orchestrator = _get_http_orchestrator()
    except Exception as exc:
        logger.error("Unified orchestrator init failed: %s", exc)
        raise HTTPException(status_code=503, detail="Unified orchestrator is unavailable") from exc

    mode = normalize_chat_mode(request.chat_mode or CHAT_MODE_EXPERT_AUTO)
    workflow_id = _resolve_workflow_id(mode)
    grpc_request = agent_service_pb2.ChatRequest(
        request_id=f"http_{uuid.uuid4().hex}",
        user_id=str(current_user.id),
        session_id=request.session_id,
        message=request.query,
        chat_mode=mode,
    )

    full_text = ""
    delta_parts: list[str] = []
    response_metadata: dict[str, Any] = {}

    try:
        async for item in orchestrator.process_stream(
            grpc_request,
            db_session=db,
            context_data={
                "chat_mode": mode,
                "workflow_id": workflow_id,
                "prompt_version": "v1",
            },
        ):
            if item.HasField("error"):
                raise RuntimeError(item.error.message or "multi-agent processing failed")
            if item.full_text:
                full_text = item.full_text
            if item.delta:
                delta_parts.append(item.delta)
            if item.metadata:
                response_metadata.update(dict(item.metadata))
    except Exception as exc:
        logger.error("Unified multi-agent error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Multi-agent processing failed: {exc}") from exc

    response_text = full_text or "".join(delta_parts)
    selected_experts = parse_selected_experts(response_metadata.get("selected_experts"))
    agent_name = selected_experts[0] if selected_experts else "orchestrator"
    agent_role = "specialist" if selected_experts else "orchestrator"
    confidence = _coerce_float(response_metadata.get("route_confidence"))
    trace = _build_trace_payload(workflow_id=workflow_id, metadata=response_metadata, confidence=confidence) if request.enable_trace else None

    normalized_metadata: dict[str, Any] = dict(response_metadata)
    if selected_experts:
        normalized_metadata["selected_experts"] = selected_experts

    return MultiAgentResponse(
        response_text=response_text,
        agent_role=agent_role,
        agent_name=agent_name,
        reasoning=str(response_metadata.get("routing_strategy", "")) or None,
        confidence=confidence,
        metadata=normalized_metadata,
        trace=trace,
    )


@router.get("/agents")
async def list_agents(current_user: User = Depends(get_current_user)):
    """列出可用公开专家（由统一能力注册层提供）"""

    _ = current_user
    experts = list(get_expert_capability_catalog())
    return {
        "total_agents": len(experts),
        "agents": [
            {
                "type": expert["id"],
                "name": expert["display_name"],
                "role": expert["id"],
                "description": expert["description"],
                "capabilities": expert.get("tags", []),
                "entry_chat_mode": expert["entry_chat_mode"],
                "enabled": bool(expert.get("enabled", False)),
                "rank": int(expert.get("rank", 999)),
            }
            for expert in experts
        ],
    }


@router.post("/route-preview")
async def preview_routing(
    request: MultiAgentRequest,
    current_user: User = Depends(get_current_user),
):
    """路由预览（主链策略结果）"""

    _ = current_user
    mode = normalize_chat_mode(request.chat_mode or CHAT_MODE_EXPERT_AUTO)
    if settings.ENABLE_EXPERT_STRATEGY_V2:
        strategy_cls = ExpertStrategyV2
        decision = strategy_cls.route(
            message=request.query,
            chat_mode=mode,
            user_preferences={},
            user_context={},
            session_weight=float(getattr(settings, "EXPERT_AFFINITY_SESSION_WEIGHT", 0.65)),
            long_term_weight=float(getattr(settings, "EXPERT_AFFINITY_LONG_TERM_WEIGHT", 0.35)),
        )
        score_rows = strategy_cls.score_experts(
            message=request.query,
            chat_mode=mode,
            user_preferences={},
            user_context={},
            session_weight=float(getattr(settings, "EXPERT_AFFINITY_SESSION_WEIGHT", 0.65)),
            long_term_weight=float(getattr(settings, "EXPERT_AFFINITY_LONG_TERM_WEIGHT", 0.35)),
        )
    else:
        strategy_cls = ExpertStrategyV1
        decision = strategy_cls.route(message=request.query, chat_mode=mode, user_preferences={}, user_context={})
        score_rows = strategy_cls.score_experts(message=request.query, user_preferences={})

    selected = set(decision.selected_experts)
    all_scores = []
    for row in score_rows:
        expert_id = str(row.get("expert_id", ""))
        score_value = row.get("final_score", row.get("score", 0.0))
        all_scores.append(
            {
                "agent_name": row.get("display_name", expert_id),
                "agent_type": expert_id,
                "confidence": round(float(score_value), 4),
                "selected": expert_id in selected,
            }
        )

    return {
        "query": request.query,
        "chat_mode": mode,
        "policy_id": decision.policy_id,
        "strategy_pack": _extract_strategy_pack(decision.policy_id),
        "routing_decision": [
            {"name": expert_id, "type": expert_id}
            for expert_id in decision.selected_experts
        ],
        "route_confidence": decision.route_confidence,
        "fallback_reason": decision.fallback_reason,
        "all_scores": all_scores,
    }


@router.get("/catalog")
async def get_multi_agent_catalog(current_user: User = Depends(get_current_user)):
    """Unified catalog for public multi-agent modes and experts."""

    _ = current_user
    if not settings.ENABLE_EXPERT_ENTRY:
        return {
            "modes": [],
            "experts": [],
            "total_experts": 0,
        }
    return get_capability_catalog()


@router.get("/policy-report")
async def get_expert_policy_report(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
):
    """Quality report for expert policy governance (7/14-day operational view)."""

    _ = current_user
    service = ExpertPolicyReportService()
    report = await service.build_report(days=days)
    return report
