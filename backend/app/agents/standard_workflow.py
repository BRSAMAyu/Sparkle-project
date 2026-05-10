"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import re
import time
import uuid
from datetime import datetime
from typing import Any

from google.protobuf import struct_pb2
from loguru import logger

from app.agents.collaboration_workflows import (
    CollaborationResult,
    ErrorDiagnosisWorkflow,
    ProgressiveExplorationWorkflow,
    TaskDecompositionWorkflow,
    _build_timeline_step,
)
from app.agents.enhanced_agents import EnhancedAgentContext

# Phase 1: Review System
from app.agents.graph.nodes.review_nodes import (
    execution_review_node,
    generation_review_node,
    reflection_node,
)

# P1 & P2: Tool Fallback and Enhanced Features
from app.agents.tool_fallback import ToolExecutionFallback
from app.agents.workflow_experience import (
    build_collaboration_user_query,
    build_handoff_packet,
    format_handoff_packets,
    inject_examples_into_user_context,
    resolve_few_shot_examples,
    should_inject_few_shot,
)
from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType, agent_profile_registry
from app.core.business_metrics import HITL_REQUESTED, TASK_LOOP_COMPLETED
from app.core.context_pack import ContextBudgetManager, estimate_tokens, format_document_chunks_for_prompt
from app.core.metrics import DOCUMENT_CONTEXT_CHUNKS_INJECTED_TOTAL, DOCUMENT_CONTEXT_TOKENS_USED
from app.core.pending_actions import pending_actions_store
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.chat_modes import CHAT_MODE_TEAM_PREFIX, parse_team_spec
from app.orchestration.context_focus import infer_route_intent_from_chat_mode
from app.orchestration.executor import ToolExecutor
from app.orchestration.graph_rag import (
    GraphRAGRetriever,
    filter_graph_rag_result,
    filter_retrieved_chunks,
    format_graph_rag_document_context,
)
from app.orchestration.prompts import build_system_prompt
from app.orchestration.statechart_engine import StateGraph, WorkflowState
from app.services.aurora_doc_context_kill_switch_service import AuroraDocContextKillSwitchService
from app.services.document_service import document_service
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import (
    get_configured_llm_service,
    get_configured_llm_service_for_tier,
    get_llm_service_for_specific_model,
    llm_service,
)

# ==========================================
# Nodes
# ==========================================

_EXPLICIT_COLLAB_LLM_TIMEOUT_SECONDS = 10.0
_GENERATION_FIRST_CHUNK_TIMEOUT_SECONDS = 18.0
_GENERATION_CHUNK_TIMEOUT_SECONDS = 45.0
_STREAM_DELTA_FLUSH_CHARS = 96
_STREAM_DELTA_FLUSH_SECONDS = 0.12
_MAX_TOOL_LOOPS_PER_TURN = 2


def _max_tool_loops_for_state(state: WorkflowState) -> int:
    chat_mode = str(state.context_data.get("chat_mode", "standard")).strip().lower()
    if chat_mode in {"study_plan", "error_diagnosis"}:
        return 1
    return _MAX_TOOL_LOOPS_PER_TURN


def _should_force_final_synthesis_without_tools(state: WorkflowState) -> bool:
    chat_mode = str(state.context_data.get("chat_mode", "standard")).strip().lower()
    tool_loop_count = int(state.context_data.get("tool_loop_count") or 0)
    if chat_mode in {"study_plan", "error_diagnosis"} and tool_loop_count >= 1:
        return True

    if tool_loop_count < 1:
        return False

    tool_results = state.context_data.get("tool_results") or []
    for result in tool_results:
        if not isinstance(result, dict):
            continue
        widget_type = str(result.get("widget_type") or "").strip().lower()
        if widget_type in {"plan_card", "task_list"}:
            return True
    return False


def _phase_d_forced_model_tier(state: WorkflowState) -> ModelTier | None:
    raw = str(state.context_data.get("phase_d_forced_model_tier") or "").strip().lower()
    if not raw:
        return None
    try:
        return ModelTier(raw)
    except ValueError:
        return None


def _build_minimal_user_context_for_grounded_synthesis(user_context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(user_context, dict):
        return {}

    allowed_keys = {
        "preferences",
        "next_actions",
        "active_plans",
        "task_status_summary",
        "profile_context",
        "recent_progress",
        "context_focus",
    }
    return {key: user_context.get(key) for key in allowed_keys if key in user_context}


def _first_document_page_number(chunk: Any) -> int | None:
    if chunk is None:
        return None

    page_numbers = getattr(chunk, "page_numbers", None)
    if isinstance(page_numbers, list):
        for item in page_numbers:
            try:
                return int(item)
            except (TypeError, ValueError):
                continue

    page_number = getattr(chunk, "page_number", None)
    try:
        return int(page_number) if page_number is not None else None
    except (TypeError, ValueError):
        return None


def _resolve_generation_agent_role(state: WorkflowState) -> str:
    explicit_role = state.context_data.get("agent_role")
    if explicit_role:
        return str(explicit_role)

    answer_experts = state.context_data.get("answer_experts")
    if isinstance(answer_experts, list):
        for expert in answer_experts:
            cleaned = str(expert).strip()
            if cleaned and not cleaned.startswith("custom_expert:"):
                return cleaned

    selected_experts = state.context_data.get("selected_experts")
    if isinstance(selected_experts, list):
        for expert in selected_experts:
            cleaned = str(expert).strip()
            if cleaned and not cleaned.startswith("custom_expert:"):
                return cleaned

    return "generation"


def _resolve_generation_task_type(state: WorkflowState) -> TaskType:
    chat_mode = str(state.context_data.get("chat_mode", "standard")).strip().lower()
    if chat_mode == "deep_analysis":
        return TaskType.DEEP_REASONING
    if chat_mode == "study_plan":
        return TaskType.TASK_DECOMPOSITION
    if chat_mode == "error_diagnosis":
        return TaskType.ERROR_DIAGNOSIS
    return TaskType.STANDARD_RESPONSE


def _resolve_reasoning_mode(state: WorkflowState, default: str = "balanced") -> str:
    value = str(state.context_data.get("reasoning_mode") or default).strip().lower()
    if value in {"fast", "balanced", "deep"}:
        return value
    return default


def _needs_fast_standard_guard(
    *,
    use_slim_standard_context: bool,
    reasoning_mode: str,
    selection: Any | None,
) -> bool:
    if not use_slim_standard_context or reasoning_mode != "fast" or selection is None:
        return False
    tier_value = str(getattr(getattr(selection, "config", None), "tier", "") or "").strip().lower()
    if not tier_value and hasattr(getattr(selection, "config", None), "tier"):
        tier_value = str(getattr(selection.config.tier, "value", "") or "").strip().lower()
    return tier_value not in {"fast", "standard"}


def _should_force_fast_first_touch(
    state: WorkflowState,
    *,
    explicit_runtime: dict[str, Any] | None = None,
    task_type: TaskType | None = None,
) -> bool:
    if not getattr(settings, "STANDARD_CHAT_FORCE_FAST_TIER", True):
        return False
    if explicit_runtime is not None:
        return False
    if task_type is not TaskType.STANDARD_RESPONSE:
        return False
    if _resolve_reasoning_mode(state) != "fast":
        return False
    chat_mode = str(state.context_data.get("chat_mode", "standard")).strip().lower()
    return chat_mode == "standard"


def _should_force_balanced_fast_first_touch(
    state: WorkflowState,
    *,
    explicit_runtime: dict[str, Any] | None = None,
    task_type: TaskType | None = None,
    user_message: str = "",
    use_slim_standard_context: bool = False,
) -> bool:
    if explicit_runtime is not None:
        return False
    if task_type is not TaskType.STANDARD_RESPONSE:
        return False
    if _resolve_reasoning_mode(state) != "balanced":
        return False
    if not use_slim_standard_context:
        return False

    chat_mode = str(state.context_data.get("chat_mode", "standard")).strip().lower()
    if chat_mode not in {"standard", "chat"}:
        return False

    text = (user_message or "").strip().lower()
    if not text or len(text) > 120:
        return False

    deep_markers = (
        "深入",
        "详细",
        "原理",
        "推导",
        "证明",
        "严谨",
        "系统地",
        "systematically",
        "in depth",
        "deep dive",
        "why exactly",
    )
    return not any(marker in text for marker in deep_markers)


def _coerce_agent_role(role: str | None) -> AgentRole:
    cleaned = str(role or "").strip().lower()
    for item in AgentRole:
        if item.value == cleaned:
            return item
    return AgentRole.GENERATION


def _selected_expert_ids(state: WorkflowState) -> list[str]:
    raw = state.context_data.get("selected_experts")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _answer_expert_ids(state: WorkflowState) -> list[str]:
    raw = state.context_data.get("answer_experts")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _single_explicit_expert_id(state: WorkflowState) -> str | None:
    experts = _selected_expert_ids(state)
    if len(experts) == 1:
        return experts[0]
    return None


def _get_custom_expert_profile(state: WorkflowState, expert_id: str | None) -> dict[str, Any] | None:
    if not expert_id:
        return None
    profiles = state.context_data.get("_custom_expert_profiles") or {}
    if not isinstance(profiles, dict):
        return None
    profile = profiles.get(expert_id)
    return profile if isinstance(profile, dict) else None


def _reasoning_mode_to_task_type(value: str | None, fallback: TaskType) -> TaskType:
    mode = str(value or "").strip().lower()
    if mode == "fast":
        return TaskType.QUICK_QUERY
    if mode == "deep":
        return TaskType.DEEP_REASONING
    return fallback


async def _resolve_llm_for_expert(
    *,
    expert_id: str,
    state: WorkflowState,
    task_type: TaskType,
):
    custom_profile = _get_custom_expert_profile(state, expert_id)
    if custom_profile:
        base_role = str(custom_profile.get("base_expert_id") or "generation").strip().lower()
        effective_role = _coerce_agent_role(base_role)
        custom_task_type = _reasoning_mode_to_task_type(custom_profile.get("reasoning_mode"), task_type)
        model_key = str(custom_profile.get("preferred_model_key") or "").strip()
        reasoning_mode = str(custom_profile.get("reasoning_mode") or "balanced").strip().lower()
        if model_key:
            service = await get_llm_service_for_specific_model(model_key, effective_role)
        else:
            tier_value = str(custom_profile.get("preferred_model_tier") or "").strip().lower()
            if tier_value and tier_value in {item.value for item in ModelTier}:
                service = await get_configured_llm_service_for_tier(
                    effective_role,
                    ModelTier(tier_value),
                    task_type=custom_task_type,
                    reasoning_mode=reasoning_mode,
                )
            else:
                service = await get_configured_llm_service(
                    effective_role,
                    custom_task_type,
                    reasoning_mode=reasoning_mode,
                )
        return {
            "service": service,
            "agent_role": effective_role,
            "display_name": str(custom_profile.get("display_name") or custom_profile.get("name") or expert_id),
            "system_prompt": str(custom_profile.get("system_prompt") or "").strip(),
            "expert_id": expert_id,
            "is_custom": True,
        }

    effective_role = _coerce_agent_role(expert_id)
    service = await get_configured_llm_service(effective_role, task_type)
    profile = agent_profile_registry.get_profile(effective_role)
    return {
        "service": service,
        "agent_role": effective_role,
        "display_name": profile.display_name,
        "system_prompt": "",
        "expert_id": expert_id,
        "is_custom": False,
    }


def _build_expert_collaboration_system_prompt(
    *,
    state: WorkflowState,
    runtime: dict[str, Any],
    user_context: dict[str, Any],
    conversation_context: dict[str, Any],
    prompt_version: str,
) -> str:
    agent_role = runtime["agent_role"]
    base_prompt = build_system_prompt(
        user_context,
        conversation_history=conversation_context,
        prompt_version=prompt_version,
        agent_role=agent_role,
        model_key=getattr(runtime["service"], "model_key", None),
        plan_context=state.context_data.get("plan_context"),
        session_feedback_instruction=str(state.context_data.get("session_feedback_instruction") or ""),
        dual_core_instruction=str(state.context_data.get("dual_core_prompt_instruction") or ""),
        context_focus=state.context_data.get("context_focus"),
        context_briefing_note=str(state.context_data.get("context_briefing_note") or ""),
        chat_mode=str(state.context_data.get("chat_mode", "standard") or "standard"),
    )
    directive = (
        f"\n\n## 当前参与身份\n"
        f"你正在以「{runtime['display_name']}」的身份参与专家协作。"
        "请只从这一专家视角发言，避免和其他专家重复。"
        "\n输出要求：1. 先给结论；2. 再给你的依据；3. 最后给可执行建议。"
    )
    custom_prompt = str(runtime.get("system_prompt") or "").strip()
    if custom_prompt:
        directive += f"\n\n## 自定义专家指令\n{custom_prompt}"
    return f"{base_prompt}{directive}"


async def _execute_explicit_expert_collaboration(state: WorkflowState) -> CollaborationResult:
    selected = _selected_expert_ids(state)
    answer_targets = _answer_expert_ids(state) or list(selected)
    team_spec = parse_team_spec(str(state.context_data.get("chat_mode") or ""))
    run_parallel = (
        isinstance(team_spec, dict)
        and str(team_spec.get("mode") or team_spec.get("collaboration_mode") or "").strip().lower() == "parallel"
        and len(selected) > 1
    )
    user_message = state.messages[-1]["content"] if state.messages else ""
    user_context = state.context_data.get("user_context") or {}
    conversation_context = state.context_data.get("conversation_context") or {"messages": []}
    prompt_version = str(state.context_data.get("prompt_version") or "v1")
    task_type = _resolve_generation_task_type(state)

    expert_outputs: list[dict[str, Any]] = []
    handoff_packets: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    few_shot_total = 0

    async def _run_single_expert(
        expert_id: str, prior_handoffs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
        started_at = time.time()
        runtime = await _resolve_llm_for_expert(expert_id=expert_id, state=state, task_type=task_type)
        few_shot_examples: list[dict[str, Any]] = []
        if should_inject_few_shot(
            workflow_type="explicit_expert_collaboration",
            stage="collaboration",
            agent_role=expert_id,
            is_final_target=expert_id in answer_targets,
        ):
            few_shot_examples = await resolve_few_shot_examples(
                db_session=state.context_data.get("db_session"),
                user_id=state.context_data.get("user_id") or getattr(state, "user_id", None),
                workflow_type="explicit_expert_collaboration",
                chat_mode=str(state.context_data.get("chat_mode", "standard") or "standard"),
                agent_role=expert_id,
                stage="collaboration",
                count=1,
            )
        system_prompt = _build_expert_collaboration_system_prompt(
            state=state,
            runtime=runtime,
            user_context=inject_examples_into_user_context(user_context, few_shot_examples),
            conversation_context=conversation_context,
            prompt_version=prompt_version,
        )
        expert_request = build_collaboration_user_query(
            base_query=user_message,
            workflow_type="explicit_expert_collaboration",
            handoff_packets=prior_handoffs,
            few_shot_examples=few_shot_examples,
            extra_instruction=("请用你的专业视角回答下面的问题。必须保留你的独特判断，不要假装代表其他专家。"),
        )
        try:
            response = await asyncio.wait_for(
                runtime["service"].chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": expert_request},
                    ],
                    temperature=0.5,
                ),
                timeout=_EXPLICIT_COLLAB_LLM_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.warning(
                "Explicit expert collaboration timed out for expert=%s after %.1fs",
                expert_id,
                _EXPLICIT_COLLAB_LLM_TIMEOUT_SECONDS,
            )
            response = (
                f"{runtime['display_name']} 暂时没有在时限内返回完整分析。"
                "请先基于其他专家视角继续综合，并保留这一缺口提示。"
            )
        except Exception as exc:
            logger.warning(
                "Explicit expert collaboration degraded for expert=%s: %s",
                expert_id,
                exc,
            )
            response = (
                f"{runtime['display_name']} 本轮未稳定返回。请基于现有专家观点继续完成综合，并明确说明该视角暂时缺席。"
            )
        expert_output = {
            "expert_id": expert_id,
            "display_name": runtime["display_name"],
            "agent_role": runtime["agent_role"].value,
            "response": response,
            "few_shot_examples": few_shot_examples,
        }
        handoff_packet = await build_handoff_packet(
            agent=runtime["display_name"],
            response_text=response,
            workflow_type="explicit_expert_collaboration",
        )
        timeline_step = _build_timeline_step(
            runtime["display_name"],
            "expert_analysis",
            datetime.fromtimestamp(started_at),
            output_summary=response[:120],
            agent_role=runtime["agent_role"].value,
        )
        return expert_output, handoff_packet.to_dict(), timeline_step, len(few_shot_examples[:1])

    if run_parallel:
        parallel_results = await asyncio.gather(*[_run_single_expert(expert_id, []) for expert_id in selected])
        for expert_output, handoff_packet, timeline_step, few_shot_count in parallel_results:
            expert_outputs.append(expert_output)
            handoff_packets.append(handoff_packet)
            timeline.append(timeline_step)
            few_shot_total += few_shot_count
    else:
        for expert_id in selected:
            expert_output, handoff_packet, timeline_step, few_shot_count = await _run_single_expert(
                expert_id,
                list(handoff_packets),
            )
            expert_outputs.append(expert_output)
            handoff_packets.append(handoff_packet)
            timeline.append(timeline_step)
            few_shot_total += few_shot_count

    synthesis_target = answer_targets[0] if answer_targets else selected[0]
    synthesis_runtime = await _resolve_llm_for_expert(
        expert_id=synthesis_target,
        state=state,
        task_type=TaskType.STANDARD_RESPONSE,
    )
    synthesis_runtime["display_name"] = f"{synthesis_runtime['display_name']}·综合"
    synthesis_examples: list[dict[str, Any]] = []
    if few_shot_total < 3 and should_inject_few_shot(
        workflow_type="explicit_expert_collaboration",
        stage="synthesis",
        agent_role="synthesis",
    ):
        synthesis_examples = await resolve_few_shot_examples(
            db_session=state.context_data.get("db_session"),
            user_id=state.context_data.get("user_id") or getattr(state, "user_id", None),
            workflow_type="explicit_expert_collaboration",
            chat_mode=str(state.context_data.get("chat_mode", "standard") or "standard"),
            agent_role="synthesis",
            stage="synthesis",
            count=1,
        )
    synthesis_prompt = _build_expert_collaboration_system_prompt(
        state=state,
        runtime=synthesis_runtime,
        user_context=inject_examples_into_user_context(user_context, synthesis_examples),
        conversation_context=conversation_context,
        prompt_version=prompt_version,
    )
    synthesis_input = format_handoff_packets(handoff_packets, title="专家桥接摘要包")
    synthesis_raw_excerpt = "\n\n".join(
        f"### {item['display_name']} 原文片段\n{item['response'][:220]}"
        for item in expert_outputs
        if item["expert_id"] in answer_targets
    )
    answer_names = (
        "、".join(item["display_name"] for item in expert_outputs if item["expert_id"] in answer_targets)
        or synthesis_runtime["display_name"]
    )
    try:
        final_response = await asyncio.wait_for(
            synthesis_runtime["service"].chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{synthesis_prompt}\n\n"
                            "## 多专家综合要求\n"
                            f"本轮参与专家：{'、'.join(item['display_name'] for item in expert_outputs)}。\n"
                            f"最终定稿优先吸收：{answer_names}。\n"
                            "请输出一份统一答案，既保留分歧，也给出清晰结论。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"{build_collaboration_user_query(base_query=user_message, workflow_type='explicit_expert_collaboration', handoff_packets=handoff_packets, few_shot_examples=synthesis_examples)}\n\n"
                            f"专家观点汇总：\n{synthesis_input}\n\n"
                            f"必要原文片段：\n{synthesis_raw_excerpt}"
                        ),
                    },
                ],
                temperature=0.4,
            ),
            timeout=_EXPLICIT_COLLAB_LLM_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning(
            "Explicit expert collaboration synthesis timed out for target=%s after %.1fs",
            synthesis_target,
            _EXPLICIT_COLLAB_LLM_TIMEOUT_SECONDS,
        )
        final_response = (
            "我先给你一个保底综合版，避免这轮协作卡住：\n\n"
            + "\n".join(
                f"{index + 1}. {item['display_name']}：{str(item['response']).strip()[:120]}"
                for index, item in enumerate(expert_outputs[:3])
            )
            + "\n\n最终建议：先按以上共识执行；如果你需要，我可以继续补一版更完整的综合说明。"
        )
    except Exception as exc:
        logger.warning("Explicit expert collaboration synthesis degraded: %s", exc)
        final_response = (
            "这轮多专家综合出现波动，我先把已经稳定拿到的观点整理给你：\n\n"
            + "\n".join(
                f"- {item['display_name']}：{str(item['response']).strip()[:140]}" for item in expert_outputs[:3]
            )
            + "\n\n你可以先按这个版本继续推进，我随后还能继续细化。"
        )
    timeline.append(
        _build_timeline_step(
            synthesis_runtime["display_name"],
            "final_synthesis",
            datetime.fromtimestamp(time.time()),
            output_summary=final_response[:120],
            agent_role=synthesis_runtime["agent_role"].value,
        )
    )
    return CollaborationResult(
        workflow_type="explicit_expert_collaboration",
        participants=[item["display_name"] for item in expert_outputs],
        outputs=[],
        final_response=final_response,
        reasoning=" -> ".join(item["display_name"] for item in expert_outputs),
        metadata={
            "selected_experts": list(selected),
            "answer_experts": list(answer_targets),
            "expert_outputs": expert_outputs,
            "handoff_packets": handoff_packets,
            "few_shot_total": few_shot_total + len(synthesis_examples[:1]),
        },
        timeline=timeline,
        confidence=0.85,
    )


