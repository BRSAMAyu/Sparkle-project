from typing import Dict, Any, AsyncGenerator, Optional, List
from loguru import logger
import json
import uuid
import asyncio
import re

from app.orchestration.statechart_engine import StateGraph, WorkflowState, GraphEventType, GraphEvent
from app.services.llm_service import llm_service
from app.services.galaxy_service import GalaxyService
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
    # In real impl: GalaxyService.hybrid_search(query)
    
    # Placeholder
    state.context_data["knowledge"] = "" 
    return state

async def generation_node(state: WorkflowState) -> WorkflowState:
    """LLM Generation (Streaming)."""
    # We need to access the 'stream_callback' from context to yield tokens
    stream_callback = state.context_data.get("stream_callback")
    
    # Cast to Dict to satisfy type checker
    user_context = state.context_data.get("user_context", {})
    if not isinstance(user_context, dict):
        user_context = {}

    conversation_context = state.context_data.get("conversation_context") or {
        "messages": state.messages[:-1]
    }
    system_prompt = build_system_prompt(
        user_context,
        conversation_history=conversation_context
    )
    
    user_message = state.messages[-1]["content"] or ""
    tools = state.context_data.get("tools_schema", [])
    
    full_response = ""
    tool_calls = []
    
    # We assume llm_service is available globally
    async for chunk in llm_service.chat_stream_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=tools
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
    """Execute Tools."""
    tool_calls = state.context_data.get("tool_calls", [])
    executor = ToolExecutor() # Should be injected or cached

    stream_callback = state.context_data.get("stream_callback")
    user_id = state.context_data.get("user_id", "")
    db_session = state.context_data.get("db_session")

    for tc in tool_calls:
        if stream_callback:
            await stream_callback(agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                    details=f"Executing {tc.tool_name}...",
                    active_agent=agent_service_pb2.ORCHESTRATOR
                )
            ))

        # Parse arguments if needed (ToolExecutor expects dict)
        args = tc.full_arguments
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {}

        result = await executor.execute_tool_call(
            tool_name=tc.tool_name,
            arguments=args,
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
                    tool_call_id=tc.tool_call_id
                )
            ))

        # ToolResult object to JSON
        result_json = json.dumps({
            "success": result.success,
            "result": result.data,
            "error": result.error_message
        })
        state.append_message("tool", result_json, name=tc.tool_name)

    # Clear tool calls and loop back to generation
    state.context_data["tool_calls"] = []
    # If we want to feed result back to LLM:
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
