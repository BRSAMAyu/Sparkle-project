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
from app.orchestration.chat_modes import CHAT_MODE_EXPERT_AUTO
from app.orchestration.expert_strategy_v2 import ExpertStrategyV2
from app.orchestration.mode_workflow_config import get_workflow_config


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
        collaboration_plan = _analyze_collaboration_needs(user_message, state=state)

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


def _analyze_collaboration_needs(message: str, state: SparkleState | None = None) -> dict[str, Any]:
    """Analyze if message needs multi-agent collaboration

    Returns:
        Dict with:
        - mode: "single", "sequential", or "parallel"
        - primary_agent: Primary responsible agent
        - agents: List of participating agents
        - order: Execution order
    """
    state_data = state or {}
    mode_name = str(state_data.get("mode_name") or "").strip()
    mode_config = get_workflow_config(mode_name) if mode_name else None

    # Priority 1: mode workflow config (single source for rich mode decomposition).
    if mode_config and mode_config.collaboration_agents:
        configured_order = _normalize_order(mode_config.collaboration_order, default_task=message)
        if not configured_order:
            configured_order = _build_order_from_agents(mode_config.collaboration_agents, message)
        configured_agents = [step["agent"] for step in configured_order]
        if configured_agents:
            return {
                "mode": mode_config.collaboration_mode if len(configured_agents) > 1 else "single",
                "primary_agent": configured_agents[0],
                "agents": configured_agents,
                "order": configured_order,
            }

    # Priority 2: explicit selected experts propagated from orchestrator strategy.
    selected_experts = state_data.get("selected_experts")
    if isinstance(selected_experts, list):
        normalized_agents = []
        for expert_id in selected_experts:
            resolved = resolve_node_name(str(expert_id))
            if resolved and resolved not in normalized_agents:
                normalized_agents.append(resolved)
        if normalized_agents:
            return {
                "mode": "sequential" if len(normalized_agents) > 1 else "single",
                "primary_agent": normalized_agents[0],
                "agents": normalized_agents,
                "order": _build_order_from_agents(normalized_agents, message),
            }

    # Priority 3: scored strategy (v2) for dynamic collaboration routing.
    user_profile = state_data.get("user_profile")
    user_preferences = user_profile if isinstance(user_profile, dict) else {}
    chat_mode = mode_name or CHAT_MODE_EXPERT_AUTO
    try:
        decision = ExpertStrategyV2.route(
            message=message,
            chat_mode=chat_mode,
            user_preferences=user_preferences,
            user_context=user_preferences,
        )
        resolved_agents: list[str] = []
        for expert_id in decision.selected_experts:
            resolved = resolve_node_name(str(expert_id))
            if resolved and resolved not in resolved_agents:
                resolved_agents.append(resolved)
        if resolved_agents:
            return {
                "mode": "sequential" if len(resolved_agents) > 1 else "single",
                "primary_agent": resolved_agents[0],
                "agents": resolved_agents,
                "order": _build_order_from_agents(resolved_agents, message),
            }
    except Exception as exc:
        logger.warning(f"ExpertStrategyV2 route failed in collaboration node: {exc}")

    # Priority 4: legacy keyword fallback only.
    legacy_plan = _legacy_keyword_plan(message)
    if legacy_plan:
        return legacy_plan

    primary_agent = _classify_primary_agent(message)
    return {
        "mode": "single",
        "primary_agent": primary_agent,
        "agents": [],
        "order": [],
    }


def _legacy_keyword_plan(message: str) -> dict[str, Any] | None:
    msg_lower = message.lower()
    collaboration_keywords = {
        ("复习计划", "学习计划", "study plan", "复习策略"): ["galaxy_guide", "exam_oracle", "time_tutor"],
        ("基础差", "先修", "prerequisite", "知识关联"): ["galaxy_guide", "time_tutor"],
        ("考试预测", "重点", "exam focus", "past paper"): ["exam_oracle", "time_tutor"],
    }
    for keywords, agents in collaboration_keywords.items():
        if any(kw in msg_lower for kw in keywords):
            return {
                "mode": "sequential" if len(agents) > 1 else "single",
                "primary_agent": agents[0],
                "agents": agents,
                "order": _build_order_from_agents(agents, message),
            }
    return None


def _build_order_from_agents(agents: list[str], message: str) -> list[dict[str, str]]:
    order: list[dict[str, str]] = []
    for expert in agents:
        resolved = resolve_node_name(str(expert))
        if not resolved:
            continue
        order.append({"agent": resolved, "task": f"[{resolved}] {message}"})
    return order


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
