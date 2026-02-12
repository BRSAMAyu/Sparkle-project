from __future__ import annotations

from collections.abc import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.state import SparkleState


def create_specialist_node(
    *,
    agent_id: str,
    planning_prompt: str,
    task_prompt_prefix: str | None = None,
    toolset: list | None = None,
) -> Callable[[SparkleState], dict]:
    """Create reusable graph node for specialists not hardcoded in workflow."""

    async def _node(state: SparkleState) -> dict:
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
        response = await llm.ainvoke(messages)

        return {
            "messages": [response],
            "active_agent": agent_id,
            "next_step": None,
        }

    return _node
