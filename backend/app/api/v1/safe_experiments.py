from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.core.cache import cache_service
from app.core.metrics import SAFE_EXPERIMENT_EPISODES_TOTAL, SAFE_EXPERIMENT_TRANSITIONS_TOTAL
from app.models.safe_experiment import SafeExperiment, SafeExperimentEpisode
from app.models.user import User
from app.models.user_settings import UserSettings
from app.signals.safe_experiment_platform import (
    ExperimentDesignValidator,
    ExperimentGuardrails,
    RewardModel,
    SafePolicyExperiment,
)
from app.signals.safe_experiment_promotion_gate import (
    enqueue_promotion_candidate,
    evaluate_safe_experiment_promotion,
)

router = APIRouter(tags=["safe-experiments"])


class SafeExperimentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    hypothesis: str = Field(..., min_length=1)
    domain: str = Field(..., max_length=80)
    eligible_context: dict[str, Any] = Field(default_factory=dict)
    excluded_context: list[str] = Field(default_factory=lambda: ["D0_exam_day", "fatigue_critical"])
    policies: list[dict[str, Any]] = Field(..., min_length=2)
    assignment_mode: str = "shadow"
    reward_model: dict[str, Any] = Field(default_factory=dict)
    guardrails: dict[str, Any] = Field(default_factory=dict)
    min_episodes: int = Field(50, ge=1)
    min_distinct_users: int = Field(15, ge=1)
    evidence_grade_required: int = Field(3, ge=1, le=5)
    rollback_version: str | None = None
    previous_versions: list[dict[str, Any]] = Field(default_factory=list)


class SafeExperimentUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    hypothesis: str | None = None
    domain: str | None = Field(None, max_length=80)
    eligible_context: dict[str, Any] | None = None
    excluded_context: list[str] | None = None
    policies: list[dict[str, Any]] | None = None
    guardrails: dict[str, Any] | None = None
    min_episodes: int | None = Field(None, ge=1)
    min_distinct_users: int | None = Field(None, ge=1)
    rollback_version: str | None = None


class SafeExperimentTransitionRequest(BaseModel):
    target_status: str
    reason: str = ""


class SafeExperimentEpisodeRequest(BaseModel):
    user_id: UUID | None = None
    context_signature: dict[str, Any] = Field(default_factory=dict)
    candidate_actions: list[str] = Field(default_factory=list)
    selected_action: str
    selection_reason: str = ""
    assignment_mode: str = "shadow"
    risk_level: str = "low"
    reward: float | None = None
    outcome_vector: dict[str, Any] = Field(default_factory=dict)


class SafeExperimentOptOutRequest(BaseModel):
    opted_out: bool


class SafeExperimentResponse(BaseModel):
    id: UUID
    experiment_key: str
    name: str
    hypothesis: str
    domain: str
    status: str
    eligible_context: dict[str, Any]
    excluded_context: list[str]
    policies: list[dict[str, Any]]
    assignment_mode: str
    reward_model: dict[str, Any]
    guardrails: dict[str, Any]
    min_episodes: int
    min_distinct_users: int
    evidence_grade_required: int
    current_episodes: int
    distinct_users: list[str]
    rollback_version: str | None
    kill_switch_key: str
    incident_trace: list[dict[str, Any]]
    promotion_candidate: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SafeExperimentEpisodeResponse(BaseModel):
    id: UUID
    experiment_key: str
    selected_action: str
    selection_reason: str
    assignment_mode: str
    risk_level: str
    reward: float | None
    guardrail_result: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


def _reward_model(payload: dict[str, Any] | None) -> RewardModel:
    payload = payload or {}
    return RewardModel(
        primary=payload.get("primary") or RewardModel().primary,
        guardrails=payload.get("guardrails") or RewardModel().guardrails,
        secondary=payload.get("secondary") or RewardModel().secondary,
    )


def _guardrails(payload: dict[str, Any] | None) -> ExperimentGuardrails:
    allowed = set(ExperimentGuardrails.__dataclass_fields__)
    return ExperimentGuardrails(**{k: v for k, v in (payload or {}).items() if k in allowed})