def _build_generation_fallback_response(
    *,
    user_message: str,
    knowledge_context: str,
    document_context: str,
    task_type: TaskType = TaskType.STANDARD_RESPONSE,
) -> str:
    best_fact = _extract_best_retrieval_fact(knowledge_context, document_context)
    snippets = _extract_retrieval_snippets(knowledge_context, document_context)

    if task_type is TaskType.TASK_DECOMPOSITION:
        evidence = best_fact or (snippets[0] if snippets else "")
        steps = snippets[:3]
        lines = [
            "我先给你一版可直接执行的学习任务拆解：",
            "",
            "1. 今天先做什么",
            (
                f"- 先聚焦当前主题，拿出 25 分钟完成一个最小闭环。{evidence}"
                if evidence
                else "- 先用 25 分钟完成一个最小闭环：明确目标、做 1 个例题、写 3 行总结。"
            ),
            "",
            "2. 接下来怎么拆",
        ]
        if steps:
            lines.extend(f"- 第 {index + 1} 步：{item}" for index, item in enumerate(steps))
        else:
            lines.extend(
                [
                    "- 第 1 步：先梳理概念和公式/定义。",
                    "- 第 2 步：立刻做 2-3 个代表题，找出卡点。",
                    "- 第 3 步：把卡点整理成一张错因清单，明天回看。",
                ]
            )
        lines.extend(
            [
                "",
                "3. 一个关键提醒",
                "- 先做可完成的最小任务，不要一上来把学习计划写得过满。",
            ]
        )
        return "\n".join(lines).strip()

    if task_type is TaskType.ERROR_DIAGNOSIS:
        evidence = best_fact or (snippets[0] if snippets else "")
        lines = [
            "我先给你一版结构化诊断：",
            "",
            "1. 最可能的问题",
            f"- {evidence}" if evidence else "- 你现在更像是概念边界没压实，导致一遇到变体题就开始混淆。",
            "",
            "2. 为什么会这样",
            f"- {snippets[1]}" if len(snippets) > 1 else "- 常见原因是只记结论、不记触发条件，做题时只能靠感觉判断。",
            "",
            "3. 立刻怎么修",
            (
                f"- {snippets[2]}"
                if len(snippets) > 2
                else "- 现在就写出“判断条件 -> 典型反例 -> 一句口诀”三联表，再做 2 题验证。"
            ),
            "",
            "4. 5 分钟自测",
            "- 任选一道相似题，不看答案先说出判断条件；如果说不完整，说明问题还在概念层。",
        ]
        return "\n".join(lines).strip()

    if best_fact:
        return f"根据当前检索到的可靠信息，{best_fact}"

    if snippets:
        joined = "\n".join(snippets)
        return f"我先根据已检索到的知识结果直接回答你：\n{joined}"

    return f"我已经收到你的问题“{user_message}”。如果你愿意，我可以继续把它整理成更细的步骤、诊断或执行清单。"


def _extract_retrieval_snippets(*contexts: str) -> list[str]:
    snippets: list[str] = []
    for raw_context in contexts:
        if not raw_context:
            continue
        for line in raw_context.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if cleaned.startswith("Relevant Knowledge Base") or cleaned.startswith("Relevant Documents"):
                continue
            if cleaned.startswith("- [") and "]: " in cleaned:
                cleaned = cleaned.split("]: ", 1)[1].strip()
            elif cleaned.startswith("- "):
                cleaned = cleaned[2:].strip()
            snippets.append(cleaned)
            if len(snippets) >= 4:
                return snippets
    return snippets


def _rescue_tier_for_task(task_type: TaskType) -> ModelTier:
    if task_type is TaskType.ERROR_DIAGNOSIS:
        return ModelTier.PRO
    if task_type is TaskType.TASK_DECOMPOSITION:
        return ModelTier.PLUS
    return ModelTier.FAST


def _build_mode_rescue_instruction(task_type: TaskType) -> str:
    if task_type is TaskType.TASK_DECOMPOSITION:
        return (
            "你需要直接输出一版高质量、结构化、可执行的学习任务拆解。\n"
            "固定输出：1. 目标判断；2. 今天先做什么；3. 3-5 步学习拆解；4. 风险提醒。\n"
            "不要暴露内部错误、工具过程、检索过程、模型忙等信息。"
        )
    if task_type is TaskType.ERROR_DIAGNOSIS:
        return (
            "你需要直接输出一版高质量、结构化的错误诊断。\n"
            "固定输出：1. 最可能误区；2. 为什么会混淆；3. 立刻修正办法；4. 5 分钟自测。\n"
            "不要暴露内部错误、工具过程、检索过程、模型忙等信息。"
        )
    return (
        "主生成链当前不可用时，你需要直接输出一版可靠、简洁、可执行的最终回答。\n"
        "不要暴露内部错误、工具失败、检索过程或“我来帮你查一下”这类过程性话术。\n"
        "优先给结论、步骤和关键提醒，保持短段落。"
    )


