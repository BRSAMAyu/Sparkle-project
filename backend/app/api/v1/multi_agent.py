"""
Multi-Agent API - 多智能体协作API

提供多专家智能体协作服务
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator_agent import create_multi_agent_workflow
from app.api.deps import get_current_user
from app.config import settings
from app.core.agent_profiles import get_public_agent_catalog, get_public_mode_catalog
from app.db.session import get_db
from app.models.user import User
from app.services.custom_expert_service import CustomExpertService

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
    reasoning: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] | None = None

    # 追踪信息
    trace: dict[str, Any] | None = None


class CustomExpertCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    system_prompt: str = Field(..., min_length=10, max_length=8000)
    base_expert_id: str | None = Field(default=None, max_length=100)
    preferred_model_key: str | None = Field(default=None, max_length=100)
    preferred_model_tier: str | None = Field(default=None, max_length=40)
    reasoning_mode: Literal["fast", "balanced", "deep"] = "balanced"
    metadata_json: dict[str, Any] | None = None


class CustomExpertUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    system_prompt: str | None = Field(default=None, min_length=10, max_length=8000)
    base_expert_id: str | None = Field(default=None, max_length=100)
    preferred_model_key: str | None = Field(default=None, max_length=100)
    preferred_model_tier: str | None = Field(default=None, max_length=40)
    reasoning_mode: Literal["fast", "balanced", "deep"] | None = None
    metadata_json: dict[str, Any] | None = None
    is_enabled: bool | None = None


class CustomExpertTeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    collaboration_mode: Literal["auto", "single", "sequential", "parallel", "debate", "delegation"] = "auto"
    expert_ids: list[str] = Field(default_factory=list)
    answer_expert_ids: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] | None = None


class CustomExpertTeamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    collaboration_mode: Literal["auto", "single", "sequential", "parallel", "debate", "delegation"] | None = None
    expert_ids: list[str] | None = None
    answer_expert_ids: list[str] | None = None
    metadata_json: dict[str, Any] | None = None
    is_enabled: bool | None = None


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


@router.get("/catalog")
async def get_multi_agent_catalog(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unified catalog for public multi-agent modes and experts."""
    if not settings.ENABLE_EXPERT_ENTRY:
        return {
            "modes": [],
            "experts": [],
            "custom_experts": [],
            "custom_teams": [],
            "model_options": [],
            "total_experts": 0,
        }
    experts = get_public_agent_catalog()
    service = CustomExpertService(db)
    custom_payload = await service.build_catalog_payload(str(current_user.id))
    return {
        "modes": get_public_mode_catalog(),
        "experts": experts,
        "custom_experts": custom_payload["experts"],
        "custom_teams": custom_payload["teams"],
        "model_options": CustomExpertService.build_model_options(),
        "total_experts": len(experts),
    }


def _validate_expert_payload(
    payload: CustomExpertCreateRequest | CustomExpertUpdateRequest,
) -> None:
    if payload.preferred_model_tier and payload.preferred_model_tier not in CustomExpertService.valid_tier_values():
        raise HTTPException(status_code=422, detail="invalid preferred_model_tier")
    if payload.base_expert_id and payload.base_expert_id not in CustomExpertService.valid_base_expert_ids():
        raise HTTPException(status_code=422, detail="invalid base_expert_id")
    valid_model_keys = {item["key"] for item in CustomExpertService.build_model_options()}
    if payload.preferred_model_key and payload.preferred_model_key not in valid_model_keys:
        raise HTTPException(status_code=422, detail="invalid preferred_model_key")


@router.get("/custom-experts")
async def list_custom_experts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomExpertService(db)
    experts = [service.serialize_runtime_profile(item) for item in await service.list_custom_experts(str(current_user.id))]
    return {"experts": experts}


@router.post("/custom-experts")
async def create_custom_expert(
    request: CustomExpertCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_expert_payload(request)
    service = CustomExpertService(db)
    expert = await service.create_custom_expert(
        user_id=str(current_user.id),
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        base_expert_id=request.base_expert_id,
        preferred_model_key=request.preferred_model_key,
        preferred_model_tier=request.preferred_model_tier,
        reasoning_mode=request.reasoning_mode,
        metadata_json=request.metadata_json,
    )
    return service.serialize_runtime_profile(expert)


@router.put("/custom-experts/{expert_id}")
async def update_custom_expert(
    expert_id: str,
    request: CustomExpertUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_expert_payload(request)
    service = CustomExpertService(db)
    updated = await service.update_custom_expert(
        user_id=str(current_user.id),
        expert_id=expert_id,
        payload=request.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="custom expert not found")
    return service.serialize_runtime_profile(updated)


@router.delete("/custom-experts/{expert_id}")
async def delete_custom_expert(
    expert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomExpertService(db)
    deleted = await service.soft_delete_custom_expert(user_id=str(current_user.id), expert_id=expert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="custom expert not found")
    return {"success": True}


@router.get("/custom-teams")
async def list_custom_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomExpertService(db)
    teams = [service.serialize_team(item) for item in await service.list_custom_teams(str(current_user.id))]
    return {"teams": teams}


@router.post("/custom-teams")
async def create_custom_team(
    request: CustomExpertTeamCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomExpertService(db)
    team = await service.create_custom_team(
        user_id=str(current_user.id),
        name=request.name,
        description=request.description,
        collaboration_mode=request.collaboration_mode,
        expert_ids=request.expert_ids,
        answer_expert_ids=request.answer_expert_ids,
        metadata_json=request.metadata_json,
    )
    return service.serialize_team(team)


@router.put("/custom-teams/{team_id}")
async def update_custom_team(
    team_id: str,
    request: CustomExpertTeamUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomExpertService(db)
    updated = await service.update_custom_team(
        user_id=str(current_user.id),
        team_id=team_id,
        payload=request.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="custom team not found")
    return service.serialize_team(updated)


@router.delete("/custom-teams/{team_id}")
async def delete_custom_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomExpertService(db)
    deleted = await service.soft_delete_custom_team(user_id=str(current_user.id), team_id=team_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="custom team not found")
    return {"success": True}
