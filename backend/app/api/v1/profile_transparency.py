import json
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.services.cognitive_service import CognitiveService
from app.services.memory_service import MemoryService
from app.services.persona_service import PersonaService
from app.services.personalization.preference_service import PreferenceService
from app.services.system_update_service import SystemUpdateService, build_system_update

router = APIRouter(prefix="/profile", tags=["profile"])


def _snippet(value: str, limit: int = 80) -> str:
    if not value:
        return ""
    return value if len(value) <= limit else f"{value[:limit - 1]}…"


def _response_style_from_depth(depth: float) -> str:
    if depth >= 0.7:
        return "detailed"
    if depth <= 0.3:
        return "concise"
    return "balanced"

def _source_score(source: str) -> float:
    mapping = {
        "user": 1.0,
        "mixed": 0.6,
        "system": 0.2,
    }
    return mapping.get(source, 0.5)


def _risk_score(risk: str) -> float:
    mapping = {
        "low": 0.1,
        "medium": 0.4,
        "high": 0.8,
    }
    return mapping.get(risk, 0.4)


def _field_score(field_type: str) -> float:
    mapping = {
        "preference": 1.0,
        "behavior": 0.4,
        "analysis": 0.2,
    }
    return mapping.get(field_type, 0.5)


def _editability_meta(
    *,
    source: str,
    confidence: float,
    risk_level: str,
    field_type: str,
    source_type: str = None,
) -> dict[str, Any]:
    """
    构建偏好项的可编辑性元数据

    Args:
        source: 数据来源 ("user", "system", "mixed")
        confidence: 置信度 (0-1)
        risk_level: 风险等级 ("low", "medium", "high")
        field_type: 字段类型 ("preference", "behavior", "analysis")
        source_type: 来源类型，用于前端显示
            - "explicit": 用户直接设置的偏好
            - "inferred": 系统推断的偏好
            - "collaborative": 协作校准的内容

    Returns:
        包含可编辑性元数据的字典
    """
    score = (
        0.4 * _source_score(source)
        + 0.3 * confidence
        - 0.2 * _risk_score(risk_level)
        + 0.1 * _field_score(field_type)
    )
    if score > 0.6:
        level = "editable"
    elif score >= 0.3:
        level = "warn"
    else:
        level = "readonly"

    reason_map = {
        "editable": "来源可信且风险较低，可直接修改",
        "warn": "建议提交修正，系统评估后采纳",
        "readonly": "基于系统分析，暂不支持修改",
    }

    # 自动推断 source_type（如果未显式指定）
    if source_type is None:
        if source == "user":
            source_type = "explicit"
        elif source == "system":
            source_type = "inferred"
        else:  # mixed
            source_type = "collaborative"

    # source_type 的用户友好标签
    source_type_labels = {
        "explicit": "用户设置",
        "inferred": "系统推断",
        "collaborative": "协作校准",
    }

    return {
        "level": level,
        "score": round(score, 2),
        "reason": reason_map[level],
        "source": source,
        "source_type": source_type,
        "source_type_label": source_type_labels.get(source_type, source_type),
        "risk_level": risk_level,
        "confidence": confidence,
        "field_type": field_type,
    }


class OnboardingRequest(BaseModel):
    learning_goal_type: str | None = None
    learning_goal: str | None = None
    learning_style: str | None = None
    study_time_minutes: int | None = Field(default=None, ge=5, le=360)
    knowledge_level: str | None = None
    response_depth: float | None = Field(default=None, ge=0.0, le=1.0)
    curiosity_preference: float | None = Field(default=None, ge=0.0, le=1.0)


class CorrectionRequest(BaseModel):
    target_type: str
    target_id: str | None = None
    field_name: str | None = None
    suggested_value: str | None = None
    reason: str | None = None


class PreferenceUpdateRequest(BaseModel):
    pref_key: str
    value: Any


class PreferenceRollbackRequest(BaseModel):
    pref_key: str


class GoalUpdateRequest(BaseModel):
    goal_id: UUID
    title: str | None = None
    status: str | None = None
    target_date: date | None = None


def _coerce_preference_value(pref_key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, (int, float)):
        return {"value": value}
    if isinstance(value, str):
        stripped = value.strip()
        if pref_key == "study_time_preference" and stripped.isdigit():
            return {"minutes": int(stripped)}
        if stripped.replace(".", "", 1).isdigit():
            if "." in stripped:
                return {"value": float(stripped)}
            return {"value": int(stripped)}
        return {"value": stripped}
    return {"value": str(value)}


