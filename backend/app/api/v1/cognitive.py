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
from app.db.session import AsyncSessionLocal
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
    
    # Trigger AI Analysis via Background Task
    background_tasks.add_task(
        _analyze_fragment_task, 
        current_user.id, 
        fragment.id, 
        AsyncSessionLocal
    )
        
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