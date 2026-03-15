from __future__ import annotations

import time
from collections.abc import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.state import SparkleState
from app.core.metrics import AGENT_PERFORMANCE_RECORDED_TOTAL
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback
from app.orchestration.agent_scoring import AgentScoringService


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
            AGENT_PERFORMANCE_RECORDED_TOTAL.labels(
                agent_id=agent_id,
                success="true",
            ).inc()
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
            AGENT_PERFORMANCE_RECORDED_TOTAL.labels(
                agent_id=agent_id,
                success="false",
            ).inc()
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
            "active_agent": agent_id,
            "next_step": None,
        }

    return _node