@router.get("/transparent")
async def get_profile_transparent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    memory_service = MemoryService(db)
    persona_service = PersonaService(db, cache_service.redis)
    cognitive_service = CognitiveService(db)

    preferences = await memory_service.list_preference_records(current_user.id)
    goals = await memory_service.list_active_goals(current_user.id)
    persona = await persona_service.get_snapshot(current_user.id, "transparency_view")
    patterns = await cognitive_service.get_user_patterns(current_user.id, min_confidence=0.6)
    fragments = await cognitive_service.get_fragments(current_user.id, limit=5)

    layer_1 = {
        "preferences": [
            {
                "id": str(item.id),
                "key": item.pref_key,
                "value": item.pref_value,
                "confidence": item.confidence,
                "version": item.version,
                "can_rollback": item.version > 1,
                "updated_at": item.updated_at,
                "metadata": _editability_meta(
                    source="user",
                    confidence=float(item.confidence or 0.9),
                    risk_level="low",
                    field_type="preference",
                ),
            }
            for item in preferences
        ],
        "goals": [
            {
                "id": str(item.id),
                "title": item.title,
                "status": item.status,
                "target_date": item.target_date,
                "updated_at": item.updated_at,
                "metadata": _editability_meta(
                    source="user",
                    confidence=0.9,
                    risk_level="low",
                    field_type="preference",
                ),
            }
            for item in goals
        ],
    }

    layer_2 = {
        "persona": {
            "tags": [
                {
                    "value": tag,
                    "metadata": _editability_meta(
                        source="mixed",
                        confidence=0.6,
                        risk_level="medium",
                        field_type="behavior",
                    ),
                }
                for tag in persona.get("tags", [])
            ],
            "capabilities": [
                {
                    "key": k,
                    "value": v,
                    "metadata": _editability_meta(
                        source="mixed",
                        confidence=0.6,
                        risk_level="medium",
                        field_type="analysis",
                    ),
                }
                for k, v in (persona.get("capabilities") or {}).items()
            ],
            "meta": {
                "persona_version": persona.get("persona_version"),
                "last_update_event_id": persona.get("last_update_event_id"),
            },
        },
        "editable": False,
    }

    layer_3 = {
        "patterns": [
            {
                "id": str(item.id),
                "name": item.pattern_name,
                "type": item.pattern_type,
                "confidence": item.confidence_score,
                "description": item.description,
                "metadata": {
                    **_editability_meta(
                    source="system",
                    confidence=float(item.confidence_score or 0.0),
                    risk_level="high",
                    field_type="analysis",
                ),
                    "evidence_ids": item.evidence_ids or [],
                },
            }
            for item in patterns
        ],
        "fragments": [
            {
                "id": str(item.id),
                "content": _snippet(item.content),
                "source_type": item.source_type,
                "created_at": item.created_at,
                "metadata": _editability_meta(
                    source="system",
                    confidence=0.7,
                    risk_level="high",
                    field_type="analysis",
                ),
            }
            for item in fragments
        ],
    }

    return {
        "layer_1": layer_1,
        "layer_2": layer_2,
        "layer_3": layer_3,
    }


