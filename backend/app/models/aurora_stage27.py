from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class PersDynAttractor(BaseModel):
    __tablename__ = "persdyn_attractors"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    dim: Mapped[str] = mapped_column(String(40), nullable=False)
    baseline: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    variability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recovery_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    user = relationship("User", backref="persdyn_attractors")


Index("idx_persdyn_attractors_user_dim", PersDynAttractor.user_id, PersDynAttractor.dim, unique=True)
Index("idx_persdyn_attractors_user_confidence", PersDynAttractor.user_id, PersDynAttractor.confidence)
