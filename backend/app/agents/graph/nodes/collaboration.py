"""
Collaboration node with sequential, parallel, debate, and delegation modes.
"""
from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.graph.expert_registry import (
    get_graph_expert_specs,
    get_node_function,
    resolve_node_name,
)
from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.state import SparkleState
from app.config import settings
from app.core.agent_profiles import ModelTier, TaskType
from app.core.metrics import (
    AGENT_COLLAB_DECISION_TOTAL,
    AGENT_COMBINATION_EXPLORATION_TOTAL,
)
from app.orchestration.agent_activity import AGENT_DISPLAY_CONFIG, emit_agent_activity, get_stream_callback
from app.orchestration.agent_scoring import AgentScoringService
from app.services.custom_expert_service import is_custom_expert_id

COLLABORATION_MODES = {"single", "sequential", "parallel", "debate", "delegation"}


class CollaborationPlanItem(BaseModel):
    agent: str = Field(..., description="Target agent id")
    task: str = Field(..., description="Subtask assigned to this agent")


class CollaborationDecision(BaseModel):
    mode: str = Field(..., description="single or multi")
    primary_agent: str = Field("study_buddy", description="Primary agent when single mode or delegation lead")
    agents: list[str] = Field(default_factory=list, description="Agents participating in collaboration")
    order: list[CollaborationPlanItem] = Field(default_factory=list, description="Execution order and task assignment")
    reasoning: str = Field("", description="Why this collaboration choice is made")
    execution_mode: str = Field(
        "sequential",
        description=(
            "Agent execution strategy: sequential, parallel, debate, or delegation. "
            "Use parallel for independent subtasks, debate for conflicting perspectives, "
            "delegation when one lead agent should decompose and synthesize."
        ),
    )


class DelegationTask(BaseModel):
    agent_id: str
    task: str


class DelegationPlan(BaseModel):
    subtasks: list[DelegationTask] = Field(default_factory=list)


def _planning_intent_type(state: SparkleState) -> str:
    planning_constraints = state.get("_planning_constraints") or {}
    route_intent = planning_constraints.get("route_intent")
    if route_intent:
        return str(route_intent)
    mode_name = state.get("mode_name")
    if mode_name:
        return str(mode_name)
    return "general"


def _activity_metadata(
    *,
    mode: str,
    phase: str = "analysis",
    task: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "collaboration_mode": mode,
        "phase": phase,
    }
    if task:
        payload["task"] = task[:120]
    return payload


async def _build_available_agents(
    *,
    user_id: str,
    redis_client,
) -> list[dict[str, Any]]:
    specs = [spec for spec in get_graph_expert_specs() if spec.supports_collaboration]
    scoring_service = AgentScoringService(redis_client)
    quality_scores = (
        await scoring_service.get_quality_scores(
            user_id=user_id,
            agent_ids=[spec.node_name for spec in specs],
        )
        if settings.ENABLE_AGENT_QUALITY_FEEDBACK and redis_client and user_id
        else {}
    )
    available_agents = []
    for spec in specs:
        display = AGENT_DISPLAY_CONFIG.get(spec.node_name, {})
        score = quality_scores.get(spec.node_name)
        available_agents.append(
            {
                "id": spec.node_name,
                "display_name": display.get("display_name", spec.node_name),
                "description": display.get("description", ""),
                "quality_score": round(score.quality_score, 4) if score else 0.5,
                "default_rank": spec.default_rank,
            }
        )
    return available_agents


def _clone_state_for_agent(
    state: SparkleState,
    *,
    agent_id: str,
    task: str | None = None,
) -> SparkleState:
    cloned = dict(state)
    cloned["messages"] = list(state.get("messages") or [])
    cloned["active_agent"] = agent_id
    if task:
        cloned["collaboration_context"] = task
    return cloned  # type: ignore[return-value]


def _extract_messages(result: dict[str, Any] | None) -> list[BaseMessage]:
    if not isinstance(result, dict):
        return []
    messages = result.get("messages")
    if isinstance(messages, list):
        return [message for message in messages if isinstance(message, BaseMessage)]
    return []


def _extract_content(result: dict[str, Any] | None) -> str:
    messages = _extract_messages(result)
    if messages:
        content = getattr(messages[-1], "content", None)
        if content:
            return str(content)
    return ""


