"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.core.business_metrics import HITL_APPROVED, HITL_REJECTED
from app.core.cache import cache_service
from app.core.pending_actions import pending_actions_store
from app.db.session import get_db
from app.models.chat import ChatMessage, MessageRole
from app.models.user import User
from app.orchestration.composer import ResponseComposer
from app.orchestration.error_handler import AgentErrorHandler
from app.orchestration.executor import ToolExecutor
from app.orchestration.planning_workflow import PlanningWorkflowManager
from app.orchestration.prompts import build_system_prompt
from app.services.analytics_service import AnalyticsService
from app.services.llm_service import LLMResponse, llm_service
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService
from app.tools.registry import tool_registry

router = APIRouter()
planning_workflow_manager = PlanningWorkflowManager()

TASK_CHAT_ALLOWED_TOOLS = [
    "breakdown_task",
    "create_task",
    "update_task_status",
    "suggest_quick_task",
    "get_task_detail",
]

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_conversation_id(conversation_id: str | None) -> tuple[UUID, str]:
    if conversation_id:
        try:
            session_id = UUID(conversation_id)
            return session_id, str(session_id)
        except ValueError:
            pass

    session_id = uuid4()
    return session_id, str(session_id)


def _build_task_chat_tools_schema() -> list[dict[str, Any]]:
    """Limit task chat to task-scoped tools to avoid accidental plan-level detours."""
    schemas: list[dict[str, Any]] = []
    for tool_name in TASK_CHAT_ALLOWED_TOOLS:
        tool = tool_registry.get_tool(tool_name)
        if tool is None:
            logger.warning(f"Task chat tool not registered, skipping: {tool_name}")
            continue
        schemas.append(tool.to_openai_schema())
    return schemas


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    context: dict[str, Any] | None = None  # 前端传递的额外上下文

class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    widgets: list[dict[str, Any]] = []        # 需要渲染的组件列表
    tool_results: list[dict[str, Any]] = []   # 工具执行结果
    has_errors: bool = False
    errors: list[dict[str, str]] | None = None
    requires_confirmation: bool = False
    confirmation_data: dict | None = None
    dormant_injection: dict | None = None     # WS-D: dormant metadata for mobile

