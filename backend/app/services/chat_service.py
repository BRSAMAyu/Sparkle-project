"""
对话服务
Chat Service - 管理用户对话和 LLM 交互
"""
import json
import uuid
from typing import AsyncGenerator, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from datetime import datetime

from app.models.chat import ChatMessage, MessageRole
from app.models.user import User
from app.services.llm.parser import LLMResponseParser, LLMResponse

class ChatService:
    def __init__(self):
        self.parser = LLMResponseParser()
    
    async def stream_chat(
        self,
        db: AsyncSession,
        user_id: UUID,
        content: str,
        session_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        message_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式对话核心逻辑
        """
        if not session_id:
            session_id = uuid.uuid4()
            
        # 1. 保存用户消息 (如果有 message_id，需检查幂等，但通常由中间件处理请求级幂等)
        # 这里我们只是保存记录
        user_message = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            role=MessageRole.USER,
            content=content,
            message_id=message_id or str(uuid.uuid4())
        )
        db.add(user_message)
        await db.commit()
        
        # 2. 调用 LLM (模拟流式输出)
        # TODO: 集成真实的 LLM Service (OpenAI/Qwen)
        full_response_text = ""
        
        # 模拟 LLM 输出 "你好"
        mock_chunks = ["我", "是", "Sparkle", "，", "很", "高", "兴", "为", "你", "服", "务", "。"]
        
        for chunk in mock_chunks:
            full_response_text += chunk
            yield {
                "event": "token",
                "data": json.dumps({"content": chunk})
            }
            # 模拟网络延迟
            await asyncio.sleep(0.05)
            
        # 3. 解析响应 (尝试解析 Actions)
        # 这里模拟一个非 JSON 响应，触发降级或正常文本
        # 如果 content 包含 JSON，则解析
        
        llm_response = self.parser.parse(full_response_text)
        
        # 4. 处理解析结果
        if llm_response.parse_degraded:
            # 🆕 v2.1: 推送降级状态
            yield {
                "event": "parse_status",
                "data": json.dumps({
                    "degraded": True,
                    "reason": llm_response.degraded_reason
                })
            }
        elif llm_response.actions:
            # 推送 Actions
            yield {
                "event": "actions",
                "data": json.dumps({
                    "actions": [action.model_dump() for action in llm_response.actions]
                })
            }
            # TODO: 异步执行 Actions (JobService)
            
        # 5. 保存 Assistant 消息
        assistant_message = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            role=MessageRole.ASSISTANT,
            content=llm_response.assistant_message,
            actions=[a.model_dump() for a in llm_response.actions] if llm_response.actions else None,
            parse_degraded=llm_response.parse_degraded
        )
        db.add(assistant_message)
        await db.commit()
        
        # 6. 结束
        yield {
            "event": "done",
            "data": json.dumps({
                "message_id": str(assistant_message.id),
                "session_id": str(session_id)
            })
        }

# 导出单例
chat_service = ChatService()
