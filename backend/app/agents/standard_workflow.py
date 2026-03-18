from __future__ import annotations
import json
import re
import time
import uuid
from typing import Any

from google.protobuf import struct_pb2
from loguru import logger

from app.agents.collaboration_workflows import (
    ErrorDiagnosisWorkflow,
    ProgressiveExplorationWorkflow,
    TaskDecompositionWorkflow,
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
from app.core.agent_profiles import TaskType
from app.core.business_metrics import HITL_REQUESTED, TASK_LOOP_COMPLETED
from app.core.pending_actions import pending_actions_store
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.executor import ToolExecutor
from app.orchestration.prompts import build_system_prompt
from app.orchestration.statechart_engine import StateGraph, WorkflowState
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import get_configured_llm_service, llm_service

# ==========================================
# Nodes
# ==========================================


def _resolve_generation_agent_role(state: WorkflowState) -> str:
    explicit_role = state.context_data.get("agent_role")
    if explicit_role:
        return str(explicit_role)

    selected_experts = state.context_data.get("selected_experts")
    if isinstance(selected_experts, list):
        for expert in selected_experts:
            cleaned = str(expert).strip()
            if cleaned:
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


def _build_generation_fallback_response(
    *,
    user_message: str,
    knowledge_context: str,
    document_context: str,
) -> str:
    best_fact = _extract_best_retrieval_fact(knowledge_context, document_context)
    if best_fact:
        return (
            f"根据当前检索到的知识，{best_fact}\n\n"
            "当前生成模型暂时繁忙，所以我先直接返回了检索结果里的关键信息。"
        )

    snippets: list[str] = []

    for raw_context in (knowledge_context, document_context):
        if not raw_context:
            continue
        for line in raw_context.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if cleaned.startswith("Relevant Knowledge Base") or cleaned.startswith("Relevant Documents"):
                continue
            snippets.append(cleaned)
            if len(snippets) >= 4:
                break
        if len(snippets) >= 4:
            break

    if snippets:
        joined = "\n".join(snippets)
        return (
            "我先根据已检索到的知识结果直接回答你：\n"
            f"{joined}\n\n"
            "当前生成模型暂时繁忙，所以我优先返回了检索到的可靠内容。"
        )

    return (
        f"我已经收到你的问题“{user_message}”，但当前生成模型暂时繁忙。"
        "请稍后再试，或让我先基于已有知识检索结果继续整理。"
    )


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
    if not question_match:
        return None

    memory_key = question_match.group("key").strip()
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
        if not fact_match:
            continue
        if fact_match.group("key").strip() != memory_key:
            continue
        value = fact_match.group("value").strip().strip("“”\"'")
        if value in {"什么", "多少", "谁", "哪", "哪里", "几点", "几号", "怎么"}:
            continue
        return value

    return None

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

    if not db_session or not user_id or not query:
        state.context_data["knowledge_context"] = ""
        state.context_data["document_context"] = ""
        return state

    try:
        user_uuid = uuid.UUID(str(user_id))
    except ValueError:
        state.context_data["knowledge_context"] = ""
        state.context_data["document_context"] = ""
        return state

    knowledge_context = ""
    try:
        ks = KnowledgeService(db_session)
        knowledge_context = await ks.retrieve_context(user_id=user_uuid, query=query, limit=5)
    except Exception as e:
        logger.warning(f"Knowledge retrieval failed: {e}")

    document_context = ""
    citations = []
    if file_ids:
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
                    limit=5,
                    threshold=0.4
                )

                if doc_results:
                    lines = ["Relevant Documents:"]
                    for item in doc_results:
                        chunk = item.chunk
                        snippet = chunk.content.strip()
                        if len(snippet) > 400:
                            snippet = snippet[:400] + "..."

                        label_parts = [item.file_name]
                        if chunk.section_title:
                            label_parts.append(chunk.section_title)
                        if chunk.page_number is not None:
                            label_parts.append(f"p{chunk.page_number}")
                        label_parts.append(f"#{chunk.chunk_index}")
                        label = " | ".join(label_parts)
                        lines.append(f"- [{label}] {snippet}")

                        if include_references:
                            title = item.file_name
                            if chunk.section_title:
                                title = f"{item.file_name} - {chunk.section_title}"

                            citations.append(agent_service_pb2.Citation(
                                id=str(chunk.id),
                                title=title,
                                content=snippet,
                                source_type="document",
                                url="",
                                score=item.score,
                                file_id=str(chunk.file_id),
                                page_number=chunk.page_number or 0,
                                chunk_index=chunk.chunk_index,
                                section_title=chunk.section_title or ""
                            ))

                    document_context = "\n".join(lines)
            except Exception as e:
                logger.warning(f"Document retrieval failed: {e}")

    state.context_data["knowledge_context"] = knowledge_context
    state.context_data["document_context"] = document_context

    if include_references and citations:
        stream_callback = state.context_data.get("stream_callback")
        if stream_callback:
            await stream_callback(agent_service_pb2.ChatResponse(
                citations=agent_service_pb2.CitationBlock(citations=citations)
            ))

    return state

