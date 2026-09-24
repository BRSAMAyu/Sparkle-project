"""
幂等性键模型
IdempotencyKey Model - 用于防止重复请求处理
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.base import GUID


class IdempotencyKey(Base):
    """
    幂等键记录表
    用于存储 API 请求的幂等性键和响应缓存
    """
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    endpoint: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    response_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    response: Mapped[Any] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # 关系
    user = relationship("User")

    def __repr__(self):
        return f"<IdempotencyKey(key={self.key})>"


# 复合索引：用于清理过期记录
Index("idx_idempotency_expires", IdempotencyKey.expires_at)