async def _build_mode_rescue_response(
    *,
    agent_role: str,
    system_prompt: str,
    user_message: str,
    task_type: TaskType,
    reasoning_mode: str,
    knowledge_context: str = "",
    document_context: str = "",
) -> tuple[str, ModelTier]:
    rescue_tier = _rescue_tier_for_task(task_type)
    rescue_task_type = TaskType.QUICK_QUERY if task_type is TaskType.STANDARD_RESPONSE else task_type
    rescue_llm = await get_configured_llm_service_for_tier(
        agent_role,
        rescue_tier,
        task_type=rescue_task_type,
        reasoning_mode=reasoning_mode,
    )
    snippets = _extract_retrieval_snippets(knowledge_context, document_context)
    rescue_context = ""
    if snippets:
        rescue_context = "\n\n## 可用知识线索\n" + "\n".join(f"- {item}" for item in snippets[:4])
    rescue_prompt = system_prompt + "\n\n## 紧急回退要求\n" + _build_mode_rescue_instruction(task_type) + rescue_context
    response = await rescue_llm.chat(
        [
            {"role": "system", "content": rescue_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.35,
    )
    return str(response or "").strip(), rescue_tier


def _extract_community_prompt_context(user_message: str) -> dict[str, str]:
    text = str(user_message or "")
    if not text:
        return {}

    private_match = re.search(r"你是Sparkle内置的私聊AI助手，正在协助我与「(?P<name>[^」]+)」的对话。", text)
    if private_match:
        question_match = re.search(r"用户问题:\s*(?P<question>.+)$", text, re.S)
        return {
            "context_type": "community_private",
            "name": private_match.group("name").strip(),
            "question": (question_match.group("question").strip() if question_match else ""),
        }

    group_match = re.search(r"你是Sparkle内置的群聊AI助手，正在协助群聊「(?P<name>[^」]+)」。", text)
    if group_match:
        question_match = re.search(r"用户问题:\s*(?P<question>.+)$", text, re.S)
        return {
            "context_type": "community_group",
            "name": group_match.group("name").strip(),
            "question": (question_match.group("question").strip() if question_match else ""),
        }

    return {}


def _build_community_prompt_fallback_response(user_message: str) -> str:
    prompt_context = _extract_community_prompt_context(user_message)
    context_type = prompt_context.get("context_type")
    name = prompt_context.get("name", "").strip()
    question = prompt_context.get("question", "").strip()
    if not context_type or not question:
        return ""

    normalized_question = re.sub(r"\s+", " ", question).strip()
    normalized_question = normalized_question.rstrip("。！？!?")

    if context_type == "community_private":
        direct_message = normalized_question
        question_parts = re.split(r"[，,]", normalized_question, maxsplit=1)
        if len(question_parts) == 2 and any(
            marker in question_parts[0] for marker in ("写一条", "回复", "消息", "文案", "建议")
        ):
            direct_message = question_parts[1].strip()
        else:
            direct_message = re.sub(
                r"^帮我给[^，,。]*写一条.*?(?:回复|消息|文案|建议)?",
                "",
                normalized_question,
            ).strip()
        if not direct_message:
            direct_message = normalized_question
        if direct_message.startswith("约"):
            direct_message = direct_message[1:].strip()
        direct_message = direct_message.rstrip("。！？!?")
        if not direct_message:
            direct_message = "这件事我们再对一下"
        prefix = f"{name}，" if name else ""
        return f"{prefix}{direct_message}，你方便吗？"

    if context_type == "community_group":
        direct_message = re.sub(
            r"^帮我(?:在群里)?(?:发|写|说)(?:一条)?(?:简短|自然|清晰)?(?:、|，|,)?(?:消息|提醒|回复)?(?:，|,)?",
            "",
            normalized_question,
        ).strip()
        if not direct_message:
            direct_message = normalized_question
        direct_message = direct_message.rstrip("。！？!?")
        if not direct_message:
            direct_message = "这件事大家同步一下"
        return f"大家好，{direct_message}。"

    return ""


def _strip_wrapping_quotes(text: str) -> str:
    pairs = (("“", "”"), ('"', '"'), ("'", "'"))
    stripped = text.strip()
    for left, right in pairs:
        if stripped.startswith(left) and stripped.endswith(right) and len(stripped) >= 2:
            return stripped[1:-1].strip()
    return stripped


def _sanitize_community_sendable_response(user_message: str, response_text: str) -> str:
    prompt_context = _extract_community_prompt_context(user_message)
    if not prompt_context:
        return str(response_text or "").strip()

    cleaned = str(response_text or "").strip()
    if not cleaned:
        return cleaned

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return ""

    lead_in_patterns = (
        r"^(我来帮你|让我帮你|我帮你|我先帮你)",
        r"^(你可以这样发|可以这样发|可以直接发|建议发|建议回复|建议你发|建议你回复)",
        r"^(下面是|这是|给你的|为你准备的).*(消息|回复|文案)",
        r"^(群里可以这样发|私聊可以这样回|可直接发送|直接发这句)",
    )
    while lines and any(re.match(pattern, lines[0]) for pattern in lead_in_patterns):
        lines.pop(0)

    if lines and re.match(r"^(消息|回复|文案|发送内容|建议内容)\s*[:：]$", lines[0]):
        lines.pop(0)

    sanitized = "\n".join(lines).strip()
    sanitized = _strip_wrapping_quotes(sanitized)
    return sanitized or cleaned


def _extract_best_retrieval_fact(*contexts: str) -> str:
    for raw_context in contexts:
        if not raw_context:
            continue
        for line in raw_context.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if cleaned.startswith("Relevant Knowledge Base") or cleaned.startswith("Relevant Documents"):
                continue
            if cleaned.startswith("- [") and "]: " in cleaned:
                return cleaned.split("]: ", 1)[1].strip()
            if cleaned.startswith("- "):
                return cleaned[2:].strip()
    return ""


def _is_low_information_generation_response(text: str) -> bool:
    normalized = re.sub(r"\s+", "", str(text or "")).lower()
    if not normalized:
        return False

    weak_starters = (
        "我来帮你查询",
        "我来帮你查找",
        "我来帮你看看",
        "我来帮你给",
        "我来帮你写",
        "我来帮你草拟",
        "我来帮你整理",
        "让我帮你查询",
        "让我帮你查找",
        "我帮你查询",
        "我先帮你查询",
    )
    return any(starter in normalized for starter in weak_starters)


def _resolve_recent_memory_answer(conversation_context: dict[str, Any] | None, user_message: str) -> str | None:
    normalized_question = str(user_message or "").strip()
    if not normalized_question:
        return None

    question_match = re.search(r"(?:我刚才说的)?我的(?P<key>[\w\u4e00-\u9fa5]{1,12})是什么", normalized_question)
    english_question_match = re.search(
        r"what(?:'s| is) my (?P<key>[a-z][a-z0-9 _-]{0,40})\??",
        normalized_question.strip().lower(),
    )
    if not question_match and not english_question_match:
        return None

    memory_key = (
        question_match.group("key").strip()
        if question_match
        else re.sub(r"\s+", " ", english_question_match.group("key").strip().lower())
    )
    messages = (conversation_context or {}).get("messages", []) if isinstance(conversation_context, dict) else []

    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = str(message.get("content") or "").strip()
        if not content or content == normalized_question or "？" in content or "?" in content:
            continue
        fact_match = re.search(
            r"(?:记住)?我的(?P<key>[\w\u4e00-\u9fa5]{1,12})是(?P<value>[^，。！？\n]+)",
            content,
        )
        english_fact_match = re.search(
            r"(?:remember\s+)?my (?P<key>[a-z][a-z0-9 _-]{0,40}) is (?P<value>[^,.!?\n]+)",
            content.strip().lower(),
        )
        fact_key = ""
        value = ""
        if fact_match:
            fact_key = fact_match.group("key").strip()
            value = fact_match.group("value").strip().strip("“”\"'")
        elif english_fact_match:
            fact_key = re.sub(r"\s+", " ", english_fact_match.group("key").strip().lower())
            value = english_fact_match.group("value").strip().strip("“”\"'")
        else:
            continue
        if fact_key != memory_key:
            continue
        if value in {"什么", "多少", "谁", "哪", "哪里", "几点", "几号", "怎么"}:
            continue
        return value

    return None


def _select_recent_conversation_messages(
    conversation_context: dict[str, Any] | None,
    state_messages: list[dict[str, Any]] | None,
    current_user_message: str,
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    messages = []
    if isinstance(conversation_context, dict):
        raw_messages = conversation_context.get("messages") or []
        if isinstance(raw_messages, list):
            messages = [msg for msg in raw_messages if isinstance(msg, dict)]
    if not messages and isinstance(state_messages, list):
        messages = [msg for msg in state_messages if isinstance(msg, dict)]
    if limit > 0:
        messages = messages[-limit:]

    if (
        messages
        and str(messages[-1].get("role") or "") == "user"
        and str(messages[-1].get("content") or "").strip() == str(current_user_message or "").strip()
    ):
        messages = messages[:-1]

    return messages


def _document_group_scope(context_data: dict[str, Any] | None) -> tuple[bool, list[str]]:
    payload = context_data or {}
    conversation_settings = payload.get("conversation_settings")
    if not isinstance(conversation_settings, dict):
        conversation_settings = {}

    include_group_documents = bool(
        payload.get("include_group_documents")
        or conversation_settings.get("include_group_documents")
        or payload.get("group_id")
        or conversation_settings.get("group_id")
    )

    raw_group_ids = payload.get("group_ids") or conversation_settings.get("group_ids") or []
    group_ids: list[str] = []
    seen: set[str] = set()
    for item in raw_group_ids:
        value = str(item or "").strip()
        if value and value not in seen:
            seen.add(value)
            group_ids.append(value)

    primary_group_id = str(payload.get("group_id") or conversation_settings.get("group_id") or "").strip()
    if primary_group_id and primary_group_id not in seen:
        group_ids.append(primary_group_id)

    return include_group_documents, group_ids


async def context_builder_node(state: WorkflowState) -> WorkflowState:
    """Build user and conversation context."""
    logger.info("Building context...")
    user_context = state.context_data.get("user_context")
    if not user_context:
        user_context = {"name": "User", "preferences": {}}
    state.context_data["user_context"] = user_context
    return state


async def retrieval_node(state: WorkflowState) -> WorkflowState:
    """RAG Retrieval."""
    query = state.messages[-1]["content"] if state.messages else ""
    db_session = state.context_data.get("db_session")
    user_id = state.context_data.get("user_id")
    file_ids = state.context_data.get("file_ids") or []
    include_references = bool(state.context_data.get("include_references"))

    existing_document_context = str(state.context_data.get("document_context") or "").strip()
    if not db_session or not user_id or not query:
        state.context_data["knowledge_context"] = ""
        state.context_data["document_context"] = existing_document_context
        return state

    try:
        user_uuid = uuid.UUID(str(user_id))
    except ValueError:
        state.context_data["knowledge_context"] = ""
        state.context_data["document_context"] = existing_document_context
        return state

    knowledge_context = ""
    document_context = existing_document_context
    citations = []
    turn_citation_payloads: list[dict[str, Any]] = []
    injected_document_chunks = 0
    conversation_id = str(state.context_data.get("session_id") or "").strip() or None
    query_type = "knowledge_query"
    include_group_documents, group_ids = _document_group_scope(state.context_data)
    document_context_mode = await AuroraDocContextKillSwitchService().get_mode()
    state.context_data["document_context_mode"] = document_context_mode
    state.context_data["document_context_controls"] = {
        "mode": document_context_mode,
        "ratio": settings.DOCUMENT_CONTEXT_RATIO,
        "max_chunks": settings.DOCUMENT_CONTEXT_MAX_CHUNKS,
        "similarity_threshold": settings.DOCUMENT_CONTEXT_SIMILARITY_THRESHOLD,
        "recency_boost_days": settings.DOCUMENT_CONTEXT_RECENCY_BOOST_DAYS,
    }
    if existing_document_context and document_context_mode == "off":
        state.context_data["document_context_candidate"] = existing_document_context
        document_context = ""
    try:
        await document_service.capture_implicit_feedback_from_message(
            user_id=str(user_uuid),
            conversation_id=conversation_id,
            user_message=query,
            db=db_session,
        )
    except Exception as exc:
        logger.warning(f"Implicit document feedback capture failed: {exc}")
    try:
        ks = KnowledgeService(db_session)
        knowledge_context = await ks.retrieve_context(user_id=user_uuid, query=query, limit=5)
        decision = (
            state.context_data.get("document_retrieval_decision") or state.context_data.get("retrieval_decision") or {}
        )
        route_intent = (
            state.context_data.get("route_intent")
            or state.context_data.get("intent_type")
            or infer_route_intent_from_chat_mode(state.context_data.get("chat_mode"))
        )
        if (
            isinstance(decision, dict)
            and decision.get("should_retrieve")
            and not document_context
            and document_context_mode != "off"
        ):
            mode = str(decision.get("retrieval_mode") or "selective")
            # v2.9: Spine RetrievalDirective may override retrieval depth
            _spine_ret_dir = state.context_data.get("spine_retrieval_directive")
            _rag_depth = 2 if mode == "aggressive" else 1
            if isinstance(_spine_ret_dir, dict):
                _spine_retrieval_mode = _spine_ret_dir.get("retrieval_mode")
                if _spine_retrieval_mode == "task_bound_graph_rag":
                    _rag_depth = 2
                elif _spine_retrieval_mode == "off":
                    mode = "off"
                _spine_budget = _spine_ret_dir.get("token_budget")
                if isinstance(_spine_budget, int) and _spine_budget > 0:
                    state.context_data["spine_rag_token_budget"] = _spine_budget
            retriever = GraphRAGRetriever(ks)
            rag_result = await asyncio.wait_for(
                retriever.retrieve(
                    query,
                    str(user_uuid),
                    depth=_rag_depth,
                    route_intent=str(route_intent) if route_intent else None,
                    include_group_documents=include_group_documents,
                    group_ids=group_ids,
                ),
                timeout=max(6.0, float(getattr(settings, "GRAPHRAG_FASTPATH_TIMEOUT_SECONDS", 2.5) or 2.5) * 3),
            )
            filtered_rag = filter_graph_rag_result(rag_result)
            document_context_candidate = format_graph_rag_document_context(rag_result, filtered_rag.chunks)
            state.context_data["document_context_candidate"] = document_context_candidate
            state.context_data["document_context_candidate_chunks"] = len(filtered_rag.chunks)
            document_context = document_context_candidate
            injected_document_chunks = len(filtered_rag.chunks)
            state.context_data["document_context_retrieval"] = {
                "source": "graphrag",
                "mode": mode,
                "total_retrieved": filtered_rag.total_retrieved,
                "total_passed": filtered_rag.total_passed,
                "fallback_triggered": filtered_rag.fallback_triggered,
                "entities": list(rag_result.entities or []),
            }
            for item in filtered_rag.chunks:
                turn_citation_payloads.append(
                    {
                        "chunk_id": item.chunk_id,
                        "file_id": item.source_file_id,
                        "title": item.file_name,
                        "page_number": item.page_number,
                        "chunk_index": item.chunk_index,
                        "section_title": item.metadata.get("section_title"),
                        "content_preview": item.content[:400],
                    }
                )
                if include_references and item.chunk_id and item.source_file_id:
                    title = item.file_name or "Study material"
                    section_title = str(item.metadata.get("section_title") or "").strip()
                    if section_title:
                        title = f"{title} - {section_title}"
                    citations.append(
                        agent_service_pb2.Citation(
                            id=str(item.chunk_id),
                            title=title,
                            content=item.content[:400] + ("..." if len(item.content) > 400 else ""),
                            source_type="document",
                            url="",
                            score=item.relevance_score,
                            file_id=str(item.source_file_id),
                            page_number=item.page_number or 0,
                            chunk_index=item.chunk_index or 0,
                            section_title=section_title,
                        )
                    )
    except Exception as e:
        logger.warning(f"Knowledge retrieval failed: {e}")

    if file_ids and document_context_mode in {"shadow", "live"}:
        file_uuid_list = []
        for fid in file_ids:
            try:
                file_uuid_list.append(uuid.UUID(str(fid)))
            except ValueError:
                continue

        if file_uuid_list:
            try:
                ks = KnowledgeService(db_session)
                hyde_query = await ks.generate_hypothetical_answer(query)
                retrieval = KnowledgeRetrievalService(db_session)
                doc_results = await retrieval.document_vector_search(
                    user_id=user_uuid,
                    query=query,
                    file_ids=file_uuid_list,
                    vector_query=hyde_query,
                    limit=max(0, int(settings.DOCUMENT_CONTEXT_MAX_CHUNKS or 0)),
                    threshold=float(settings.DOCUMENT_CONTEXT_SIMILARITY_THRESHOLD),
                    include_group_documents=include_group_documents,
                    group_ids=group_ids,
                )
                filtered_docs = filter_retrieved_chunks(query=query, chunks=doc_results)
                state.context_data["document_context_retrieval"] = {
                    "source": "document_vector_search",
                    "total_retrieved": filtered_docs.total_retrieved,
                    "total_passed": filtered_docs.total_passed,
                    "fallback_triggered": filtered_docs.fallback_triggered,
                }

                if filtered_docs.chunks:
                    document_budget = ContextBudgetManager().allocate().get("document_chunks", 0)
                    document_context_candidate, document_budget_metadata = format_document_chunks_for_prompt(
                        filtered_docs.chunks,
                        budget=document_budget,
                    )
                    state.context_data["document_context_budget"] = document_budget_metadata
                    for item in filtered_docs.chunks:
                        chunk = item.chunk
                        snippet = chunk.content.strip()
                        if len(snippet) > 400:
                            snippet = snippet[:400] + "..."
                        page_number = _first_document_page_number(chunk)

                        turn_citation_payloads.append(
                            {
                                "chunk_id": str(chunk.id),
                                "file_id": str(chunk.file_id),
                                "title": item.file_name,
                                "page_number": page_number,
                                "chunk_index": chunk.chunk_index,
                                "section_title": chunk.section_title,
                                "content_preview": snippet,
                            }
                        )
                        if include_references:
                            title = item.file_name
                            if chunk.section_title:
                                title = f"{item.file_name} - {chunk.section_title}"

                            citations.append(
                                agent_service_pb2.Citation(
                                    id=str(chunk.id),
                                    title=title,
                                    content=snippet,
                                    source_type="document",
                                    url="",
                                    score=item.relevance_score,
                                    file_id=str(chunk.file_id),
                                    page_number=page_number or 0,
                                    chunk_index=chunk.chunk_index,
                                    section_title=chunk.section_title or "",
                                )
                            )

                    state.context_data["document_context_candidate"] = document_context_candidate
                    state.context_data["document_context_candidate_chunks"] = document_budget_metadata.get(
                        "shown_results",
                        len(filtered_docs.chunks),
                    )
                    if document_context_mode == "live":
                        document_context = document_context_candidate
                        injected_document_chunks = int(document_budget_metadata.get("shown_results") or 0)
                    else:
                        state.context_data["document_context_shadow_only"] = True
            except Exception as e:
                logger.warning(f"Document retrieval failed: {e}")

    state.context_data["knowledge_context"] = knowledge_context
    state.context_data["document_context"] = document_context
    if document_context:
        DOCUMENT_CONTEXT_CHUNKS_INJECTED_TOTAL.inc(injected_document_chunks)
        DOCUMENT_CONTEXT_TOKENS_USED.observe(estimate_tokens(document_context))

    if turn_citation_payloads:
        try:
            await document_service.register_turn_citations(
                user_id=str(user_uuid),
                conversation_id=conversation_id,
                query=query,
                query_type=query_type,
                citations=turn_citation_payloads,
            )
        except Exception as exc:
            logger.warning(f"Failed to register cited chunks for implicit feedback: {exc}")

    if include_references and citations and document_context_mode != "off":
        stream_callback = state.context_data.get("stream_callback")
        if stream_callback:
            await stream_callback(
                agent_service_pb2.ChatResponse(citations=agent_service_pb2.CitationBlock(citations=citations))
            )

    return state


async def generation_node(state: WorkflowState) -> WorkflowState:
    """LLM Generation (Streaming)."""
    executable_plan = state.context_data.get("executable_plan")
    if executable_plan and getattr(executable_plan, "tool_calls", None):
        logger.info(
            "Executable plan already available for session {}, skipping generation and entering tool execution",
            state.context_data.get("session_id", ""),
        )
        state.next_step = "tool_execution"
        return state

    # We need to access the 'stream_callback' from context to yield tokens
    stream_callback = state.context_data.get("stream_callback")

    # Cast to Dict to satisfy type checker
    user_context = state.context_data.get("user_context", {})
    # Ensure user_context is never None
    if user_context is None or not isinstance(user_context, dict):
        user_context = {}

    conversation_context = state.context_data.get("conversation_context")
    if conversation_context is None or not isinstance(conversation_context, dict):
        conversation_context = {"messages": state.messages[:-1]}
    prompt_version = state.context_data.get("prompt_version") or "v1"
    agent_role = _resolve_generation_agent_role(state)
    task_type = _resolve_generation_task_type(state)
    explicit_runtime = None
    user_message = state.messages[-1]["content"] or ""
    use_slim_deep_context = _should_use_slim_deep_analysis_context(state, user_message)
    use_fast_grounded_synthesis = _should_force_final_synthesis_without_tools(state)
    memory_answer = _resolve_recent_memory_answer(conversation_context, user_message)
    use_slim_standard_context = _should_use_slim_standard_context(state, user_message)

    if memory_answer:
        if stream_callback:
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    delta=memory_answer,
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.GENERATING,
                        details="正在根据最近对话补全答案...",
                        current_agent_name="Sparkle AI",
                    ),
                )
            )
        state.context_data["generation_shortcut"] = "recent_memory"
        state.append_message("assistant", memory_answer)
        state.next_step = "__end__"
        return state

    try:
        reasoning_mode = _resolve_reasoning_mode(state)
        explicit_expert_id = _single_explicit_expert_id(state)
        if explicit_expert_id:
            explicit_runtime = await _resolve_llm_for_expert(
                expert_id=explicit_expert_id,
                state=state,
                task_type=task_type,
            )
            generation_llm = explicit_runtime["service"]
            agent_role = explicit_runtime["agent_role"].value
        else:
            forced_phase_d_tier = _phase_d_forced_model_tier(state)
            if forced_phase_d_tier is not None:
                generation_llm = await get_configured_llm_service_for_tier(
                    agent_role,
                    forced_phase_d_tier,
                    task_type=task_type,
                    reasoning_mode=reasoning_mode,
                )
                state.context_data["phase_d_model_tier_enforced"] = forced_phase_d_tier.value
            elif _should_force_fast_first_touch(
                state,
                explicit_runtime=explicit_runtime,
                task_type=task_type,
            ):
                generation_llm = await get_configured_llm_service_for_tier(
                    agent_role,
                    ModelTier.FAST,
                    task_type=task_type,
                    reasoning_mode=reasoning_mode,
                )
                state.context_data["first_touch_model_tier"] = ModelTier.FAST.value
            elif _should_force_balanced_fast_first_touch(
                state,
                explicit_runtime=explicit_runtime,
                task_type=task_type,
                user_message=user_message,
                use_slim_standard_context=use_slim_standard_context,
            ):
                generation_llm = await get_configured_llm_service_for_tier(
                    agent_role,
                    ModelTier.FAST,
                    task_type=TaskType.QUICK_QUERY,
                    reasoning_mode=reasoning_mode,
                )
                state.context_data["first_touch_model_tier"] = ModelTier.FAST.value
                state.context_data["first_touch_profile"] = "balanced_fast_path"
            elif use_fast_grounded_synthesis:
                if reasoning_mode == "fast":
                    generation_llm = await get_configured_llm_service_for_tier(
                        agent_role,
                        ModelTier.FAST,
                        task_type=task_type,
                        reasoning_mode=reasoning_mode,
                    )
                    state.context_data["final_synthesis_model_tier"] = ModelTier.FAST.value
                else:
                    generation_llm = await get_configured_llm_service(
                        agent_role,
                        task_type,
                        reasoning_mode=reasoning_mode,
                    )
            else:
                generation_llm = await get_configured_llm_service(
                    agent_role,
                    task_type,
                    reasoning_mode=reasoning_mode,
                )
    except Exception as e:
        logger.warning(f"Failed to configure role-scoped LLM for {agent_role}/{task_type.value}: {e}")
        generation_llm = llm_service

    # Extract plan_context from state if available
    plan_context = state.context_data.get("plan_context")
    if use_fast_grounded_synthesis:
        prompt_user_context = _build_minimal_user_context_for_grounded_synthesis(user_context)
        prompt_conversation_context = {
            "messages": (conversation_context.get("messages") or [])[-4:],
        }
    elif use_slim_standard_context:
        prompt_user_context = _build_slim_user_context_for_standard_reply(user_context)
        prompt_conversation_context = {
            # For generic standard Q&A, keep only the current in-session turns to
            # avoid dragging historical plan/task state into concept explanations.
            "messages": _select_recent_conversation_messages(
                conversation_context,
                list(state.messages or []),
                user_message,
                limit=6,
            ),
        }
    else:
        prompt_user_context = (
            _build_slim_user_context_for_deep_analysis(user_context) if use_slim_deep_context else user_context
        )
        prompt_conversation_context = {"messages": []} if use_slim_deep_context else conversation_context

    seed_library_enabled = bool((prompt_user_context or {}).get("seed_library_enabled"))
    generation_seed_examples: list[dict[str, Any]] = []
    if seed_library_enabled:
        try:
            generation_seed_examples = await resolve_few_shot_examples(
                db_session=state.context_data.get("db_session"),
                user_id=state.context_data.get("user_id") or getattr(state, "user_id", None),
                workflow_type=str(state.context_data.get("workflow_id") or "standard_chat"),
                chat_mode=str(state.context_data.get("chat_mode", "standard") or "standard"),
                agent_role=str(getattr(generation_llm, "agent_role", agent_role) or agent_role),
                stage="generation",
                count=2,
            )
        except Exception as exc:
            logger.warning(f"Failed to resolve generation seed examples: {exc}")

    if generation_seed_examples:
        prompt_user_context = inject_examples_into_user_context(
            prompt_user_context,
            generation_seed_examples,
        )
        state.context_data["seed_library_example_count"] = len(generation_seed_examples)
    else:
        state.context_data["seed_library_example_count"] = 0

    # Extract intent instruction from plan_metadata (Vision Item 4b)
    # P1 Improvement: Enhanced intent instructions with stronger constraints
    plan_metadata = state.context_data.get("plan_metadata", {})
    route_reason = plan_metadata.get("route_reason", "")
    route_reason_lc = str(route_reason).lower()
    intent_instruction = None

    if "intent: translation" in route_reason_lc or "unified:translation" in route_reason_lc:
        intent_instruction = """
IMPORTANT: User wants TRANSLATION.
You MUST use the 'translate' tool to translate the user's text.
DO NOT provide translation yourself - always use the tool.
"""
    elif "intent: prism" in route_reason_lc or "unified:cognitive_prism" in route_reason_lc:
        intent_instruction = """
IMPORTANT: User wants BEHAVIOR ANALYSIS (Cognitive Prism).
You MUST use the 'get_user_behavior_patterns' tool to retrieve their behavior patterns.
After getting the results, provide insights about their study habits based on the data.
DO NOT make up or assume patterns - always use the tool first.
The tool will return:
- cognitive patterns: thinking and learning patterns
- emotional patterns: emotional responses during study
- execution patterns: task execution habits
"""
    elif "intent: sprint" in route_reason_lc or "unified:sprint_plan" in route_reason_lc:
        intent_instruction = """
IMPORTANT: User wants to enter FOCUS/SPRINT MODE.
You MUST use the 'suggest_focus_session' tool to recommend a focus session.
Include duration and task suggestions based on the user's current context.
Ask about their available time and current tasks if needed.
"""

    system_prompt = build_system_prompt(
        prompt_user_context,
        conversation_history=prompt_conversation_context,
        prompt_version=prompt_version,
        agent_role=_coerce_agent_role(getattr(generation_llm, "agent_role", agent_role)),
        model_key=getattr(generation_llm, "model_key", None),
        plan_context=(
            None
            if (use_slim_deep_context or use_fast_grounded_synthesis or use_slim_standard_context)
            else plan_context
        ),
        intent_instruction=intent_instruction,  # Vision Item 4b
        session_feedback_instruction=(
            "" if use_slim_standard_context else str(state.context_data.get("session_feedback_instruction") or "")
        ),
        dual_core_instruction=(
            "" if use_slim_standard_context else str(state.context_data.get("dual_core_prompt_instruction") or "")
        ),
        context_focus=None if use_slim_standard_context else state.context_data.get("context_focus"),
        context_briefing_note=(
            "" if use_slim_standard_context else str(state.context_data.get("context_briefing_note") or "")
        ),
        context_level=(
            "light" if (use_slim_deep_context or use_fast_grounded_synthesis or use_slim_standard_context) else "full"
        ),
        chat_mode=str(state.context_data.get("chat_mode", "standard") or "standard"),
        spine_response_directive=state.context_data.get("spine_response_directive"),
        spine_chronicle_summary=(
            str(state.context_data.get("spine_chronicle_summary") or "")
            if not use_slim_standard_context else None
        ),
        spine_fatigue_context=(
            state.context_data.get("spine_fatigue_context")
            if not use_slim_standard_context else None
        ),
    )
    if explicit_runtime and explicit_runtime.get("system_prompt"):
        system_prompt += f"\n\n## 自定义专家指令\n{explicit_runtime['system_prompt']}"
    if use_slim_deep_context:
        system_prompt += (
            "\n\n## 深度分析输出约束\n"
            "这是一个通用概念型深度分析问题，请优先输出高密度、强结构化答案，避免冗长铺陈。\n"
            "输出格式固定为：1. 关键结论；2. 类比；3. 反例；4. 最易混淆点；5. 一个立即可用的判断口诀。\n"
            "总长度尽量控制在 700 个中文字符以内；每一部分 1-2 个要点即可，用短段落，不要写成长篇教程。"
        )
    elif use_fast_grounded_synthesis:
        system_prompt += (
            "\n\n## 工具落地收口约束\n"
            "你正在基于已经查到的计划/任务结果给出最终可执行答案。\n"
            "不要再次发起工具或重新铺陈背景，直接输出一版可执行结论。\n"
            "优先给出：1. 今天先做什么；2. 接下来 7 天/诊断步骤；3. 一个最关键提醒。\n"
            "总长度尽量控制在 700 个中文字符以内，使用短段落和项目符号。"
        )
    elif use_slim_standard_context:
        system_prompt += (
            "\n\n## 通用知识问答约束\n"
            "这是一个通用概念解释或轻量建议问题。\n"
            "除非用户明确询问，否则不要引入当前计划、任务、专注统计、画像或系统状态。\n"
            "先直接回答问题本身，再决定是否补一个很轻的下一步建议。\n"
            "如果要给开始动作，也只能给通用、与任何当前待办或计划无关的最小动作，不要点名具体任务。"
        )
    else:
        system_prompt += (
            "\n\n## 对话呈现约束\n"
            "不要把内部动作写给用户，例如“我先帮你查一下”“让我获取一下计划状态”。\n"
            "如果需要工具，直接调用，等待结果后再给结论。\n"
            "如果工具失败，不要原样转述内部错误堆栈；只用一句自然的话说明相关数据暂时不可用，并继续给出可执行建议。"
        )

    chat_mode = str(state.context_data.get("chat_mode", "standard") or "standard").strip()
    if stream_callback and explicit_runtime and chat_mode.startswith("expert::"):
        await stream_callback(
            agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details=f"{explicit_runtime['display_name']} 正在整理专业视角...",
                    current_agent_name=str(explicit_runtime["display_name"] or "Sparkle Expert"),
                ),
                metadata={
                    "selected_experts": json.dumps([explicit_runtime["expert_id"]], ensure_ascii=False),
                    "expert_entry_source": json.dumps({"mode": "explicit_single"}, ensure_ascii=False),
                },
            )
        )

    raw_knowledge_context = state.context_data.get("knowledge_context") or ""
    knowledge_context = (
        ""
        if (use_slim_deep_context or use_fast_grounded_synthesis or use_slim_standard_context)
        else raw_knowledge_context
    )

    raw_document_context = state.context_data.get("document_context") or ""
    document_context = (
        ""
        if (use_slim_deep_context or use_fast_grounded_synthesis or use_slim_standard_context)
        else raw_document_context
    )
    context_budget_manager = ContextBudgetManager()
    context_assembly = context_budget_manager.assemble_prompt(
        base_system_prompt=system_prompt,
        user_message=user_message,
        conversation_history=prompt_conversation_context.get("messages", []),
        galaxy_knowledge=knowledge_context,
        document_context=document_context,
    )
    system_prompt = context_assembly.system_prompt
    prompt_conversation_context = {"messages": context_assembly.conversation_history}
    state.context_data["context_budget"] = {
        "budgets": context_assembly.budgets,
        "token_usage": context_assembly.token_usage,
        "budget_remaining": context_assembly.budget_remaining,
        "metadata": context_assembly.metadata,
    }

    tools = state.context_data.get("tools_schema", [])
    if _should_disable_tools_for_light_standard_reply(state, user_message):
        logger.info("Disabling tool exposure for light standard follow-up reply")
        tools = []
    elif _should_disable_tools_for_deep_analysis(state):
        logger.info("Disabling tool exposure for deep analysis generation")
        tools = []

    force_fast_first_touch = _should_force_fast_first_touch(
        state,
        explicit_runtime=explicit_runtime,
        task_type=task_type,
    )
    force_balanced_fast_first_touch = _should_force_balanced_fast_first_touch(
        state,
        explicit_runtime=explicit_runtime,
        task_type=task_type,
        user_message=user_message,
        use_slim_standard_context=use_slim_standard_context,
    )

    if stream_callback and (force_fast_first_touch or force_balanced_fast_first_touch):
        await stream_callback(
            agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details=(
                        "已收到，Flash 快响层正在组织首轮回复..."
                        if force_fast_first_touch
                        else "已收到，均衡快响层正在组织首轮回复..."
                    ),
                    current_agent_name="Sparkle Flash",
                ),
                metadata={
                    "fast_first_touch": "true" if force_fast_first_touch else "false",
                    "balanced_fast_path": "true" if force_balanced_fast_first_touch else "false",
                    "first_touch_tier": ModelTier.FAST.value,
                },
            )
        )

    # 检查是否使用思考模式，如果是则发送状态更新
    # 这会让前端显示"思考中"提示
    try:
        is_thinking = generation_llm.is_thinking_mode()

        if is_thinking and stream_callback:
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.THINKING,
                        details="正在深度思考中，请稍候...",
                        current_agent_name="Sparkle AI",
                    )
                )
            )
    except Exception as e:
        logger.warning(f"Failed to check thinking mode: {e}")

    full_response = ""
    tool_calls = []
    first_chunk_sent = False  # Track first chunk for status transition
    delta_buffer: list[str] = []
    last_flush_at = time.monotonic()

    state.context_data["active_generation_agent_role"] = str(getattr(generation_llm, "agent_role", agent_role))
    selection = generation_llm.get_current_selection()
    run_ledger = state.context_data.get("run_ledger")
    if selection is not None:
        state.context_data["active_generation_model"] = selection.config.model_name
        state.context_data["generation_model_key"] = selection.model_key
        state.context_data["generation_provider"] = selection.config.provider.value
        state.context_data["generation_model_tier"] = selection.config.tier.value
        state.context_data["model_used"] = selection.model_key
        if run_ledger is not None:
            await run_ledger.record_event(
                event_type="generation_started",
                label="主生成模型开始工作",
                workflow_stage="generation",
                metadata={
                    "role": "generation",
                    "model_key": selection.model_key,
                    "provider": selection.config.provider.value,
                    "tier": selection.config.tier.value,
                    "estimated_cost_per_1k": selection.estimated_cost_per_1k,
                    "is_fallback": selection.is_fallback,
                },
                emit_snapshot=False,
            )

    effective_tools = tools
    if _should_force_final_synthesis_without_tools(state):
        logger.info("Disabling tools for final synthesis after first tool loop")
        effective_tools = []

    try:
        usage_prompt_tokens = 0
        usage_completion_tokens = 0
        generation_stream = generation_llm.chat_stream_with_tools(
            **_build_generation_stream_kwargs(
                generation_llm,
                system_prompt=system_prompt,
                user_message=user_message,
                tools=effective_tools,
                conversation_history=prompt_conversation_context.get("messages", []),
                user_context=user_context,
            )
        )
        try:
            async for chunk in _stream_generation_chunks_with_timeout(generation_stream):
                if chunk.type == "text":
                    full_response += chunk.content
                    if stream_callback:
                        delta_buffer.append(chunk.content)
                        now = time.monotonic()
                        if (
                            sum(len(part) for part in delta_buffer) >= _STREAM_DELTA_FLUSH_CHARS
                            or (now - last_flush_at) >= _STREAM_DELTA_FLUSH_SECONDS
                        ):
                            first_chunk_sent = await _flush_stream_text_buffer(
                                stream_callback=stream_callback,
                                buffer=delta_buffer,
                                first_chunk_sent=first_chunk_sent,
                            )
                            last_flush_at = now
                elif chunk.type == "tool_call_end":
                    tool_calls.append(chunk)
                    if stream_callback:
                        first_chunk_sent = await _flush_stream_text_buffer(
                            stream_callback=stream_callback,
                            buffer=delta_buffer,
                            first_chunk_sent=first_chunk_sent,
                        )
                        last_flush_at = time.monotonic()
                        await stream_callback(
                            agent_service_pb2.ChatResponse(
                                tool_call=agent_service_pb2.ToolCall(
                                    id=chunk.tool_call_id,
                                    name=chunk.tool_name,
                                    arguments=json.dumps(chunk.full_arguments),
                                )
                            )
                        )
                elif chunk.type == "usage":
                    usage_prompt_tokens = chunk.prompt_tokens or 0
                    usage_completion_tokens = chunk.completion_tokens or 0
                    if stream_callback:
                        first_chunk_sent = await _flush_stream_text_buffer(
                            stream_callback=stream_callback,
                            buffer=delta_buffer,
                            first_chunk_sent=first_chunk_sent,
                        )
                        last_flush_at = time.monotonic()
                        await stream_callback(
                            agent_service_pb2.ChatResponse(
                                usage=agent_service_pb2.Usage(
                                    prompt_tokens=chunk.prompt_tokens or 0,
                                    completion_tokens=chunk.completion_tokens or 0,
                                    total_tokens=(chunk.prompt_tokens or 0) + (chunk.completion_tokens or 0),
                                )
                            )
                        )
        finally:
            with contextlib.suppress(Exception):
                await generation_stream.aclose()
    except Exception as e:
        logger.warning(f"Generation streaming failed, attempting fast rescue response: {e}")
        state.context_data["generation_fallback_reason"] = str(e)
        usage_prompt_tokens = 0
        usage_completion_tokens = 0
        try:
            rescued_response, rescue_tier = await _build_mode_rescue_response(
                agent_role=agent_role,
                system_prompt=system_prompt,
                user_message=user_message,
                task_type=task_type,
                reasoning_mode=reasoning_mode,
                knowledge_context=raw_knowledge_context,
                document_context=raw_document_context,
            )
            if rescued_response:
                full_response = rescued_response
                if stream_callback:
                    await stream_callback(
                        agent_service_pb2.ChatResponse(
                            delta=rescued_response,
                            status_update=agent_service_pb2.AgentStatus(
                                state=agent_service_pb2.AgentStatus.GENERATING,
                                details="主生成链波动，已切到快速备援回复...",
                                current_agent_name="Sparkle Rescue",
                            ),
                            metadata={
                                "generation_rescue": "true",
                                "generation_rescue_tier": rescue_tier.value,
                            },
                        )
                    )
        except Exception as rescue_error:
            logger.warning(f"Fast rescue response also failed, using retrieval fallback: {rescue_error}")

    retrieval_grounded_response = _build_generation_fallback_response(
        user_message=user_message,
        knowledge_context=raw_knowledge_context,
        document_context=raw_document_context,
        task_type=task_type,
    )
    if full_response and not tool_calls:
        sanitized_community_response = _sanitize_community_sendable_response(user_message, full_response)
        if sanitized_community_response != full_response:
            logger.info("Sanitized community generation response into direct sendable content")
            full_response = sanitized_community_response
        if _needs_fast_standard_guard(
            use_slim_standard_context=use_slim_standard_context,
            reasoning_mode=reasoning_mode,
            selection=selection,
        ):
            logger.info("Fast standard reply escaped to a higher tier; forcing fast rescue response")
            try:
                rescued_response, _ = await _build_mode_rescue_response(
                    agent_role=agent_role,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    task_type=TaskType.QUICK_QUERY,
                    reasoning_mode="fast",
                )
                if rescued_response:
                    full_response = rescued_response
            except Exception as rescue_error:
                logger.warning(f"Fast standard tier guard rescue failed: {rescue_error}")
        if use_slim_standard_context and (
            _has_standard_tool_or_system_leak(full_response)
            or _has_standard_personal_context_leak(full_response, user_context)
        ):
            logger.info("Replacing standard response that leaked tool/system or unrelated personal context")
            try:
                rescued_response, _ = await _build_mode_rescue_response(
                    agent_role=agent_role,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    task_type=TaskType.QUICK_QUERY,
                    reasoning_mode="fast",
                )
            except Exception as rescue_error:
                logger.warning(f"Standard leak rescue failed, using retrieval-grounded answer: {rescue_error}")
                rescued_response = ""

            if rescued_response and not (
                _has_standard_tool_or_system_leak(rescued_response)
                or _has_standard_personal_context_leak(rescued_response, user_context)
            ):
                full_response = rescued_response
            else:
                full_response = retrieval_grounded_response

    if full_response and not tool_calls and _is_low_information_generation_response(full_response):
        community_fallback = _build_community_prompt_fallback_response(user_message)
        if community_fallback:
            logger.info("Replacing low-information generation response with community prompt fallback")
            full_response = community_fallback
        else:
            try:
                rescued_response, _ = await _build_mode_rescue_response(
                    agent_role=agent_role,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    task_type=task_type,
                    reasoning_mode=reasoning_mode,
                    knowledge_context=raw_knowledge_context,
                    document_context=raw_document_context,
                )
            except Exception as rescue_error:
                logger.warning(f"Low-information rescue failed, using retrieval-grounded answer: {rescue_error}")
                rescued_response = ""

            if rescued_response and not _is_low_information_generation_response(rescued_response):
                logger.info("Replacing low-information generation response with fast rescue answer")
                full_response = rescued_response
            else:
                logger.info("Replacing low-information generation response with retrieval-grounded answer")
                full_response = retrieval_grounded_response

    if not full_response:
        fallback_response = retrieval_grounded_response
        full_response = fallback_response
        if stream_callback:
            if not first_chunk_sent:
                await stream_callback(
                    agent_service_pb2.ChatResponse(
                        delta=fallback_response,
                        status_update=agent_service_pb2.AgentStatus(
                            state=agent_service_pb2.AgentStatus.GENERATING,
                            details="正在返回检索结果（生成模型暂时繁忙）...",
                            current_agent_name="Sparkle AI",
                        ),
                    )
                )
            else:
                await stream_callback(agent_service_pb2.ChatResponse(delta=fallback_response))
    elif stream_callback:
        first_chunk_sent = await _flush_stream_text_buffer(
            stream_callback=stream_callback,
            buffer=delta_buffer,
            first_chunk_sent=first_chunk_sent,
        )
    if selection is not None and run_ledger is not None:
        total_tokens = usage_prompt_tokens + usage_completion_tokens
        await run_ledger.record_event(
            event_type="generation_completed",
            label="主生成模型完成输出",
            workflow_stage="generation",
            metadata={
                "role": "generation",
                "model_key": selection.model_key,
                "provider": selection.config.provider.value,
                "tier": selection.config.tier.value,
                "estimated_cost_per_1k": selection.estimated_cost_per_1k,
                "is_fallback": selection.is_fallback,
                "prompt_tokens": usage_prompt_tokens,
                "completion_tokens": usage_completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_usd": (
                    round((total_tokens / 1000.0) * selection.estimated_cost_per_1k, 6) if total_tokens > 0 else 0.0
                ),
            },
            emit_snapshot=False,
        )

    state.append_message("assistant", full_response)
    if tool_calls:
        tool_loop_count = int(state.context_data.get("tool_loop_count") or 0)
        max_tool_loops = _max_tool_loops_for_state(state)
        if tool_loop_count >= max_tool_loops:
            logger.warning(f"Stopping tool loop after {tool_loop_count} rounds; returning current response directly")
            state.context_data["tool_calls"] = []
            state.next_step = "__end__"
            return state
        state.context_data["tool_calls"] = tool_calls
        state.next_step = "tool_execution"
    else:
        state.context_data["tool_loop_count"] = 0
        state.next_step = "__end__"

    return state