async def generation_node(state: WorkflowState) -> WorkflowState:
    """LLM Generation (Streaming)."""
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

    try:
        generation_llm = await get_configured_llm_service(agent_role, task_type)
    except Exception as e:
        logger.warning(f"Failed to configure role-scoped LLM for {agent_role}/{task_type.value}: {e}")
        generation_llm = llm_service

    # Extract plan_context from state if available
    plan_context = state.context_data.get("plan_context")

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
        user_context,
        conversation_history=conversation_context,
        prompt_version=prompt_version,
        agent_role=getattr(generation_llm, "agent_role", "generation"),
        plan_context=plan_context,
        intent_instruction=intent_instruction, # Vision Item 4b
        session_feedback_instruction=str(state.context_data.get("session_feedback_instruction") or ""),
        dual_core_instruction=str(state.context_data.get("dual_core_prompt_instruction") or ""),
        context_focus=state.context_data.get("context_focus"),
        context_briefing_note=str(state.context_data.get("context_briefing_note") or ""),
        chat_mode=str(state.context_data.get("chat_mode", "standard") or "standard"),
    )

    knowledge_context = state.context_data.get("knowledge_context") or ""
    if knowledge_context:
        system_prompt += f"\n\n## Retrieved Knowledge\n{knowledge_context}"

    document_context = state.context_data.get("document_context") or ""
    if document_context:
        system_prompt += f"\n\n## Retrieved Documents\n{document_context}"

    user_message = state.messages[-1]["content"] or ""
    tools = state.context_data.get("tools_schema", [])
    memory_answer = _resolve_recent_memory_answer(conversation_context, user_message)

    if memory_answer:
        if stream_callback:
            await stream_callback(agent_service_pb2.ChatResponse(
                delta=memory_answer,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.GENERATING,
                    details="正在根据最近对话补全答案...",
                    current_agent_name="Sparkle AI"
                )
            ))
        state.context_data["generation_shortcut"] = "recent_memory"
        state.append_message("assistant", memory_answer)
        state.next_step = "__end__"
        return state

    # 检查是否使用思考模式，如果是则发送状态更新
    # 这会让前端显示"思考中"提示
    try:
        is_thinking = generation_llm.is_thinking_mode()

        if is_thinking and stream_callback:
            await stream_callback(agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details="正在深度思考中，请稍候...",
                    current_agent_name="Sparkle AI"
                )
            ))
    except Exception as e:
        logger.warning(f"Failed to check thinking mode: {e}")

    full_response = ""
    tool_calls = []
    first_chunk_sent = False  # Track first chunk for status transition

    state.context_data["active_generation_agent_role"] = str(getattr(generation_llm, "agent_role", agent_role))
    selection = generation_llm.get_current_selection()
    if selection is not None:
        state.context_data["active_generation_model"] = selection.config.model_name

    try:
        async for chunk in generation_llm.chat_stream_with_tools(
            system_prompt=system_prompt,
            user_message=user_message,
            tools=tools,
            user_context=user_context,
        ):
            if chunk.type == "text":
                full_response += chunk.content
                if stream_callback:
                    # Send GENERATING status with first chunk to transition from THINKING
                    if not first_chunk_sent:
                        first_chunk_sent = True
                        await stream_callback(agent_service_pb2.ChatResponse(
                            delta=chunk.content,
                            status_update=agent_service_pb2.AgentStatus(
                                state=agent_service_pb2.AgentStatus.GENERATING,
                                details="正在生成回复...",
                                current_agent_name="Sparkle AI"
                            )
                        ))
                    else:
                        await stream_callback(agent_service_pb2.ChatResponse(
                            delta=chunk.content
                        ))
            elif chunk.type == "tool_call_end":
                tool_calls.append(chunk)
                if stream_callback:
                    await stream_callback(agent_service_pb2.ChatResponse(
                        tool_call=agent_service_pb2.ToolCall(
                            id=chunk.tool_call_id,
                            name=chunk.tool_name,
                            arguments=json.dumps(chunk.full_arguments)
                        )
                    ))
            elif chunk.type == "usage":
                if stream_callback:
                    await stream_callback(agent_service_pb2.ChatResponse(
                        usage=agent_service_pb2.Usage(
                            prompt_tokens=chunk.prompt_tokens or 0,
                            completion_tokens=chunk.completion_tokens or 0,
                            total_tokens=(chunk.prompt_tokens or 0) + (chunk.completion_tokens or 0)
                        )
                    ))
    except Exception as e:
        logger.warning(f"Generation streaming failed, using retrieval fallback: {e}")
        state.context_data["generation_fallback_reason"] = str(e)

    retrieval_grounded_response = _build_generation_fallback_response(
        user_message=user_message,
        knowledge_context=knowledge_context,
        document_context=document_context,
    )
    if full_response and not tool_calls and _is_low_information_generation_response(full_response):
        community_fallback = _build_community_prompt_fallback_response(user_message)
        if community_fallback:
            logger.info("Replacing low-information generation response with community prompt fallback")
            full_response = community_fallback
        else:
            logger.info("Replacing low-information generation response with retrieval-grounded answer")
            full_response = retrieval_grounded_response

    if not full_response:
        fallback_response = retrieval_grounded_response
        full_response = fallback_response
        if stream_callback:
            if not first_chunk_sent:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=fallback_response,
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.GENERATING,
                        details="正在返回检索结果（生成模型暂时繁忙）...",
                        current_agent_name="Sparkle AI"
                    )
                ))
            else:
                await stream_callback(agent_service_pb2.ChatResponse(delta=fallback_response))

    state.append_message("assistant", full_response)
    if tool_calls:
        state.context_data["tool_calls"] = tool_calls
        state.next_step = "tool_execution"
    else:
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

    # === Phase 2: Check for executable_plan from LangGraph planner ===
    executable_plan = state.context_data.get("executable_plan")
    snapshot = state.context_data.get("snapshot")

    if executable_plan and executable_plan.source == "langgraph":
        logger.info(
            f"Executing LangGraph plan: {len(executable_plan.tool_calls)} tool calls, "
            f"plan_id={executable_plan.plan_id}"
        )

        # Use snapshot for validation if available
        validator = state.context_data.get("grounding_validator")
        if validator:
            # Re-validate with snapshot (business rules check)
            validation_result = await validator.validate_plan(executable_plan, snapshot)

            if not validation_result.is_valid:
                logger.error(f"LangGraph plan validation failed: {validation_result.failure_reason}")
                if stream_callback:
                    await stream_callback(agent_service_pb2.ChatResponse(
                        delta=f"\n\n⚠️ 计划执行被拒绝: {validation_result.failure_reason}"
                    ))
                state.context_data["validation_failed"] = True
                state.next_step = "__end__"
                return state

            if validation_result.requires_confirmation or validation_result.requires_hitl:
                logger.warning(f"LangGraph plan requires confirmation: {validation_result.risk_flags}")
                action_id = await _queue_hitl_action(
                    user_id=str(user_id),
                    reason="risk_flags",
                    description="高风险操作需要确认",
                    tool_calls=executable_plan.tool_calls,
                    plan_id=executable_plan.plan_id,
                    snapshot_id=getattr(snapshot, "snapshot_id", None)
                )
                if stream_callback:
                    await stream_callback(agent_service_pb2.ChatResponse(
                        delta=f"\n\n⚠️ 该操作需要确认才能执行: {', '.join(validation_result.risk_flags)}\n"
                              f"action_id={action_id}",
                        metadata={
                            "requires_hitl": "true",
                            "action_id": action_id,
                            "reason": "risk_flags"
                        }
                    ))
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
                await stream_callback(agent_service_pb2.ChatResponse(
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                        details=details,
                        active_agent=agent_service_pb2.ORCHESTRATOR
                    ),
                    metadata={
                        "dag_execution_event": json.dumps(payload_event, ensure_ascii=False),
                    },
                ))
                return

            await stream_callback(agent_service_pb2.ChatResponse(
                metadata={
                    "dag_execution_event": json.dumps(payload_event, ensure_ascii=False),
                }
            ))

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

            if stream_callback:
                status_msg = f"{step_result.tool_name}: {'执行成功' if result.success else '执行失败'}"
                await stream_callback(agent_service_pb2.ChatResponse(
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.IDLE,
                        details=status_msg,
                        active_agent=agent_service_pb2.ORCHESTRATOR
                    )
                ))

                data_struct = struct_pb2.Struct()
                if isinstance(result.data, dict):
                    data_struct.update(result.data)
                widget_struct = struct_pb2.Struct()
                if isinstance(result.widget_data, dict):
                    widget_struct.update(result.widget_data)

                await stream_callback(agent_service_pb2.ChatResponse(
                    tool_result=agent_service_pb2.ToolResultPayload(
                        tool_name=result.tool_name,
                        success=result.success,
                        data=data_struct,
                        error_message=result.error_message or "",
                        suggestion=result.suggestion or "",
                        widget_type=result.widget_type or "",
                        widget_data=widget_struct,
                        tool_call_id=step_result.step_id
                    )
                ))

            result_json = json.dumps({
                "success": result.success,
                "result": result.data,
                "error": result.error_message,
                "fallback": result.data.get("fallback", False) if isinstance(result.data, dict) else False,
            })
            state.append_message("tool", result_json, name=step_result.tool_name)

        if plan_result.aborted and stream_callback:
            await stream_callback(agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 计划执行中断: {plan_result.abort_reason or 'required step failed'}"
            ))

        # Write feedback for LangGraph plan
        await _write_feedback(
            state=state,
            user_id=user_id,
            session_id=session_id,
            redis_client=redis_client,
            start_time=start_time,
            tool_count=len(plan_result.step_results),
            plan_id=executable_plan.plan_id
        )

        # Clear executable_plan and loop back
        state.context_data["executable_plan"] = None
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
            elif isinstance(tc.full_arguments, str):
                try:
                    return {"_raw_json": tc.full_arguments}
                except:
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
                    point_of_no_return=tc.tool_name in ["delete_task", "delete_plan"]
                )
                for tc in tool_calls
            ]
        )

        validation_result = await validator.validate_plan(plan)

        if not validation_result.is_valid:
            logger.error(f"Grounding validation failed: {validation_result.failure_reason}")
            if stream_callback:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"\n\n⚠️ 执行被拒绝: {validation_result.failure_reason}"
                ))
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
                snapshot_id=None
            )
            if stream_callback:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"\n\n⚠️ 该操作需要确认才能执行: {', '.join(validation_result.risk_flags)}\n"
                          f"action_id={action_id}",
                    metadata={
                        "requires_hitl": "true",
                        "action_id": action_id,
                        "reason": "risk_flags"
                    }
                ))
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
            except:
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
        plan_id=plan_id
    )

    # Clear tool calls and loop back to generation
    state.context_data["tool_calls"] = []
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
        any(keyword in message_lower for keyword in exam_planning_keywords)
        or detect_exam_urgency(message) is not None
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
    collaboration_intents = [
        "exam_preparation",
        "task_decomposition",
        "error_diagnosis",
        "deep_learning"
    ]

    return intent in collaboration_intents


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
        # Build enhanced context
        context = EnhancedAgentContext(
            user_id=user_id,
            user_query=user_message,
            conversation_history=state.messages[:-1],
            knowledge_graph=state.context_data.get("knowledge_graph"),
            learning_status=state.context_data.get("learning_status"),
            focus_stats=state.context_data.get("focus_stats"),
            db_session=db_session,
        )

        # Send status update
        if stream_callback:
            await stream_callback(agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details=f"Executing {intent} collaboration workflow...",
                    active_agent=agent_service_pb2.ORCHESTRATOR
                )
            ))

        # Execute workflow
        logger.info(f"Executing {WorkflowClass.__name__} for intent: {intent}")
        workflow = WorkflowClass(None)  # orchestrator is optional
        result = await workflow.execute(user_message, context)

        logger.info(f"Collaboration result: {result.workflow_type}, participants: {result.participants}")

        # Validate and ensure action cards in output
        validated_result = await _ensure_action_cards(result, state)

        # Store result for generation node
        state.context_data["collaboration_result"] = validated_result

        # Emit collaboration timeline metadata for clients
        if stream_callback and hasattr(validated_result, 'timeline'):
            execution_time = 0.0
            if hasattr(validated_result, 'metadata') and validated_result.metadata:
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
            await stream_callback(agent_service_pb2.ChatResponse(
                delta="",
                metadata={
                    "collaboration_timeline": json.dumps(collaboration_timeline, ensure_ascii=False)
                }
            ))

        # Send collaboration result to client (optional: timeline visualization)
        if stream_callback and hasattr(validated_result, 'timeline'):
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

    # Stream the final response
    if stream_callback and hasattr(collaboration_result, 'final_response'):
        await stream_callback(agent_service_pb2.ChatResponse(
            delta=collaboration_result.final_response
        ))

    # Extract and queue action cards for execution
    action_cards = []
    if hasattr(collaboration_result, 'outputs'):
        for output in collaboration_result.outputs:
            if hasattr(output, 'tool_results'):
                for tool_result in output.tool_results:
                    if hasattr(tool_result, 'widget_type') and tool_result.widget_type:
                        action_cards.append(tool_result)

    if action_cards:
        logger.info(f"Found {len(action_cards)} action cards from collaboration")
        # 这些卡片已经包含 widget_type 和 widget_data，前端可以直接渲染
        state.context_data["collaboration_action_cards"] = action_cards
        # 后续可选择直接返回或继续对话
        state.next_step = "__end__"
    else:
        # 如果没有动作卡片，继续标准流程
        state.next_step = "tool_planning"

    return state