@router.post("/task/{task_id}", response_model=ChatResponse)
async def chat_with_task_context(
    task_id: UUID,
    request: ChatRequest,
    req_raw: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Task-specific Chat Endpoint
    Binds conversation to a task and injects task context.
    """
    from app.models.task import Task
    logger.info(f"Chat request headers: {req_raw.headers}")

    # 1. Verify Task Ownership
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    tool_executor = ToolExecutor()
    response_composer = ResponseComposer()
    AgentErrorHandler()

    # 2. Build Context
    user_context = await get_user_context(
        db,
        current_user.id,
        payload={"context": request.context, "message": request.message},
    )

    # Inject Task Context specifically
    task_context = {
        "id": str(task.id),
        "title": task.title,
        "type": task.type,
        "status": task.status,
        "guide_content": task.guide_content,
        "guide_json": task.guide_json,
        "ai_prompt": task.ai_prompt,
        "phase_index": task.phase_index,
        "success_criteria": task.success_criteria,
        "estimated_minutes": task.estimated_minutes,
        "current_focus": "The user is currently working on this task."
    }
    user_context["current_task"] = task_context

    # --- WS-D: Dormant injection (behind its own flag, sidecar semantics) ---
    dormant_injection_block = ""
    dormant_injection_meta: dict | None = None
    try:
        from app.config.aurora import aurora_flags
        if aurora_flags.TASK_ASSISTANT_DORMANT_MODE:
            from app.task_assistant.dormant_injector import DormantInjector
            injector = DormantInjector()
            injection = await injector.inject(task.id, current_user.id)
            # Build injection context block only from available items
            available = [it for it in injection.items if it.available]
            if available:
                lines = ["\nAurora dormant injection (read-only context):"]
                for item in available:
                    if item.payload:
                        lines.append(f"- [{item.kind.value}] {item.payload}")
                lines.append(
                    f"- ux_intent={injection.ux_intent}, "
                    f"presence={injection.aurora_presence}"
                )
                dormant_injection_block = "\n".join(lines)
            # Store injection data for outcome capture + mobile metadata
            injection_data = injection.model_dump(mode="json")
            user_context["_dormant_injection"] = injection_data
            dormant_injection_meta = injection_data
    except Exception as exc:
        logger.debug(f"WS-D: dormant injection skipped: {exc}")

    conversation_history_raw = await get_conversation_history(
        db, current_user.id, request.conversation_id
    )

    llm_conversation_history = [
        {"role": msg["role"], "content": msg["content"]} for msg in conversation_history_raw
    ]

    # 3. System Prompt with Task Focus
    system_prompt = build_system_prompt(user_context, "History injected.")
    system_prompt += (
        "\n\nCURRENT TASK CONTEXT:\n"
        f"You are assisting the user with the task: '{task.title}'. "
        "Focus your guidance on completing this specific task.\n"
        "For this task chat, stay task-scoped.\n"
        "- Prefer using breakdown_task, get_task_detail, suggest_quick_task, "
        "create_task, and update_task_status.\n"
        "- Do not query plan-wide state unless the user explicitly asks about "
        "other tasks or overall plan progress.\n"
        "- If the task has no valid plan context, continue helping within the "
        "task itself instead of blocking on plan data."
    )
    if dormant_injection_block:
        system_prompt += dormant_injection_block
    # 4. LLM Call (Standard Flow)
    # This duplicates the logic of the main chat endpoint but simplifies for this phase
    # Ideally, refactor common logic into a service method. For now, we inline for safety.

    llm_response: LLMResponse = await llm_service.chat_with_tools(
        system_prompt=system_prompt,
        user_message=request.message,
        tools=_build_task_chat_tools_schema(),
        conversation_history=llm_conversation_history
    )

    # ... (Simplified tool handling same as main chat, omitting complex confirm/retry for brevity unless needed)
    # For Phase 1.3, we'll implement basic response first.

    llm_text = llm_response.content
    tool_results = []

    # ... (If we want full tool support here, copy logic from /chat. Let's assume basic chat for now or minimal tools)
    # Re-using the exact logic from /chat is best.
    # Let's just delegate to a common handler or copy the critical parts.

    # Copying critical parts for tool execution support:
    if llm_response.tool_calls:
        tool_results = await tool_executor.execute_tool_calls(
            tool_calls=llm_response.tool_calls,
            user_id=str(current_user.id),
            db_session=db
        )
        # We skip the complex confirmation/retry loop for this specific endpoint for now
        # to keep it simple, or we can copy it.
        # Let's do a simple follow-up if tools were called.

        if tool_results:
             # Append LLM's initial response
            llm_response_for_history = {
                "role": "assistant",
                "content": llm_response.content,
                "tool_calls": llm_response.tool_calls
            }

            updated_history = llm_conversation_history + [
                {"role": "user", "content": request.message}
            ] + [llm_response_for_history]

            final_llm_response = await llm_service.continue_with_tool_results(
                conversation_history=updated_history,
                tool_results=[tr.model_dump() for tr in tool_results]
            )
            llm_text = final_llm_response.content

    # 5. Save Message (linked to task? Schema doesn't have task_id on ChatMessage yet,
    # but the Plan says "Task.chat_messages = relationship...".
    # Let's check ChatMessage model in `app/models/chat.py` to see if it has task_id).
    # I'll check it in a separate read if needed, but for now I'll just save it as normal chat.
    # Actually, the user requirement says "Modify backend/app/api/v1/chat.py - Bind conversation to task".

    # If ChatMessage doesn't have task_id, we might need to add it or just rely on session_id being tracked elsewhere.
    # For now, we return the response.

    session_id_uuid, session_id_str = _normalize_conversation_id(
        request.conversation_id,
    )

    response_data = response_composer.compose_response(
        llm_text=llm_text,
        tool_results=tool_results,
        requires_confirmation=False,
        confirmation_data=None
    )

    # Save standard chat message
    await save_chat_message(
        db=db,
        user_id=current_user.id,
        session_id=session_id_uuid,
        user_message=request.message,
        assistant_message=llm_text,
        tool_results=[tr.model_dump() for tr in tool_results],
        task_id=task.id,
    )

    # --- WS-D: Outcome capture for nearline next-turn optimization ---
    try:
        if user_context.get("_dormant_injection"):
            from app.task_assistant.outcome_capture import OutcomeCapture
            cap = OutcomeCapture()
            await cap.record(
                task_id=task.id,
                user_id=current_user.id,
                conversation_id=session_id_uuid,
                turn_number=len(conversation_history_raw) // 2 + 1,
                injection_was_used=bool(dormant_injection_block),
            )
    except Exception as exc:
        logger.debug(f"WS-D: outcome capture skipped: {exc}")

    return ChatResponse(**response_data, conversation_id=session_id_str, dormant_injection=dormant_injection_meta)

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    req_raw: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Agent 模式的聊天接口
    支持工具调用和结构化响应
    """
    logger.info(f"Main chat request headers: {req_raw.headers}")
    tool_executor = ToolExecutor()
    response_composer = ResponseComposer()
    error_handler = AgentErrorHandler()
    request_context = dict(request.context or {})
    session_id_uuid, session_id_str = _normalize_conversation_id(
        request.conversation_id,
    )

    # 1. 构建上下文和对话历史
    user_context = await get_user_context(
        db,
        current_user.id,
        payload={"context": request.context, "message": request.message},
    )
    conversation_history_raw = await get_conversation_history(
        db, current_user.id, request.conversation_id
    )

    # Pre-format for LLM
    llm_conversation_history = [
        {"role": msg["role"], "content": msg["content"]} for msg in conversation_history_raw
    ]

    planning_context = dict(request_context)
    planning_context["profile_context"] = user_context.get("profile_context", {})

    if request_context.get("mode") == "onboarding_modeling":
        if bool(request_context.get("skip")):
            await planning_workflow_manager.skip_onboarding(
                db=db,
                user_id=current_user.id,
                conversation_id=session_id_str,
            )
            response_data = {
                "message": "先跳过这一步也没关系。我会先带你进入主界面，之后需要时再补齐这些信息。",
                "widgets": [],
                "tool_results": [],
                "has_errors": False,
                "errors": None,
            }
        else:
            onboarding_data = await planning_workflow_manager.process_onboarding_turn(
                db=db,
                user_id=current_user.id,
                conversation_id=session_id_str,
                message=request.message,
                context=planning_context,
            )
            response_data = {
                "message": onboarding_data["message"],
                "widgets": onboarding_data.get("widgets", []),
                "tool_results": [],
                "has_errors": False,
                "errors": None,
            }

        await save_chat_message(
            db=db,
            user_id=current_user.id,
            session_id=session_id_uuid,
            user_message=request.message,
            assistant_message=response_data["message"],
            tool_results=[],
        )
        return ChatResponse(**response_data, conversation_id=session_id_str)

    planning_response = await planning_workflow_manager.process_planning_turn(
        db=db,
        user_id=current_user.id,
        chat_session_id=session_id_str,
        message=request.message,
        context=planning_context,
    )
    if planning_response and not planning_response.get("bypass_planning"):
        response_data = {
            "message": planning_response["message"],
            "widgets": planning_response.get("widgets", []),
            "tool_results": [],
            "has_errors": False,
            "errors": None,
        }
        await save_chat_message(
            db=db,
            user_id=current_user.id,
            session_id=session_id_uuid,
            user_message=request.message,
            assistant_message=response_data["message"],
            tool_results=[],
        )
        return ChatResponse(**response_data, conversation_id=session_id_str)

    planning_detour_prompt = ""
    if planning_response and planning_response.get("bypass_planning"):
        planning_runtime_state = await planning_workflow_manager.runtime_adapter.load_state(
            user_id=str(current_user.id),
            conversation_id=session_id_str,
        )
        if planning_runtime_state is not None:
            planning_detour_prompt = planning_workflow_manager.runtime_adapter.build_detour_prompt(planning_runtime_state)

    # 2. 构建 System Prompt
    system_prompt = build_system_prompt(user_context, "暂无对话历史") # History passed directly to LLM
    if planning_detour_prompt:
        system_prompt += f"\n\nAURORA PLANNING SIDECAR:\n{planning_detour_prompt}"

    # 3. 调用 LLM（带工具定义）
    llm_response: LLMResponse = await llm_service.chat_with_tools(
        system_prompt=system_prompt,
        user_message=request.message,
        tools=tool_registry.get_openai_tools_schema(),
        conversation_history=llm_conversation_history
    )

    # 4. 处理工具调用
    tool_results = []
    requires_confirmation = False
    confirmation_data = None

    if llm_response.tool_calls:
        # 4.1 检查是否有需要确认的工具
        for tool_call in llm_response.tool_calls:
            tool_name = tool_call["function"]["name"]
            tool = tool_registry.get_tool(tool_name)

            if tool and tool.requires_confirmation:
                # 保存待确认操作
                arguments = tool_call["function"]["arguments"]
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)

                action_id = await pending_actions_store.save(
                    tool_name=tool_name,
                    arguments=arguments,
                    user_id=str(current_user.id),
                    description=f"执行 {tool.description}",
                    preview_data={"tool_call": tool_call}
                )

                requires_confirmation = True
                confirmation_data = {
                    "action_id": action_id,
                    "tool_name": tool_name,
                    "description": f"即将执行: {tool.description}",
                    "preview": arguments
                }
                break  # 只处理第一个需要确认的工具

        # 4.2 如果不需要确认，执行工具调用
        if not requires_confirmation:
            tool_results = await tool_executor.execute_tool_calls(
                tool_calls=llm_response.tool_calls,
                user_id=str(current_user.id),
                db_session=db
            )

            # 4.3 错误处理与自我修正
            # 检查是否有失败的工具调用，并尝试自动修正
            corrected_results = await error_handler.handle_batch_errors(
                llm_service=llm_service,
                tool_results=tool_results,
                original_requests=llm_response.tool_calls,
                user_id=str(current_user.id),
                db_session=db
            )
            tool_results = corrected_results

        # 5. 将工具执行结果反馈给 LLM，获取最终回复
        if requires_confirmation:
            # 如果需要确认，直接使用 LLM 的初始回复，提示用户确认
            llm_text = llm_response.content or "需要确认操作，请查看下方的确认卡片。"
        elif tool_results:
            # Append LLM's initial response (which contained tool calls) to history
            llm_response_for_history = {
                "role": "assistant",
                "content": llm_response.content,
                "tool_calls": llm_response.tool_calls # Store raw tool calls if needed
            }

            updated_conversation_history = llm_conversation_history + [
                {"role": "user", "content": request.message} # User message
            ] + [llm_response_for_history]

            final_llm_response = await llm_service.continue_with_tool_results(
                conversation_history=updated_conversation_history,
                tool_results=[tr.model_dump() for tr in tool_results]
            )
            llm_text = final_llm_response.content
        else:
            llm_text = llm_response.content
    else:
        llm_text = llm_response.content

    # 6. 组装响应
    response_data = response_composer.compose_response(
        llm_text=llm_text,
        tool_results=tool_results,
        requires_confirmation=requires_confirmation,
        confirmation_data=confirmation_data
    )

    # 7. 保存消息到数据库
    await save_chat_message(
        db=db,
        user_id=current_user.id,
        session_id=session_id_uuid,
        user_message=request.message,
        assistant_message=llm_text,
        tool_results=[tr.model_dump() for tr in tool_results] # save tool results in message
    )

    return ChatResponse(**response_data, conversation_id=session_id_str)

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    流式聊天接口（SSE）
    适合长回复场景，实时展示 LLM 生成内容
    """
    async def event_generator():
        tool_executor = ToolExecutor()
        error_handler = AgentErrorHandler()

        user_id_uuid = current_user.id

        # Build context
        user_context = await get_user_context(
            db,
            user_id_uuid,
            payload={"context": request.context, "message": request.message},
        )
        conversation_history_raw = await get_conversation_history(
            db, user_id_uuid, request.conversation_id
        )
        llm_conversation_history = [
            {"role": msg["role"], "content": msg["content"]} for msg in conversation_history_raw
        ]

        system_prompt = build_system_prompt(user_context, "暂无对话历史") # History passed directly to LLM

        collected_text_content = ""
        collected_tool_calls_raw = [] # Raw tool calls from LLM (function_call format)

        # Keep track of messages for history
        message_history_for_llm_callback = llm_conversation_history + [
            {"role": "user", "content": request.message} # Add user message to history
        ]

        async for chunk in llm_service.chat_stream_with_tools(
            system_prompt=system_prompt,
            user_message=request.message,
            tools=tool_registry.get_openai_tools_schema(),
            conversation_history=llm_conversation_history,
            user_context=user_context,
        ):
            if chunk.type == "text":
                collected_text_content += chunk.content
                yield f"data: {json.dumps({'type': 'text', 'content': chunk.content})}\\n\n"

            elif chunk.type == "tool_call_chunk":
                # For now, we only care about the tool_call_end for execution
                # We can send tool_start event when tool_name is first received
                if chunk.tool_name and collected_tool_calls_raw and \
                   collected_tool_calls_raw[-1].get("function", {}).get("name") != chunk.tool_name:
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': chunk.tool_name})}\\n\n"

                # Append raw chunks to reconstruct full tool call later
                if not collected_tool_calls_raw or collected_tool_calls_raw[-1]["id"] != chunk.tool_call_id:
                    collected_tool_calls_raw.append({
                        "id": chunk.tool_call_id,
                        "function": {"name": chunk.tool_name or "", "arguments": chunk.arguments or ""}
                    })
                else:
                    if chunk.tool_name:
                        collected_tool_calls_raw[-1]["function"]["name"] = chunk.tool_name
                    if chunk.arguments:
                        collected_tool_calls_raw[-1]["function"]["arguments"] += chunk.arguments


            elif chunk.type == "tool_call_end":
                # Execute tool once full arguments are received
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': chunk.tool_name})}\\n\n"

                result = await tool_executor.execute_tool_call(
                    tool_name=chunk.tool_name,
                    arguments=chunk.full_arguments,
                    user_id=str(current_user.id),
                    db_session=db
                )

                # 错误处理与自我修正
                if not result.success and error_handler.should_retry(result):
                    original_request = {
                        "id": chunk.tool_call_id,
                        "function": {
                            "name": chunk.tool_name,
                            "arguments": json.dumps(chunk.full_arguments)
                        }
                    }
                    result = await error_handler.handle_tool_error(
                        llm_service=llm_service,
                        tool_result=result,
                        original_request=original_request,
                        retry_count=0,
                        user_id=str(current_user.id),
                        db_session=db
                    )

                yield f"data: {json.dumps({'type': 'tool_result', 'result': result.model_dump()})}\\n\n"

                # If there's a widget, send it separately
                if result.widget_type:
                    yield f"data: {json.dumps({'type': 'widget', 'widget_type': result.widget_type, 'widget_data': result.widget_data})}\\n\n"

                # If tool was successfully executed, send tool result back to LLM to continue conversation
                # This requires an extra turn to LLM
                # Add LLM's initial response (which contained tool calls) to history
                message_history_for_llm_callback.append({
                    "role": "assistant",
                    "content": "", # no text content with tool call initially
                    "tool_calls": [
                        {
                            "id": chunk.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": chunk.tool_name,
                                "arguments": json.dumps(chunk.full_arguments)
                            }
                        }
                    ]
                })

                # Call LLM again to get final text
                final_llm_response = await llm_service.continue_with_tool_results(
                    conversation_history=message_history_for_llm_callback,
                    tool_results=[result.model_dump()]
                )
                final_text = final_llm_response.content
                yield f"data: {json.dumps({'type': 'text', 'content': final_text})}\\n\n"
                collected_text_content += final_text

        # If no tool calls were made, just final text from first LLM call
        if not collected_tool_calls_raw and collected_text_content:
             # Already yielded content above, but ensuring consistency
             pass

        # Save message to database after all is done
        await save_chat_message(
            db=db,
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            user_message=request.message,
            assistant_message=collected_text_content,
            # tool_results should be collected during the stream, but simplified here
            tool_results=[]
        )

        yield f"data: {json.dumps({'type': 'done'})}\\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/chat/confirm")
async def confirm_action(
    action_id: str,
    confirmed: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    确认高风险操作
    用于需要用户二次确认的工具调用
    """
    # 获取待确认的操作
    pending_action = await pending_actions_store.get(action_id, str(current_user.id))

    if not pending_action:
        raise HTTPException(status_code=404, detail="操作不存在或已过期")

    # 如果用户取消操作
    if not confirmed:
        reason = pending_action.get("preview_data", {}).get("reason", "unknown")
        HITL_REJECTED.labels(reason=reason).inc()
        await pending_actions_store.delete(action_id, str(current_user.id))
        return {"status": "cancelled", "message": "操作已取消"}

    # 用户确认，执行实际操作
    tool_executor = ToolExecutor()
    error_handler = AgentErrorHandler()

    try:
        if pending_action["tool_name"] == "__plan__":
            tool_calls = pending_action.get("arguments", {}).get("tool_calls", [])
            results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("name")
                arguments = tool_call.get("params") or {}
                compensation_call = tool_call.get("compensation_call")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except Exception:
                        arguments = {}

                result = await tool_executor.execute_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    user_id=str(current_user.id),
                    db_session=db,
                    compensation_call=compensation_call
                )

                # 错误处理与自我修正
                if not result.success and error_handler.should_retry(result):
                    original_request = {
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(arguments)
                        }
                    }
                    result = await error_handler.handle_tool_error(
                        llm_service=llm_service,
                        tool_result=result,
                        original_request=original_request,
                        retry_count=0,
                        user_id=str(current_user.id),
                        db_session=db
                    )

                results.append(result.model_dump())

                if not result.success:
                    break

            reason = pending_action.get("preview_data", {}).get("reason", "unknown")
            HITL_APPROVED.labels(reason=reason).inc()
            await pending_actions_store.delete(action_id, str(current_user.id))
            return {"status": "executed", "results": results}

        result = await tool_executor.execute_tool_call(
            tool_name=pending_action["tool_name"],
            arguments=pending_action["arguments"],
            user_id=str(current_user.id),
            db_session=db
        )

        # 错误处理与自我修正
        if not result.success and error_handler.should_retry(result):
            original_request = {
                "function": {
                    "name": pending_action["tool_name"],
                    "arguments": json.dumps(pending_action["arguments"])
                }
            }
            result = await error_handler.handle_tool_error(
                llm_service=llm_service,
                tool_result=result,
                original_request=original_request,
                retry_count=0,
                user_id=str(current_user.id),
                db_session=db
            )

        reason = pending_action.get("preview_data", {}).get("reason", "unknown")
        HITL_APPROVED.labels(reason=reason).inc()

        # 删除已处理的待确认操作
        await pending_actions_store.delete(action_id, str(current_user.id))

        return {"status": "executed", "result": result.model_dump()}

    except Exception:
        # 删除失败的待确认操作
        await pending_actions_store.delete(action_id, str(current_user.id))
        raise HTTPException(status_code=500, detail="Action execution failed")

