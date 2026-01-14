"""
Document chunk models
文档分块模型
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.models.base import BaseModel, GUID


class DocumentChunk(BaseModel):
    """
    Document chunks for vector search.
    """
    __tablename__ = "document_chunks"

    file_id = Column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(255), nullable=True)
    bbox = Column(String, nullable=True) # JSON stored as String or JSONB depending on DB
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)

    file = relationship("StoredFile")
    user = relationship("User")