@router.get("/system-updates")
async def list_system_updates(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = SystemUpdateService(cache_service.redis)
    items = await service.list_updates(current_user.id, limit=limit, offset=offset)
    return {"items": items}


@router.post("/onboarding")
async def submit_onboarding(
    payload: OnboardingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    memory_service = MemoryService(db)
    pref_service = PreferenceService(db, cache_service.redis)

    evidence_refs = [
        {"type": "user_state", "id": "onboarding", "schema_version": "onboarding.v1"}
    ]

    updated: dict[str, Any] = {}
    explicit_updates: dict[str, Any] = {}

    if payload.learning_style:
        record = await memory_service.upsert_preference(
            current_user.id,
            "learning_style",
            {"value": payload.learning_style},
            evidence_refs,
            source_type="user_state",
        )
        if record:
            updated["learning_style"] = payload.learning_style

    if payload.knowledge_level:
        record = await memory_service.upsert_preference(
            current_user.id,
            "knowledge_level",
            {"value": payload.knowledge_level},
            evidence_refs,
            source_type="user_state",
        )
        if record:
            updated["knowledge_level"] = payload.knowledge_level

    if payload.study_time_minutes is not None:
        record = await memory_service.upsert_preference(
            current_user.id,
            "study_time_preference",
            {"minutes": payload.study_time_minutes},
            evidence_refs,
            source_type="user_state",
        )
        if record:
            updated["study_time_preference"] = payload.study_time_minutes

    if payload.response_depth is not None:
        explicit_updates["depth_preference"] = payload.response_depth
        record = await memory_service.upsert_preference(
            current_user.id,
            "depth_preference",
            {"value": payload.response_depth},
            evidence_refs,
            source_type="user_state",
        )
        if record:
            updated["depth_preference"] = payload.response_depth

        style = _response_style_from_depth(payload.response_depth)
        record = await memory_service.upsert_preference(
            current_user.id,
            "response_style",
            {"value": style},
            evidence_refs,
            source_type="user_state",
        )
        if record:
            updated["response_style"] = style

    if payload.curiosity_preference is not None:
        explicit_updates["curiosity_preference"] = payload.curiosity_preference
        record = await memory_service.upsert_preference(
            current_user.id,
            "curiosity_preference",
            {"value": payload.curiosity_preference},
            evidence_refs,
            source_type="user_state",
        )
        if record:
            updated["curiosity_preference"] = payload.curiosity_preference

    if payload.learning_goal:
        metadata: dict[str, Any] | None = None
        if payload.learning_goal_type:
            metadata = {"goal_type": payload.learning_goal_type}
        record = await memory_service.create_goal(
            current_user.id,
            payload.learning_goal,
            metadata=metadata,
            evidence_refs=evidence_refs,
            source_type="user_state",
        )
        if record:
            updated["learning_goal"] = payload.learning_goal

    if explicit_updates:
        await pref_service.update_explicit(current_user.id, explicit_updates)

    return {"status": "ok", "updated": updated}


@router.put("/preferences")
async def update_preference(
    payload: PreferenceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not payload.pref_key:
        return {"status": "error", "message": "pref_key required"}

    memory_service = MemoryService(db)
    evidence_refs = [
        {"type": "user_state", "id": "manual_edit", "schema_version": "manual_edit.v1"}
    ]
    value_payload = _coerce_preference_value(payload.pref_key, payload.value)
    record = await memory_service.upsert_preference(
        current_user.id,
        payload.pref_key,
        value_payload,
        evidence_refs,
        source_type="user_state",
    )
    if record is None:
        return {"status": "blocked"}
    return {"status": "ok", "version": record.version}


@router.post("/preferences/rollback")
async def rollback_preference(
    payload: PreferenceRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not payload.pref_key:
        return {"status": "error", "message": "pref_key required"}

    memory_service = MemoryService(db)
    history = await memory_service.list_preference_history(current_user.id)
    candidates = [item for item in history if item.pref_key == payload.pref_key]
    if len(candidates) < 2:
        return {"status": "error", "message": "no previous version"}

    current = candidates[0]
    previous = candidates[1]
    evidence_refs = [
        {"type": "user_state", "id": "rollback", "schema_version": "rollback.v1"}
    ]
    record = await memory_service.upsert_preference(
        current_user.id,
        payload.pref_key,
        previous.pref_value,
        evidence_refs,
        source_type="user_state",
    )
    if record is None:
        return {"status": "blocked"}
    return {
        "status": "ok",
        "from_version": current.version,
        "to_version": previous.version,
        "new_version": record.version,
    }


@router.put("/goals")
async def update_goal(
    payload: GoalUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    memory_service = MemoryService(db)
    updates: dict[str, Any] = {}
    if payload.title is not None:
        updates["title"] = payload.title
    if payload.status is not None:
        updates["status"] = payload.status
    if payload.target_date is not None:
        updates["target_date"] = payload.target_date

    if not updates:
        return {"status": "error", "message": "no updates"}

    record = await memory_service.update_goal(current_user.id, payload.goal_id, **updates)
    if record is None:
        return {"status": "error", "message": "goal not found"}

    await SystemUpdateService(cache_service.redis).enqueue(
        current_user.id,
        build_system_update(
            update_type="memory_goal_updated",
            category="goal",
            title=f"更新了目标：{_snippet(record.title)}",
            description="学习目标已更新",
            priority="medium",
            metadata={
                "goal_id": str(record.id),
                "status": record.status,
            },
        ),
    )
    return {"status": "ok"}


@router.post("/corrections")
async def submit_correction(
    payload: CorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.models.memory import MemoryCorrection

    if not payload.target_type:
        return {"status": "error", "message": "target_type required"}

    correction = MemoryCorrection(
        user_id=current_user.id,
        memory_type=payload.target_type,
        memory_id=current_user.id,
        action="suggest_update",
        reason=json.dumps(
            {
                "target_id": payload.target_id,
                "field_name": payload.field_name,
                "suggested_value": payload.suggested_value,
                "reason": payload.reason,
            },
            ensure_ascii=True,
        ),
    )
    db.add(correction)
    await db.commit()
    await SystemUpdateService(cache_service.redis).enqueue(
        current_user.id,
        build_system_update(
            update_type="correction_received",
            category="cognitive",
            title="收到你的修正建议",
            description="系统将评估并逐步调整画像",
            priority="medium",
            metadata={
                "target_type": payload.target_type,
                "field_name": payload.field_name,
            },
        ),
    )
    return {"status": "ok"}