async def _ensure_action_cards(collaboration_result, state: WorkflowState):
    """Validate collaboration result contains action cards, if not generate them."""
    has_action_cards = False

    # Check if result already has action cards
    if hasattr(collaboration_result, 'outputs'):
        for output in collaboration_result.outputs:
            if hasattr(output, 'tool_results'):
                for tr in output.tool_results:
                    if hasattr(tr, 'widget_type') and tr.widget_type:
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
                action_cards = [
                    ToolResult(
                        widget_type="task_list",
                        widget_data={
                            "tasks": action_data,
                            "source": "collaboration_fallback"
                        }
                    )
                ]
                if hasattr(collaboration_result, 'outputs') and collaboration_result.outputs:
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
            {
                "tool": "create_plan",
                "description": "创建考前冲刺计划",
                "requires_context": ["subject"]
            },
            {
                "tool": "generate_tasks_for_plan",
                "description": "自动生成微任务",
                "requires_context": ["plan_id"]
            },
            {
                "tool": "suggest_focus_session",
                "description": "建议专注时段",
                "requires_context": ["task_ids"]
            }
        ],
        "task_decomposition": [
            {
                "tool": "breakdown_task",
                "description": "分解任务为子任务",
                "requires_context": ["task_description"]
            },
            {
                "tool": "suggest_focus_session",
                "description": "建议专注时段",
                "requires_context": ["task_ids"]
            }
        ],
        "skill_building": [
            {
                "tool": "create_plan",
                "description": "创建学习计划",
                "requires_context": ["topic", "target_level"]
            },
            {
                "tool": "generate_tasks_for_plan",
                "description": "生成学习路径",
                "requires_context": ["plan_id"]
            }
        ]
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
        decision = state.context_data.get('router_decision')
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
        reflection_round = state.context_data.get("review_context", {}).get("reflection_round", 0)
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
        await stream_callback(agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                details=progress_msg,
                active_agent=agent_service_pb2.ORCHESTRATOR
            )
        ))

    try:
        result = await executor.execute_tool_call(
            tool_name=tool_name,
            arguments=tool_args,
            user_id=user_id,
            db_session=db_session,
            compensation_call=compensation_call
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
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"\n\n{fallback_message}"
                ))

            # Create fallback result
            from app.tools.base import ToolResult
            result = ToolResult(
                success=True,  # Fallback successful
                tool_name=tool_name,
                data={"message": fallback_message, "fallback": True},
                error_message=None,
                suggestion="如需完整功能，请稍后再试"
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
            await stream_callback(agent_service_pb2.ChatResponse(
                delta=f"\n\n{fallback_message}"
            ))

        # Create fallback result
        from app.tools.base import ToolResult
        result = ToolResult(
            success=True,  # Fallback successful
            tool_name=tool_name,
            data={"message": fallback_message, "fallback": True},
            error_message=None,
            suggestion="如需完整功能，请稍后再试"
        )

    # P2: Tool execution result status
    if stream_callback:
        status_msg = f"{tool_name}: {'执行成功' if result.success else '执行失败'}"
        await stream_callback(agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.IDLE,
                details=status_msg,
                active_agent=agent_service_pb2.ORCHESTRATOR
            )
        ))

        data_struct = struct_pb2.Struct()
        if result.data:
            data_struct.update(result.data)
        widget_struct = struct_pb2.Struct()
        if result.widget_data:
            widget_struct.update(result.widget_data)

        await stream_callback(agent_service_pb2.ChatResponse(
            tool_result=agent_service_pb2.ToolResultPayload(
                tool_name=result.tool_name,
                success=result.success,
                data=data_struct,
                error_message=result.error_message or "",
                suggestion=result.suggestion or "",
                widget_type=result.widget_type or "",
                widget_data=widget_struct,
                tool_call_id=tool_call_id
            )
        ))

    # Add tool result to message history
    result_json = json.dumps({
        "success": result.success,
        "result": result.data,
        "error": result.error_message,
        "fallback": result.data.get("fallback", False) if result.data else False
    })
    state.append_message("tool", result_json, name=tool_name)


