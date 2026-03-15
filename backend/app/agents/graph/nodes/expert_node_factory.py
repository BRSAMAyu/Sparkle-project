from __future__ import annotations

import time
from collections.abc import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.state import SparkleState
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback


def create_specialist_node(
    *,
    agent_id: str,
    planning_prompt: str,
    task_prompt_prefix: str | None = None,
    toolset: list | None = None,
) -> Callable[[SparkleState, dict | None], dict]:
    """Create reusable graph node for specialists not hardcoded in workflow."""

    async def _node(state: SparkleState, config: dict | None = None) -> dict:
        stream_cb = get_stream_callback(config)
        await emit_agent_activity(stream_cb, agent_id=agent_id, status="active")
        started_at = time.time()
        messages = state["messages"]
        collaboration_context = state.get("collaboration_context")
        if collaboration_context:
            messages = list(messages)
            task_prefix = task_prompt_prefix or "Collaboration task"
            messages.append(HumanMessage(content=f"[{task_prefix}] {collaboration_context}"))

        if state.get("planning_mode") or state.get("_planning_mode"):
            messages = list(messages)
            messages.insert(0, SystemMessage(content=planning_prompt))

        llm = LLMFactory.get_llm(agent_id)
        if toolset:
            llm = llm.bind_tools(toolset)
        try:
            response = await llm.ainvoke(messages)
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
            "active_agent": agent_id,
            "next_step": None,
        }

    return _node