async def tool_execution_node(state: WorkflowState) -> WorkflowState:
    """Execute Tools with Grounding Validation (Phase 1 & Phase 2).

    Phase 2: Now consumes executable_plan from LangGraph planner.
    """
    executor = ToolExecutor()  # Should be injected or cached

    stream_callback = state.context_data.get("stream_callback")
    user_id = state.context_data.get("user_id", "")
    session_id = state.context_data.get("session_id", "")
    db_session = state.context_data.get("db_session")
    redis_client = state.context_data.get("redis_client")
    state.context_data["tool_results"] = []

    # === Phase 2: Check for executable_plan from LangGraph planner ===
    executable_plan = state.context_data.get("executable_plan")
    snapshot = state.context_data.get("snapshot")

    if executable_plan and getattr(executable_plan, "tool_calls", None):
        logger.info(
            f"Executing executable plan: {len(executable_plan.tool_calls)} tool calls, "
            f"plan_id={executable_plan.plan_id}, source={getattr(executable_plan, 'source', 'unknown')}"
        )

        # Use snapshot for validation if available
        validator = state.context_data.get("grounding_validator")
        if validator:
            # Re-validate with snapshot (business rules check)
            validation_result = await validator.validate_plan(executable_plan, snapshot)

            if not validation_result.is_valid:
                logger.error(f"LangGraph plan validation failed: {validation_result.failure_reason}")
                state.context_data["executable_plan"] = None
                if stream_callback:
                    await stream_callback(
                        agent_service_pb2.ChatResponse(
                            delta=f"\n\n⚠️ 计划执行被拒绝: {validation_result.failure_reason}"
                        )
                    )
                state.context_data["validation_failed"] = True
                state.next_step = "__end__"
                return state

            if validation_result.requires_confirmation or validation_result.requires_hitl:
                logger.warning(f"LangGraph plan requires confirmation: {validation_result.risk_flags}")
                state.context_data["executable_plan"] = None
                action_id = await _queue_hitl_action(
                    user_id=str(user_id),
                    reason="risk_flags",
                    description="高风险操作需要确认",
                    tool_calls=executable_plan.tool_calls,
                    plan_id=executable_plan.plan_id,
                    snapshot_id=getattr(snapshot, "snapshot_id", None),
                )
                if stream_callback:
                    await stream_callback(
                        agent_service_pb2.ChatResponse(
                            delta=f"\n\n⚠️ 该操作需要确认才能执行: {', '.join(validation_result.risk_flags)}\n"
                            f"action_id={action_id}",
                            metadata={"requires_hitl": "true", "action_id": action_id, "reason": "risk_flags"},
                        )
                    )
                state.context_data["validation_failed"] = True
                state.next_step = "__end__"
                return state

        # Execute plan with DAG-aware executor (parallel by layer).
        start_time = time.time()

        def _to_camel_case_dag_event(event: dict[str, Any]) -> dict[str, Any]:
            key_map = {
                "layer_index": "layerIndex",
                "layer_number": "layerNumber",
                "total_layers": "totalLayers",
                "step_id": "stepId",
                "tool_name": "toolName",
                "duration_ms": "durationMs",
                "completed_steps": "completedSteps",
                "step_ids": "stepIds",
                "tool_names": "toolNames",
                "plan_id": "planId",
                "layers_completed": "layersCompleted",
                "steps_total": "stepsTotal",
                "abort_reason": "abortReason",
            }
            return {key_map.get(k, k): v for k, v in event.items()}

        async def _execution_observer(event: dict[str, Any]) -> None:
            if not stream_callback:
                return

            payload_event = _to_camel_case_dag_event(event)
            event_type = event.get("event")
            if event_type == "layer_start":
                details = (
                    f"正在执行 DAG 第 {event.get('layer_number', 0)}/{event.get('total_layers', 0)} 层，"
                    f"{len(event.get('tool_names', []))} 个步骤并行"
                )
                await stream_callback(
                    agent_service_pb2.ChatResponse(
                        status_update=agent_service_pb2.AgentStatus(
                            state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                            details=details,
                            active_agent=agent_service_pb2.ORCHESTRATOR,
                        ),
                        metadata={
                            "dag_execution_event": json.dumps(payload_event, ensure_ascii=False),
                        },
                    )
                )
                return

            await stream_callback(
                agent_service_pb2.ChatResponse(
                    metadata={
                        "dag_execution_event": json.dumps(payload_event, ensure_ascii=False),
                    }
                )
            )

        plan_result = await executor.execute_plan(
            plan=executable_plan,
            user_id=user_id,
            db_session=db_session,
            progress_callback=None,
            execution_observer=_execution_observer,
        )
        state.context_data["plan_execution_result"] = plan_result

        for step_result in plan_result.step_results:
            result = step_result.tool_result
            state.context_data["tool_results"].append(
                {
                    "name": step_result.tool_name,
                    "success": result.success,
                    "result": result.data or {},
                    "error": result.error_message,
                    "suggestion": result.suggestion,
                    "widget_type": result.widget_type,
                    "widget_data": result.widget_data or {},
                    "tool_call_id": step_result.step_id,
                }
            )

            if stream_callback:
                status_msg = f"{step_result.tool_name}: {'执行成功' if result.success else '执行失败'}"
                await stream_callback(
                    agent_service_pb2.ChatResponse(
                        status_update=agent_service_pb2.AgentStatus(
                            state=agent_service_pb2.AgentStatus.IDLE,
                            details=status_msg,
                            active_agent=agent_service_pb2.ORCHESTRATOR,
                        )
                    )
                )

                data_struct = struct_pb2.Struct()
                if isinstance(result.data, dict):
                    data_struct.update(result.data)
                widget_struct = struct_pb2.Struct()
                if isinstance(result.widget_data, dict):
                    widget_struct.update(result.widget_data)

                await stream_callback(
                    agent_service_pb2.ChatResponse(
                        tool_result=agent_service_pb2.ToolResultPayload(
                            tool_name=result.tool_name,
                            success=result.success,
                            data=data_struct,
                            error_message=result.error_message or "",
                            suggestion=result.suggestion or "",
                            widget_type=result.widget_type or "",
                            widget_data=widget_struct,
                            tool_call_id=step_result.step_id,
                        )
                    )
                )

            result_json = json.dumps(
                {
                    "success": result.success,
                    "result": result.data,
                    "error": result.error_message,
                    "fallback": result.data.get("fallback", False) if isinstance(result.data, dict) else False,
                }
            )
            state.append_message("tool", result_json, name=step_result.tool_name)

        if plan_result.aborted and stream_callback:
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    delta=f"\n\n⚠️ 计划执行中断: {plan_result.abort_reason or 'required step failed'}"
                )
            )

        # Write feedback for LangGraph plan
        await _write_feedback(
            state=state,
            user_id=user_id,
            session_id=session_id,
            redis_client=redis_client,
            start_time=start_time,
            tool_count=len(plan_result.step_results),
            plan_id=executable_plan.plan_id,
        )

        # Clear executable_plan and loop back
        state.context_data["executable_plan"] = None
        state.context_data["tool_loop_count"] = int(state.context_data.get("tool_loop_count") or 0) + 1
        state.next_step = "generation"
        return state

    # === Phase 1: Original LLM tool_calls path ===
    tool_calls = state.context_data.get("tool_calls", [])
    if not tool_calls:
        state.next_step = "__end__"
        return state

    # Grounding Validation
    validator = state.context_data.get("grounding_validator")
    if validator:
        from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

        def _prepare_params(tc) -> dict:
            """准备参数用于验证和执行"""
            if isinstance(tc.full_arguments, dict):
                return tc.full_arguments
            if isinstance(tc.full_arguments, str):
                try:
                    return json.loads(tc.full_arguments)
                except (json.JSONDecodeError, TypeError):
                    return {"_raw": tc.full_arguments}
            return {}

        plan = ExecutablePlan(
            context_version=state.context_data.get("plan_metadata", {}).get("context_version", "v0"),
            source="fast_path",
            rationale=state.context_data.get("plan_metadata", {}).get("route_reason", ""),
            tool_calls=[
                ToolCallSpec(
                    id=tc.tool_call_id or str(uuid.uuid4()),
                    name=tc.tool_name,
                    params=_prepare_params(tc),
                    point_of_no_return=tc.tool_name in ["delete_task", "delete_plan"],
                )
                for tc in tool_calls
            ],
        )

        validation_result = await validator.validate_plan(plan)

        if not validation_result.is_valid:
            logger.error(f"Grounding validation failed: {validation_result.failure_reason}")
            if stream_callback:
                await stream_callback(
                    agent_service_pb2.ChatResponse(delta=f"\n\n⚠️ 执行被拒绝: {validation_result.failure_reason}")
                )
            state.context_data["validation_failed"] = True
            state.next_step = "__end__"
            return state

        if validation_result.requires_confirmation or validation_result.requires_hitl:
            logger.warning(f"Plan requires confirmation: {validation_result.risk_flags}")
            action_id = await _queue_hitl_action(
                user_id=str(user_id),
                reason="risk_flags",
                description="高风险操作需要确认",
                tool_calls=plan.tool_calls,
                plan_id=plan.plan_id,
                snapshot_id=None,
            )
            if stream_callback:
                await stream_callback(
                    agent_service_pb2.ChatResponse(
                        delta=f"\n\n⚠️ 该操作需要确认才能执行: {', '.join(validation_result.risk_flags)}\n"
                        f"action_id={action_id}",
                        metadata={"requires_hitl": "true", "action_id": action_id, "reason": "risk_flags"},
                    )
                )
            state.context_data["validation_failed"] = True
            state.next_step = "__end__"
            return state

    start_time = time.time()
    total_tools = len(tool_calls)

    for idx, tc in enumerate(tool_calls):
        # Parse arguments if needed (ToolExecutor expects dict)
        args = tc.full_arguments
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, TypeError):
                args = {}

        await _execute_single_tool(
            tool_name=tc.tool_name,
            tool_args=args,
            tool_call_id=tc.tool_call_id or str(uuid.uuid4()),
            stream_callback=stream_callback,
            user_id=user_id,
            db_session=db_session,
            executor=executor,
            state=state,
            tool_index=idx,
            total_tools=total_tools,
        )

    # Write feedback for Phase 1 LLM tool_calls
    plan_id = state.context_data.get("plan_metadata", {}).get("plan_id", str(uuid.uuid4()))
    await _write_feedback(
        state=state,
        user_id=user_id,
        session_id=session_id,
        redis_client=redis_client,
        start_time=start_time,
        tool_count=len(tool_calls),
        plan_id=plan_id,
    )

    # Clear tool calls and loop back to generation
    state.context_data["tool_calls"] = []
    state.context_data["tool_loop_count"] = int(state.context_data.get("tool_loop_count") or 0) + 1
    state.next_step = "generation"

    return state


