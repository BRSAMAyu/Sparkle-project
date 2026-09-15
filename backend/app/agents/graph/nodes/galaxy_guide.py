from __future__ import annotations

import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import (
    create_knowledge_node,
    link_nodes,
    query_knowledge,
)
from app.agents.graph.state import SparkleState
from app.core.metrics import AGENT_PERFORMANCE_RECORDED_TOTAL
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback
from app.orchestration.agent_scoring import AgentScoringService


def _build_system_prompt(state: SparkleState, *, planning: bool) -> str:
    collaboration_mode = str(state.get("collaboration_mode") or "").strip()
    collaboration_agents = [
        str(agent).strip()
        for agent in (state.get("collaboration_agents") or [])
        if str(agent).strip()
    ]
    other_agents = [agent for agent in collaboration_agents if agent != "galaxy_guide"]

    if planning:
        prompt = (
            "你是星图导航（规划模式），擅长在知识图谱中定位前置与关联概念。\n"
            "## 思维框架\n"
            "先识别关键概念与前置依赖，再决定需要补齐的知识点。\n"
            "## 规划输出\n"
            "必须用 tool calls 检索或创建知识节点，不要直接给最终答案。"
        )
    else:
        prompt = (
            "你是星图导航，擅长用知识图谱视角解释概念与前置依赖。\n"
            "## 思维框架\n"
            "先定位概念位置与前置关系，再指出关键关联与易混点。\n"
            "## 输出格式\n"
            "1. 核心判断（1 句）\n"
            "2. 2-3 条知识关联/前置说明\n"
            "3. 1 条可执行建议（补哪块/如何练）\n"
            "## 个性化适配\n"
            "若上文包含用户偏好或难度提示，请据此调整术语密度与解释深度。"
        )

    if collaboration_mode and other_agents:
        prompt += (
            "\n\n## 协作须知\n"
            f"协作模式：{collaboration_mode}\n"
            f"其他参与专家：{', '.join(other_agents)}\n"
            "专注于知识结构与前置依赖，不要重复他人内容。\n"
            "关键论点可简短标注“星图导航视角”。"
        )
    return prompt


# --- 2. 节点逻辑 ---
async def galaxy_guide_node(state: SparkleState, config: dict | None = None):
    """
    Knowledge Galaxy 专家
    负责解释概念、查询图谱
    """
    stream_cb = get_stream_callback(config)
    agent_id = "galaxy_guide"
    activity_metadata = {
        "collaboration_mode": str(state.get("collaboration_mode") or ""),
        "phase": "analysis",
    }
    await emit_agent_activity(stream_cb, agent_id=agent_id, status="active", metadata=activity_metadata)
    started_at = time.time()
    messages = state["messages"]
    collaboration_context = state.get("collaboration_context")
    if collaboration_context:
        messages = list(messages)
        messages.append(HumanMessage(content=collaboration_context))

    planning_mode = state.get("planning_mode") or state.get("_planning_mode")
    messages = list(messages)
    messages.insert(0, SystemMessage(content=_build_system_prompt(state, planning=bool(planning_mode))))

    # 获取 DeepSeek 或强推理模型
    llm = LLMFactory.get_llm("galaxy_guide")

    # 绑定工具
    tools = [query_knowledge, create_knowledge_node, link_nodes]
    llm_with_tools = llm.bind_tools(tools)

    # 执行
    # 注意：这里我们只传入 messages，LangGraph 会自动处理历史
    try:
        response = await llm_with_tools.ainvoke(messages)
        duration_ms = (time.time() - started_at) * 1000
        tool_calls_count = len(getattr(response, "tool_calls", []) or [])
        result_summary = None
        content = getattr(response, "content", None)
        if content:
            result_summary = str(content)[:80]
        await AgentScoringService(None).record_from_runtime(
            redis_client=(config or {}).get("configurable", {}).get("redis_client"),
            state=state,
            agent_id=agent_id,
            latency_ms=duration_ms,
            success=True,
            tool_calls_count=tool_calls_count,
            result_used=tool_calls_count > 0,
            intent_type=((state.get("_planning_constraints") or {}).get("route_intent")),
        )
        AGENT_PERFORMANCE_RECORDED_TOTAL.labels(agent_id=agent_id, success="true").inc()
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="completed",
            duration_ms=duration_ms,
            result_summary=result_summary,
            metadata=activity_metadata,
        )
    except Exception as exc:
        duration_ms = (time.time() - started_at) * 1000
        await AgentScoringService(None).record_from_runtime(
            redis_client=(config or {}).get("configurable", {}).get("redis_client"),
            state=state,
            agent_id=agent_id,
            latency_ms=duration_ms,
            success=False,
            tool_calls_count=0,
            result_used=False,
            intent_type=((state.get("_planning_constraints") or {}).get("route_intent")),
        )
        AGENT_PERFORMANCE_RECORDED_TOTAL.labels(agent_id=agent_id, success="false").inc()
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="error",
            duration_ms=duration_ms,
            result_summary=str(exc)[:80],
            metadata=activity_metadata,
        )
        raise

    return {
        "messages": [response],
        "active_agent": "galaxy_guide",
        "next_step": None # 任务结束 (除非有 Tool Call，LangGraph 引擎会自动处理)
    }
