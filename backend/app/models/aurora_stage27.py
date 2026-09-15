from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class PersDynAttractor(BaseModel):
    __tablename__ = "persdyn_attractors"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    dim = Column(String(40), nullable=False)
    baseline = Column(Float, nullable=False, default=0.0)
    variability = Column(Float, nullable=False, default=0.0)
    recovery_rate = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.0)

    user = relationship("User", backref="persdyn_attractors")


Index("idx_persdyn_attractors_user_dim", PersDynAttractor.user_id, PersDynAttractor.dim, unique=True)
Index("idx_persdyn_attractors_user_confidence", PersDynAttractor.user_id, PersDynAttractor.confidence)
