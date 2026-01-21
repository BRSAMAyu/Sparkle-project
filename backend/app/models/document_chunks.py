"""
Document chunk models
文档分块模型
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.models.base import BaseModel, GUID

VectorCompat = Vector(1024).with_variant(JSON(), "sqlite")

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
    content = Column(Text, nullable=False)
    embedding = Column(VectorCompat, nullable=True)

    file = relationship("StoredFile")
    user = relationship("User")
