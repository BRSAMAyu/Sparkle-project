"""
Memory ranking policy model for personalized weights.
"""
from typing import Any

from sqlalchemy import JSON, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class MemoryRankPolicy(BaseModel):
    __tablename__ = "memory_rank_policies"

    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(120), nullable=True)
    weights: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)


Index(
    "uq_memory_rank_policies_scope",
    MemoryRankPolicy.scope_type,
    MemoryRankPolicy.scope_key,
    unique=True,
)