# ============辅助函数 ============

async def get_user_context(db: AsyncSession, user_id: UUID, payload: dict[str, Any] | None = None) -> dict:
    """
    获取用户上下文信息
    为 LLM 提供用户的学习状态，帮助其做出更个性化的决策
    """
    from datetime import timedelta

    from app.models.galaxy import UserNodeStatus
    from app.models.plan import Plan
    from app.models.task import Task

    context = {
        "recent_tasks": [],
        "active_plans": [],
        "flame_level": 1,
        "flame_brightness": 0,
        "knowledge_stats": {},
        "analytics_summary": ""
    }

    try:
        if settings.USE_CONTEXT_PACK:
            from app.core.context_pack import ContextPackBuilder
            from app.core.intent_router import IntentRouter

            intent = "chat"
            if settings.USE_CONTEXT_INTENT_ROUTER and payload is not None:
                intent = IntentRouter().get_intent(payload)
            pack_builder = ContextPackBuilder(db, redis=cache_service.redis)
            request_id = payload.get("request_id") if payload else None
            trace_id = payload.get("trace_id") if payload else None
            query_text = str(payload.get("message") or "") if payload else ""
            focus_mode = payload.get("focus_mode") if payload else None
            route_intent = payload.get("route_intent") if payload else None

            # Extract plan_id from payload for PlanScope context
            plan_id = None
            if payload and isinstance(payload.get("context"), dict):
                plan_id_str = payload["context"].get("plan_id")
                if plan_id_str:
                    try:
                        plan_id = UUID(str(plan_id_str))
                    except (ValueError, TypeError):
                        plan_id = None

            pack = await pack_builder.build(
                user_id,
                intent=intent,
                request_id=request_id,
                trace_id=trace_id,
                plan_id=plan_id,
                query_text=query_text,
                focus_mode=focus_mode,
                route_intent=route_intent or intent,
            )
            prompt_context = pack.to_prompt_context()
            try:
                from app.services.profile_context_service import ProfileContextService

                profile_context = await ProfileContextService(db, cache_service.redis).get_profile_context(
                    user_id,
                    include_metacognition_prompt_extensions=True,
                )
                prompt_context["profile_context"] = profile_context.to_prompt_context()
            except Exception as exc:
                logger.warning(f"Failed to attach profile context: {exc}")
            return prompt_context

        # 0. 获取 Analytics Summary
        analytics_service = AnalyticsService(db)
        # Ensure today's stats are up to date (optional, might be slow for every chat, maybe skip calculation here and just read?)
        # For MVP, let's just get the summary which reads stored data.
        # Ideally, we calculate it async or periodically.
        context["analytics_summary"] = await analytics_service.get_user_profile_summary(user_id)

        # 1. 获取用户基本信息（火花等级和亮度）
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if user:
            context["flame_level"] = user.flame_level or 1
            context["flame_brightness"] = user.flame_brightness or 0

            try:
                from app.services.personalization.preference_service import PreferenceService

                pref_service = PreferenceService(db)
                prefs_center = await pref_service.get_preferences(user_id)
                explicit = prefs_center.explicit if prefs_center else {}
            except Exception:
                explicit = {}

        context["learning_preferences"] = {
            "depth_preference": explicit.get("depth_preference", user.depth_preference),
            "curiosity_preference": explicit.get("curiosity_preference", user.curiosity_preference),
        }

        try:
            from app.services.profile_context_service import ProfileContextService

            profile_context = await ProfileContextService(db, cache_service.redis).get_profile_context(
                user_id,
                include_metacognition_prompt_extensions=True,
            )
            context["profile_context"] = profile_context.to_prompt_context()
        except Exception as exc:
            logger.warning(f"Failed to attach profile context: {exc}")

        # 2. 获取近期任务（最近7天）
        seven_days_ago = _utcnow() - timedelta(days=7)
        tasks_stmt = (
            select(Task)
            .where(
                and_(
                    Task.user_id == user_id,
                    Task.created_at >= seven_days_ago
                )
            )
            .order_by(Task.created_at.desc())
            .limit(10)  # 最多返回10个任务
        )
        tasks_result = await db.execute(tasks_stmt)
        tasks = tasks_result.scalars().all()

        context["recent_tasks"] = [
            {
                "id": str(task.id),
                "title": task.title,
                "type": task.task_type,
                "status": task.status,
                "estimated_minutes": task.estimated_minutes,
                "actual_minutes": task.actual_minutes
            }
            for task in tasks
        ]

        # 3. 获取活跃计划（未完成的计划）
        plans_stmt = (
            select(Plan)
            .where(
                and_(
                    Plan.user_id == user_id,
                    not Plan.is_completed
                )
            )
            .order_by(Plan.created_at.desc())
            .limit(5)  # 最多返回5个计划
        )
        plans_result = await db.execute(plans_stmt)
        plans = plans_result.scalars().all()

        context["active_plans"] = [
            {
                "id": str(plan.id),
                "title": plan.title,
                "type": plan.plan_type,
                "target_date": plan.target_date.isoformat() if plan.target_date else None,
                "progress": plan.progress or 0
            }
            for plan in plans
        ]

        # 4. 获取知识星图统计
        nodes_stmt = (
            select(UserNodeStatus)
            .where(UserNodeStatus.user_id == user_id)
        )
        nodes_result = await db.execute(nodes_stmt)
        nodes = nodes_result.scalars().all()

        total_nodes = len(nodes)
        mastered_nodes = sum(1 for n in nodes if n.mastery_level >= 0.8)
        learning_nodes = sum(1 for n in nodes if 0.3 <= n.mastery_level < 0.8)

        context["knowledge_stats"] = {
            "total_nodes": total_nodes,
            "mastered_nodes": mastered_nodes,
            "learning_nodes": learning_nodes
        }

    except Exception as e:
        # 如果获取上下文失败，返回默认值，不影响聊天功能
        logger.warning(f"Failed to fetch user context: {e}")

    return context

