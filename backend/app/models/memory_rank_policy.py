"""
Memory ranking policy model for personalized weights.
"""
from sqlalchemy import Column, String, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class MemoryRankPolicy(BaseModel):
    __tablename__ = "memory_rank_policies"

    scope_type = Column(String(20), nullable=False)
    scope_key = Column(String(120), nullable=True)
    weights = Column(JSONBCompat, nullable=False, default=dict)


Index(
    "uq_memory_rank_policies_scope",
    MemoryRankPolicy.scope_type,
    MemoryRankPolicy.scope_key,
    unique=True,
)
