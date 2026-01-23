"""
Capsule Favorite Model
"""
from sqlalchemy import Column, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class CapsuleFavorite(BaseModel):
    """
    胶囊收藏模型

    用户可以收藏喜欢的胶囊
    """
    __tablename__ = "capsule_favorites"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    capsule_id = Column(GUID(), ForeignKey("curiosity_capsules.id", ondelete="CASCADE"), nullable=False, index=True)
    note = Column(Text, nullable=True)  # 用户收藏时的备注

    __table_args__ = (
        UniqueConstraint("user_id", "capsule_id", name="uq_capsule_favorite"),
    )

    # Relationships
    user = relationship("User", back_populates="capsule_favorites")
    capsule = relationship("CuriosityCapsule", back_populates="favorites")

    def __repr__(self):
        return f"<CapsuleFavorite(user_id={self.user_id}, capsule_id={self.capsule_id})>"