async def get_conversation_history(
    db: AsyncSession,
    user_id: UUID,
    conversation_id: str | None
) -> list[dict[str, str]]:
    """获取对话历史"""
    if not conversation_id:
        return []

    try:
        session_id = UUID(conversation_id)
    except ValueError:
        return [] # Invalid conversation_id format

    stmt = (
        select(ChatMessage)
        .where(
            and_(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id
            )
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(10) # Limit history to last 10 messages for simplicity
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    history_for_llm = []
    # Messages are fetched in descending order, reverse to chronological for LLM
    for msg in reversed(messages):
        role = msg.role.value if isinstance(msg.role, MessageRole) else msg.role
        history_for_llm.append({
            "role": role,
            "content": msg.content
        })
    return history_for_llm

async def save_chat_message(
    db: AsyncSession,
    user_id: UUID,
    session_id: UUID,
    user_message: str,
    assistant_message: str,
    tool_results: list[dict],
    task_id: UUID | None = None,
):
    """保存聊天消息"""
    session_meta = await db.get(ChatSessionModel, session_id)
    now = _utcnow()
    if session_meta is None:
        db.add(
            ChatSessionModel(
                id=session_id,
                user_id=user_id,
                is_active=True,
                last_message_at=now,
            )
        )
    else:
        session_meta.last_message_at = now
        session_meta.is_active = True

    # Save user message
    user_msg_db = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role=MessageRole.USER,
        content=user_message,
        task_id=task_id,
    )
    db.add(user_msg_db)

    # Save assistant message
    # Actions should be saved as JSON directly if the model supports it
    assistant_msg_db = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=assistant_message,
        task_id=task_id,
        actions=tool_results if tool_results else None, # Store tool results as actions
    )
    db.add(assistant_msg_db)

    await db.commit()
    MemoryInferredWriteLaneService.enqueue_from_chat_turn(
        user_id=user_id,
        session_id=session_id,
        user_message=user_message,
        assistant_message=assistant_message,
        user_message_id=str(user_msg_db.id),
        assistant_message_id=str(assistant_msg_db.id),
    )