def _extract_summary(result: dict[str, Any] | None) -> str:
    content = _extract_content(result)
    return content[:120] if content else "已完成本轮分析。"


def _get_latest_human_message(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return messages[-1].content if messages else ""


def _normalize_order(order: list[Any], default_task: str) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in order:
        if isinstance(item, dict):
            agent = item.get("agent")
            if not agent:
                continue
            resolved = _normalize_agent_identifier(str(agent))
            if not resolved:
                continue
            task_value = str(item.get("task") or "").strip()
            if not task_value or task_value == "mode_required":
                task_value = default_task
            normalized.append({"agent": resolved, "task": task_value})
        elif isinstance(item, str):
            resolved = _normalize_agent_identifier(item)
            if resolved:
                normalized.append({"agent": resolved, "task": default_task})
    return normalized


def _normalize_agent_identifier(agent: str | None) -> str | None:
    raw = str(agent or "").strip()
    if not raw:
        return None
    if is_custom_expert_id(raw):
        return raw
    return resolve_node_name(raw)


def _classify_primary_agent(message: str) -> str:
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in ["知识", "概念", "关联", "prerequisite", "graph"]):
        return "galaxy_guide"
    if any(kw in msg_lower for kw in ["考试", "预测", "重点", "exam", "paper"]):
        return "exam_oracle"
    if any(kw in msg_lower for kw in ["时间", "任务", "schedule", "task", "pomodoro"]):
        return "time_tutor"
    if any(kw in msg_lower for kw in ["错误", "诊断", "错因", "debug", "bug"]):
        return "error_analyst"
    return "time_tutor"


def _analyze_collaboration_needs_fast(message: str) -> tuple[dict[str, Any], float] | None:
    """Keyword-based fast path for collaboration analysis.

    Returns (plan, confidence) or None.
    Confidence is 1.0 for exact matches, lower when multiple keyword sets
    partially match or the match is short relative to message length.
    """
    msg_lower = message.lower()
    collaboration_keywords = {
        ("复习计划", "学习计划", "study plan", "复习策略"): {
            "mode": "sequential",
            "agents": ["galaxy_guide", "exam_oracle", "time_tutor"],
            "order": [
                {"agent": "galaxy_guide", "task": f"Analyze knowledge prerequisites: {message}"},
                {"agent": "exam_oracle", "task": f"Analyze exam focus: {message}"},
                {"agent": "time_tutor", "task": f"Create schedule: {message}"},
            ],
        },
        ("基础差", "先修", "prerequisite", "知识关联"): {
            "mode": "sequential",
            "agents": ["galaxy_guide", "time_tutor"],
            "order": [
                {"agent": "galaxy_guide", "task": f"Analyze knowledge graph: {message}"},
                {"agent": "time_tutor", "task": f"Create foundation plan: {message}"},
            ],
        },
        ("考试预测", "重点", "exam focus", "past paper"): {
            "mode": "parallel",
            "agents": ["exam_oracle", "time_tutor"],
            "order": [
                {"agent": "exam_oracle", "task": f"Analyze exam focus: {message}"},
                {"agent": "time_tutor", "task": f"Schedule review: {message}"},
            ],
        },
        ("利弊", "优缺点", "正反", "争议", "debate"): {
            "mode": "debate",
            "agents": ["deep_analyst", "search_agent", "study_buddy"],
            "order": [
                {"agent": "deep_analyst", "task": f"Provide a rigorous analysis of both sides: {message}"},
                {"agent": "search_agent", "task": f"Collect evidence and counterpoints: {message}"},
                {"agent": "study_buddy", "task": f"Frame the trade-offs for the user context: {message}"},
            ],
        },
    }

    matches: list[tuple[dict[str, Any], float]] = []
    for keywords, plan in collaboration_keywords.items():
        matched_keywords = [kw for kw in keywords if kw in msg_lower]
        if not matched_keywords:
            continue
        best_match_len = max(len(kw) for kw in matched_keywords)
        coverage = best_match_len / max(len(msg_lower), 1)
        confidence = min(1.0, 0.5 + coverage * 2.5)
        matches.append((plan, confidence))

    if not matches:
        return None

    matches.sort(key=lambda x: x[1], reverse=True)

    if len(matches) > 1:
        best_plan, best_conf = matches[0]
        return best_plan, best_conf * 0.7

    return matches[0]


