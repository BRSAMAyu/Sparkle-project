"""
Chat API Endpoints
"""
import json
import time
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from asyncio import TimeoutError as AsyncTimeoutError

from app.db.session import get_db
from app.services.chat_service import chat_service
from app.schemas.chat import ChatMessageSend
from app.models.user import User
from app.api.deps import get_current_user
from app.config import settings

router = APIRouter()

@router.post("/stream")
async def chat_stream(
    request: ChatMessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
):
    """
    流式对话接口 (v2.1)
    """
    async def event_generator():
        start_time = time.time()
        
        # SSE 配置
        keep_alive_interval = getattr(settings, "SSE_KEEP_ALIVE_INTERVAL", 15)
        connection_timeout = getattr(settings, "SSE_CONNECTION_TIMEOUT", 300)
        
        try:
            async for event in chat_service.stream_chat(
                db=db,
                user_id=current_user.id,
                content=request.content,
                session_id=request.session_id,
                task_id=request.task_id,
                message_id=request.message_id,
            ):
                # 🆕 检查连接超时
                if time.time() - start_time > connection_timeout:
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": "连接超时，请重试"})
                    }
                    return
                
                yield event
                
        except AsyncTimeoutError:
            yield {
                "event": "error",
                "data": json.dumps({"message": "处理超时，请重试"})
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": f"Server Error: {str(e)}"})
            }
    
    return EventSourceResponse(
        event_generator(),
        ping=getattr(settings, "SSE_KEEP_ALIVE_INTERVAL", 15),
    )
