from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.llm_service import llm_service, LLMResponse, StreamChunk
from app.tools.registry import tool_registry
from app.orchestration.executor import ToolExecutor
from app.orchestration.composer import ResponseComposer
from app.orchestration.prompts import build_system_prompt
from app.models.chat import ChatMessage, MessageRole

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # 前端传递的额外上下文

class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    widgets: List[Dict[str, Any]] = []        # 需要渲染的组件列表
    tool_results: List[Dict[str, Any]] = []   # 工具执行结果
    has_errors: bool = False
    errors: Optional[List[Dict[str, str]]] = None
    requires_confirmation: bool = False
    confirmation_data: Optional[Dict] = None

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Agent 模式的聊天接口
    支持工具调用和结构化响应
    """
    tool_executor = ToolExecutor()
    response_composer = ResponseComposer()
    
    # 1. 构建上下文和对话历史
    user_context = await get_user_context(db, current_user.id)
    conversation_history_raw = await get_conversation_history(
        db, current_user.id, request.conversation_id
    )
    
    # Pre-format for LLM
    llm_conversation_history = [
        {"role": msg["role"], "content": msg["content"]} for msg in conversation_history_raw
    ]

    # 2. 构建 System Prompt
    system_prompt = build_system_prompt(user_context, "暂无对话历史") # History passed directly to LLM
    
    # 3. 调用 LLM（带工具定义）
    llm_response: LLMResponse = await llm_service.chat_with_tools(
        system_prompt=system_prompt,
        user_message=request.message,
        tools=tool_registry.get_openai_tools_schema(),
        conversation_history=llm_conversation_history
    )
    
    # 4. 处理工具调用
    tool_results = []
    if llm_response.tool_calls:
        tool_results = await tool_executor.execute_tool_calls(
            tool_calls=llm_response.tool_calls,
            user_id=str(current_user.id),
            db_session=db
        )
        
        # 5. 将工具执行结果反馈给 LLM，获取最终回复
        # Append LLM's initial response (which contained tool calls) to history
        llm_response_for_history = {
            "role": "assistant",
            "content": llm_response.content,
            "tool_calls": llm_response.tool_calls # Store raw tool calls if needed
        }
        
        # Append tool results in history as tool messages
        tool_messages_for_history = []
        for tr in tool_results:
             tool_messages_for_history.append({
                 "role": "tool",
                 "content": json.dumps(tr.model_dump(), ensure_ascii=False)
             })
        
        updated_conversation_history = llm_conversation_history + [
            {"role": "user", "content": request.message} # User message
        ] + [llm_response_for_history] + tool_messages_for_history

        final_llm_response = await llm_service.continue_with_tool_results(
            conversation_history=updated_conversation_history
        )
        llm_text = final_llm_response.content
    else:
        llm_text = llm_response.content
    
    # 6. 组装响应
    response_data = response_composer.compose_response(
        llm_text=llm_text,
        tool_results=tool_results
    )
    
    # 7. 保存消息到数据库
    await save_chat_message(
        db=db,
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        user_message=request.message,
        assistant_message=llm_text,
        tool_results=[tr.model_dump() for tr in tool_results] # save tool results in message
    )
    
    return ChatResponse(**response_data, conversation_id=request.conversation_id or "new")

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
        
        user_id_uuid = current_user.id
        
        # Build context
        user_context = await get_user_context(db, user_id_uuid)
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
                            "function": {
                                "name": chunk.tool_name,
                                "arguments": json.dumps(chunk.full_arguments)
                            }
                        }
                    ]
                })

                message_history_for_llm_callback.append({
                    "role": "tool",
                    "content": json.dumps(result.model_dump(), ensure_ascii=False)
                })

                # Call LLM again to get final text
                final_llm_response = await llm_service.continue_with_tool_results(
                    conversation_history=message_history_for_llm_callback
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
    # From the plan, this is not implemented yet in backend fully
    # Placeholder for now
    if not confirmed:
        return {"status": "cancelled", "message": "操作已取消"}
    
    # In a real scenario, retrieve pending action from cache/db based on action_id
    # For now, simulate success
    return {"status": "executed", "result": {"success": True, "tool_name": "simulated_tool", "data": {"action_id": action_id}}}

# ============辅助函数 ============ 

async def get_user_context(db: AsyncSession, user_id: UUID) -> dict:
    """获取用户上下文信息"""
    # TODO: 实现获取用户近期任务、计划等
    return {
        "recent_tasks": [],
        "active_plans": [],
        "flame_level": 1
    }

async def get_conversation_history(
    db: AsyncSession, 
    user_id: UUID, 
    conversation_id: Optional[str]
) -> List[Dict[str, str]]:
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
    conversation_id: Optional[str],
    user_message: str,
    assistant_message: str,
    tool_results: List[Dict]
):
    """保存聊天消息"""
    session_id_uuid = UUID(conversation_id) if conversation_id else UUID('00000000-0000-0000-0000-000000000000') 
    
    # Save user message
    user_msg_db = ChatMessage(
        user_id=user_id,
        session_id=session_id_uuid,
        role=MessageRole.USER,
        content=user_message,
    )
    db.add(user_msg_db)

    # Save assistant message
    # Actions should be saved as JSON directly if the model supports it
    assistant_msg_db = ChatMessage(
        user_id=user_id,
        session_id=session_id_uuid,
        role=MessageRole.ASSISTANT,
        content=assistant_message,
        actions=tool_results if tool_results else None, # Store tool results as actions
    )
    db.add(assistant_msg_db)
    
    await db.commit()