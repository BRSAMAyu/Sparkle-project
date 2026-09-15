"""
IRT Models
项目反应理论相关模型
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class IRTItemParameter(BaseModel):
    """
    题目 IRT 参数
    """
    __tablename__ = "irt_item_parameters"

    question_id = Column(GUID(), nullable=False, index=True)
    subject_id = Column(String(32), nullable=True, index=True)
    a = Column(Float, default=1.0, nullable=False)  # discrimination
    b = Column(Float, default=0.0, nullable=False)  # difficulty
    c = Column(Float, default=0.2, nullable=False)  # guess


class UserIRTAbility(BaseModel):
    """
    用户能力参数 (theta)
    """
    __tablename__ = "user_irt_ability"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(String(32), nullable=True, index=True)
    theta = Column(Float, default=0.0, nullable=False)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
