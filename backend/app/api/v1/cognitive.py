"""
Cognitive Prism API
认知棱镜相关 API
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.cache import cache_service
from app.core.celery_app import get_celery_queue_status
from app.db.session import AsyncSessionLocal
from app.models.cognitive import BehaviorPattern
from app.models.user import User
from app.schemas.cognitive import BehaviorPatternResponse, CognitiveFragmentCreate, CognitiveFragmentResponse
from app.services.cognitive_service import CognitiveService
from app.services.evidence import EvidenceDirection, EvidenceSourceType, EvidenceTarget, FusionEngine, UnifiedEvidence
from app.services.glm_batch_service import glm_batch_service
from app.services.strategy_belief_service import strategy_belief_service

router = APIRouter()


class StrategyMigrationRequest(BaseModel):
    goal_id: UUID
    new_strategy_id: str = Field(min_length=1)


class StrategyMigrationResponse(BaseModel):
    goal_id: str
    previous_strategy_id: str
    new_strategy_id: str
    new_strategy_title: str
    migrated_at: str


class BeliefCorrectionRequest(BaseModel):
    correction_key: str = Field(min_length=1)
    conversation_id: str | None = None
    turn_index: int | None = None
    belief_target: str | None = None


class BeliefCorrectionResponse(BaseModel):
    accepted: bool
    correction_key: str
    evidence: dict
    belief_state_id: str | None = None
    interrupt_payload: dict = Field(default_factory=dict)


async def _analyze_fragment_task(user_id: UUID, fragment_id: UUID, db_session_factory):
    """Background task wrapper for analysis"""
    # Note: BackgroundTasks in FastAPI with async SQLAlchemy session requires creating a new session scope
    # because the dependency session might be closed.
    async with db_session_factory() as session:
        service = CognitiveService(session)
        await service.analyze_behavior(user_id, fragment_id)


def _belief_correction_evidence(
    *,
    user_id: UUID,
    payload: BeliefCorrectionRequest,
) -> UnifiedEvidence:
    metadata = {
        "correction_source": "belief_summary_mvp",
        "stage_of_change": "unknown",
        "conversation_id": payload.conversation_id,
        "turn_index": payload.turn_index,
    }
    scope = {
        "user_id": str(user_id),
        "conversation_id": payload.conversation_id,
        "turn_index": payload.turn_index,
    }
    if payload.correction_key == "not_tired_stuck":
        metadata.update({"cognitive_load_type": "intrinsic", "academic_prior": "cognitive_load_theory.v1"})
        return UnifiedEvidence(
            source_type=EvidenceSourceType.PROBE_EXPLICIT,
            target_latent_variable=EvidenceTarget.COGNITIVE_LOAD,
            direction=EvidenceDirection.INCREASE,
            strength=0.86,
            confidence=0.95,
            evidence_text="用户纠正：我不是累，是不会。",
            ttl_seconds=12 * 3600,
            scope=scope,
            metadata=metadata,
        )
    if payload.correction_key == "not_stuck_avoidant":
        return UnifiedEvidence(
            source_type=EvidenceSourceType.PROBE_EXPLICIT,
            target_latent_variable=EvidenceTarget.TASK_AVERSION,
            direction=EvidenceDirection.INCREASE,
            strength=0.84,
            confidence=0.95,
            evidence_text="用户纠正：我不是不会，是不想开始。",
            ttl_seconds=24 * 3600,
            scope=scope,
            metadata=metadata,
        )
    if payload.correction_key == "ready_to_execute":
        return UnifiedEvidence(
            source_type=EvidenceSourceType.PROBE_EXPLICIT,
            target_latent_variable=EvidenceTarget.EXECUTION_CAPACITY,
            direction=EvidenceDirection.INCREASE,
            strength=0.88,
            confidence=0.95,
            evidence_text="用户纠正：我现在可以直接做。",
            ttl_seconds=6 * 3600,
            scope=scope,
            metadata={**metadata, "stage_of_change": "action"},
        )
    return UnifiedEvidence(
        source_type=EvidenceSourceType.PROBE_EXPLICIT,
        target_latent_variable=EvidenceTarget.SYSTEM_DISSATISFACTION,
        direction=EvidenceDirection.INCREASE,
        strength=0.62,
        confidence=0.90,
        evidence_text=f"用户纠正：{payload.correction_key}",
        ttl_seconds=12 * 3600,
        scope=scope,
        metadata=metadata,
    )


@router.post("/belief-corrections", response_model=BeliefCorrectionResponse)
async def submit_belief_correction(
    *,
    payload: BeliefCorrectionRequest,
    current_user: User = Depends(get_current_user),
):
    """Accept a lightweight user correction from the belief summary MVP."""
    evidence = _belief_correction_evidence(user_id=current_user.id, payload=payload)
    belief_state_id: str | None = None
    interrupt_payload = _belief_correction_interrupt_payload(payload.correction_key)
    if cache_service.redis is not None:
        engine = FusionEngine(str(current_user.id))
        prior_state = await engine.load_state(cache_service.redis, str(current_user.id))
        predicted_target = str(payload.belief_target or "")
        if predicted_target:
            predicted_var = prior_state.variables.get(predicted_target)
            predicted_confidence = (
                max(0.0, min(1.0, 1.0 - float(predicted_var.variance)))
                if predicted_var is not None
                else 0.0
            )
            await engine.append_calibration_sample(
                cache_service.redis,
                user_id=str(current_user.id),
                sample={
                    "schema_version": "evidence_calibration_sample.v1",
                    "predicted_target": predicted_target,
                    "predicted_confidence": round(predicted_confidence, 4),
                    "corrected_target": evidence.target_latent_variable.value,
                    "is_correct": predicted_target == evidence.target_latent_variable.value,
                    "direction_matched": predicted_target == evidence.target_latent_variable.value,
                    "confidence": round(predicted_confidence, 4),
                    "target": predicted_target,
                    "source_type": "llm_or_belief_summary",
                    "correction_key": payload.correction_key,
                    "conversation_id": payload.conversation_id,
                    "turn_index": payload.turn_index,
                },
            )
        state = await engine.update_user_state(
            cache_service.redis,
            user_id=str(current_user.id),
            evidence_items=[evidence],
        )
        trace = engine.generate_rl_trace(
            state,
            action_taken={
                "source": "belief_summary_mvp",
                "action_type": "user_correction",
                "correction_key": payload.correction_key,
                "conversation_id": payload.conversation_id,
                "turn_index": payload.turn_index,
            },
            router_snapshot={"source": "belief_summary_mvp", "actual_router_mode": None},
            evidence_metadata_summary=engine.summarize_evidence_metadata([evidence]),
            outcome="user_correction",
            training_eligible=False,
        )
        await engine.append_trace(cache_service.redis, user_id=str(current_user.id), trace=trace)
        belief_state_id = state.state_id
        interrupt_payload["updated_belief_summary"] = _belief_summary_from_state(state)
    return BeliefCorrectionResponse(
        accepted=True,
        correction_key=payload.correction_key,
        evidence=evidence.to_cognitive_context(),
        belief_state_id=belief_state_id,
        interrupt_payload=interrupt_payload,
    )


def _belief_correction_interrupt_payload(correction_key: str) -> dict:
    if correction_key == "ready_to_execute":
        return {
            "schema_version": "belief_correction_interrupt.v1",
            "correction_ack_text": "收到，我刚才把你的状态判断改成“可以直接推进”。下一步会更直接。",
            "recommended_dual_core_mode": "execution_first",
            "invalidate_current_plan_cards": True,
        }
    if correction_key == "not_tired_stuck":
        return {
            "schema_version": "belief_correction_interrupt.v1",
            "correction_ack_text": "收到，不是累，是卡在知识点上。下一步我会先补关键前置。",
            "recommended_dual_core_mode": "balanced",
            "invalidate_current_plan_cards": True,
        }
    if correction_key == "not_stuck_avoidant":
        return {
            "schema_version": "belief_correction_interrupt.v1",
            "correction_ack_text": "收到，不是不会，是启动阻力高。下一步我会压到最小启动动作。",
            "recommended_dual_core_mode": "cognitive_first",
            "invalidate_current_plan_cards": True,
        }
    return {
        "schema_version": "belief_correction_interrupt.v1",
        "correction_ack_text": "收到，我会用你的纠正更新接下来的判断。",
        "recommended_dual_core_mode": "balanced",
        "invalidate_current_plan_cards": False,
    }


def _belief_summary_from_state(state) -> dict:
    try:
        variables = state.variables
    except Exception:
        variables = {}
    if not isinstance(variables, dict) or not variables:
        return {}
    target, variable = max(variables.items(), key=lambda item: float(getattr(item[1], "mean", 0.0)))
    return {
        "target": str(target),
        "mean": round(float(getattr(variable, "mean", 0.0)), 4),
        "variance": round(float(getattr(variable, "variance", 0.25)), 4),
        "confidence": round(max(0.0, min(1.0, 1.0 - float(getattr(variable, "variance", 0.25)))), 4),
    }


@router.post("/fragments", response_model=CognitiveFragmentResponse)
async def create_fragment(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    fragment_in: CognitiveFragmentCreate,
    background_tasks: BackgroundTasks,
):
    """
    创建一个新的认知碎片 (闪念/拦截)
    """
    service = CognitiveService(db)
    user_id = current_user.id

    fragment = await service.create_fragment(
        user_id=user_id,
        fragment_id=fragment_in.id,
        content=fragment_in.content,
        source_type=fragment_in.source_type,
        resource_type=fragment_in.resource_type,
        resource_url=fragment_in.resource_url,
        context_tags=fragment_in.context_tags,
        error_tags=fragment_in.error_tags,
        severity=fragment_in.severity,
        task_id=fragment_in.task_id,
        source_event_id=fragment_in.source_event_id,
        persona_version=fragment_in.persona_version,
    )

    celery_status = get_celery_queue_status(settings.GLM_BATCH_QUEUE)
    dispatch = glm_batch_service.decide_cognitive_dispatch(
        severity=fragment.severity,
        context_tags=fragment.context_tags,
        error_tags=fragment.error_tags,
        celery_status=celery_status,
    )
    should_enqueue_glm_batch = (
        settings.GLM_BATCH_ENABLED and settings.GLM_BATCH_COGNITIVE_ANALYSIS_ENABLED and dispatch.should_enqueue
    )

    if should_enqueue_glm_batch:
        glm_batch_service.enqueue_cognitive_analysis(
            user_id=user_id,
            fragment_id=fragment.id,
            severity=fragment.severity,
            context_tags=fragment.context_tags,
            error_tags=fragment.error_tags,
        )
    else:
        background_tasks.add_task(_analyze_fragment_task, user_id, fragment.id, AsyncSessionLocal)

    return fragment


@router.get("/fragments", response_model=list[CognitiveFragmentResponse])
async def get_fragments(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0,
):
    """
    获取用户的认知碎片列表
    """
    service = CognitiveService(db)
    fragments = await service.get_fragments(user_id=current_user.id, limit=limit, offset=skip)
    return fragments


@router.get("/patterns", response_model=list[BehaviorPatternResponse])
async def get_patterns(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的行为定式列表
    """
    stmt = (
        select(BehaviorPattern)
        .where(BehaviorPattern.user_id == current_user.id)
        .order_by(desc(BehaviorPattern.created_at))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# route-tier: authed
@router.get("/alternative-strategies")
async def get_alternative_strategies(
    *,
    goal_id: UUID,
    limit: int = 3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return replacement strategies when a goal's current strategy has counter-evidence."""
    bundle = await strategy_belief_service.suggest_alternatives(
        user_id=current_user.id,
        goal_id=goal_id,
        db=db,
        limit=limit,
    )
    return bundle.to_dict()


# route-tier: authed
@router.post("/strategies/migrate", response_model=StrategyMigrationResponse)
async def migrate_strategy(
    payload: StrategyMigrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StrategyMigrationResponse:
    """Switch a goal to a selected alternative strategy."""
    result = await strategy_belief_service.migrate_strategy(
        user_id=current_user.id,
        goal_id=payload.goal_id,
        new_strategy_id=payload.new_strategy_id,
        db=db,
    )
    await db.commit()
    return StrategyMigrationResponse(**result.to_dict())