# ==========================================
# Intent Classification & Tool Planning
# ==========================================


def detect_exam_urgency(text: str) -> int | None:
    """Return days until exam, or None if no exam urgency detected."""
    text_lower = text.lower()
    exam_keywords = ["考试", "考研", "期末", "测验", "quiz", "midterm", "final", "exam", "test", "考"]
    if not any(keyword in text_lower for keyword in exam_keywords):
        return None

    exam_pattern = r"(?:考|考试|考研|期末|测验|quiz|midterm|final|exam|test)"
    patterns = [
        (rf"(?:明天|明日).{{0,6}}{exam_pattern}", 1),
        (rf"{exam_pattern}.{{0,6}}(?:明天|明日)", 1),
        (rf"(?:tomorrow).{{0,6}}{exam_pattern}", 1),
        (rf"{exam_pattern}.{{0,6}}(?:tomorrow)", 1),
        (rf"(?:后天).{{0,6}}{exam_pattern}", 2),
        (rf"{exam_pattern}.{{0,6}}(?:后天)", 2),
        (rf"(?:下周|下星期|下礼拜|next\s*week).{{0,6}}{exam_pattern}", 7),
        (rf"{exam_pattern}.{{0,6}}(?:下周|下星期|下礼拜|next\s*week)", 7),
        (rf"(?:还有|距|离|in\s*)(\d+)\s*(?:天|days?).{{0,6}}{exam_pattern}", lambda m: int(m.group(1))),
        (rf"(\d+)\s*(?:天|days?).{{0,6}}{exam_pattern}", lambda m: int(m.group(1))),
    ]

    for pattern, days in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return days(match) if callable(days) else days

    return None