def _to_policy_experiment(record: SafeExperiment) -> SafePolicyExperiment:
    return SafePolicyExperiment(
        experiment_id=record.experiment_key,
        name=record.name,
        hypothesis=record.hypothesis,
        domain=record.domain,
        status=record.status,
        eligible_context=record.eligible_context or {},
        excluded_context=record.excluded_context or [],
        policies=record.policies or [],
        assignment_mode=record.assignment_mode,
        reward_model=_reward_model(record.reward_model),
        guardrails=_guardrails(record.guardrails),
        min_episodes=record.min_episodes,
        min_distinct_users=record.min_distinct_users,
        evidence_grade_required=record.evidence_grade_required,
        current_episodes=record.current_episodes,
        distinct_users=record.distinct_users or [],
        outcome_history=record.outcome_history or [],
        rollback_version=record.rollback_version or "",
        previous_versions=record.previous_versions or [],
        kill_switch_key=record.kill_switch_key,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else "",
    )


async def _get_experiment(db: AsyncSession, experiment_key: str, current_user: User) -> SafeExperiment:
    query = select(SafeExperiment).where(
        SafeExperiment.experiment_key == experiment_key,
        SafeExperiment.not_deleted_filter(),
    )
    if not current_user.is_superuser:
        query = query.where(SafeExperiment.created_by == current_user.id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Safe experiment not found")
    return record


# route-tier: internal
@router.post("/", response_model=SafeExperimentResponse)
async def create_safe_experiment(
    payload: SafeExperimentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    draft = SafePolicyExperiment(
        name=payload.name,
        hypothesis=payload.hypothesis,
        domain=payload.domain,
        eligible_context=payload.eligible_context,
        excluded_context=payload.excluded_context,
        policies=payload.policies,
        assignment_mode=payload.assignment_mode,
        reward_model=_reward_model(payload.reward_model),
        guardrails=_guardrails(payload.guardrails),
        min_episodes=payload.min_episodes,
        min_distinct_users=payload.min_distinct_users,
        evidence_grade_required=payload.evidence_grade_required,
        rollback_version=payload.rollback_version or "",
        previous_versions=payload.previous_versions,
    )
    validation = ExperimentDesignValidator.validate(draft)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail={"issues": validation["issues"]})

    record = SafeExperiment(
        experiment_key=draft.experiment_id,
        name=draft.name,
        hypothesis=draft.hypothesis,
        domain=draft.domain,
        status=draft.status,
        eligible_context=draft.eligible_context,
        excluded_context=draft.excluded_context,
        policies=draft.policies,
        assignment_mode=draft.assignment_mode,
        reward_model=draft.reward_model.to_dict(),
        guardrails=draft.guardrails.to_dict(),
        min_episodes=draft.min_episodes,
        min_distinct_users=draft.min_distinct_users,
        evidence_grade_required=draft.evidence_grade_required,
        current_episodes=0,
        distinct_users=[],
        outcome_history=[],
        rollback_version=draft.rollback_version,
        previous_versions=draft.previous_versions,
        kill_switch_key=draft.kill_switch_key,
        incident_trace=[],
        created_by=current_user.id,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


# route-tier: internal
@router.get("/", response_model=list[SafeExperimentResponse])
async def list_safe_experiments(
    status: str | None = Query(None),
    domain: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(SafeExperiment).where(SafeExperiment.not_deleted_filter())
    if status:
        query = query.where(SafeExperiment.status == status)
    if domain:
        query = query.where(SafeExperiment.domain == domain)
    if not current_user.is_superuser:
        query = query.where(SafeExperiment.created_by == current_user.id)
    query = query.order_by(SafeExperiment.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


# route-tier: internal
@router.get("/{experiment_key}", response_model=SafeExperimentResponse)
async def get_safe_experiment(
    experiment_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_experiment(db, experiment_key, current_user)


# route-tier: internal
@router.patch("/{experiment_key}", response_model=SafeExperimentResponse)
async def update_safe_experiment(
    experiment_key: str,
    payload: SafeExperimentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    record = await _get_experiment(db, experiment_key, current_user)
    if record.status not in {"draft", "paused"}:
        raise HTTPException(status_code=409, detail="Only draft or paused experiments can be edited")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    validation = ExperimentDesignValidator.validate(_to_policy_experiment(record))
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail={"issues": validation["issues"]})
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


# route-tier: internal
@router.delete("/{experiment_key}")
async def delete_safe_experiment(
    experiment_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    record = await _get_experiment(db, experiment_key, current_user)
    record.soft_delete()
    db.add(record)
    return {"status": "deleted", "experiment_key": experiment_key}


# route-tier: internal
@router.post("/{experiment_key}/transition", response_model=SafeExperimentResponse)
async def transition_safe_experiment(
    experiment_key: str,
    payload: SafeExperimentTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    record = await _get_experiment(db, experiment_key, current_user)
    before = record.status
    policy_exp = _to_policy_experiment(record)
    ok, message = policy_exp.transition_to(payload.target_status)
    SAFE_EXPERIMENT_TRANSITIONS_TOTAL.labels(before, payload.target_status, "accepted" if ok else "rejected").inc()
    if not ok:
        raise HTTPException(status_code=409, detail=message)

    record.status = policy_exp.status
    record.incident_trace = [
        *(record.incident_trace or []),
        {
            "type": "lifecycle_transition",
            "from": before,
            "to": record.status,
            "reason": payload.reason,
            "message": message,
            "at": policy_exp.updated_at,
        },
    ]
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


# route-tier: internal
@router.post("/{experiment_key}/episodes", response_model=SafeExperimentEpisodeResponse)
async def record_safe_experiment_episode(
    experiment_key: str,
    payload: SafeExperimentEpisodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    from app.signals.intervention_episode import OutcomeVector

    record = await _get_experiment(db, experiment_key, current_user)
    policy_exp = _to_policy_experiment(record)
    outcome = OutcomeVector.from_dict(payload.outcome_vector)
    guardrail_result = policy_exp.record_outcome(str(payload.user_id or current_user.id), outcome)
    record.current_episodes = policy_exp.current_episodes
    record.distinct_users = policy_exp.distinct_users
    record.outcome_history = policy_exp.outcome_history[-200:]
    record.status = policy_exp.status
    if guardrail_result.get("violations"):
        record.incident_trace = [
            *(record.incident_trace or []),
            {"type": "guardrail_violation", "result": guardrail_result, "source": "episode_record"},
        ]
    episode = SafeExperimentEpisode(
        experiment_id=record.id,
        experiment_key=record.experiment_key,
        user_id=payload.user_id or current_user.id,
        context_signature=payload.context_signature,
        candidate_actions=payload.candidate_actions,
        selected_action=payload.selected_action,
        selection_reason=payload.selection_reason,
        assignment_mode=payload.assignment_mode,
        risk_level=payload.risk_level,
        reward=payload.reward,
        outcome_vector=payload.outcome_vector,
        guardrail_result=guardrail_result,
        incident_trace=record.incident_trace[-1] if guardrail_result.get("violations") else None,
    )
    db.add(record)
    db.add(episode)
    SAFE_EXPERIMENT_EPISODES_TOTAL.labels(record.status, payload.risk_level).inc()
    await db.flush()
    await db.refresh(episode)
    return episode


# route-tier: internal
@router.post("/{experiment_key}/promotion-candidate")
async def evaluate_promotion_candidate(
    experiment_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    record = await _get_experiment(db, experiment_key, current_user)
    result = evaluate_safe_experiment_promotion(record)
    if result.eligible and result.candidate_payload:
        record.promotion_candidate = result.candidate_payload
        await enqueue_promotion_candidate(cache_service.redis, result.candidate_payload)
        db.add(record)
    return result.to_dict()


# route-tier: internal
@router.get("/me/opt-out")
async def get_safe_experiment_opt_out(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = result.scalar_one_or_none()
    return {"opted_out": bool(settings and settings.safe_experiments_opt_out)}


# route-tier: internal
@router.post("/me/opt-out")
async def set_safe_experiment_opt_out(
    payload: SafeExperimentOptOutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=current_user.id)
    settings.safe_experiments_opt_out = payload.opted_out
    db.add(settings)
    if cache_service.redis is not None:
        await cache_service.redis.set(
            f"spine:safe_experiments:opt_out:{current_user.id}",
            "1" if payload.opted_out else "0",
            ex=30 * 24 * 3600,
        )
    return {"opted_out": payload.opted_out}
