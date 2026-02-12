"""
Collaboration Node - Phase 3

Responsibilities:
1. Detect if multi-agent collaboration is needed
2. Coordinate multiple agents in sequential execution
3. Aggregate tool_calls from each agent
"""
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage
from loguru import logger

from app.agents.graph.expert_registry import resolve_node_name
from app.agents.graph.state import SparkleState


async def collaboration_node(state: SparkleState) -> SparkleState:
    """Multi-Agent Collaboration Node

    Collaboration modes:
    - single: Single agent processing
    - sequential: Multiple agents in sequence (agent2 based on agent1 results)
    - parallel: Multiple agents in parallel (merge all results)

    Collaboration examples:
    1. "Create final exam study plan" -> galaxy_guide (knowledge graph) + exam_oracle (exam focus) + time_tutor (schedule)
    2. "I'm weak in math, how to prepare for calculus exam" -> galaxy_guide (prerequisites) + exam_oracle (exam analysis)
    """
    messages = state["messages"]

    user_message = _get_latest_human_message(messages)

    # If a collaboration plan is already in progress, continue it.
    collaboration_mode = state.get("collaboration_mode")
    collaboration_order = state.get("collaboration_order")
    collaboration_agents = state.get("collaboration_agents")
    if collaboration_mode in {"sequential", "parallel"} and collaboration_order:
        normalized_order = _normalize_order(collaboration_order, default_task=user_message)
        collaboration_plan = {
            "mode": collaboration_mode,
            "agents": collaboration_agents or [],
            "order": normalized_order,
        }
    else:
        # 1. Analyze if collaboration is needed
        collaboration_plan = _analyze_collaboration_needs(user_message)

    if collaboration_plan["mode"] == "single":
        # Single agent mode, route directly
        state["next_step"] = collaboration_plan["primary_agent"]
        state["active_agent"] = "router"
        state["collaboration_mode"] = "single"
        return state

    # 2. Multi-agent collaboration mode
    logger.info(
        f"Multi-agent collaboration: {collaboration_plan['mode']}, "
        f"agents: {collaboration_plan['agents']}"
    )

    # Record collaboration plan
    state["collaboration_mode"] = collaboration_plan["mode"]
    state["collaboration_agents"] = collaboration_plan["agents"]
    state["collaboration_order"] = collaboration_plan["order"]

    # 3. Execute agents in sequence (sequential mode)
    # Note: This just sets the routing order, actual execution done by LangGraph edges
    collaboration_index = state.get("collaboration_index", 0)
    if collaboration_index >= len(collaboration_plan["order"]):
        state["next_step"] = "aggregator"
        state["active_agent"] = "collaboration"
        return state

    agent_spec = collaboration_plan["order"][collaboration_index]
    agent_name = agent_spec["agent"]
    agent_task = agent_spec.get("task", user_message)

    logger.info(f"Executing agent: {agent_name} with task: {agent_task[:50]}...")

    # Set next agent to execute
    state["next_step"] = agent_name
    state["active_agent"] = agent_name
    state["collaboration_context"] = agent_task
    state["collaboration_index"] = collaboration_index + 1

    # Return updated state
    return state


