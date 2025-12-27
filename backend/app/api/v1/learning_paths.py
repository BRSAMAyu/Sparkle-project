"""
Learning Paths API
基于拓扑排序的动态学习路径接口
"""
from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.services.graph_reasoning_service import GraphReasoningService

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths"])

async def get_graph_reasoning_service(db: AsyncSession = Depends(get_db)) -> GraphReasoningService:
    return GraphReasoningService(db)

@router.get("/{target_node_id}", response_model=List[Dict[str, Any]])
async def get_dynamic_learning_path(
    target_node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    service: GraphReasoningService = Depends(get_graph_reasoning_service)
):
    """
    获取到达目标节点的动态学习路径 (DAG Topological Sort)
    
    返回按学习顺序排列的节点列表，包含状态（locked/unlocked/mastered）。
    """
    path = await service.generate_learning_path(UUID(user_id), target_node_id)
    
    if not path:
        # 可能是目标节点不存在，或者没有路径（比如孤立点）
        # 这里返回空列表而不是 404，由前端处理提示 "无需前置" 或 "未找到"
        return []
        
    return path
