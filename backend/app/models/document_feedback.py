"""
Document retrieval feedback model
文档检索反馈模型
"""
from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class DocumentRetrievalFeedback(BaseModel):
    """
    Stores per-citation user feedback signals to improve document retrieval quality.

    feedback_score:
        1  = positive (helpful citation)
        -1 = negative (unhelpful / misleading citation)
        0  = neutral (implicit, e.g. user read but no strong signal)

    feedback_source:
        "explicit"          — user tapped thumbs up/down
        "implicit_positive" — user asked a topical follow-up after cited content
        "implicit_negative" — user asked for a different explanation right after cited content
    """

    __tablename__ = "document_retrieval_feedback"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(GUID(), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)

    query_intent_type = Column(String(64), nullable=True)  # knowledge_query, task_management, etc.
    feedback_score = Column(Integer, nullable=False)  # 1=positive, -1=negative, 0=neutral
    feedback_source = Column(String(32), nullable=False)  # "explicit", "implicit_positive", "implicit_negative"
    conversation_id = Column(String(128), nullable=True)
    context = Column(JSON, nullable=True)

    user = relationship("User")
    file = relationship("StoredFile")
    chunk = relationship("DocumentChunk")