def _sort_plan_by_quality(
    plan: dict[str, Any],
    quality_by_agent: dict[str, float],
    message: str,
) -> dict[str, Any]:
    agents = [str(agent).strip() for agent in (plan.get("agents") or []) if str(agent).strip()]
    if len(agents) < 2:
        return plan

    mode = str(plan.get("mode") or "sequential")
    if mode == "delegation":
        primary_agent = _normalize_agent_identifier(plan.get("primary_agent")) or agents[0]
        delegate_agents = [agent for agent in agents if agent != primary_agent]
        delegate_agents = sorted(delegate_agents, key=lambda agent_id: (-quality_by_agent.get(agent_id, 0.5), agent_id))
        ordered_agents = [primary_agent, *delegate_agents]
    else:
        ordered_agents = sorted(agents, key=lambda agent_id: (-quality_by_agent.get(agent_id, 0.5), agent_id))

    order_map = {
        str(item.get("agent")): str(item.get("task") or message)
        for item in (plan.get("order") or [])
        if isinstance(item, dict) and item.get("agent")
    }
    return {
        **plan,
        "agents": ordered_agents,
        "order": [{"agent": agent_id, "task": order_map.get(agent_id, message)} for agent_id in ordered_agents],
    }


def _rebuild_plan_with_agents(
    *,
    agents: list[str],
    source_plan: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    mode = str(source_plan.get("mode") or "sequential")
    if len(agents) <= 1:
        return {
            "mode": "single",
            "primary_agent": agents[0] if agents else source_plan.get("primary_agent", "study_buddy"),
            "agents": [],
            "order": [],
            "reasoning": source_plan.get("reasoning", ""),
        }
    original_tasks = {
        str(item.get("agent")): str(item.get("task") or message)
        for item in (source_plan.get("order") or [])
        if isinstance(item, dict) and item.get("agent")
    }
    rebuilt = {
        "mode": mode,
        "agents": agents,
        "order": [
            {"agent": agent_id, "task": original_tasks.get(agent_id, f"Use your specialty to contribute to: {message}")}
            for agent_id in agents
        ],
        "reasoning": source_plan.get("reasoning", ""),
    }
    if source_plan.get("primary_agent"):
        rebuilt["primary_agent"] = source_plan.get("primary_agent")
    return rebuilt


async def _analyze_collaboration_needs_llm(
    *,
    message: str,
    available_agents: list[dict[str, Any]],
    combination_hints: list[dict[str, Any]],
) -> dict[str, Any]:
    llm = LLMFactory.get_llm(
        "orchestrator",
        task_type=TaskType.ROUTING,
        force_tier=ModelTier.FAST,
    )
    structured_llm = llm.with_structured_output(CollaborationDecision)
    agent_lines = "\n".join(
        f"- {item['id']} ({item['display_name']}): {item['description']} | quality_score={item['quality_score']:.2f}"
        for item in available_agents
    )
    combination_lines = "\n".join(
        f"- {' + '.join(hint.get('agents', []))}: feedback_score={hint.get('feedback_score', 0):.2f}, samples={hint.get('sample_size', 0)}"
        for hint in combination_hints[:3]
    ) or "- 暂无稳定历史组合"
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You decide whether a user query needs single-agent handling or multi-agent collaboration.\n"
                "Prefer single-agent unless collaboration clearly improves the result.\n"
                "If multi-agent is needed, choose 2-3 agents and assign a concise subtask to each.\n"
                "Available execution_mode values:\n"
                '- "sequential": agents work one after another and later agents depend on earlier results.\n'
                '- "parallel": agents work independently at the same time.\n'
                '- "debate": agents independently analyze, then cross-review each other.\n'
                '- "delegation": one lead agent decomposes the problem and synthesizes delegate results.\n'
                "Available agents:\n{agent_lines}\n\n"
                "Historical high-performing combinations:\n{combination_lines}\n\n"
                "Return structured output only.",
            ),
            ("user", "{query}"),
        ]
    )
    chain = prompt | structured_llm
    decision = await chain.ainvoke(
        {
            "query": message,
            "agent_lines": agent_lines,
            "combination_lines": combination_lines,
        }
    )

    resolved_primary = _normalize_agent_identifier(decision.primary_agent) or _classify_primary_agent(message)
    resolved_agents = []
    for agent in decision.agents:
        resolved = _normalize_agent_identifier(agent)
        if resolved and resolved not in resolved_agents:
            resolved_agents.append(resolved)
    resolved_order = []
    for item in decision.order:
        resolved = _normalize_agent_identifier(item.agent)
        if resolved:
            resolved_order.append({"agent": resolved, "task": item.task})

    if decision.mode == "single" or len(resolved_agents) <= 1:
        return {
            "mode": "single",
            "primary_agent": resolved_primary,
            "agents": [],
            "order": [],
            "reasoning": decision.reasoning,
        }

    execution_mode = str(decision.execution_mode or "sequential").strip().lower()
    if execution_mode not in COLLABORATION_MODES - {"single"}:
        execution_mode = "sequential"
    if execution_mode == "delegation" and resolved_primary not in resolved_agents:
        resolved_agents.insert(0, resolved_primary)

    if not resolved_order:
        resolved_order = [
            {"agent": agent_id, "task": f"Use your specialty to contribute to: {message}"}
            for agent_id in resolved_agents
        ]
    return {
        "mode": execution_mode,
        "primary_agent": resolved_primary,
        "agents": resolved_agents,
        "order": resolved_order,
        "reasoning": decision.reasoning,
    }


