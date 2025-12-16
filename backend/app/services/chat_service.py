"""
对话服务
Chat Service - 管理用户对话和 LLM 交互
"""
import json
import uuid
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger
from datetime import datetime

from app.models.chat import ChatMessage, MessageRole
from app.models.user import User
from app.services.llm.parser import LLMResponseParser, LLMResponse
from app.services.llm_service import llm_service

SYSTEM_PROMPT = """你是一个名为 Sparkle (星火) 的 AI 学习助手。
你的目标是帮助大学生制定学习计划、拆解任务、并提供学习反馈。
你需要通过对话引导用户，并在适当的时候自动创建任务 (Task) 或计划 (Plan)。
请时刻保持鼓励、积极的语气。

当用户通过对话明确了具体的学习任务时，你应该尝试以 JSON 格式返回 "Actions"，例如创建任务。
如果不确定，请先通过对话确认。
"""

class ChatService:
    def __init__(self):
        self.parser = LLMResponseParser()
    
    async def _get_chat_history(self, db: AsyncSession, session_id: UUID, limit: int = 10) -> List[Dict[str, str]]:
        """获取最近的对话历史"""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        # 转换为 LLM 格式 (反转顺序，因为是从新到旧查的)
        history = []
        for msg in reversed(messages):
            # 过滤掉 System 消息 (通常不需要历史中的 System 消息，只在当前 Prompt 头部加)
            if msg.role == MessageRole.SYSTEM:
                continue
            history.append({
                "role": msg.role.value,
                "content": msg.content
            })
        return history

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
            
        # 1. 保存用户消息
        # 如果 message_id 已存在，这里可能会报错，但在 Service 层我们假设它是唯一的或由上层处理
        user_message_id = message_id or str(uuid.uuid4())
        user_message = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            role=MessageRole.USER,
            content=content,
            message_id=user_message_id
        )
        db.add(user_message)
        await db.commit()
        
        # 2. 构建 LLM Prompt
        history = await self._get_chat_history(db, session_id, limit=10)
        # 确保当前消息在最后 (虽然保存了，但刚才查出来可能不包含它，或者包含它。
        # _get_chat_history 查的是 DB，我们刚刚 commit 了，所以应该包含。
        # 为了稳妥，我们手动构建 messages 列表)
        
        # 重新构建 messages：System + History (Exclude current if fetched) + Current (if not in fetched)
        # 简单起见：History 包含了刚刚保存的 User Message
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        
        # 3. 调用 LLM
        full_response_text = ""
        
        try:
            async for chunk in llm_service.stream_chat(messages):
                full_response_text += chunk
                yield {
                    "event": "token",
                    "data": json.dumps({"content": chunk})
                }
        except Exception as e:
            logger.error(f"LLM Stream Error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": "AI 服务暂时不可用，请稍后再试。"})
            }
            return

        # 4. 解析响应
        logger.info(f"Full LLM response: {full_response_text}")
        llm_response = self.parser.parse(full_response_text)
        
        # 5. 处理解析结果
        if llm_response.parse_degraded:
            yield {
                "event": "parse_status",
                "data": json.dumps({
                    "degraded": True,
                    "reason": llm_response.degraded_reason
                })
            }
        elif llm_response.actions:
            yield {
                "event": "actions",
                "data": json.dumps({
                    "actions": [action.model_dump() for action in llm_response.actions]
                })
            }
            # TODO: 异步执行 Actions (JobService) 或前端确认后执行
            
        # 6. 保存 Assistant 消息
        assistant_message = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            role=MessageRole.ASSISTANT,
            content=llm_response.assistant_message,
            actions=[a.model_dump() for a in llm_response.actions] if llm_response.actions else None,
            parse_degraded=llm_response.parse_degraded,
            model_name=llm_service.default_model
        )
        db.add(assistant_message)
        await db.commit()
        
        # 7. 结束
        yield {
            "event": "done",
            "data": json.dumps({
                "message_id": str(assistant_message.id),
                "session_id": str(session_id)
            })
        }

# 导出单例
chat_service = ChatService()
