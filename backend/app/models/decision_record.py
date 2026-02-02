"""
决策记录模型
"""
from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class DecisionRecord(BaseModel):
    """系统决策记录"""

    __tablename__ = "decision_records"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    module = Column(String(50), nullable=False, index=True)  # "ai" | "push" | "task"
    action = Column(String(100), nullable=False)
    preference_version = Column(Integer, nullable=False)
    preferences_snapshot = Column(JSONBCompat, nullable=True)
    outcome = Column(String(500), nullable=True)