def _classify_user_intent(message: str) -> str | None:
    """Classify user intent from message for multi-step tool planning."""
    if _extract_community_prompt_context(message):
        return None

    message_lower = message.lower()

    exam_keywords = ["考试", "考研", "期末", "测验", "模拟考", "quiz", "midterm", "final", "exam", "test"]
    exam_planning_keywords = ["准备", "备考", "复习", "冲刺", "计划", "安排", "倒计时", "最后", "提分"]
    if any(keyword in message_lower for keyword in exam_keywords) and (
        any(keyword in message_lower for keyword in exam_planning_keywords) or detect_exam_urgency(message) is not None
    ):
        return "exam_preparation"

    # Intent patterns mapping
    intent_patterns = {
        "exam_preparation": ["准备考试", "备考", "复习计划", "考前冲刺", "准备期末"],
        "skill_building": ["学习", "掌握", "提升", "精通", "练习"],
        "quick_task": ["15分钟", "碎片时间", "快速", "快点学"],
        "task_decomposition": ["分解", "拆解", "怎么", "怎样", "如何", "帮我规划"],
        "error_diagnosis": ["错误", "不懂", "不理解", "为什么", "错在哪里", "诊断"],
        "deep_learning": ["详细", "深入", "原理", "详解", "彻底理解"],
    }

    for intent, patterns in intent_patterns.items():
        if any(pattern in message_lower for pattern in patterns):
            return intent

    return None


def _should_use_collaboration(message: str, intent: str | None) -> bool:
    """Determine if collaboration workflow should be triggered."""
    if not intent:
        return False

    # 这些意图触发协作工作流
    collaboration_intents = ["exam_preparation", "task_decomposition", "error_diagnosis", "deep_learning"]

    return intent in collaboration_intents


def _should_disable_tools_for_light_standard_reply(state: WorkflowState, user_message: str) -> bool:
    context_data = state.context_data or {}
    chat_mode = str(context_data.get("chat_mode") or "standard").strip().lower()
    if chat_mode not in {"standard", "chat"}:
        return False
    if context_data.get("planned_tool_sequence"):
        return False
    if context_data.get("selected_experts") or context_data.get("answer_experts"):
        return False

    text = (user_message or "").strip().lower()
    if not text:
        return False

    explicit_tool_intents = (
        "创建",
        "新建",
        "添加",
        "保存",
        "同步",
        "提醒",
        "加入日历",
        "开始专注",
        "帮我建",
        "帮我加",
        "帮我创建",
        "帮我安排",
        "设个提醒",
        "预约",
        "schedule",
        "remind",
        "create",
        "add",
        "save",
        "sync",
        "start focus",
    )
    personal_data_intents = (
        "我的计划",
        "我现在的计划",
        "我的任务",
        "我当前的任务",
        "我的日程",
        "我的日历",
        "我的知识星图",
        "我的画像",
        "我的专注",
        "我的进度",
        "我的状态",
        "结合我现在",
        "根据我的",
        "看看我的",
        "查一下我的",
        "我今天要做什么",
        "我今天该做什么",
        "my plan",
        "my task",
        "my tasks",
        "my schedule",
        "my calendar",
        "my progress",
        "my profile",
        "based on my",
        "check my",
    )
    if any(keyword in text for keyword in explicit_tool_intents + personal_data_intents):
        return False

    # 标准闲聊 / 概念解释默认不暴露工具，避免把用户历史工具偏好误带入无关问题。
    return True


def _should_use_slim_standard_context(state: WorkflowState, user_message: str) -> bool:
    context_data = state.context_data or {}
    chat_mode = str(context_data.get("chat_mode") or "standard").strip().lower()
    if chat_mode not in {"standard", "chat"}:
        return False
    if context_data.get("file_ids"):
        return False
    if str(context_data.get("document_context") or "").strip():
        return False
    decision = context_data.get("document_retrieval_decision") or context_data.get("retrieval_decision") or {}
    if isinstance(decision, dict) and decision.get("should_retrieve"):
        return False
    if context_data.get("planned_tool_sequence"):
        return False
    if context_data.get("selected_experts") or context_data.get("answer_experts"):
        return False
    return _should_disable_tools_for_light_standard_reply(state, user_message)