async def analyze_collaboration_plan(
    message: str,
    *,
    state: SparkleState,
    config: dict | None,
) -> dict[str, Any]:
    user_id = str(state.get("user_id") or "").strip()
    redis_client = (config or {}).get("configurable", {}).get("redis_client")
    intent_type = _planning_intent_type(state)
    planning_constraints = state.get("_planning_constraints") or {}
    excluded_agents = {
        str(agent).strip()
        for agent in (planning_constraints.get("excluded_agents") or [])
        if str(agent).strip()
    }
    scoring_service = AgentScoringService(redis_client)
    fast_result = _analyze_collaboration_needs_fast(message)
    available_agents = await _build_available_agents(user_id=user_id, redis_client=redis_client)
    if excluded_agents:
        available_agents = [
            agent for agent in available_agents if agent.get("id") not in excluded_agents
        ]
    quality_by_agent = {item["id"]: float(item.get("quality_score") or 0.5) for item in available_agents}

    # Confidence threshold: below this, escalate to LLM even if keywords matched
    _KEYWORD_CONFIDENCE_THRESHOLD = 0.65

    plan = None
    if fast_result is not None:
        fast_plan, fast_confidence = fast_result
        if fast_confidence >= _KEYWORD_CONFIDENCE_THRESHOLD or not settings.ENABLE_AGENT_LLM_COLLAB_ROUTING:
            plan = _sort_plan_by_quality(fast_plan, quality_by_agent, message)
            AGENT_COLLAB_DECISION_TOTAL.labels(source="keyword", intent_type=intent_type).inc()
        else:
            logger.debug(f"Keyword match confidence {fast_confidence:.2f} below threshold, escalating to LLM")

    if plan is None and settings.ENABLE_AGENT_LLM_COLLAB_ROUTING and available_agents:
        try:
            combination_hints = (
                await scoring_service.analyze_best_combinations(
                    user_id=user_id,
                    intent_type=intent_type,
                    min_samples=5,
                )
                if redis_client and user_id
                else []
            )
            plan = await _analyze_collaboration_needs_llm(
                message=message,
                available_agents=available_agents,
                combination_hints=combination_hints,
            )
            plan = _sort_plan_by_quality(plan, quality_by_agent, message)
            AGENT_COLLAB_DECISION_TOTAL.labels(source="llm", intent_type=intent_type).inc()
        except Exception as exc:
            logger.warning(f"LLM collaboration analysis failed: {exc}")

    if plan is None:
        AGENT_COLLAB_DECISION_TOTAL.labels(source="fallback_single", intent_type=intent_type).inc()
        return {
            "mode": "single",
            "primary_agent": _normalize_agent_identifier(state.get("next_step")) or _classify_primary_agent(message),
            "agents": [],
            "order": [],
        }

    if excluded_agents and isinstance(plan, dict):
        filtered_agents = [
            str(agent).strip()
            for agent in (plan.get("agents") or [])
            if str(agent).strip() and str(agent).strip() not in excluded_agents
        ]
        filtered_order = [
            item
            for item in (plan.get("order") or [])
            if isinstance(item, dict) and str(item.get("agent") or "").strip() not in excluded_agents
        ]
        if len(filtered_agents) <= 1:
            primary_agent = filtered_agents[0] if filtered_agents else plan.get("primary_agent")
            return {
                "mode": "single",
                "primary_agent": primary_agent or _classify_primary_agent(message),
                "agents": [],
                "order": [],
                "reasoning": plan.get("reasoning", ""),
            }
        plan = {
            **plan,
            "agents": filtered_agents,
            "order": filtered_order,
        }

    if plan.get("mode") in {"sequential", "parallel"} and redis_client and user_id:
        explored_agents = await scoring_service.maybe_apply_exploration(
            user_id=user_id,
            intent_type=intent_type,
            current_agents=[str(agent) for agent in (plan.get("agents") or []) if str(agent).strip()],
            exploration_rate=settings.AGENT_COMBINATION_EXPLORATION_RATE,
            available_agents=[item["id"] for item in available_agents],
        )
        current_agents = [str(agent) for agent in (plan.get("agents") or []) if str(agent).strip()]
        if explored_agents and explored_agents != current_agents:
            plan = _rebuild_plan_with_agents(agents=explored_agents, source_plan=plan, message=message)
            AGENT_COMBINATION_EXPLORATION_TOTAL.labels(intent_type=intent_type).inc()
            AGENT_COLLAB_DECISION_TOTAL.labels(source="exploration", intent_type=intent_type).inc()

    return plan


