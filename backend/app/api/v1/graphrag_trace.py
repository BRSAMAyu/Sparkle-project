"""
GraphRAG 检索追踪 API - 必杀技 A

用于前端实时可视化检索过程
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from app.api.deps import get_current_user
from app.models.user import User
from orchestration.graph_rag import GraphRAGRetriever, RetrievalTrace
from app.services.knowledge_service import KnowledgeService


router = APIRouter(prefix="/graphrag", tags=["graphrag"])


class GraphRAGTraceResponse(BaseModel):
    """GraphRAG 追踪响应"""
    trace_id: str
    query: str
    timestamp: datetime

    # 节点信息
    nodes_retrieved: List[Dict[str, Any]]
    node_sources: Dict[str, str]  # node_id -> source (vector/graph/user_interest)

    # 关系信息
    relationships: List[Dict[str, Any]]

    # 检索方法详情
    vector_search_count: int
    graph_search_count: int
    user_interest_count: int

    # 性能指标
    timing: Dict[str, float]

    class Config:
        from_attributes = True


# 内存缓存（生产环境应使用 Redis）
_trace_cache: Dict[str, RetrievalTrace] = {}


@router.get("/trace/latest", response_model=GraphRAGTraceResponse)
async def get_latest_trace(
    current_user: User = Depends(get_current_user)
):
    """
    获取用户最新的检索追踪信息

    用于前端实时可视化：
    - 显示哪些节点被检索
    - 显示检索方法（向量/图/用户兴趣）
    - 显示节点间关系
    """
    # 这里应该从缓存中获取用户最新的trace
    # 临时实现：返回mock数据

    logger.info(f"获取用户 {current_user.id} 的最新检索追踪")

    # TODO: 从Redis或内存缓存中获取真实数据
    # 这里返回示例响应
    raise HTTPException(
        status_code=404,
        detail="No recent GraphRAG query found. Please send a chat message first."
    )


@router.get("/trace/{trace_id}", response_model=GraphRAGTraceResponse)
async def get_trace_by_id(
    trace_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    根据 trace_id 获取特定的检索追踪信息
    """
    trace = _trace_cache.get(trace_id)

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return GraphRAGTraceResponse(
        trace_id=trace.trace_id,
        query=trace.query,
        timestamp=trace.timestamp,
        nodes_retrieved=trace.nodes_retrieved,
        node_sources=trace.node_sources,
        relationships=trace.relationships,
        vector_search_count=len(trace.vector_search_results),
        graph_search_count=len(trace.graph_search_results),
        user_interest_count=len(trace.user_interest_nodes),
        timing=trace.timing
    )


def cache_trace(trace: RetrievalTrace):
    """
    缓存追踪信息（供orchestrator调用）

    Args:
        trace: 检索追踪对象
    """
    _trace_cache[trace.trace_id] = trace

    # 限制缓存大小（保留最近100条）
    if len(_trace_cache) > 100:
        # 删除最旧的
        oldest_key = min(_trace_cache.keys(), key=lambda k: _trace_cache[k].timestamp)
        del _trace_cache[oldest_key]

    logger.debug(f"缓存追踪信息: {trace.trace_id}, 当前缓存大小: {len(_trace_cache)}")


@router.post("/test-retrieval")
async def test_graphrag_retrieval(
    query: str,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends()
):
    """
    测试端点：执行 GraphRAG 检索并返回追踪信息

    用于开发和演示
    """
    try:
        retriever = GraphRAGRetriever(knowledge_service)
        result = await retriever.retrieve(
            query=query,
            user_id=str(current_user.id),
            enable_trace=True
        )

        if result.trace:
            # 缓存追踪信息
            cache_trace(result.trace)

            return {
                "trace_id": result.trace.trace_id,
                "query": query,
                "nodes_count": len(result.trace.nodes_retrieved),
                "vector_count": len(result.trace.vector_search_results),
                "graph_count": len(result.trace.graph_search_results),
                "relationships_count": len(result.trace.relationships),
                "timing": result.trace.timing,
                "fused_context_preview": result.fused_context[:200] + "..."
            }
        else:
            return {"error": "Trace not enabled"}

    except Exception as e:
        logger.error(f"GraphRAG 测试检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
