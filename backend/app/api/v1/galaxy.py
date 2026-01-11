"""
Knowledge Galaxy API
知识星图相关接口
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_id, get_db
from app.services.galaxy_service import GalaxyService
from app.services.decay_service import DecayService
from app.schemas.galaxy import (
    GalaxyGraphResponse,
    SparkRequest,
    SparkResult,
    SearchRequest,
    SearchResponse,
    ExpansionFeedbackRequest,
    ExpansionFeedbackResponse,
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


class MasterySyncRequest(BaseModel):
    node_id: UUID
    mastery: int = Field(..., ge=0, le=100)
    version: datetime
    reason: str = "offline_sync"

@router.post("/sync/mastery")
async def sync_node_mastery(
    request: MasterySyncRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    Synchronize node mastery from mobile client (via Gateway).
    Supports optimistic concurrency using the version (timestamp) field.
    """
    result = await galaxy_service.update_node_mastery(
        user_id=UUID(user_id),
        node_id=request.node_id,
        new_mastery=request.mastery,
        reason=request.reason,
        version=request.version
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("reason", "conflict")
        )
        
    return result

# ==========================================
# API 端点
# ==========================================
@router.get("/graph", response_model=GalaxyGraphResponse)
async def get_galaxy_graph(
    sector_code: Optional[str] = Query(None, description="筛选特定星域"),
    include_locked: bool = Query(True, description="是否包含未解锁节点"),
    zoom_level: float = Query(1.0, description="缩放级别 (LOD控制)"),
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    获取用户的知识星图数据

    返回所有知识节点、关系和用户状态，用于前端渲染完整星图。
    支持 LOD (Level of Detail):
    - zoom_level < 0.5: 仅返回重要节点 (Level >= 3)
    - zoom_level >= 0.5: 返回所有节点
    """
    return await galaxy_service.get_galaxy_graph(
        user_id=UUID(user_id),
        sector_code=sector_code,
        include_locked=include_locked,
        zoom_level=zoom_level
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


@router.post("/expansion/feedback", response_model=ExpansionFeedbackResponse)
async def submit_expansion_feedback(
    request: ExpansionFeedbackRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    提交知识拓展反馈
    """
    feedback_id = await galaxy_service.record_expansion_feedback(
        user_id=UUID(user_id),
        trigger_node_id=request.trigger_node_id,
        expansion_queue_id=request.expansion_queue_id,
        rating=request.rating,
        implicit_score=request.implicit_score,
        feedback_type=request.feedback_type,
        prompt_version=request.prompt_version,
        metadata=request.metadata
    )
    return ExpansionFeedbackResponse(success=True, feedback_id=feedback_id)


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


@router.post("/predict-next", response_model=Optional[NodeDetailResponse])
async def predict_next_node(
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
    db: AsyncSession = Depends(get_db)
):
    """
    预测下一个最佳学习节点

    基于用户的学习历史和知识图谱结构，推荐下一个最值得学习的节点。
    """
    node_with_status = await galaxy_service.predict_next_node(UUID(user_id))
    
    if not node_with_status:
        return None
        
    # 获取关系以便前端渲染连接线
    relations_query = select(NodeRelation).where(
        or_(
            NodeRelation.source_node_id == node_with_status.id,
            NodeRelation.target_node_id == node_with_status.id
        )
    )
    relations_result = await db.execute(relations_query)
    relations = relations_result.scalars().all()
    
    return NodeDetailResponse(
        node=node_with_status,
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


@router.get("/events")
async def galaxy_events_stream(
    user_id: str = Depends(get_current_user_id)
):
    """
    SSE 事件流

    前端连接此端点以接收实时事件：
    - nodes_expanded: 新节点涌现
    - node_sparked: 节点被点亮
    - decay_warning: 衰减警告
    """
    from fastapi.responses import StreamingResponse
    from app.core.sse import sse_manager, event_generator

    # 创建连接
    queue = await sse_manager.connect(user_id)

    async def cleanup():
        """清理连接"""
        await sse_manager.disconnect(user_id, queue)

    # 返回 SSE 流
    response = StreamingResponse(
        event_generator(queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        }
    )

    # 注册清理回调
    response.background = cleanup

    return response

# ==========================================
# Phase 3 & 4 Endpoints
# ==========================================

class ViewportRequest(BaseModel):
    min_x: float
    max_x: float
    min_y: float
    max_y: float

class PositionUpdateItem(BaseModel):
    id: UUID
    x: float
    y: float

class PositionUpdateRequest(BaseModel):
    updates: list[PositionUpdateItem]

@router.post("/nodes/viewport", response_model=GalaxyGraphResponse)
async def get_nodes_in_viewport(
    request: ViewportRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    Get nodes within a specific viewport (bounding box).
    Phase 3.2 Backend Viewport API.
    """
    nodes = await galaxy_service.get_nodes_in_bounds(
        request.min_x, request.max_x, request.min_y, request.max_y
    )
    # Convert to GalaxyGraphResponse format (simplified for viewport)
    # We might need to fetch status for these nodes too.
    # For efficiency, we just return the nodes and let frontend handle status or fetch status in batch.
    # But GalaxyGraphResponse expects NodeWithStatus.
    
    # Quick fix: fetch status for these nodes
    # Ideally structure service should return NodeWithStatus if we modify get_nodes_in_bounds to do join.
    # For MVP of this feature, let's map what we have.
    
    # We can reuse get_galaxy_graph logic but restricted by IDs if we had get_nodes_by_ids.
    # Or just return raw nodes data in a specific response model.
    # Reusing GalaxyGraphResponse for consistency.
    
    # Construct minimal response
    from app.schemas.galaxy import NodeBase, NodeStatus, UserStatusInfo
    
    mapped_nodes = []
    for node in nodes:
        # TODO: Fetch real status efficiently (bulk query)
        status = UserNodeStatus(mastery_score=0, is_unlocked=False) 
        mapped_nodes.append(NodeWithStatus.from_models(node, status))
        
    return GalaxyGraphResponse(
        nodes=mapped_nodes,
        relations=[], # Do not fetch relations for viewport query to save bandwidth? Or maybe local relations.
        user_stats=None
    )

@router.post("/nodes/positions")
async def update_node_positions(
    request: PositionUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    Persist node positions calculated by frontend layout engine.
    Phase 3.2 Layout Persistence.
    """
    # Convert Pydantic models to dicts
    updates = [{"id": item.id, "x": item.x, "y": item.y} for item in request.updates]
    count = await galaxy_service.update_node_positions(updates)
    return {"status": "success", "updated_count": count}

@router.post("/node/{node_id}/autolink")
async def trigger_auto_link(
    node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    Trigger Auto-Link Worker for a specific node.
    Phase 4.1 Automation.
    """
    links_created = await galaxy_service.auto_link_nodes(node_id)
    return {"status": "success", "links_created": links_created}

@router.get("/heatmap")
async def get_heatmap(
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    Get Heatmap Data for MiniMap.
    Phase 4.2 Insight.
    """
    return await galaxy_service.get_heatmap_data(UUID(user_id))


# 导入必要的 or_ 函数
from sqlalchemy import or_