async def _emit_initial_agent_states(
    agents: list[str],
    *,
    stream_cb,
    mode: str,
) -> None:
    for index, agent_id in enumerate(agents):
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="pending" if mode != "parallel" and index > 0 else "active",
            metadata=_activity_metadata(mode=mode, phase="queued"),
        )


async def _execute_agents_parallel(
    agents: list[str],
    state: SparkleState,
    config: dict | None,
    stream_cb,
    *,
    task_map: dict[str, str] | None = None,
    phase: str = "analysis",
) -> list[dict[str, Any]]:
    async def _run_one(agent_id: str, index: int) -> dict[str, Any]:
        node_fn = get_node_function(agent_id)
        if node_fn is None:
            return {"agent_id": agent_id, "success": False, "error": f"Unknown agent: {agent_id}", "index": index}
        task = (task_map or {}).get(agent_id) or _get_latest_human_message(state.get("messages") or [])
        agent_state = _clone_state_for_agent(state, agent_id=agent_id, task=task)
        try:
            result = await node_fn(agent_state, config)
            return {"agent_id": agent_id, "result": result, "success": True, "index": index, "task": task}
        except Exception as exc:
            await emit_agent_activity(
                stream_cb,
                agent_id=agent_id,
                status="error",
                result_summary=str(exc)[:120],
                metadata=_activity_metadata(mode=str(state.get("collaboration_mode") or "parallel"), phase=phase, task=task),
            )
            return {"agent_id": agent_id, "error": str(exc), "success": False, "index": index, "task": task}

    results = await asyncio.gather(
        *[_run_one(agent_id, index) for index, agent_id in enumerate(agents)],
        return_exceptions=False,
    )
    return sorted(results, key=lambda item: item["index"])


async def _merge_parallel_results(
    results: list[dict[str, Any]],
    state: SparkleState,
    config: dict | None,
) -> dict[str, Any]:
    successful = [result for result in results if result.get("success")]
    if not successful:
        return {
            "messages": [AIMessage(content="所有专家分析均未成功，请重试。")],
            "collaboration_index": len(results),
            "collaboration_mode": "parallel",
            "next_step": "end",
            "active_agent": "collaboration",
        }

    collected_messages: list[BaseMessage] = []
    for item in successful:
        collected_messages.extend(_extract_messages(item.get("result")))

    if len(successful) == 1:
        return {
            "messages": collected_messages,
            "collaboration_index": len(results),
            "collaboration_mode": "parallel",
            "next_step": "aggregator",
            "active_agent": "collaboration",
        }

    agent_outputs = []
    for item in successful:
        content = _extract_content(item.get("result"))
        if content:
            agent_outputs.append(f"【{item['agent_id']}】\n{content}")
    merged_messages = list(collected_messages)
    if agent_outputs:
        merge_prompt = (
            "以下是多位专家对同一问题的分析结果，请综合整理为一份连贯、全面的回答：\n\n"
            f"{chr(10).join(agent_outputs)}\n\n"
            "要求：\n"
            "1. 保留各专家的核心观点\n"
            "2. 去除重复内容\n"
            "3. 如有矛盾观点，客观呈现并说明差异\n"
            "4. 用自然流畅的语言输出"
        )
        llm = LLMFactory.get_llm("aggregator")
        merged_response = await llm.ainvoke([HumanMessage(content=merge_prompt)])
        merged_messages.append(merged_response)

    return {
        "messages": merged_messages,
        "collaboration_index": len(results),
        "collaboration_mode": "parallel",
        "next_step": "aggregator",
        "active_agent": "collaboration",
    }


