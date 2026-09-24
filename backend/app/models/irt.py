"""
IRT Models
项目反应理论相关模型
"""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class IRTItemParameter(BaseModel):
    """
    题目 IRT 参数
    """
    __tablename__ = "irt_item_parameters"

    question_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(32), nullable=True, index=True)
    a: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # discrimination
    b: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # difficulty
    c: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)  # guess


class UserIRTAbility(BaseModel):
    """
    用户能力参数 (theta)
    """
    __tablename__ = "user_irt_ability"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(32), nullable=True, index=True)
    theta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
