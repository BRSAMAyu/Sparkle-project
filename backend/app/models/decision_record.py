"""
决策记录模型
"""
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class DecisionRecord(BaseModel):
    """系统决策记录"""

    __tablename__ = "decision_records"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "ai" | "push" | "task"
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    preference_version: Mapped[int] = mapped_column(Integer, nullable=False)
    preferences_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    outcome: Mapped[str] = mapped_column(String(500), nullable=True)
