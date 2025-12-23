"""
Cognitive Prism API
认知棱镜相关 API
"""
from typing import List, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.cognitive import BehaviorPattern
from app.schemas.cognitive import CognitiveFragmentCreate, CognitiveFragmentResponse, BehaviorPatternResponse
from app.services.cognitive_service import CognitiveService

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
    
    fragment = await service.create_fragment(
        user_id=current_user.id,
        content=fragment_in.content,
        source_type=fragment_in.source_type,
        resource_type=fragment_in.resource_type,
        resource_url=fragment_in.resource_url,
        context_tags=fragment_in.context_tags,
        error_tags=fragment_in.error_tags,
        severity=fragment_in.severity,
        task_id=fragment_in.task_id
    )
    
    # Trigger AI Analysis
    # Note: To avoid complexity with session passing in background tasks, 
    # for this iteration we can run it inline if it's not too slow, 
    # OR we need a proper session factory dependency.
    # Given the complexity of "analyze_behavior" (RAG + LLM), it will be slow.
    # For now, I will skip the background task trigger implementation in API 
    # and rely on the client to call /analyze/trigger or just accept it's manual for now,
    # OR (Better) - Implement a proper background worker later.
    # 
    # BUT, to fulfill the "Real-time" feel, I will attempt to run it 
    # if the user specifically requests it or just logging it.
    #
    # Actually, simplest way for prototype: just await it. It might take 3-5 seconds.
    # Let's try to await it for immediate feedback in testing, 
    # but the response model doesn't include the analysis result yet (it's in patterns).
    
    # Let's execute it inline for now to ensure it works.
    try:
        await service.analyze_behavior(current_user.id, fragment.id)
    except Exception as e:
        # Log but don't fail the request
        print(f"Analysis failed: {e}")
        
    return fragment

@router.get("/fragments", response_model=List[CognitiveFragmentResponse])
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

@router.get("/patterns", response_model=List[BehaviorPatternResponse])
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