def _has_standard_tool_or_system_leak(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return False
    leak_markers = (
        "get_plan_state",
        "query_plan_tasks",
        "功能暂时不可用",
        "错误详情",
        "我们正在努力恢复服务",
        "根据你的计划",
        "当前有 2 个计划",
        "当前有2个计划",
        "今日专注",
        "番茄钟次数",
        "与你当前计划匹配",
        "待办任务top 1",
        "根据你的行为模式分析",
        "当前专注度不足",
        "从你的待办任务中选择",
        "当前最重要的学习任务",
        "你的待办任务",
    )
    return any(marker.lower() in lowered for marker in leak_markers)


def _has_standard_personal_context_leak(text: str, user_context: dict[str, Any] | None) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered or not isinstance(user_context, dict):
        return False

    generic_markers = (
        "根据你的待办任务",
        "根据你当前的待办任务",
        "从你当前待办任务中",
        "你的任务列表",
        "结合你当前计划",
        "根据你当前计划",
    )
    if any(marker.lower() in lowered for marker in generic_markers):
        return True

    def _iter_titles(items: Any) -> list[str]:
        titles: list[str] = []
        if not isinstance(items, list):
            return titles
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            if len(title) >= 4:
                titles.append(title)
        return titles

    personal_titles = (
        _iter_titles(user_context.get("next_actions"))
        + _iter_titles(user_context.get("active_plans"))
        + _iter_titles(user_context.get("active_goals"))
    )
    return any(title.lower() in lowered for title in personal_titles)


def _should_disable_tools_for_deep_analysis(state: WorkflowState) -> bool:
    context_data = state.context_data or {}
    chat_mode = str(context_data.get("chat_mode") or "").strip().lower()
    if chat_mode != "deep_analysis":
        return False
    if context_data.get("planned_tool_sequence"):
        return False
    if context_data.get("selected_experts") or context_data.get("answer_experts"):
        return False
    return True


def _should_use_slim_deep_analysis_context(state: WorkflowState, user_message: str) -> bool:
    context_data = state.context_data or {}
    chat_mode = str(context_data.get("chat_mode") or "").strip().lower()
    if chat_mode != "deep_analysis":
        return False
    if context_data.get("planned_tool_sequence"):
        return False
    if context_data.get("selected_experts") or context_data.get("answer_experts"):
        return False

    text = (user_message or "").strip().lower()
    if not text or len(text) > 220:
        return False

    personal_or_system_keywords = (
        "我的",
        "我当前",
        "我的计划",
        "我的任务",
        "根据我的",
        "结合我的",
        "你看到我",
        "我的画像",
        "我的知识星图",
        "帮我规划",
        "上传",
        "文档",
        "文件",
        "笔记",
        "错题",
        "计划",
        "任务",
        "日程",
        "calendar",
        "task",
        "plan",
        "profile",
        "history",
        "document",
        "file",
        "upload",
        "my ",
    )
    return not any(keyword in text for keyword in personal_or_system_keywords)


def _build_slim_user_context_for_deep_analysis(user_context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(user_context, dict):
        return {}

    allowed_keys = {
        "user_context",
        "preferences",
        "llm_profile",
        "understanding_depth",
        "understanding_depth_hint",
        "context_focus",
    }
    slim = {key: user_context.get(key) for key in allowed_keys if key in user_context}
    current_query = user_context.get("current_query")
    if current_query:
        slim["current_query"] = current_query
    return slim


def _build_slim_user_context_for_standard_reply(user_context: dict[str, Any]) -> dict[str, Any]:
    return {}


async def _flush_stream_text_buffer(
    *,
    stream_callback,
    buffer: list[str],
    first_chunk_sent: bool,
) -> bool:
    if not stream_callback or not buffer:
        return first_chunk_sent

    content = "".join(buffer)
    buffer.clear()
    if not content:
        return first_chunk_sent

    if not first_chunk_sent:
        await stream_callback(
            agent_service_pb2.ChatResponse(
                delta=content,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.GENERATING,
                    details="正在生成回复...",
                    current_agent_name="Sparkle AI",
                ),
            )
        )
        return True

    await stream_callback(agent_service_pb2.ChatResponse(delta=content))
    return first_chunk_sent


async def _stream_generation_chunks_with_timeout(
    stream,
    *,
    first_chunk_timeout: float = _GENERATION_FIRST_CHUNK_TIMEOUT_SECONDS,
    chunk_timeout: float = _GENERATION_CHUNK_TIMEOUT_SECONDS,
):
    """Consume a generation stream with explicit first-token and per-chunk deadlines."""
    first_chunk = True
    while True:
        timeout = first_chunk_timeout if first_chunk else chunk_timeout
        try:
            chunk = await asyncio.wait_for(stream.__anext__(), timeout=timeout)
        except StopAsyncIteration:
            break
        first_chunk = False
        yield chunk


def _build_generation_stream_kwargs(
    llm: Any,
    *,
    system_prompt: str,
    user_message: str,
    tools: list[dict[str, Any]],
    conversation_history: list[dict[str, Any]],
    user_context: dict[str, Any],
) -> dict[str, Any]:
    """Call `chat_stream_with_tools` compatibly across old and new test doubles."""
    kwargs: dict[str, Any] = {
        "system_prompt": system_prompt,
        "user_message": user_message,
        "tools": tools,
        "user_context": user_context,
    }
    try:
        signature = inspect.signature(llm.chat_stream_with_tools)
    except (TypeError, ValueError):
        kwargs["conversation_history"] = conversation_history
        return kwargs
    if "conversation_history" in signature.parameters:
        kwargs["conversation_history"] = conversation_history
    return kwargs


def _select_workflow(intent: str):
    """Select appropriate collaboration workflow based on intent."""
    workflow_mapping = {
        "exam_preparation": TaskDecompositionWorkflow,
        "task_decomposition": TaskDecompositionWorkflow,
        "deep_learning": ProgressiveExplorationWorkflow,
        "error_diagnosis": ErrorDiagnosisWorkflow,
    }

    return workflow_mapping.get(intent)


async def collaboration_node(state: WorkflowState) -> WorkflowState:
    """Execute collaboration workflow based on user intent."""
    logger.info("Collaboration node: Executing multi-agent workflow...")

    user_message = state.messages[-1]["content"] if state.messages else ""
    intent = state.context_data.get("detected_intent")
    stream_callback = state.context_data.get("stream_callback")
    user_id = state.context_data.get("user_id", "")
    db_session = state.context_data.get("db_session")
    selected_experts = _selected_expert_ids(state)

    if selected_experts:
        try:
            logger.info(f"Executing explicit expert collaboration with experts={selected_experts}")
            if stream_callback:
                await stream_callback(
                    agent_service_pb2.ChatResponse(
                        status_update=agent_service_pb2.AgentStatus(
                            state=agent_service_pb2.AgentStatus.THINKING,
                            details=f"已进入专家协作，正在调度 {len(selected_experts)} 位专家...",
                            active_agent=agent_service_pb2.ORCHESTRATOR,
                            current_agent_name="Sparkle Orchestrator",
                        ),
                        metadata={
                            "selected_experts": json.dumps(selected_experts, ensure_ascii=False),
                            "collaboration_mode": "explicit_expert",
                        },
                    )
                )
            result = await _execute_explicit_expert_collaboration(state)
            state.context_data["collaboration_result"] = result
            state.context_data["workflow_type"] = result.workflow_type
            state.next_step = "collaboration_post_process"
            return state
        except Exception as e:
            logger.error(f"Explicit expert collaboration failed: {e}", exc_info=True)
            state.context_data["collaboration_error"] = str(e)
            state.next_step = "tool_planning"
            return state

    if not intent or not _should_use_collaboration(user_message, intent):
        logger.info("No collaboration needed, moving to standard workflow")
        state.next_step = "tool_planning"
        return state

    # Select workflow
    WorkflowClass = _select_workflow(intent)
    if not WorkflowClass:
        logger.warning(f"No workflow found for intent: {intent}")
        state.next_step = "tool_planning"
        return state

    try:
        learning_status = state.context_data.get("learning_status") or {}
        if not isinstance(learning_status, dict):
            learning_status = {}
        # Build enhanced context
        context = EnhancedAgentContext(
            user_id=user_id,
            session_id=state.context_data.get("session_id") or getattr(state, "session_id", ""),
            user_query=user_message,
            conversation_history=state.messages[:-1],
            knowledge_context=state.context_data.get("knowledge_context"),
            user_preferences=state.context_data.get("user_preferences"),
            knowledge_graph=state.context_data.get("knowledge_graph"),
            mastery_levels=learning_status.get("mastery_levels"),
            weak_concepts=learning_status.get("weak_points"),
            forgetting_risks=learning_status.get("forgetting_risks"),
            db_session=db_session,
        )

        # Send status update
        if stream_callback:
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.THINKING,
                        details=f"Executing {intent} collaboration workflow...",
                        active_agent=agent_service_pb2.ORCHESTRATOR,
                    )
                )
            )

        # Execute workflow
        logger.info(f"Executing {WorkflowClass.__name__} for intent: {intent}")
        workflow = WorkflowClass(None)  # orchestrator is optional
        result = await workflow.execute(user_message, context)

        logger.info(f"Collaboration result: {result.workflow_type}, participants: {result.participants}")

        # Validate and ensure action cards in output
        validated_result = await _ensure_action_cards(result, state)

        # Store result for generation node
        state.context_data["collaboration_result"] = validated_result
        state.context_data["workflow_type"] = validated_result.workflow_type

        # Emit collaboration timeline metadata for clients
        if stream_callback and hasattr(validated_result, "timeline"):
            execution_time = 0.0
            if hasattr(validated_result, "metadata") and validated_result.metadata:
                execution_time = validated_result.metadata.get("execution_time", 0.0)
            steps = []
            for event in validated_result.timeline:
                agent_name = event.get("agent_name") or event.get("agent") or "Agent"
                action = event.get("action") or ""
                status = event.get("status") or "completed"
                start_time_ms = event.get("start_time_ms")
                if start_time_ms is None and event.get("timestamp") is not None:
                    start_time_ms = int(float(event.get("timestamp")) * 1000)
                duration_ms = event.get("duration_ms")
                output_summary = event.get("output_summary")
                agent_role = event.get("agent_role")
                step = {
                    "agent_name": agent_name,
                    "action": action,
                    "status": status,
                    "start_time_ms": start_time_ms or 0,
                }
                if agent_role:
                    step["agent_role"] = agent_role
                if duration_ms is not None:
                    step["duration_ms"] = duration_ms
                if output_summary:
                    step["output_summary"] = output_summary
                if event.get("metadata"):
                    step["metadata"] = event.get("metadata")
                steps.append(step)
            collaboration_timeline = {
                "schema_version": "1.0",
                "workflow_type": validated_result.workflow_type,
                "execution_time_ms": int(execution_time * 1000),
                "steps": steps,
            }
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    delta="",
                    metadata={"collaboration_timeline": json.dumps(collaboration_timeline, ensure_ascii=False)},
                )
            )

        # Send collaboration result to client (optional: timeline visualization)
        if stream_callback and hasattr(validated_result, "timeline"):
            for event in validated_result.timeline:
                logger.info(f"Timeline event: {event}")

        state.next_step = "collaboration_post_process"

    except Exception as e:
        logger.error(f"Collaboration workflow failed: {e}", exc_info=True)
        # Fallback to standard workflow
        state.context_data["collaboration_error"] = str(e)
        state.next_step = "tool_planning"

    return state


async def collaboration_post_process_node(state: WorkflowState) -> WorkflowState:
    """Post-process collaboration result and convert to tool calls."""
    logger.info("Post-processing collaboration result...")

    collaboration_result = state.context_data.get("collaboration_result")
    if not collaboration_result:
        state.next_step = "tool_planning"
        return state

    stream_callback = state.context_data.get("stream_callback")
    chat_mode = str(state.context_data.get("chat_mode") or "")
    selected_experts = _selected_expert_ids(state)
    answer_experts = _answer_expert_ids(state)
    has_explicit_team = parse_team_spec(chat_mode) is not None
    has_explicit_expert_answer = bool(selected_experts or answer_experts or has_explicit_team)
    final_response_text = ""

    # Stream the final response
    if stream_callback and hasattr(collaboration_result, "final_response"):
        final_response_text = str(collaboration_result.final_response or "").strip()
        await stream_callback(agent_service_pb2.ChatResponse(delta=final_response_text))
    elif hasattr(collaboration_result, "final_response"):
        final_response_text = str(collaboration_result.final_response or "").strip()

    if final_response_text:
        state.append_message("assistant", final_response_text)

    # Extract and queue action cards for execution
    action_cards = []
    if hasattr(collaboration_result, "outputs"):
        for output in collaboration_result.outputs:
            if hasattr(output, "tool_results"):
                for tool_result in output.tool_results:
                    if hasattr(tool_result, "widget_type") and tool_result.widget_type:
                        action_cards.append(tool_result)

    if action_cards:
        logger.info(f"Found {len(action_cards)} action cards from collaboration")
        # 这些卡片已经包含 widget_type 和 widget_data，前端可以直接渲染
        state.context_data["collaboration_action_cards"] = action_cards
        # 后续可选择直接返回或继续对话
        state.next_step = "__end__"
    elif has_explicit_expert_answer and final_response_text:
        # Explicit expert/team requests already produced a complete answer.
        # Ending here avoids a second generation pass that can flood the stream
        # and cause gateway-side timeouts on long-running collaborations.
        logger.info(
            "Explicit expert/team collaboration produced final answer; ending workflow without extra generation"
        )
        state.next_step = "__end__"
    else:
        # 如果没有动作卡片，继续标准流程
        state.next_step = "tool_planning"

    return state


async def _ensure_action_cards(collaboration_result, state: WorkflowState):
    """Validate collaboration result contains action cards, if not generate them."""
    has_action_cards = False

    # Check if result already has action cards
    if hasattr(collaboration_result, "outputs"):
        for output in collaboration_result.outputs:
            if hasattr(output, "tool_results"):
                for tr in output.tool_results:
                    if hasattr(tr, "widget_type") and tr.widget_type:
                        has_action_cards = True
                        break

    if not has_action_cards:
        logger.warning("Collaboration result missing action cards, attempting to generate...")
        # Use LLM to convert result to action cards
        llm_prompt = f"""
Based on the collaboration result below, generate structured action card data.
Return a JSON array with items containing: title, description, type (task|plan|focus), estimated_minutes

Result: {collaboration_result.final_response}

Return only valid JSON array, no markdown.
"""
        try:
            action_data = await llm_service.chat_json(llm_prompt)
            if action_data and isinstance(action_data, list):
                # Wrap as ToolResult objects
                from app.tools.base import ToolResult
                from app.tools.entity_cards import (
                    build_task_list_entity_card,
                    wrap_widget_payload,
                )

                action_cards = [
                    ToolResult(
                        widget_type="task_list",
                        widget_data=wrap_widget_payload(
                            widget_type="task_list",
                            widget_data={"tasks": action_data, "source": "collaboration_fallback"},
                            entity_card=build_task_list_entity_card(
                                action_data,
                                tool_name="collaboration_fallback",
                            ),
                        ),
                    )
                ]
                if hasattr(collaboration_result, "outputs") and collaboration_result.outputs:
                    collaboration_result.outputs[0].tool_results = action_cards
                has_action_cards = True
                logger.info("Generated fallback action cards")
        except Exception as e:
            logger.error(f"Failed to generate fallback action cards: {e}")

    return collaboration_result


async def tool_planning_node(state: WorkflowState) -> WorkflowState:
    """Intelligent tool planning node for multi-step workflows."""
    logger.info("Tool planning node: Analyzing user intent for multi-step execution...")

    # Get the latest user message
    user_message = state.messages[-1]["content"] if state.messages else ""
    intent = _classify_user_intent(user_message)

    logger.info(f"Classified intent: {intent}")

    # Store intent for collaboration node decision
    state.context_data["detected_intent"] = intent

    if intent == "exam_preparation":
        days_left = detect_exam_urgency(user_message)
        if days_left is not None:
            urgent = days_left <= 3
            state.context_data["exam_days_left"] = days_left
            state.context_data["urgent_exam"] = urgent
            user_context = state.context_data.get("user_context")
            if isinstance(user_context, dict):
                user_context = dict(user_context)
                user_context["exam_urgency"] = {"days_left": days_left, "urgent": urgent}
                state.context_data["user_context"] = user_context

    # Define tool sequences for different intents
    tool_sequences = {
        "exam_preparation": [
            {"tool": "create_plan", "description": "创建考前冲刺计划", "requires_context": ["subject"]},
            {"tool": "generate_tasks_for_plan", "description": "自动生成微任务", "requires_context": ["plan_id"]},
            {"tool": "suggest_focus_session", "description": "建议专注时段", "requires_context": ["task_ids"]},
        ],
        "task_decomposition": [
            {"tool": "breakdown_task", "description": "分解任务为子任务", "requires_context": ["task_description"]},
            {"tool": "suggest_focus_session", "description": "建议专注时段", "requires_context": ["task_ids"]},
        ],
        "skill_building": [
            {"tool": "create_plan", "description": "创建学习计划", "requires_context": ["topic", "target_level"]},
            {"tool": "generate_tasks_for_plan", "description": "生成学习路径", "requires_context": ["plan_id"]},
        ],
    }

    if intent and intent in tool_sequences:
        # Store the planned tool sequence for generation node to pick up
        state.context_data["planned_tool_sequence"] = tool_sequences[intent]
        logger.info(f"Planning multi-step sequence for intent '{intent}': {len(tool_sequences[intent])} steps")
        state.next_step = "generation"  # Let generation node handle the sequence
    else:
        # No specific planning needed, go straight to generation
        state.context_data["planned_tool_sequence"] = None
        logger.info("No specific tool planning needed, using standard generation")
        state.next_step = "generation"

    return state


# ==========================================
# Graph Definition
# ==========================================