# ============ Chat Session Management API ============

from app.models.chat import ChatSession as ChatSessionModel
from app.schemas.chat import ChatMessageDetail, ChatSession


@router.get("/sessions", response_model=list[ChatSession])
async def get_chat_sessions(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的聊天会话列表
    """
    # Query distinct sessions with message counts and last message time
    stmt = (
        select(
            ChatMessage.session_id,
            ChatMessage.user_id,
            ChatMessage.task_id,
            func.count(ChatMessage.id).label("message_count"),
            func.max(ChatMessage.created_at).label("last_message_at"),
            func.min(ChatMessage.created_at).label("created_at")
        )
        .where(ChatMessage.user_id == current_user.id)
        .where(ChatMessage.session_id != UUID('00000000-0000-0000-0000-000000000000'))
        .group_by(ChatMessage.session_id, ChatMessage.user_id, ChatMessage.task_id)
        .order_by(func.max(ChatMessage.created_at).desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    sessions = []
    for row in rows:
        sessions.append(ChatSession(
            session_id=row.session_id,
            user_id=row.user_id,
            task_id=row.task_id,
            message_count=row.message_count,
            created_at=row.created_at,
            last_message_at=row.last_message_at,
        ))

    return sessions


@router.get("/history/{session_id}", response_model=list[ChatMessageDetail])
async def get_chat_history(
    session_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取特定会话的聊天历史
    """
    ownership_stmt = (
        select(func.count())
        .select_from(ChatMessage)
        .where(
            and_(
                ChatMessage.user_id == current_user.id,
                ChatMessage.session_id == session_id,
            )
        )
    )
    ownership_result = await db.execute(ownership_stmt)
    owns_session = (ownership_result.scalar() or 0) > 0

    if not owns_session:
        session_meta_stmt = (
            select(ChatSessionModel.id)
            .where(
                and_(
                    ChatSessionModel.id == session_id,
                    ChatSessionModel.user_id == current_user.id,
                )
            )
            .limit(1)
        )
        session_meta_result = await db.execute(session_meta_stmt)
        owns_session = session_meta_result.scalar_one_or_none() is not None

    if not owns_session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    stmt = (
        select(ChatMessage)
        .where(
            and_(
                ChatMessage.user_id == current_user.id,
                ChatMessage.session_id == session_id
            )
        )
        .order_by(ChatMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        ChatMessageDetail(
            id=msg.id,
            session_id=msg.session_id,
            user_id=msg.user_id,
            role=msg.role,
            content=msg.content,
            task_id=msg.task_id,
            actions=msg.actions,
            tokens_used=msg.tokens_used,
            model_name=msg.model_name,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
        )
        for msg in messages
    ]
