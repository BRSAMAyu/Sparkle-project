"""
聊天消息模型
ChatMessage Model - 用户与AI的对话记录
"""
import enum
import uuid
from sqlalchemy import Column, String, Integer, Text, Enum, ForeignKey, Index, JSON, Boolean, Float
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID
from sqlalchemy import DateTime


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"           # 用户消息
    ASSISTANT = "assistant" # AI助手消息
    SYSTEM = "system"       # 系统消息


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

    关系:
        user: 所属用户
        task: 关联任务(可选)
    """

    __tablename__ = "chat_messages"

    # 关联关系
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)

    # 会话信息
    session_id = Column(GUID(), nullable=False, index=True, default=uuid.uuid4)
    # 🆕 v2.1: 客户端生成的消息 ID (用于幂等性)
    message_id = Column(String(36), unique=True, nullable=True)

    # 消息内容
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # AI相关信息
    actions = Column(JSON, nullable=True)  # AI执行的动作列表
    # 🆕 v2.1: 解析降级标记
    parse_degraded = Column(Boolean, default=False)
    
    tokens_used = Column(Integer, nullable=True)
    model_name = Column(String(100), nullable=True)

    # 关系定义
    user = relationship("User", back_populates="chat_messages")
    task = relationship("Task", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage(role={self.role}, session_id={self.session_id})>"


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

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    request_id = Column(String(100), nullable=False, unique=True)

    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    model = Column(String(100), nullable=False, default="gpt-4")
    cost = Column(Float, nullable=True)  # 估算成本（美元）

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

Index("idx_token_usage_user_id", TokenUsage.user_id)
Index("idx_token_usage_session_id", TokenUsage.session_id)
Index("idx_token_usage_created_at", TokenUsage.created_at)