async def _execute_review_round(
    review_tasks: list[tuple[str, str]],
    *,
    stream_cb,
    mode: str,
) -> list[dict[str, str]]:
    async def _run_review(agent_id: str, prompt: str) -> dict[str, str]:
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="active",
            metadata=_activity_metadata(mode=mode, phase="review"),
        )
        llm = LLMFactory.get_llm(agent_id)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        summary = str(getattr(response, "content", "") or "")[:120]
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="completed",
            result_summary=summary,
            metadata=_activity_metadata(mode=mode, phase="review"),
        )
        return {"agent_id": agent_id, "content": str(getattr(response, "content", "") or "")}

    return await asyncio.gather(*[_run_review(agent_id, prompt) for agent_id, prompt in review_tasks])


async def _execute_debate(
    agents: list[str],
    state: SparkleState,
    config: dict | None,
    stream_cb,
    *,
    task_map: dict[str, str],
) -> dict[str, Any]:
    round1_results = await _execute_agents_parallel(
        agents,
        state,
        config,
        stream_cb,
        task_map=task_map,
        phase="round1",
    )
    successful_round1 = [result for result in round1_results if result.get("success")]
    if len(successful_round1) <= 1:
        return await _merge_parallel_results(round1_results, state, config)

    round1_summaries = {
        result["agent_id"]: _extract_content(result.get("result"))
        for result in successful_round1
    }
    review_tasks = []
    for agent_id in round1_summaries:
        others = {other_id: text for other_id, text in round1_summaries.items() if other_id != agent_id}
        review_prompt = "其他专家的分析如下：\n"
        for other_id, content in others.items():
            review_prompt += f"\n【{other_id}】: {content}\n"
        review_prompt += "\n请评审这些观点，指出你认同和不认同的部分，并补充你的最终见解。"
        review_tasks.append((agent_id, review_prompt))

    review_results = await _execute_review_round(review_tasks, stream_cb=stream_cb, mode="debate")
    judge_sections = []
    for agent_id, content in round1_summaries.items():
        judge_sections.append(f"Round1 - {agent_id}:\n{content}")
    for review in review_results:
        judge_sections.append(f"Review - {review['agent_id']}:\n{review['content']}")

    judge_prompt = (
        "你是辩论协作的综合裁判，请基于以下多轮观点与交叉评审，给出一份平衡、清晰的最终结论。\n\n"
        + "\n\n".join(judge_sections)
        + "\n\n要求：保留分歧、指出共识、最后给出用户可执行建议。"
    )
    llm = LLMFactory.get_llm("aggregator")
    final_response = await llm.ainvoke([HumanMessage(content=judge_prompt)])

    messages: list[BaseMessage] = []
    for result in successful_round1:
        messages.extend(_extract_messages(result.get("result")))
    messages.append(final_response)
    return {
        "messages": messages,
        "collaboration_index": len(agents),
        "collaboration_mode": "debate",
        "next_step": "aggregator",
        "active_agent": "collaboration",
    }


