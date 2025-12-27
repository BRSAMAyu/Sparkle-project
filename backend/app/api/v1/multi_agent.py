"""
Multi-Agent API - 多智能体协作API

提供多专家智能体协作服务
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from loguru import logger

from app.core.deps import get_current_user
from app.models.user import User
from app.agents.orchestrator_agent import create_multi_agent_workflow


router = APIRouter(prefix="/multi-agent", tags=["multi-agent"])


class MultiAgentRequest(BaseModel):
    """多智能体请求"""
    query: str
    session_id: str
    enable_trace: bool = True  # 是否启用追踪（用于可视化）


class MultiAgentResponse(BaseModel):
    """多智能体响应"""
    response_text: str
    agent_role: str
    agent_name: str

    # 可选字段
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    # 追踪信息
    trace: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=MultiAgentResponse)
async def multi_agent_chat(
    request: MultiAgentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    多智能体聊天 API

    流程：
    1. 分析用户查询
    2. 路由到合适的专家智能体
    3. 执行智能体协作
    4. 返回整合后的响应

    示例场景：
    - 用户：\"用 Python 实现牛顿法求解方程 x^2 - 2 = 0，并写一篇学习报告\"
    - 系统：调用 CodeAgent + MathAgent + WritingAgent
    """
    try:
        logger.info(f"Multi-agent request from user {current_user.id}: {request.query[:50]}...")

        # 创建工作流
        workflow = create_multi_agent_workflow()

        # 执行
        result = await workflow.execute(
            user_query=request.query,
            user_id=str(current_user.id),
            session_id=request.session_id
        )

        # 构建追踪信息（用于前端可视化）
        trace = None
        if request.enable_trace:
            trace = {
                "workflow_type": "multi_agent",
                "agents_involved": result["metadata"].get("agents_involved", [result["agent_name"]]),
                "is_multi_agent": result["metadata"].get("multi_agent", False),
                "confidence": result.get("confidence", 0.8),
            }

        return MultiAgentResponse(
            response_text=result["response_text"],
            agent_role=result["agent_role"],
            agent_name=result["agent_name"],
            reasoning=result.get("reasoning"),
            confidence=result.get("confidence"),
            metadata=result.get("metadata"),
            trace=trace
        )

    except Exception as e:
        logger.error(f"Multi-agent error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Multi-agent processing failed: {str(e)}"
        )


@router.get("/agents")
async def list_agents(current_user: User = Depends(get_current_user)):
    """
    列出所有可用的专家智能体

    用途：前端展示智能体列表
    """
    from app.agents import AGENT_REGISTRY

    agents_info = []
    for agent_type, agent_class in AGENT_REGISTRY.items():
        if agent_type == "orchestrator":
            continue  # 跳过协调者

        agent_instance = agent_class()
        agents_info.append({
            "type": agent_type,
            "name": agent_instance.name,
            "role": agent_instance.role.value,
            "description": agent_instance.description,
            "capabilities": agent_instance.capabilities
        })

    return {
        "total_agents": len(agents_info),
        "agents": agents_info
    }


@router.post("/route-preview")
async def preview_routing(
    request: MultiAgentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    路由预览 - 显示查询会被路由到哪些智能体

    用途：前端实时显示"正在咨询 X 专家"
    """
    from app.agents.orchestrator_agent import OrchestratorAgent

    try:
        orchestrator = OrchestratorAgent()
        selected_agents = await orchestrator._route_query(request.query)

        # 计算每个智能体的匹配度
        agent_scores = []
        for agent in orchestrator.specialist_agents:
            score = agent.can_handle(request.query)
            agent_scores.append({
                "agent_name": agent.name,
                "agent_type": agent.role.value,
                "confidence": round(score, 2),
                "selected": agent in selected_agents
            })

        agent_scores.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "query": request.query,
            "routing_decision": [
                {"name": agent.name, "type": agent.role.value}
                for agent in selected_agents
            ],
            "all_scores": agent_scores
        }

    except Exception as e:
        logger.error(f"Routing preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
