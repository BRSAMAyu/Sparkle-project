import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import create_knowledge_node, query_knowledge
from app.agents.graph.state import SparkleState
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback


DEEP_ANALYST_PLANNING_PROMPT = (
    "You are in planning-only mode. Perform deep analysis planning with evidence retrieval. "
    "Use tool calls (query_knowledge, create_knowledge_node) when needed. "
    "Do not provide final narrative answers."
)


async def deep_analyst_node(state: SparkleState, config: dict | None = None):
    stream_cb = get_stream_callback(config)
    agent_id = "deep_analyst"
    await emit_agent_activity(stream_cb, agent_id=agent_id, status="active")
    started_at = time.time()
    messages = state["messages"]
    collaboration_context = state.get("collaboration_context")
    if collaboration_context:
        messages = list(messages)
        messages.append(HumanMessage(content=collaboration_context))

    if state.get("planning_mode") or state.get("_planning_mode"):
        messages = list(messages)
        messages.insert(0, SystemMessage(content=DEEP_ANALYST_PLANNING_PROMPT))

    llm = LLMFactory.get_llm("deep_analyst")
    llm_with_tools = llm.bind_tools([query_knowledge, create_knowledge_node])
    try:
        response = await llm_with_tools.ainvoke(messages)
        duration_ms = (time.time() - started_at) * 1000
        result_summary = None
        content = getattr(response, "content", None)
        if content:
            result_summary = str(content)[:80]
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="completed",
            duration_ms=duration_ms,
            result_summary=result_summary,
        )
    except Exception as exc:
        duration_ms = (time.time() - started_at) * 1000
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="error",
            duration_ms=duration_ms,
            result_summary=str(exc)[:80],
        )
        raise

    return {
        "messages": [response],
        "active_agent": "deep_analyst",
        "next_step": None,
    }
