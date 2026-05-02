from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.aurora.runtime_v1.self_model import SparkleSelfModelService
from app.core.cache import cache_service
from app.models.user import User
from app.services.aurora_control_surface_service import AuroraControlSurfaceService

router = APIRouter(prefix="/experience", tags=["experience"])

CorrectionEffectScope = Literal[
    "memory_claim",
    "routing_policy",
    "task_granularity",
    "plan_risk",
    "knowledge_bottleneck",
    "wake_policy",
]


class UnderstandingCorrectionRequest(BaseModel):
    claim: str = Field(..., min_length=1, max_length=600)
    correction: str = Field(..., min_length=1, max_length=1000)
    effect_scope: CorrectionEffectScope


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"


def _scope_label(scope: str) -> str:
    labels = {
        "daily_available_time": "学习习惯",
        "task_duration_fit": "学习习惯",
        "task_difficulty_fit": "能力水平",
        "pressure_level_fit": "情绪模式",
        "emotional_state_fit": "情绪模式",
        "current_sprint": "当前阶段",
        "strategy": "策略偏好",
        "user_pair": "协作模式",
    }
    return labels.get(scope, scope or "策略偏好")


def _claim_payload(item: dict[str, Any]) -> dict[str, Any]:
    statement = _strip(item.get("statement") or item.get("claim"))
    assumption_id = _strip(item.get("assumption_id") or item.get("claim_id") or statement[:32])
    confidence = max(0.0, min(1.0, _safe_float(item.get("confidence"), default=0.0)))
    evidence_items = [
        _strip(_as_dict(evidence).get("detail") or evidence)
        for evidence in _as_list(item.get("evidence"))
        if _strip(_as_dict(evidence).get("detail") or evidence)
    ]
    if evidence_items:
        evidence_summary = evidence_items[-1]
    else:
        evidence_summary = "基于近期任务执行、纠正记录和上下文命中情况。"
    return {
        "claim_id": assumption_id,
        "claim": statement,
        "confidence": round(confidence, 4),
        "confidence_label": _confidence_label(confidence),
        "evidence_summary": evidence_summary,
        "scope": _scope_label(assumption_id or _strip(item.get("scope"))),
        "raw_scope": assumption_id or _strip(item.get("scope")),
        "user_can_correct": True,
    }


def _memory_declarations(snapshot: dict[str, Any], self_model: dict[str, Any]) -> list[dict[str, str]]:
    declarations: list[dict[str, str]] = []
    for reference in _as_list(snapshot.get("memory_references"))[:4]:
        content = _strip(reference)
        if content:
            declarations.append(
                {
                    "type": "profile_context",
                    "content": content,
                    "persistence": "可被你纠正；用于当前目标、任务粒度和对话风格。",
                }
            )
    harness = _as_dict(self_model.get("harness_effectiveness"))
    task_shape = _strip(harness.get("task_shape"))
    if task_shape:
        declarations.append(
            {
                "type": "task_shape",
                "content": f"当前任务粒度判断：{task_shape}",
                "persistence": "短期策略读数，会随完成/放弃/纠正继续更新。",
            }
        )
    return declarations


def _recently_corrected(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    effect = _as_dict(snapshot.get("last_correction_effect"))
    if not effect.get("visible"):
        return []
    claim = _strip(effect.get("semantic_value") or effect.get("action") or "用户纠正")
    return [
        {
            "claim": claim,
            "correction": _strip(effect.get("action")) or "已按你的反馈重新校准。",
            "effect_on_policy": _as_list(effect.get("affected_state_keys")),
        }
    ]


def _envelope_style(snapshot: dict[str, Any], self_model: dict[str, Any]) -> dict[str, str]:
    task_health = _as_dict(snapshot.get("task_health"))
    harness = _as_dict(self_model.get("harness_effectiveness"))
    task_shape = _strip(harness.get("task_shape"))
    needs_recalibration = bool(self_model.get("needs_recalibration"))
    if needs_recalibration:
        tone = "校准优先"
        verbosity = "先确认，再推进"
        reason = "最近的纠正或执行信号提示 Sparkle 需要降低自信并确认假设。"
    elif task_health.get("needs_attention") or task_shape == "struggling":
        tone = "更稳、更具体"
        verbosity = "拆小步骤"
        reason = "任务推进信号显示当前更适合小步确认。"
    else:
        tone = "温和直接"
        verbosity = "中等简洁"
        reason = "当前策略命中率和任务节奏读数相对稳定。"
    return {
        "current_tone": tone,
        "current_verbosity": verbosity,
        "reason_for_style": reason,
    }


async def _store_correction_effect(
    *,
    user_id: str,
    claim: str,
    correction: str,
    effect_scope: str,
) -> dict[str, Any]:
    effect = {
        "visible": True,
        "semantic_value": effect_scope,
        "action": "understanding_snapshot_correction",
        "claim": claim,
        "correction": correction,
        "affected_state_keys": [effect_scope],
        "updated_at": _utcnow_iso(),
    }
    redis = cache_service.redis
    if redis is not None:
        await redis.set(
            f"aurora:last_correction_effect:{user_id}",
            json.dumps(effect, ensure_ascii=False),
        )
        await redis.expire(f"aurora:last_correction_effect:{user_id}", 24 * 3600)
    return effect


# route-tier: authed
@router.get("/understanding-snapshot")
async def get_understanding_snapshot(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Expose the user-facing self-model readout without internal debug values."""
    redis = cache_service.redis
    service = SparkleSelfModelService(redis, db_session=db)
    self_model = await service.get_readout_summary(user_id=str(current_user.id))
    control_snapshot = await AuroraControlSurfaceService(db, redis).build_snapshot(
        user_id=current_user.id,
    )
    assumptions = [_claim_payload(item) for item in _as_list(self_model.get("known_assumptions"))]
    high_confidence_count = sum(1 for item in assumptions if item["confidence"] >= 0.75)
    total_claims = len(assumptions)

    return {
        "claims": assumptions,
        "recently_corrected": _recently_corrected(control_snapshot),
        "memory_declarations": _memory_declarations(control_snapshot, self_model),
        "envelope_style": _envelope_style(control_snapshot, self_model),
        "last_update_time": _strip(control_snapshot.get("updated_at")) or _utcnow_iso(),
        "total_claims": total_claims,
        "high_confidence_ratio": round(high_confidence_count / total_claims, 4) if total_claims else 0.0,
    }


# route-tier: authed
@router.post("/understanding-snapshot/corrections")
async def correct_understanding_snapshot(
    request: UnderstandingCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record a user correction and return the visible policy effect."""
    correction_id = f"understanding_snapshot:{uuid4().hex}"
    reason = f"{request.claim} → {request.correction} [{request.effect_scope}]"
    service = SparkleSelfModelService(cache_service.redis, db_session=db)
    await service.record_user_correction(
        user_id=str(current_user.id),
        signal_id=correction_id,
        reason=reason,
        source="understanding_snapshot",
    )
    effect = await _store_correction_effect(
        user_id=str(current_user.id),
        claim=request.claim,
        correction=request.correction,
        effect_scope=request.effect_scope,
    )
    return {
        "status": "updated",
        "correction_id": correction_id,
        "effect_on_policy": effect["affected_state_keys"],
        "message": "已更新 Sparkle 对你的理解。",
    }
