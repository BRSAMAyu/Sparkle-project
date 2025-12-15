"""
幂等性键模型
IdempotencyKey Model - 用于防止重复请求处理
"""
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from app.models.base import Base, GUID

class IdempotencyKey(Base):
    """
    🆕 幂等键记录表 (v2.1)
    """
    __tablename__ = "idempotency_keys"

    key = Column(String(64), primary_key=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    response = Column(JSON, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # 关系
    user = relationship("User")

    def __repr__(self):
        return f"<IdempotencyKey(key={self.key})>"
