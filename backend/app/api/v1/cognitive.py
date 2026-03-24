"""
Cognitive Prism API
认知棱镜相关 API
"""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.celery_app import get_celery_queue_status
from app.db.session import AsyncSessionLocal
from app.models.cognitive import BehaviorPattern
from app.models.user import User
from app.schemas.cognitive import BehaviorPatternResponse, CognitiveFragmentCreate, CognitiveFragmentResponse
from app.services.cognitive_service import CognitiveService
from app.services.glm_batch_service import glm_batch_service

router = APIRouter()

async def _analyze_fragment_task(user_id: UUID, fragment_id: UUID, db_session_factory):
    """Background task wrapper for analysis"""
    # Note: BackgroundTasks in FastAPI with async SQLAlchemy session requires creating a new session scope
    # because the dependency session might be closed.
    async with db_session_factory() as session:
        service = CognitiveService(session)
        await service.analyze_behavior(user_id, fragment_id)

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
        content=fragment_in.content,
        source_type=fragment_in.source_type,
        resource_type=fragment_in.resource_type,
        resource_url=fragment_in.resource_url,
        context_tags=fragment_in.context_tags,
        error_tags=fragment_in.error_tags,
        severity=fragment_in.severity,
        task_id=fragment_in.task_id,
        source_event_id=fragment_in.source_event_id,
        persona_version=fragment_in.persona_version
    )

    celery_status = get_celery_queue_status(settings.GLM_BATCH_QUEUE)
    dispatch = glm_batch_service.decide_cognitive_dispatch(
        severity=fragment.severity,
        context_tags=fragment.context_tags,
        error_tags=fragment.error_tags,
        celery_status=celery_status,
    )
    should_enqueue_glm_batch = (
        settings.GLM_BATCH_ENABLED
        and settings.GLM_BATCH_COGNITIVE_ANALYSIS_ENABLED
        and dispatch.should_enqueue
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
        background_tasks.add_task(
            _analyze_fragment_task,
            user_id,
            fragment.id,
            AsyncSessionLocal
        )

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
    fragments = await service.get_fragments(
        user_id=current_user.id,
        limit=limit,
        offset=skip
    )
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
