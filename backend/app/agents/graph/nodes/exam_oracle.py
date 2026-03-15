import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import (
    create_plan,
    create_task,
    generate_tasks_for_plan,
    query_knowledge,
)
from app.agents.graph.state import SparkleState
from app.core.metrics import AGENT_PERFORMANCE_RECORDED_TOTAL
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback
from app.orchestration.agent_scoring import AgentScoringService

# --- 2. 节点逻辑 (Node Logic) ---

async def exam_oracle_node(state: SparkleState, config: dict | None = None):
    """
    Exam Oracle 专家节点
    负责考点预测、真题分析、模拟出题、文档清洗、任务调度
    """
    stream_cb = get_stream_callback(config)
    agent_id = "exam_oracle"
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

    if state.get("planning_mode") or state.get("_planning_mode"):
        messages = list(messages)
        messages.insert(
            0,
            SystemMessage(
                content=(
                    "You are in planning-only mode. Use tool calls to create exam-focused plans "
                    "and tasks (create_plan, generate_tasks_for_plan, create_task, query_knowledge). "
                    "Do not provide a final narrative response."
                )
            ),
        )

    # 使用强推理模型 (GPT-4o) 处理复杂分析
    llm = LLMFactory.get_llm("exam_oracle")

    # 绑定工具 (aligned with dynamic tool registry)
    tools = [
        query_knowledge,
        create_plan,
        generate_tasks_for_plan,
        create_task,
    ]
    llm_with_tools = llm.bind_tools(tools)

    # 执行推理
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
        "active_agent": "exam_oracle",
        "next_step": None
    }
