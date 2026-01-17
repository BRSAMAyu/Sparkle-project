"""
Document chunk models
文档分块模型
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, JSON, Float
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
    
    from sqlalchemy import Float

    # Traceability
    page_numbers = Column(JSON, default=list) # [1] or [1, 2]
    section_title = Column(String(255), nullable=True)
    bbox = Column(JSON, nullable=True) # { "p1": [x,y,w,h] }
    
    # Quality & Versioning
    quality_score = Column(Float, default=1.0) # 0.0 - 1.0 (OCR confidence, etc.)
    pipeline_version = Column(String(50), nullable=True) # e.g. "v1.0", "deepseek-v2"

    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)

    file = relationship("StoredFile")
    user = relationship("User")