async def _write_feedback(
    state: WorkflowState,
    user_id: str,
    session_id: str,
    redis_client,
    start_time: float,
    tool_count: int,
    plan_id: str
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
            "tool_count": tool_count
        },
        signals={
            "clicked_next": False,
            "delayed": False,
            "abandoned": False
        }
    )

    feedback_dict = asdict(feedback)

    # 1. Write to Redis (TTL 7 days)
    feedback_key = f"feedback:{user_id}:{session_id}:{feedback.task_id}"
    try:
        await redis_client.setex(
            feedback_key,
            7 * 24 * 3600,
            json.dumps(feedback_dict, ensure_ascii=False)
        )
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
        feedback.completion.get("duration_seconds")
    )

    TASK_LOOP_COMPLETED.labels(source="standard_workflow").inc()


def _serialize_tool_calls(tool_calls: list[Any]) -> list[dict[str, Any]]:
    payload = []
    for tool_call in tool_calls:
        payload.append({
            "id": getattr(tool_call, "id", None) or getattr(tool_call, "tool_call_id", None),
            "name": getattr(tool_call, "name", None) or getattr(tool_call, "tool_name", None),
            "params": getattr(tool_call, "params", None) or getattr(tool_call, "full_arguments", None),
            "compensation_call": getattr(tool_call, "compensation_call", None),
        })
    return payload


async def _queue_hitl_action(
    *,
    user_id: str,
    reason: str,
    description: str,
    tool_calls: list[Any],
    plan_id: str | None = None,
    snapshot_id: str | None = None
) -> str:
    action_id = await pending_actions_store.save(
        tool_name="__plan__",
        arguments={
            "plan_id": plan_id,
            "snapshot_id": snapshot_id,
            "tool_calls": _serialize_tool_calls(tool_calls),
            "reason": reason
        },
        user_id=user_id,
        description=description,
        preview_data={
            "plan_id": plan_id,
            "snapshot_id": snapshot_id,
            "reason": reason,
            "tool_calls": _serialize_tool_calls(tool_calls)
        }
    )
    HITL_REQUESTED.labels(reason=reason).inc()
    return action_id