def _get_latest_human_message(messages: list[BaseMessage]) -> str:
    """Return the most recent HumanMessage content (fallback to last message)."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content
    return messages[-1].content if messages else ""


def _analyze_collaboration_needs(message: str) -> dict[str, Any]:
    """Analyze if message needs multi-agent collaboration

    Returns:
        Dict with:
        - mode: "single", "sequential", or "parallel"
        - primary_agent: Primary responsible agent
        - agents: List of participating agents
        - order: Execution order
    """
    msg_lower = message.lower()

    # Collaboration mode keywords
    collaboration_keywords = {
        ("复习计划", "学习计划", "study plan", "复习策略"): {
            "mode": "sequential",
            "agents": ["galaxy_guide", "exam_oracle", "time_tutor"],
            "order": [
                {"agent": "galaxy_guide", "task": f"Analyze knowledge prerequisites: {message}"},
                {"agent": "exam_oracle", "task": f"Analyze exam focus: {message}"},
                {"agent": "time_tutor", "task": f"Create schedule: {message}"},
            ]
        },
        ("基础差", "先修", "prerequisite", "知识关联"): {
            "mode": "sequential",
            "agents": ["galaxy_guide", "time_tutor"],
            "order": [
                {"agent": "galaxy_guide", "task": f"Analyze knowledge graph: {message}"},
                {"agent": "time_tutor", "task": f"Create foundation plan: {message}"},
            ]
        },
        ("考试预测", "重点", "exam focus", "past paper"): {
            "mode": "sequential",
            "agents": ["exam_oracle", "time_tutor"],
            "order": [
                {"agent": "exam_oracle", "task": f"Analyze exam focus: {message}"},
                {"agent": "time_tutor", "task": f"Schedule review: {message}"},
            ]
        },
    }

    # Check if matches collaboration scenario
    for keywords, plan in collaboration_keywords.items():
        if any(kw in msg_lower for kw in keywords):
            return plan

    # Default single agent mode
    return {
        "mode": "single",
        "primary_agent": _classify_primary_agent(message),
        "agents": [],
        "order": []
    }


def _normalize_order(order: list[Any], default_task: str) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in order:
        if isinstance(item, dict):
            agent = item.get("agent")
            if not agent:
                continue
            resolved = resolve_node_name(str(agent))
            if not resolved:
                continue
            normalized.append(
                {
                    "agent": resolved,
                    "task": str(item.get("task") or default_task),
                }
            )
            continue
        if isinstance(item, str):
            resolved = resolve_node_name(item)
            if resolved:
                normalized.append({"agent": resolved, "task": default_task})
    return normalized


def _classify_primary_agent(message: str) -> str:
    """Classify primary agent"""
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["知识", "概念", "关联", "prerequisite", "graph"]):
        return "galaxy_guide"
    if any(kw in msg_lower for kw in ["考试", "预测", "重点", "exam", "paper"]):
        return "exam_oracle"
    if any(kw in msg_lower for kw in ["时间", "任务", "schedule", "task", "pomodoro"]):
        return "time_tutor"

    return "time_tutor"  # Default


async def collaboration_aggregator_node(state: SparkleState) -> SparkleState:
    """Collaboration Result Aggregator Node

    Collect outputs from all participating agents, aggregate to ExecutablePlan
    """
    def _normalize_tool_call(tc) -> dict:
        if isinstance(tc, dict):
            name = tc.get("name") or tc.get("tool") or tc.get("function", {}).get("name")
            args = tc.get("args") or tc.get("arguments") or tc.get("function", {}).get("arguments", {})
            call_id = tc.get("id") or tc.get("tool_call_id")
        else:
            name = getattr(tc, "name", None) or getattr(tc, "tool", None)
            args = getattr(tc, "args", None) or getattr(tc, "arguments", None)
            call_id = getattr(tc, "id", None) or getattr(tc, "tool_call_id", None)

        if isinstance(args, str):
            try:
                import json
                args = json.loads(args)
            except Exception:
                args = {"_raw": args}

        return {
            "id": call_id,
            "name": name,
            "args": args
        }

    # Extract all tool_calls
    all_tool_calls = []
    agents_involved = state.get("collaboration_agents", [])

    messages = state.get("messages", [])
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_call = _normalize_tool_call(tc)
                if not tool_call.get("name"):
                    continue
                # Mark which agent called it
                tool_call["agent"] = state.get("active_agent", "unknown")
                all_tool_calls.append(tool_call)

    # Record collaboration metadata
    state["collaboration_results"] = {
        "agents_involved": agents_involved,
        "tool_calls_count": len(all_tool_calls),
        "collaboration_mode": state.get("collaboration_mode", "single")
    }

    logger.info(
        f"Collaboration aggregated: {len(agents_involved)} agents, "
        f"{len(all_tool_calls)} tool calls"
    )

    return state