async def _execute_delegation(
    primary_agent: str,
    delegate_agents: list[str],
    state: SparkleState,
    config: dict | None,
    stream_cb,
    *,
    task_map: dict[str, str],
) -> dict[str, Any]:
    user_query = _get_latest_human_message(state.get("messages") or [])
    if not delegate_agents:
        logger.warning(f"No delegate agents for delegation mode, falling back to primary agent: {primary_agent}")
        return {
            "messages": [],
            "next_step": primary_agent,
            "active_agent": primary_agent,
            "collaboration_mode": "single",
        }

    await emit_agent_activity(
        stream_cb,
        agent_id=primary_agent,
        status="active",
        metadata=_activity_metadata(mode="delegation", phase="decompose"),
    )
    decomposition_prompt = (
        f"作为主分析师，请将以下问题拆分为 {len(delegate_agents)} 个独立子任务，"
        f"分别适合以下专家处理：{', '.join(delegate_agents)}\n\n"
        f"用户问题：{user_query}"
    )
    primary_llm = LLMFactory.get_llm(primary_agent).with_structured_output(DelegationPlan)
    try:
        decomposition = await primary_llm.ainvoke([HumanMessage(content=decomposition_prompt)])
        subtasks = [
            {"agent": _normalize_agent_identifier(item.agent_id) or item.agent_id, "task": item.task}
            for item in decomposition.subtasks
            if (_normalize_agent_identifier(item.agent_id) or item.agent_id) in delegate_agents
        ]
    except Exception:
        subtasks = [{"agent": agent_id, "task": task_map.get(agent_id, user_query)} for agent_id in delegate_agents]

    await emit_agent_activity(
        stream_cb,
        agent_id=primary_agent,
        status="completed",
        result_summary="任务拆分完成",
        metadata=_activity_metadata(mode="delegation", phase="decompose"),
    )

    delegate_results = await _execute_agents_parallel(
        delegate_agents,
        state,
        config,
        stream_cb,
        task_map={item["agent"]: item["task"] for item in subtasks},
        phase="delegate",
    )
    successful_delegate_results = [result for result in delegate_results if result.get("success")]

    await emit_agent_activity(
        stream_cb,
        agent_id=primary_agent,
        status="active",
        metadata=_activity_metadata(mode="delegation", phase="synthesis"),
    )
    synthesis_sections = []
    for result in successful_delegate_results:
        synthesis_sections.append(f"【{result['agent_id']}】\n{_extract_content(result.get('result'))}")
    synthesis_prompt = (
        "你是主协调专家。请基于以下委派结果，整合成一份最终建议：\n\n"
        + "\n\n".join(synthesis_sections)
        + "\n\n请输出一份统一、无重复、可执行的回答。"
    )
    final_response = await LLMFactory.get_llm(primary_agent).ainvoke([HumanMessage(content=synthesis_prompt)])
    await emit_agent_activity(
        stream_cb,
        agent_id=primary_agent,
        status="completed",
        result_summary="综合输出完成",
        metadata=_activity_metadata(mode="delegation", phase="synthesis"),
    )

    messages: list[BaseMessage] = []
    for result in successful_delegate_results:
        messages.extend(_extract_messages(result.get("result")))
    messages.append(final_response)
    return {
        "messages": messages,
        "collaboration_index": len(delegate_agents) + 1,
        "collaboration_mode": "delegation",
        "next_step": "aggregator",
        "active_agent": "collaboration",
    }


