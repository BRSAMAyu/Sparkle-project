"""
�݈o!�
ChatMessage Model - (7AI��ݰU
"""
import enum
import uuid
from sqlalchemy import Column, String, Integer, Text, Enum, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class MessageRole(str, enum.Enum):
    """�o�r�>"""
    USER = "user"           # (7�o
    ASSISTANT = "assistant" # AI�K�o
    SYSTEM = "system"       # �߈o


class ChatMessage(BaseModel):
    """
    �݈o!�

    W�:
        user_id: @^(7ID
        session_id: �ID(����	
        task_id: sT��ID�	��
���	
        role: �o�ruser/assistant/system	
        content: �o��
        actions: AI�ބӄ�\JSON	
        tokens_used: ��tokenp�
        model_name: (�!��

    s�:
        user: @^(7
        task: sT���		
    """

    __tablename__ = "chat_messages"

    # sTs�
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)

    # ݡ
    session_id = Column(GUID(), nullable=False, index=True, default=uuid.uuid4)

    # �o��
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # AI�s�o
    actions = Column(JSON, nullable=True)  # AI�ބӄ�\
    tokens_used = Column(Integer, nullable=True)
    model_name = Column(String(100), nullable=True)

    # s��I
    user = relationship("User", back_populates="chat_messages")
    task = relationship("Task", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage(role={self.role}, session_id={self.session_id})>"


# �"
Index("idx_chat_user_id", ChatMessage.user_id)
Index("idx_chat_session_id", ChatMessage.session_id)
Index("idx_chat_task_id", ChatMessage.task_id)
Index("idx_chat_created_at", ChatMessage.created_at)
Index("idx_chat_role", ChatMessage.role)
