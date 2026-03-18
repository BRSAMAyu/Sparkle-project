from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.graph.expert_registry import (
    get_graph_expert_specs,
    get_graph_routable_targets,
    resolve_node_name,
)
from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.collaboration import analyze_collaboration_plan
from app.agents.graph.state import SparkleState
from app.config import settings
from app.core.metrics import AGENT_ROUTING_QUALITY_PROMPT_TOTAL
from app.orchestration.agent_scoring import AgentScoringService


class RouteDecision(BaseModel):
    """Router structured output."""

    target_agent: str = Field(..., description="The specialist agent best suited to handle the user query.")
    reasoning: str = Field(..., description="Brief reason for this routing decision.")
    needs_clarification: bool = Field(False, description="True if user query is too vague.")


PLANNING_STATUSES = ("gathering_info", "drafting", "reviewing", "executing", "completed")


def _infer_plan_type(state: SparkleState) -> str:
    """Infer plan type from context and messages."""
    messages = state.get("messages", [])
    if not messages:
        return "routine"

    last_message = messages[-1]
    user_query = last_message.content.lower() if last_message else ""

    if any(k in user_query for k in ["sprint", "突击", "冲刺", "cram", "focus"]):
        return "sprint"
    if any(k in user_query for k in ["week", "weekly", "周计划", "本周"]):
        return "routine"
    if any(k in user_query for k in ["month", "monthly", "月计划", "长期"]):
        return "long_term"

    return "routine"


async def _build_quality_context(
    *,
    state: SparkleState,
    config: dict | None,
) -> str:
    if not settings.ENABLE_AGENT_QUALITY_FEEDBACK:
        return ""

    redis_client = (config or {}).get("configurable", {}).get("redis_client")
    user_id = str(state.get("user_id") or "").strip()
    if not redis_client or not user_id:
        return ""

    agent_ids = [spec.node_name for spec in get_graph_expert_specs()]
    quality_lines = await AgentScoringService(redis_client).get_quality_prompt_lines(
        user_id=user_id,
        agent_ids=agent_ids,
    )
    if not quality_lines:
        return ""

    AGENT_ROUTING_QUALITY_PROMPT_TOTAL.labels(layer="router").inc()
    return "\nRecent agent quality signals:\n" + "\n".join(quality_lines)


async def router_node(state: SparkleState, config: dict | None = None):
    """
    Semantic router node.

    Routes the latest user query to the best specialist and decides whether
    collaboration should be used.
    """
    last_message = state["messages"][-1]
    user_query = last_message.content

    current_status = state.get("planning_status")
    if current_status in [None, "completed"]:
        planning_status = "gathering_info"
    elif current_status in PLANNING_STATUSES:
        planning_status = current_status
    else:
        planning_status = "gathering_info"

    llm = LLMFactory.get_llm("router")
    structured_llm = llm.with_structured_output(RouteDecision)

    routable_targets = get_graph_routable_targets()
    target_list_text = "\n    - " + "\n    - ".join(routable_targets)
    quality_context = await _build_quality_context(state=state, config=config)

    system_prompt = """You are the Dispatcher for Sparkle AI.
    Analyze the user's query and route it to the best specialist.
    Allowed targets are:
    {target_list}

    If query is ambiguous, default to 'study_buddy'.{quality_context}

    Return JSON with keys: target_agent, reasoning, needs_clarification.
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{query}"),
        ]
    )

    chain = prompt | structured_llm
    try:
        decision: RouteDecision = await chain.ainvoke(
            {
                "query": user_query,
                "target_list": target_list_text,
                "quality_context": quality_context,
            }
        )
    except Exception as exc:
        logger.warning(f"Router LLM failed, falling back to study_buddy: {exc}")
        decision = RouteDecision(
            target_agent="study_buddy",
            reasoning="Fallback routing due to LLM parse failure.",
            needs_clarification=False,
        )

    resolved_target = resolve_node_name(decision.target_agent) or "study_buddy"
    if resolved_target != decision.target_agent:
        decision = RouteDecision(
            target_agent=resolved_target,
            reasoning=f"{decision.reasoning} | normalized:{resolved_target}",
            needs_clarification=decision.needs_clarification,
        )

    state_updates = {
        "next_step": resolved_target,
        "active_agent": "router",
        "planning_status": planning_status,
    }

    if not state.get("collaboration_mode"):
        try:
            collaboration_plan = await analyze_collaboration_plan(
                user_query,
                state=state,
                config=config,
            )
            if collaboration_plan.get("mode") != "single":
                state_updates.update(
                    {
                        "collaboration_mode": collaboration_plan.get("mode"),
                        "collaboration_agents": collaboration_plan.get("agents", []),
                        "collaboration_order": collaboration_plan.get("order", []),
                        "collaboration_index": 0,
                        "next_step": "collaboration",
                    }
                )
            else:
                state_updates["collaboration_mode"] = "single"
                primary_agent = resolve_node_name(collaboration_plan.get("primary_agent")) or resolved_target
                state_updates["next_step"] = primary_agent
        except Exception as exc:
            logger.warning(f"Failed to analyze collaboration needs: {exc}")

    executable_plan = state.get("executable_plan")
    if executable_plan and isinstance(executable_plan, dict):
        plan_id = executable_plan.get("plan_id")
        if plan_id:
            current_plan = state.get("current_plan", {})
            if not current_plan or not isinstance(current_plan, dict):
                current_plan = {}
            state_updates["current_plan"] = {
                "plan_id": plan_id,
                "plan_type": _infer_plan_type(state),
                "status": "drafting",
            }
            state_updates["planning_status"] = "drafting"
            logger.info(f"Router: Set current_plan to {plan_id}, status=drafting")

    return state_updates
