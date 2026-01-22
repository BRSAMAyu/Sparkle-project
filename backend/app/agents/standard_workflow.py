from typing import Dict, Any, AsyncGenerator, Optional, List
from loguru import logger
import json
import uuid
import asyncio
import re
import time

from app.orchestration.statechart_engine import StateGraph, WorkflowState, GraphEventType, GraphEvent
from app.services.llm_service import llm_service
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.knowledge_service import KnowledgeService
from app.orchestration.prompts import build_system_prompt
from app.orchestration.executor import ToolExecutor
from app.gen.agent.v1 import agent_service_pb2
from google.protobuf import struct_pb2
from app.agents.collaboration_workflows import (
    TaskDecompositionWorkflow,
    ProgressiveExplorationWorkflow,
    ErrorDiagnosisWorkflow
)
from app.agents.enhanced_agents import EnhancedAgentContext
from app.core.pending_actions import pending_actions_store
from app.core.business_metrics import HITL_REQUESTED, TASK_LOOP_COMPLETED

# ==========================================
# Nodes
# ==========================================

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

    system_prompt = build_system_prompt(
        user_context,
        conversation_history=conversation_context,
        prompt_version=prompt_version
    )

    knowledge_context = state.context_data.get("knowledge_context") or ""
    if knowledge_context:
        system_prompt += f"\n\n## Retrieved Knowledge\n{knowledge_context}"

    document_context = state.context_data.get("document_context") or ""
    if document_context:
        system_prompt += f"\n\n## Retrieved Documents\n{document_context}"
    
    user_message = state.messages[-1]["content"] or ""
    tools = state.context_data.get("tools_schema", [])
    
    full_response = ""
    tool_calls = []
    
    # We assume llm_service is available globally
    async for chunk in llm_service.chat_stream_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=tools,
        user_context=user_context,
    ):
        if chunk.type == "text":
            full_response += chunk.content
            if stream_callback:
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
            from app.orchestration.schemas import ValidationResult
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

        # Execute tool calls from the plan
        start_time = time.time()

        for tool_call_spec in executable_plan.tool_calls:
            tool_args = tool_call_spec.params
            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except Exception:
                    tool_args = {}
            await _execute_single_tool(
                tool_name=tool_call_spec.name,
                tool_args=tool_args,
                tool_call_id=tool_call_spec.id,
                stream_callback=stream_callback,
                user_id=user_id,
                db_session=db_session,
                executor=executor,
                state=state
            )

        # Write feedback for LangGraph plan
        await _write_feedback(
            state=state,
            user_id=user_id,
            session_id=session_id,
            redis_client=redis_client,
            start_time=start_time,
            tool_count=len(executable_plan.tool_calls),
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
                    import json
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

    for tc in tool_calls:
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
            state=state
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

def detect_exam_urgency(text: str) -> Optional[int]:
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


def _classify_user_intent(message: str) -> Optional[str]:
    """Classify user intent from message for multi-step tool planning."""
    message_lower = message.lower()

    exam_keywords = ["考试", "考研", "期末", "测验", "模拟考", "quiz", "midterm", "final", "exam", "test"]
    if any(keyword in message_lower for keyword in exam_keywords):
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


def _should_use_collaboration(message: str, intent: Optional[str]) -> bool:
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
                    state=agent_service_pb2.AgentStatus.MULTI_AGENT_COLLABORATION,
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

    graph.add_node("context_builder", context_builder_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("router", router_node)
    graph.add_node("collaboration", collaboration_node)
    graph.add_node("collaboration_post_process", collaboration_post_process_node)
    graph.add_node("tool_planning", tool_planning_node)
    graph.add_node("generation", generation_node)
    graph.add_node("tool_execution", tool_execution_node)

    graph.set_entry_point("context_builder")

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

    # Generation node decides if tools or end
    def generation_router(state: WorkflowState) -> str:
        return state.next_step or "__end__"

    graph.add_conditional_edge("generation", generation_router)

    # Tool execution loops back to generation (to interpret results)
    graph.add_edge("tool_execution", "generation")

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
    state: WorkflowState
) -> None:
    """Execute a single tool call and stream results.

    Used by tool_execution_node for both LLM tool_calls and LangGraph executable_plan.
    """
    if stream_callback:
        await stream_callback(agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                details=f"Executing {tool_name}...",
                active_agent=agent_service_pb2.ORCHESTRATOR
            )
        ))

    result = await executor.execute_tool_call(
        tool_name=tool_name,
        arguments=tool_args,
        user_id=user_id,
        db_session=db_session
    )

    if stream_callback:
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
        "error": result.error_message
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

    from app.orchestration.schemas import FeedbackPayload
    from dataclasses import asdict

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


def _serialize_tool_calls(tool_calls: List[Any]) -> List[Dict[str, Any]]:
    payload = []
    for tool_call in tool_calls:
        payload.append({
            "id": getattr(tool_call, "id", None) or getattr(tool_call, "tool_call_id", None),
            "name": getattr(tool_call, "name", None) or getattr(tool_call, "tool_name", None),
            "params": getattr(tool_call, "params", None) or getattr(tool_call, "full_arguments", None),
        })
    return payload


async def _queue_hitl_action(
    *,
    user_id: str,
    reason: str,
    description: str,
    tool_calls: List[Any],
    plan_id: Optional[str] = None,
    snapshot_id: Optional[str] = None
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
