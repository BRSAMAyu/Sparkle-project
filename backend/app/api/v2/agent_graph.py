import json
import uuid
from typing import AsyncGenerator, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.agents.graph.workflow import sparkle_graph
from app.agents.graph.state import SparkleState
from app.api.deps import get_current_user # 假设已有 Auth
from app.services.llm_service import llm_service # 复用旧的 service 来做简单的鉴权或统计

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str = None
    stream: bool = True

async def generate_graph_events(inputs: Dict, config: Dict) -> AsyncGenerator[str, None]:
    """生成 LangGraph 事件流 (SSE 格式)"""
    
    # 使用 astream_events 获取详细的执行流
    async for event in sparkle_graph.astream_events(inputs, config=config, version="v1"):
        kind = event["event"]
        
        # 1. 节点开始 (Node Start)
        if kind == "on_chain_start" and event["name"] == "LangGraph":
             yield f"data: {json.dumps({'type': 'start', 'msg': 'Workflow started'})}\n\n"

        # 2. 聊天模型输出 (LLM Streaming)
        elif kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

        # 3. 工具调用 (Tool Start)
        elif kind == "on_tool_start":
            tool_name = event["name"]
            tool_input = event["data"].get("input")
            yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'input': tool_input})}\n\n"

        # 4. 工具输出 (Tool End)
        elif kind == "on_tool_end":
            tool_output = event["data"].get("output")
            yield f"data: {json.dumps({'type': 'tool_end', 'output': str(tool_output)})}\n\n"
            
        # 5. 节点转换 (Node Transition)
        # 可以在这里捕获 active_agent 的变化

    yield "data: [DONE]\n\n"

@router.post("/chat")
async def chat_with_agent(
    request: ChatRequest,
    # current_user = Depends(get_current_user) # 暂时注释，方便测试
):
    """
    与 Next-Gen Agent 对话
    """
    session_id = request.session_id or str(uuid.uuid4())
    user_id = "test_user" # current_user.id
    
    # 构造初始状态
    inputs = {
        "messages": [HumanMessage(content=request.message)],
        "user_id": user_id,
        "session_id": session_id
    }
    
    # LangGraph 配置 (包含 checkpointer ID)
    config = {"configurable": {"thread_id": session_id}}
    
    if request.stream:
        return StreamingResponse(
            generate_graph_events(inputs, config),
            media_type="text/event-stream"
        )
    else:
        # 同步等待结果 (非流式)
        final_state = await sparkle_graph.ainvoke(inputs, config=config)
        last_message = final_state["messages"][-1]
        return {
            "response": last_message.content,
            "session_id": session_id
        }
