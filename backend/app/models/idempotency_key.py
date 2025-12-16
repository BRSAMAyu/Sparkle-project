"""
幂等性键模型
IdempotencyKey Model - 用于防止重复请求处理
"""
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.base import GUID


class IdempotencyKey(Base):
    """
    幂等键记录表
    用于存储 API 请求的幂等性键和响应缓存
    """
    __tablename__ = "idempotency_keys"

    key = Column(String(64), primary_key=True)
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    response = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # 关系
    user = relationship("User")

    def __repr__(self):
        return f"<IdempotencyKey(key={self.key})>"


# 复合索引：用于清理过期记录
Index("idx_idempotency_expires", IdempotencyKey.expires_at)
