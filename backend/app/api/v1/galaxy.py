"""
Knowledge Galaxy API
知识星图相关接口
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus
from app.schemas.galaxy import (
    ExpansionFeedbackRequest,
    ExpansionFeedbackResponse,
    GalaxyGraphResponse,
    NodeDetailResponse,
    NodeRelationInfo,
    ReviewSuggestion,
    ReviewSuggestionsResponse,
    SearchRequest,
    SearchResponse,
    SectorCode,
    SparkRequest,
    SparkResult,
)
from app.services.decay_service import DecayService
from app.services.galaxy_service import GalaxyService
from app.services.knowledge_integration_service import KnowledgeIntegrationService

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


async def get_knowledge_integration_service(db: AsyncSession = Depends(get_db)) -> KnowledgeIntegrationService:
    """获取 KnowledgeIntegrationService 实例"""
    return KnowledgeIntegrationService(db)


class MasterySyncRequest(BaseModel):
    node_id: UUID
    mastery: int = Field(..., ge=0, le=100)
    version: datetime
    reason: str = "offline_sync"


class UpdateNodeMasteryRequest(BaseModel):
    mastery: int | None = Field(None, ge=0, le=100)
    mastery_delta: float | None = Field(None, ge=-100, le=100)
    reason: str = "manual_update"
    source: str | None = None
    version: datetime | None = None


@router.post("/sync/mastery")
async def sync_node_mastery(
    request: MasterySyncRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
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
        version=request.version,
    )

    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.get("reason", "conflict"))

    return result


@router.post("/nodes/{node_id}/update-mastery")
async def update_node_mastery(
    node_id: UUID,
    request: UpdateNodeMasteryRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
):
    """Explicit REST entrypoint for node mastery updates used by Galaxy UI flows."""
    if request.mastery is None and request.mastery_delta is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either mastery or mastery_delta is required",
        )

    target_mastery = request.mastery
    if target_mastery is None:
        current_status = await galaxy_service.retrieval._get_user_status(UUID(user_id), node_id)
        current_mastery = float(current_status.mastery_score or 0) if current_status else 0.0
        delta = float(request.mastery_delta or 0.0)
        target_mastery = max(0, min(100, int(round(current_mastery + delta))))

    result = await galaxy_service.update_node_mastery(
        user_id=UUID(user_id),
        node_id=node_id,
        new_mastery=target_mastery,
        reason=request.reason if request.reason != "manual_update" else (request.source or request.reason),
        version=request.version,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("reason", "conflict"),
        )

    return result


# ==========================================
# API 端点
# ==========================================
@router.get("/graph", response_model=GalaxyGraphResponse)
async def get_galaxy_graph(
    sector_code: str | None = Query(None, description="筛选特定星域"),
    include_locked: bool = Query(True, description="是否包含未解锁节点"),
    zoom_level: float = Query(1.0, description="缩放级别 (LOD控制)"),
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
):
    """
    获取用户的知识星图数据

    返回所有知识节点、关系和用户状态，用于前端渲染完整星图。
    支持 LOD (Level of Detail):
    - zoom_level < 0.5: 仅返回重要节点 (Level >= 3)
    - zoom_level >= 0.5: 返回所有节点
    """
    return await galaxy_service.get_galaxy_graph(
        user_id=UUID(user_id), sector_code=sector_code, include_locked=include_locked, zoom_level=zoom_level
    )


@router.post("/node/{node_id}/spark", response_model=SparkResult)
async def spark_node(
    node_id: UUID,
    request: SparkRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
):
    """
    点亮/增强知识点

    当用户完成学习任务时调用，更新掌握度并可能触发 LLM 拓展。
    """
    return await galaxy_service.spark_node(
        user_id=UUID(user_id),
        node_id=node_id,
        study_minutes=request.study_minutes if request else 1,
        task_id=request.task_id if request else None,
        trigger_expansion=request.trigger_expansion if request else True,
    )


@router.get("/node/{node_id}")
async def get_node_detail(
    node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
):
    """
    获取知识点详情 — Flutter KnowledgeDetailResponse format

    包含节点基础信息、用户状态和关系信息。
    """
    from sqlalchemy.orm import joinedload

    # 获取节点（eager-load subject）
    result = await db.execute(
        select(KnowledgeNode)
        .options(joinedload(KnowledgeNode.subject))
        .where(KnowledgeNode.id == node_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge node not found")

    # 获取用户状态
    user_status = await galaxy_service.retrieval._get_user_status(UUID(user_id), node_id)

    # 获取关系（含对端节点名称）
    relations_query = (
        select(NodeRelation)
        .options(
            joinedload(NodeRelation.source_node),
            joinedload(NodeRelation.target_node),
        )
        .where(
            or_(NodeRelation.source_node_id == node_id, NodeRelation.target_node_id == node_id)
        )
    )
    relations_result = await db.execute(relations_query)
    relations = relations_result.unique().scalars().all()

    # 构建 sector_code
    sector_code = "VOID"
    if node.subject:
        sector_code = node.subject.sector_code or "VOID"

    # 构建 user_stats (top-level, matching Flutter KnowledgeUserStats)
    if user_status:
        user_stats = {
            "mastery_score": float(user_status.mastery_score or 0),
            "total_study_minutes": int(user_status.total_study_minutes or 0),
            "study_count": int(user_status.study_count or 0),
            "is_unlocked": bool(user_status.is_unlocked),
            "is_favorite": bool(user_status.is_favorite),
            "last_study_at": user_status.last_study_at.isoformat() if user_status.last_study_at else None,
            "next_review_at": user_status.next_review_at.isoformat() if user_status.next_review_at else None,
            "decay_paused": bool(user_status.decay_paused),
        }
    else:
        user_stats = {
            "mastery_score": 0.0,
            "total_study_minutes": 0,
            "study_count": 0,
            "is_unlocked": False,
            "is_favorite": False,
            "last_study_at": None,
            "next_review_at": None,
            "decay_paused": False,
        }

    # 构建 node dict (matching Flutter KnowledgeNodeDetail)
    node_dict = {
        "id": str(node.id),
        "name": node.name,
        "name_en": node.name_en,
        "description": node.description,
        "keywords": node.keywords or [],
        "importance_level": node.importance_level,
        "sector_code": sector_code,
        "is_seed": bool(node.is_seed),
        "source_type": node.source_type or "seed",
        "parent_id": str(node.parent_id) if node.parent_id else None,
        "subject_id": node.subject_id,
        "subject_name": node.subject.name if node.subject else None,
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }

    # 构建 relations list (matching Flutter NodeRelation)
    relations_list = [
        {
            "id": str(rel.id),
            "source_node_id": str(rel.source_node_id),
            "target_node_id": str(rel.target_node_id),
            "relation_type": rel.relation_type,
            "strength": float(rel.strength or 0.5),
            "source_node_name": rel.source_node.name if rel.source_node else None,
            "target_node_name": rel.target_node.name if rel.target_node else None,
        }
        for rel in relations
    ]

    return {
        "node": node_dict,
        "userStats": user_stats,
        "relations": relations_list,
        "relatedTasks": [],
        "relatedPlans": [],
    }


@router.post("/search", response_model=SearchResponse)
async def search_nodes(
    request: SearchRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
):
    """
    语义搜索知识点

    使用向量相似度搜索相关知识点。
    """
    results = await galaxy_service.semantic_search(
        user_id=UUID(user_id), query=request.query, limit=request.limit, threshold=request.threshold
    )

    return SearchResponse(query=request.query, results=results, total_count=len(results))


@router.post("/expansion/feedback", response_model=ExpansionFeedbackResponse)
async def submit_expansion_feedback(
    request: ExpansionFeedbackRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
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
        metadata=request.metadata,
    )
    return ExpansionFeedbackResponse(success=True, feedback_id=feedback_id)


@router.get("/review/suggestions", response_model=ReviewSuggestionsResponse)
async def get_review_suggestions(
    limit: int = Query(5, ge=1, le=20),
    user_id: str = Depends(get_current_user_id),
    decay_service: DecayService = Depends(get_decay_service),
):
    """
    获取复习建议

    返回需要复习的知识点列表，按紧迫程度排序。
    """
    suggestions_data = await decay_service.get_review_suggestions(user_id=UUID(user_id), limit=limit)

    suggestions = [
        ReviewSuggestion(
            node_id=s["node_id"],
            node_name=s["node_name"],
            sector_code=SectorCode(s["sector_code"]),
            current_mastery=s["current_mastery"],
            days_since_study=s["days_since_study"],
            urgency=s["urgency"],
        )
        for s in suggestions_data
    ]

    return ReviewSuggestionsResponse(suggestions=suggestions, next_review_count=len(suggestions))


@router.post("/node/{node_id}/decay/pause")
async def pause_node_decay(
    node_id: UUID,
    pause: bool = Query(True),
    user_id: str = Depends(get_current_user_id),
    decay_service: DecayService = Depends(get_decay_service),
):
    """
    暂停/恢复知识点的遗忘衰减

    用户可以将重要的知识点标记为"暂停衰减"。
    """
    await decay_service.pause_decay(user_id=UUID(user_id), node_id=node_id, pause=pause)

    return {"status": "success", "node_id": str(node_id), "decay_paused": pause}


@router.post("/node/{node_id}/favorite")
async def toggle_node_favorite(
    node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """切换知识点收藏状态"""
    node = await db.get(KnowledgeNode, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge node not found")

    user_uuid = UUID(user_id)
    user_status = await db.get(UserNodeStatus, (user_uuid, node_id))

    if not user_status:
        user_status = UserNodeStatus(
            user_id=user_uuid,
            node_id=node_id,
            is_unlocked=True,
            is_favorite=True,
            mastery_score=0,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
        )
    else:
        user_status.is_favorite = not bool(user_status.is_favorite)

    db.add(user_status)
    await db.commit()
    await db.refresh(user_status)

    return {"status": "success", "node_id": str(node_id), "is_favorite": bool(user_status.is_favorite)}


@router.post("/predict-next", response_model=Optional[NodeDetailResponse])
async def predict_next_node(
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
    db: AsyncSession = Depends(get_db),
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
        or_(NodeRelation.source_node_id == node_with_status.id, NodeRelation.target_node_id == node_with_status.id)
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
                strength=rel.strength,
            )
            for rel in relations
        ],
    )


@router.get("/stats")
async def get_galaxy_stats(
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
    decay_service: DecayService = Depends(get_decay_service),
):
    """
    获取星图统计数据

    包含节点统计、衰减统计等。
    """
    user_stats = await galaxy_service.stats.calculate_user_stats(UUID(user_id))
    decay_stats = await decay_service.get_decay_stats(UUID(user_id))

    return {"user_stats": user_stats, "decay_stats": decay_stats}


@router.get("/events")
async def galaxy_events_stream(request: Request, user_id: str = Depends(get_current_user_id)):
    """
    SSE 事件流

    前端连接此端点以接收实时事件：
    - nodes_expanded: 新节点涌现
    - node_sparked: 节点被点亮
    - decay_warning: 衰减警告
    - evidence_pack: RAG 证据
    """
    from fastapi.responses import StreamingResponse

    from app.core.sse import event_generator, sse_manager

    # 支持断点续传
    last_event_id = request.headers.get("Last-Event-ID")

    # 创建连接 (带 Replay 支持)
    queue = await sse_manager.connect(user_id, last_event_id=last_event_id)

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
        },
    )

    # 注册清理回调
    response.background = cleanup

    return response


# ==========================================
# PR-16: Knowledge Integration Endpoints
# ==========================================


class CreateVocabularyNodeRequest(BaseModel):
    """Request model for creating vocabulary node from translation"""

    source_text: str = Field(..., description="原始文本 (e.g., 'polymorphism')")
    translation: str = Field(..., description="译文 (e.g., '多态性')")
    context: str = Field(..., description="上下文场景")
    source_url: str | None = Field(default=None, description="来源URL")
    source_document_id: str | None = Field(default=None, description="来源文档ID")
    language: str = Field(default="en", description="源语言 (en, zh)")
    domain: str | None = Field(default=None, description="领域 (cs, math, business)")
    subject_id: int | None = Field(default=None, description="关联科目ID")


class VocabularyNodeResponse(BaseModel):
    """Response model for vocabulary node creation"""

    success: bool
    node_id: UUID
    status: str
    message: str


@router.post("/vocabulary", response_model=VocabularyNodeResponse)
async def create_vocabulary_node(
    request: CreateVocabularyNodeRequest,
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeIntegrationService = Depends(get_knowledge_integration_service),
):
    """
    创建词汇知识节点（从翻译生成）

    节点以 'draft' 状态创建，用户可以：
    - 审阅和编辑内容
    - 发布到主知识图谱
    - 删除不需要的节点

    自动安排间隔重复复习（首次复习：24小时后）
    """
    try:
        node = await knowledge_service.create_vocabulary_node(
            user_id=UUID(user_id),
            source_text=request.source_text,
            translation=request.translation,
            context=request.context,
            source_url=request.source_url,
            source_document_id=UUID(request.source_document_id) if request.source_document_id else None,
            language=request.language,
            domain=request.domain,
            subject_id=request.subject_id,
        )

        return VocabularyNodeResponse(
            success=True,
            node_id=node.id,
            status=node.status,
            message=f"Vocabulary node created: {node.name} → {request.translation}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create vocabulary node: {str(e)}"
        )


@router.delete("/node/{node_id}/draft")
async def delete_draft_node(
    node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeIntegrationService = Depends(get_knowledge_integration_service),
):
    """
    删除草稿节点

    只能删除状态为 'draft' 的节点
    """
    try:
        await knowledge_service.delete_draft_node(node_id, UUID(user_id))
        return {"success": True, "node_id": str(node_id), "message": "Draft node deleted"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete draft node: {str(e)}"
        )


class UpdateNodeContentRequest(BaseModel):
    """Request model for updating node content"""

    name: str | None = None
    description: str | None = None
    keywords: list[str] | None = None


@router.patch("/node/{node_id}/content")
async def update_node_content(
    node_id: UUID,
    request: UpdateNodeContentRequest,
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeIntegrationService = Depends(get_knowledge_integration_service),
):
    """
    更新节点内容（发布前编辑）

    可以修改名称、描述和关键词
    """
    try:
        node = await knowledge_service.update_node_content(
            node_id=node_id,
            user_id=UUID(user_id),
            name=request.name,
            description=request.description,
            keywords=request.keywords,
        )

        return {"success": True, "node_id": str(node.id), "name": node.name, "message": "Node content updated"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update node content: {str(e)}"
        )


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
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
):
    """
    Get nodes within a specific viewport (bounding box).
    Returns a viewport-limited graph slice with real user status and local relations.
    """
    return await galaxy_service.get_galaxy_graph_viewport(
        user_id=UUID(user_id),
        min_x=request.min_x,
        max_x=request.max_x,
        min_y=request.min_y,
        max_y=request.max_y,
    )


@router.post("/nodes/positions")
async def update_node_positions(
    request: PositionUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
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
    galaxy_service: GalaxyService = Depends(get_galaxy_service),
):
    """
    Trigger Auto-Link Worker for a specific node.
    Phase 4.1 Automation.
    """
    links_created = await galaxy_service.auto_link_nodes(node_id)
    return {"status": "success", "links_created": links_created}


@router.get("/heatmap")
async def get_heatmap(
    user_id: str = Depends(get_current_user_id), galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    Get Heatmap Data for MiniMap.
    Phase 4.2 Insight.
    """
    return await galaxy_service.get_heatmap_data(UUID(user_id))


# 导入必要的 or_ 函数
from sqlalchemy import or_