def create_standard_chat_graph() -> StateGraph:
    graph = StateGraph("StandardChat")

    # ==========================
    # 添加所有节点
    # ==========================
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("router", router_node)
    graph.add_node("collaboration", collaboration_node)
    graph.add_node("collaboration_post_process", collaboration_post_process_node)
    graph.add_node("tool_planning", tool_planning_node)
    graph.add_node("generation", generation_node)

    # ==========================
    # Phase 1: 审查节点
    # ==========================
    graph.add_node("generation_review", generation_review_node)
    graph.add_node("reflection", reflection_node)
    graph.add_node("tool_execution", tool_execution_node)
    graph.add_node("execution_review", execution_review_node)

    graph.set_entry_point("context_builder")

    # ==========================
    # 基础流程边
    # ==========================
    graph.add_edge("context_builder", "retrieval")
    graph.add_edge("retrieval", "router")

    # Router decides next step
    def router_condition(state: WorkflowState) -> str:
        decision = state.context_data.get("router_decision")
        # If router logic failed or returned None, fallback to collaboration check
        if not decision:
            return "collaboration"

        # Map specialized agents to generation node for now
        # In Phase 4, these will be separate nodes
        if decision in ["math_agent", "code_agent", "knowledge_agent"]:
            return "generation"

        if decision in ["generation", "tool_execution"]:
            return decision

        return "collaboration"

    graph.add_conditional_edge("router", router_condition)

    # Collaboration node routes to collaboration workflows or standard flow
    def collaboration_condition(state: WorkflowState) -> str:
        return state.next_step or "tool_planning"

    graph.add_conditional_edge("collaboration", collaboration_condition)

    # Post-process collaboration result
    def collaboration_post_condition(state: WorkflowState) -> str:
        return state.next_step or "__end__"

    graph.add_conditional_edge("collaboration_post_process", collaboration_post_condition)

    # Tool planning analyzes intent and sequences tools
    graph.add_edge("tool_planning", "generation")

    # ==========================
    # Phase 1: 审查流程集成
    # ==========================

    # Generation → generation_review (所有生成内容都经过审查)
    def generation_router(state: WorkflowState) -> str:
        if state.next_step == "tool_execution":
            return "tool_execution"
        # 生成后默认进入审查
        state.next_step = "generation_review"
        return "generation_review"

    graph.add_conditional_edge("generation", generation_router)

    # generation_review的条件路由
    # - passed + has_tools → tool_execution
    # - passed + no_tools → __end__
    # - failed + requires_reflection → reflection
    # - failed → __end__ (或user_approval)
    def generation_review_condition(state: WorkflowState) -> str:
        next_step = state.next_step or "__end__"

        if next_step == "tool_execution":
            return "tool_execution"

        # 如果有工具调用需要执行
        if state.context_data.get("tool_calls") and next_step != "reflection":
            return "tool_execution"

        if next_step == "reflection":
            return "reflection"

        return "__end__"

    graph.add_conditional_edge("generation_review", generation_review_condition)

    # reflection的条件路由
    # - passed + has_tools → tool_execution
    # - passed + no_tools → __end__
    # - continue_reflection → reflection (递归)
    # - failed → __end__
    def reflection_condition(state: WorkflowState) -> str:
        next_step = state.next_step or "__end__"
        review_context = state.context_data.get("review_context")
        if review_context is None:
            # Fallback: check if state has review_context as attribute (graph state)
            review_context = getattr(state, "review_context", None)
        reflection_round = (review_context or {}).get("reflection_round", 0)
        MAX_ROUNDS = 3

        # 检查是否超过最大轮次
        if reflection_round >= MAX_ROUNDS:
            if state.context_data.get("tool_calls"):
                return "tool_execution"
            return "__end__"

        if next_step == "reflection":
            return "reflection"

        if state.context_data.get("tool_calls") and state.context_data.get("reflection_completed"):
            return "tool_execution"

        return "__end__"

    graph.add_conditional_edge("reflection", reflection_condition)

    # Tool execution → execution_review
    graph.add_edge("tool_execution", "execution_review")

    # execution_review的条件路由
    # - 需要解释结果 → generation
    # - 否则 → __end__
    def execution_review_condition(state: WorkflowState) -> str:
        next_step = state.next_step or "__end__"
        if next_step == "generation":
            return "generation"
        return "__end__"

    graph.add_conditional_edge("execution_review", execution_review_condition)

    return graph


async def router_node(state: WorkflowState) -> WorkflowState:
    """Intelligent Routing Node."""
    selected_experts = _selected_expert_ids(state)
    if selected_experts:
        chat_mode = str(state.context_data.get("chat_mode") or "").strip()
        has_team = chat_mode.startswith(CHAT_MODE_TEAM_PREFIX)
        answer_experts = _answer_expert_ids(state)
        if has_team or len(selected_experts) > 1 or len(answer_experts) > 1:
            state.context_data["router_decision"] = "collaboration"
        else:
            state.context_data["router_decision"] = "generation"
        state.context_data["router_confidence"] = 1.0
        return state

    from app.routing.router_node import RouterNode

    redis_client = state.context_data.get("redis_client")
    user_id = str(state.context_data.get("user_id", ""))

    # Define available routes (even if mapped to generation later)
    routes = ["generation", "math_agent", "code_agent", "tool_execution"]

    router = RouterNode(routes=routes, redis_client=redis_client, user_id=user_id)
    return await router(state)


# ==========================================
# Phase 2 Helper Functions
# ==========================================


async def _execute_single_tool(
    tool_name: str,
    tool_args: dict,
    tool_call_id: str,
    stream_callback,
    user_id: str,
    db_session,
    executor,
    state: WorkflowState,
    compensation_call: dict[str, Any] | None = None,
    tool_index: int = 0,
    total_tools: int = 1,
) -> None:
    """Execute a single tool call and stream results.

    Used by tool_execution_node for both LLM tool_calls and LangGraph executable_plan.

    P2 Improvement: Added progress feedback with tool index and total count.
    P1 Improvement: Added fallback handling when tool execution fails.
    """
    redis_client = state.context_data.get("redis_client")

    # P2: Tool execution start notification with progress
    if stream_callback:
        progress_msg = f"正在执行 ({tool_index + 1}/{total_tools}): {tool_name}..."
        await stream_callback(
            agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                    details=progress_msg,
                    active_agent=agent_service_pb2.ORCHESTRATOR,
                )
            )
        )

    try:
        result = await executor.execute_tool_call(
            tool_name=tool_name,
            arguments=tool_args,
            user_id=user_id,
            db_session=db_session,
            compensation_call=compensation_call,
            runtime_context={
                "session_id": state.context_data.get("session_id"),
                "plan_id": state.context_data.get("plan_id"),
                "redis_client": redis_client,
                "current_user_message": state.messages[-1]["content"] if state.messages else "",
                "file_ids": list(state.context_data.get("file_ids") or []),
                "group_id": state.context_data.get("group_id"),
                "group_ids": list(state.context_data.get("group_ids") or []),
                "include_group_documents": state.context_data.get("include_group_documents"),
                "conversation_settings": state.context_data.get("conversation_settings"),
                "situation_brief": state.context_data.get("situation_brief"),
                "user_context_payload": state.context_data.get("user_context_payload"),
                "plan_context": state.context_data.get("plan_context"),
                "focused_memory": state.context_data.get("focused_memory"),
                "context_briefing_note": state.context_data.get("context_briefing_note"),
                "visible_update_context": state.context_data.get("visible_update_context"),
                "active_interventions": state.context_data.get("active_interventions"),
                "active_intervention_id": state.context_data.get("active_intervention_id"),
                "last_feedback_binding": state.context_data.get("last_feedback_binding"),
                "dual_core_snapshot": state.context_data.get("dual_core_snapshot"),
                "session_feedback_signal": state.context_data.get("session_feedback_signal"),
                "progress_snapshot": state.context_data.get("progress_snapshot"),
                "adaptation_records": (state.context_data.get("user_context_payload", {}) or {}).get(
                    "adaptation_records"
                ),
            },
        )

        # Check if tool execution failed
        if not result.success:
            logger.warning(f"Tool '{tool_name}' execution failed: {result.error_message}")

            # P1: Attempt fallback handling
            fallback_message = await ToolExecutionFallback.handle_tool_failure(
                tool_name=tool_name,
                error_message=result.error_message or "Unknown error",
                user_id=user_id,
                db_session=db_session,
                redis_client=redis_client,
                stream_callback=stream_callback,
            )

            # Stream fallback result
            if stream_callback and fallback_message:
                await stream_callback(agent_service_pb2.ChatResponse(delta=f"\n\n{fallback_message}"))

            # Create fallback result
            from app.tools.base import ToolResult

            result = ToolResult(
                success=True,  # Fallback successful
                tool_name=tool_name,
                data={"message": fallback_message, "fallback": True},
                error_message=None,
                suggestion="如需完整功能，请稍后再试",
            )

    except Exception as e:
        logger.error(f"Tool '{tool_name}' execution exception: {e}")

        # P1: Handle unexpected exceptions with fallback
        fallback_message = await ToolExecutionFallback.handle_tool_failure(
            tool_name=tool_name,
            error_message=str(e),
            user_id=user_id,
            db_session=db_session,
            redis_client=redis_client,
            stream_callback=stream_callback,
        )

        # Stream fallback result
        if stream_callback and fallback_message:
            await stream_callback(agent_service_pb2.ChatResponse(delta=f"\n\n{fallback_message}"))

        # Create fallback result
        from app.tools.base import ToolResult

        result = ToolResult(
            success=True,  # Fallback successful
            tool_name=tool_name,
            data={"message": fallback_message, "fallback": True},
            error_message=None,
            suggestion="如需完整功能，请稍后再试",
        )

    # P2: Tool execution result status
    if stream_callback:
        status_msg = f"{tool_name}: {'执行成功' if result.success else '执行失败'}"
        await stream_callback(
            agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.IDLE,
                    details=status_msg,
                    active_agent=agent_service_pb2.ORCHESTRATOR,
                )
            )
        )

        data_struct = struct_pb2.Struct()
        if result.data:
            data_struct.update(result.data)
        widget_struct = struct_pb2.Struct()
        if result.widget_data:
            widget_struct.update(result.widget_data)

        await stream_callback(
            agent_service_pb2.ChatResponse(
                tool_result=agent_service_pb2.ToolResultPayload(
                    tool_name=result.tool_name,
                    success=result.success,
                    data=data_struct,
                    error_message=result.error_message or "",
                    suggestion=result.suggestion or "",
                    widget_type=result.widget_type or "",
                    widget_data=widget_struct,
                    tool_call_id=tool_call_id,
                )
            )
        )

    # Add tool result to message history
    result_json = json.dumps(
        {
            "success": result.success,
            "result": result.data,
            "error": result.error_message,
            "fallback": result.data.get("fallback", False) if result.data else False,
        }
    )
    state.append_message("tool", result_json, name=tool_name)
    if tool_name == "record_intervention_feedback" and isinstance(result.data, dict):
        _update_feedback_binding_runtime_state(state, result.data)
    state.context_data.setdefault("tool_results", []).append(
        {
            "name": tool_name,
            "success": result.success,
            "result": result.data or {},
            "error": result.error_message,
            "suggestion": result.suggestion,
            "widget_type": result.widget_type,
            "widget_data": result.widget_data or {},
            "tool_call_id": tool_call_id,
        }
    )


def _update_feedback_binding_runtime_state(state: WorkflowState, result_data: dict[str, Any]) -> None:
    active_interventions = result_data.get("active_interventions")
    if isinstance(active_interventions, list):
        state.context_data["active_interventions"] = active_interventions
        if active_interventions:
            active_intervention_id = str(active_interventions[0].get("intervention_id") or "").strip()
            if active_intervention_id:
                state.context_data["active_intervention_id"] = active_intervention_id
            else:
                state.context_data.pop("active_intervention_id", None)
        else:
            state.context_data.pop("active_intervention_id", None)

    last_feedback_binding = result_data.get("last_feedback_binding")
    if isinstance(last_feedback_binding, dict):
        state.context_data["last_feedback_binding"] = last_feedback_binding
    elif isinstance(active_interventions, list) and not active_interventions and not result_data.get("bound", False):
        state.context_data.pop("last_feedback_binding", None)


async def _write_feedback(
    state: WorkflowState, user_id: str, session_id: str, redis_client, start_time: float, tool_count: int, plan_id: str
) -> None:
    """Write feedback payload to Redis and logs.

    Shared by both Phase 1 (LLM tool_calls) and Phase 2 (LangGraph executable_plan).
    """
    if not redis_client or not start_time:
        return

    from dataclasses import asdict

    from app.orchestration.schemas import FeedbackPayload

    duration_seconds = time.time() - start_time

    feedback = FeedbackPayload(
        task_id=plan_id,
        user_id=user_id,
        session_id=session_id,
        context_version=state.context_data.get("plan_metadata", {}).get("context_version", "v0"),
        completion={
            "status": "completed",
            "duration_seconds": round(duration_seconds, 2),
            "attempts": 1,
            "tool_count": tool_count,
        },
        signals={"clicked_next": False, "delayed": False, "abandoned": False},
    )

    feedback_dict = asdict(feedback)

    # 1. Write to Redis (TTL 7 days)
    feedback_key = f"feedback:{user_id}:{session_id}:{feedback.task_id}"
    try:
        await redis_client.setex(feedback_key, 7 * 24 * 3600, json.dumps(feedback_dict, ensure_ascii=False))
        logger.info(f"Feedback written to Redis: {feedback_key}")
    except Exception as e:
        logger.warning(f"Failed to write feedback to Redis: {e}")

    # 2. Write structured log
    logger.info(
        "FeedbackPayload: user={}, session={}, task={}, status={}, duration={}s",
        user_id,
        session_id,
        feedback.task_id,
        feedback.completion.get("status"),
        feedback.completion.get("duration_seconds"),
    )

    TASK_LOOP_COMPLETED.labels(source="standard_workflow").inc()


def _serialize_tool_calls(tool_calls: list[Any]) -> list[dict[str, Any]]:
    payload = []
    for tool_call in tool_calls:
        payload.append(
            {
                "id": getattr(tool_call, "id", None) or getattr(tool_call, "tool_call_id", None),
                "name": getattr(tool_call, "name", None) or getattr(tool_call, "tool_name", None),
                "params": getattr(tool_call, "params", None) or getattr(tool_call, "full_arguments", None),
                "compensation_call": getattr(tool_call, "compensation_call", None),
            }
        )
    return payload


async def _queue_hitl_action(
    *,
    user_id: str,
    reason: str,
    description: str,
    tool_calls: list[Any],
    plan_id: str | None = None,
    snapshot_id: str | None = None,
) -> str:
    action_id = await pending_actions_store.save(
        tool_name="__plan__",
        arguments={
            "plan_id": plan_id,
            "snapshot_id": snapshot_id,
            "tool_calls": _serialize_tool_calls(tool_calls),
            "reason": reason,
        },
        user_id=user_id,
        description=description,
        preview_data={
            "plan_id": plan_id,
            "snapshot_id": snapshot_id,
            "reason": reason,
            "tool_calls": _serialize_tool_calls(tool_calls),
        },
    )
    HITL_REQUESTED.labels(reason=reason).inc()
    return action_id
