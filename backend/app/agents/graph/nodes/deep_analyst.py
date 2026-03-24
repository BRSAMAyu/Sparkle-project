from __future__ import annotations
import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import create_knowledge_node, query_knowledge
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
    other_agents = [agent for agent in collaboration_agents if agent != "deep_analyst"]

    if planning:
        prompt = (
            "你是深度分析师（规划模式）。\n"
            "## 思维框架\n"
            "先收集关键证据与观点，再建立论证框架与边界。\n"
            "## 规划输出\n"
            "必须用 tool calls 检索或构建知识节点，不要直接给最终答案。"
        )
    else:
        prompt = (
            "你是深度分析师，擅长多视角分析与结构化论证。\n"
            "## 思维框架\n"
            "先给出结论，再展开证据链与反方边界。\n"
            "## 输出格式\n"
            "1. 核心判断（1 句）\n"
            "2. 2-3 条证据/论点（含简要依据）\n"
            "3. 1 条可执行建议或结论落地方式\n"
            "## 个性化适配\n"
            "若上文包含用户偏好或难度提示，请据此调整深度与篇幅。"
        )

    if collaboration_mode and other_agents:
        prompt += (
            "\n\n## 协作须知\n"
            f"协作模式：{collaboration_mode}\n"
            f"其他参与专家：{', '.join(other_agents)}\n"
            "专注于分析框架与证据链，不要重复他人内容。\n"
            "关键论点可简短标注“深度分析视角”。"
        )
    return prompt


async def deep_analyst_node(state: SparkleState, config: dict | None = None):
    stream_cb = get_stream_callback(config)
    agent_id = "deep_analyst"
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

    llm = LLMFactory.get_llm("deep_analyst")
    llm_with_tools = llm.bind_tools([query_knowledge, create_knowledge_node])
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
        "active_agent": "deep_analyst",
        "next_step": None,
    }
