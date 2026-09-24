"""
Document chunk models
文档分块模型
"""
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

VectorCompat = Vector(1024).with_variant(JSON(), "sqlite")

class DocumentChunk(BaseModel):
    """
    Document chunks for vector search.
    """
    __tablename__ = "document_chunks"

    file_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    from sqlalchemy import Float

    # Traceability
    page_numbers: Mapped[Any] = mapped_column(JSON, default=list, nullable=True) # [1] or [1, 2]
    section_title: Mapped[str] = mapped_column(String(255), nullable=True)
    bbox: Mapped[Any] = mapped_column(JSON, nullable=True) # { "p1": [x,y,w,h] }

    # Quality & Versioning
    quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=True) # 0.0 - 1.0 (OCR confidence, etc.)
    pipeline_version: Mapped[str] = mapped_column(String(50), nullable=True) # e.g. "v1.0", "deepseek-v2"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(VectorCompat, nullable=True)

    # E-05 Embedding 版本溯源：记录生成该向量的 provider/model@dim（如
    # "dashscope/text-embedding-v4@1024"）。检索按当前版本过滤，防止跨模型
    # 余弦相似度污染；NULL 表示存量未标记向量（过渡期由
    # EMBEDDING_STRICT_VERSION_FILTER 决定是否参与检索）。
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=True)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=True)

    file = relationship("StoredFile")
    user = relationship("User")