async def collaboration_node(state: SparkleState, config: dict | None = None) -> SparkleState:
    stream_cb = get_stream_callback(config)
    messages = state["messages"]
    user_message = _get_latest_human_message(messages)

    collaboration_mode = str(state.get("collaboration_mode") or "")
    collaboration_order = state.get("collaboration_order")
    collaboration_agents = state.get("collaboration_agents")
    if collaboration_mode in COLLABORATION_MODES - {"single"} and collaboration_order:
        normalized_order = _normalize_order(collaboration_order, default_task=user_message)
        collaboration_plan = {
            "mode": collaboration_mode,
            "primary_agent": state.get("next_step") or (collaboration_agents or ["study_buddy"])[0],
            "agents": collaboration_agents or [],
            "order": normalized_order,
        }
    else:
        collaboration_plan = await analyze_collaboration_plan(user_message, state=state, config=config)

    mode = str(collaboration_plan.get("mode") or "single")
    if mode not in COLLABORATION_MODES:
        mode = "sequential"

    if mode == "single":
        return {
            "next_step": _normalize_agent_identifier(collaboration_plan.get("primary_agent")) or "study_buddy",
            "active_agent": "router",
            "collaboration_mode": "single",
        }

    agents = [str(agent).strip() for agent in (collaboration_plan.get("agents") or []) if str(agent).strip()]
    order = _normalize_order(collaboration_plan.get("order") or [], default_task=user_message)
    task_map = {str(item["agent"]): str(item.get("task") or user_message) for item in order}

    logger.info(f"Multi-agent collaboration: mode={mode}, agents={agents}")

    # Build a local state view with collaboration config for sub-functions
    local_state = {**state, "collaboration_mode": mode, "collaboration_agents": agents, "collaboration_order": order}

    if mode in {"parallel", "debate", "delegation"}:
        await _emit_initial_agent_states(agents, stream_cb=stream_cb, mode=mode)
        if mode == "parallel":
            results = await _execute_agents_parallel(agents, local_state, config, stream_cb, task_map=task_map)
            result = await _merge_parallel_results(results, local_state, config)
            result["collaboration_mode"] = mode
            result["collaboration_agents"] = agents
            result["collaboration_order"] = order
            return result
        if mode == "debate":
            result = await _execute_debate(agents, local_state, config, stream_cb, task_map=task_map)
            result["collaboration_mode"] = mode
            result["collaboration_agents"] = agents
            result["collaboration_order"] = order
            return result
        primary_agent = _normalize_agent_identifier(collaboration_plan.get("primary_agent")) or (agents[0] if agents else "study_buddy")
        delegates = [agent for agent in agents if agent != primary_agent]
        result = await _execute_delegation(primary_agent, delegates, local_state, config, stream_cb, task_map=task_map)
        result["collaboration_mode"] = mode
        result["collaboration_agents"] = agents
        result["collaboration_order"] = order
        return result

    collaboration_index = state.get("collaboration_index", 0)
    if collaboration_index == 0 and agents:
        await _emit_initial_agent_states(agents, stream_cb=stream_cb, mode=mode)
    if collaboration_index >= len(order):
        return {
            "next_step": "aggregator",
            "active_agent": "collaboration",
            "collaboration_mode": mode,
            "collaboration_agents": agents,
            "collaboration_order": order,
        }

    agent_spec = order[collaboration_index]
    agent_name = agent_spec["agent"]
    agent_task = agent_spec.get("task", user_message)
    logger.info(f"Executing agent: {agent_name} with task: {agent_task[:50]}...")
    return {
        "next_step": agent_name,
        "active_agent": agent_name,
        "collaboration_context": agent_task,
        "collaboration_index": collaboration_index + 1,
        "collaboration_mode": mode,
        "collaboration_agents": agents,
        "collaboration_order": order,
    }


async def collaboration_aggregator_node(state: SparkleState) -> SparkleState:
    def _normalize_tool_call(tc) -> dict:
        if isinstance(tc, dict):
            name = tc.get("name") or tc.get("tool") or tc.get("function", {}).get("name")
            args = tc.get("args") or tc.get("arguments") or tc.get("function", {}).get("arguments", {})
            call_id = tc.get("id") or tc.get("tool_call_id")
        else:
            name = getattr(tc, "name", None) or getattr(tc, "tool", None)
            args = getattr(tc, "args", None) or getattr(tc, "arguments", None)
            call_id = getattr(tc, "id", None) or getattr(tc, "tool_call_id", None)

        return {"id": call_id, "name": name, "args": args}

    all_tool_calls = []
    agents_involved = state.get("collaboration_agents", [])
    messages = state.get("messages", [])
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_call = _normalize_tool_call(tc)
                if not tool_call.get("name"):
                    continue
                tool_call["agent"] = state.get("active_agent", "unknown")
                all_tool_calls.append(tool_call)

    collaboration_mode = str(state.get("collaboration_mode", "single") or "single")
    collaboration_results = {
        "agents_involved": agents_involved,
        "tool_calls_count": len(all_tool_calls),
        "collaboration_mode": collaboration_mode,
    }

    result: dict = {"collaboration_results": collaboration_results}

    narrative = ""
    if agents_involved:
        display_names = [
            AGENT_DISPLAY_CONFIG.get(str(agent_id), {}).get("display_name", str(agent_id))
            for agent_id in agents_involved
        ]
        if display_names:
            mode_prefix = {
                "parallel": "并行协作",
                "debate": "多视角辩论",
                "delegation": "委派协作",
                "sequential": "分步协作",
            }.get(collaboration_mode, "协作")
            narrative = f"本次回答由 {'、'.join(display_names)} 以{mode_prefix}方式共同完成。"
            result["collaboration_narrative"] = narrative
            collaboration_results["narrative"] = narrative

    logger.info(
        f"Collaboration aggregated: {len(agents_involved)} agents, "
        f"{len(all_tool_calls)} tool calls, mode={collaboration_mode}"
    )
    return result
