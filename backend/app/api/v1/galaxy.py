"""
Knowledge Galaxy API
知识星图相关接口
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.services.galaxy_service import GalaxyService
from app.services.decay_service import DecayService
from app.schemas.galaxy import (
    GalaxyGraphResponse,
    SparkRequest,
    SparkResult,
    SearchRequest,
    SearchResponse,
    ReviewSuggestionsResponse,
    ReviewSuggestion,
    NodeDetailResponse,
    SectorCode
)
from app.models.galaxy import KnowledgeNode, UserNodeStatus, NodeRelation
from app.schemas.galaxy import NodeRelationInfo
from sqlalchemy import select, and_


router = APIRouter(prefix="/galaxy", tags=["Knowledge Galaxy"])


# ==========================================
# 依赖注入
# ==========================================
async def get_galaxy_service(db: AsyncSession = Depends(get_db)) -> GalaxyService:
    """获取 GalaxyService 实例"""
    return GalaxyService(db)


async def get_decay_service(db: AsyncSession = Depends(get_db)) -> DecayService:
    """获取 DecayService 实例"""
    return DecayService(db)


# ==========================================
# API 端点
# ==========================================
@router.get("/graph", response_model=GalaxyGraphResponse)
async def get_galaxy_graph(
    sector_code: Optional[str] = Query(None, description="筛选特定星域"),
    include_locked: bool = Query(True, description="是否包含未解锁节点"),
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    获取用户的知识星图数据

    返回所有知识节点、关系和用户状态，用于前端渲染完整星图。
    """
    return await galaxy_service.get_galaxy_graph(
        user_id=UUID(user_id),
        sector_code=sector_code,
        include_locked=include_locked
    )


@router.post("/node/{node_id}/spark", response_model=SparkResult)
async def spark_node(
    node_id: UUID,
    request: SparkRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    点亮/增强知识点

    当用户完成学习任务时调用，更新掌握度并可能触发 LLM 拓展。
    """
    return await galaxy_service.spark_node(
        user_id=UUID(user_id),
        node_id=node_id,
        study_minutes=request.study_minutes,
        task_id=request.task_id,
        trigger_expansion=request.trigger_expansion
    )


@router.get("/node/{node_id}", response_model=NodeDetailResponse)
async def get_node_detail(
    node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    获取知识点详情

    包含节点基础信息、用户状态和关系信息。
    """
    # 获取节点
    node = await db.get(KnowledgeNode, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge node not found"
        )

    # 获取用户状态
    user_status = await galaxy_service._get_user_status(UUID(user_id), node_id)

    # 获取关系
    relations_query = select(NodeRelation).where(
        or_(
            NodeRelation.source_node_id == node_id,
            NodeRelation.target_node_id == node_id
        )
    )
    relations_result = await db.execute(relations_query)
    relations = relations_result.scalars().all()

    from app.schemas.galaxy import NodeWithStatus

    return NodeDetailResponse(
        node=NodeWithStatus.from_models(node, user_status),
        relations=[
            NodeRelationInfo(
                source_node_id=rel.source_node_id,
                target_node_id=rel.target_node_id,
                relation_type=rel.relation_type,
                strength=rel.strength
            )
            for rel in relations
        ]
    )


@router.post("/search", response_model=SearchResponse)
async def search_nodes(
    request: SearchRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    语义搜索知识点

    使用向量相似度搜索相关知识点。
    """
    results = await galaxy_service.semantic_search(
        user_id=UUID(user_id),
        query=request.query,
        limit=request.limit,
        threshold=request.threshold
    )

    return SearchResponse(
        query=request.query,
        results=results,
        total_count=len(results)
    )


@router.get("/review/suggestions", response_model=ReviewSuggestionsResponse)
async def get_review_suggestions(
    limit: int = Query(5, ge=1, le=20),
    user_id: str = Depends(get_current_user_id),
    decay_service: DecayService = Depends(get_decay_service)
):
    """
    获取复习建议

    返回需要复习的知识点列表，按紧迫程度排序。
    """
    suggestions_data = await decay_service.get_review_suggestions(
        user_id=UUID(user_id),
        limit=limit
    )

    suggestions = [
        ReviewSuggestion(
            node_id=s['node_id'],
            node_name=s['node_name'],
            sector_code=SectorCode(s['sector_code']),
            current_mastery=s['current_mastery'],
            days_since_study=s['days_since_study'],
            urgency=s['urgency']
        )
        for s in suggestions_data
    ]

    return ReviewSuggestionsResponse(
        suggestions=suggestions,
        next_review_count=len(suggestions)
    )


@router.post("/node/{node_id}/decay/pause")
async def pause_node_decay(
    node_id: UUID,
    pause: bool = Query(True),
    user_id: str = Depends(get_current_user_id),
    decay_service: DecayService = Depends(get_decay_service)
):
    """
    暂停/恢复知识点的遗忘衰减

    用户可以将重要的知识点标记为"暂停衰减"。
    """
    await decay_service.pause_decay(
        user_id=UUID(user_id),
        node_id=node_id,
        pause=pause
    )

    return {
        "status": "success",
        "node_id": str(node_id),
        "decay_paused": pause
    }


@router.get("/stats")
async def get_galaxy_stats(
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
    decay_service: DecayService = Depends(get_decay_service)
):
    """
    获取星图统计数据

    包含节点统计、衰减统计等。
    """
    user_stats = await galaxy_service._calculate_user_stats(UUID(user_id))
    decay_stats = await decay_service.get_decay_stats(UUID(user_id))

    return {
        "user_stats": user_stats,
        "decay_stats": decay_stats
    }


# 导入必要的 or_ 函数
from sqlalchemy import or_
