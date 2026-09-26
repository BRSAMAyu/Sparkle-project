"""
聊天消息模型
ChatMessage Model - 用户与AI的对话记录
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class MessageRole(enum.StrEnum):
    """消息角色枚举"""

    USER = "user"  # 用户消息
    ASSISTANT = "assistant"  # AI助手消息
    SYSTEM = "system"  # 系统消息


class MessageOrigin(enum.StrEnum):
    """消息内容产出来源枚举（V3-FIX-258：demo 产出落库持久标记）。

    缺陷背景：demo 模式（DEMO_MODE 显式或 API key 缺失自动激活）的脚本回复
    落库后与真实模型产出在 schema 层不可区分，唯一标记是瞬态 OTel span
    ``llm.demo_mode``。取值语义：

    - ``llm``：常规管线产出（真实模型回复、user 行与系统模板行的默认值，
      以及 origin 列引入前的全部存量行——存量不做启发式回填，历史 demo 行
      不可考，本列仅对迁移上线后的新写入有区分力）；
    - ``demo``：演示模式脚本产出（llm_service demo 短路的
      DEMO_MOCK_RESPONSES/通用演示回复、guest 种子演示聊天的脚本回复）。
      注意 demo 行的 model_name 仍是「配置了但从未运行」的模型名，lineage
      查询以本列为准。
    """

    LLM = "llm"  # 常规管线产出（默认）
    DEMO = "demo"  # 演示模式脚本产出


class ChatMessage(BaseModel):
    """
    聊天消息模型

    字段:
        user_id: 所属用户ID
        session_id: 会话ID(用于区分不同对话)
        task_id: 关联任务ID(可选，当对话与某个任务相关)
        role: 消息角色(user/assistant/system)
        content: 消息内容
        actions: AI执行的动作列表(JSON)
        tokens_used: 消耗的token数量
        model_name: 使用的模型名称
        origin: 内容产出来源(llm=常规管线默认; demo=演示模式脚本产出, V3-FIX-258)

    关系:
        user: 所属用户
        task: 关联任务(可选)
    """

    __tablename__ = "chat_messages"

    # Partitioning Support: Primary Key must include partition key
    # Note: We override the fields inherited from BaseModel to include primary_key=True
    id: Mapped[Any] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, primary_key=True, default=datetime.utcnow, nullable=False)

    # 关联关系
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True)

    # 会话信息
    session_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True, default=uuid.uuid4)
    # 🆕 v2.1: 客户端生成的消息 ID (用于幂等性)
    # Note: message_id unique constraint was moved to composite (message_id, created_at) in partitioning
    message_id: Mapped[str] = mapped_column(String(128), nullable=True)

    # 消息内容
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AI相关信息
    actions: Mapped[Any] = mapped_column(JSON, nullable=True)  # AI执行的动作列表
    # 🆕 v2.1: 解析降级标记
    parse_degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    tokens_used: Mapped[int] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=True)

    # V3-FIX-258: 内容产出来源持久标记（此前唯一标记是瞬态 OTel span
    # llm.demo_mode，demo 脚本回复落库后与真实模型产出在 schema 层不可区分）。
    # 取值见 MessageOrigin；server_default 让存量行统一落 'llm'（不做启发式
    # 回填——历史 demo 行不可考，本列仅对迁移上线后的新写入有区分力）。
    # 判别查询低频且非热点谓词，不建索引（需要时可后补）。
    origin: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MessageOrigin.LLM.value, server_default=MessageOrigin.LLM.value
    )

    # 关系定义
    user = relationship("User", back_populates="chat_messages")
    task = relationship("Task", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage(role={self.role}, session_id={self.session_id})>"


class ChatSession(BaseModel):
    """
    Chat session metadata.

    Used by E2E tests and session-level UX.
    """

    __tablename__ = "chat_sessions"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="chat_sessions")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id})>"


class TokenUsage(BaseModel):
    """
    Token 使用量记录模型

    用于计费和统计分析

    字段:
        user_id: 用户ID
        session_id: 会话ID
        request_id: 请求ID
        prompt_tokens: 输入Token数
        completion_tokens: 输出Token数
        total_tokens: 总Token数
        model: 模型名称
        cost: 估算成本（美元）
    """

    __tablename__ = "token_usage"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4")
    model_tier: Mapped[str] = mapped_column(String(40), nullable=True)
    ai_reasoning_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="balanced")
    cost: Mapped[float] = mapped_column(Float, nullable=True)  # 估算成本（美元）

    # 关系
    user = relationship("User", back_populates="token_usage")

    def __repr__(self):
        return f"<TokenUsage(user_id={self.user_id}, tokens={self.total_tokens}, cost={self.cost})>"


# 创建索引
Index("idx_chat_user_id", ChatMessage.user_id)
Index("idx_chat_session_id", ChatMessage.session_id)
Index("idx_chat_task_id", ChatMessage.task_id)
Index("idx_chat_created_at", ChatMessage.created_at)
Index("idx_chat_role", ChatMessage.role)

Index("idx_chat_session_user_id", ChatSession.user_id)
Index("idx_chat_session_active", ChatSession.is_active)

Index("idx_token_usage_user_id", TokenUsage.user_id)
Index("idx_token_usage_session_id", TokenUsage.session_id)
Index("idx_token_usage_created_at", TokenUsage.created_at)
