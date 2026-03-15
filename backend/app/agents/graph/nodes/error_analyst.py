import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import query_error_history, record_error
from app.agents.graph.state import SparkleState
from app.core.metrics import AGENT_PERFORMANCE_RECORDED_TOTAL
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback
from app.orchestration.agent_scoring import AgentScoringService


ERROR_ANALYST_PLANNING_PROMPT = (
    "You are in planning-only mode for error diagnosis. "
    "Classify error type, identify root cause, and use tool calls "
    "(query_error_history, record_error) as needed. "
    "Do not provide final narrative answers."
)


async def error_analyst_node(state: SparkleState, config: dict | None = None):
    stream_cb = get_stream_callback(config)
    agent_id = "error_analyst"
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
        messages.insert(0, SystemMessage(content=ERROR_ANALYST_PLANNING_PROMPT))

    llm = LLMFactory.get_llm("error_analyst")
    llm_with_tools = llm.bind_tools([record_error, query_error_history])
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
        "active_agent": "error_analyst",
        "next_step": None,
    }
