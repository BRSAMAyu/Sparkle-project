"""Strategy belief snapshot model used by the migration assistant."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class StrategyBeliefSnapshot(BaseModel):
    """Persisted Bayesian belief summary for a strategy."""

    __tablename__ = "strategy_belief_snapshots"

    user_id = Column(String(128), nullable=False, index=True)
    strategy_key = Column(String(128), nullable=False, index=True)
    alpha = Column(Float, nullable=False, default=1.0)
    beta = Column(Float, nullable=False, default=1.0)
    evidence_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(String(64), nullable=False, default="")
    counter_evidence = Column(JSONBCompat, nullable=False, default=list)
    metadata_payload = Column("metadata", JSONBCompat, nullable=False, default=dict)

    @property
    def raw_expected_effectiveness(self) -> float:
        total = float(self.alpha or 0) + float(self.beta or 0)
        if total <= 0:
            return 0.5
        return float(self.alpha or 0) / total

    @property
    def counter_evidence_penalty(self) -> float:
        evidence = self.counter_evidence if isinstance(self.counter_evidence, list) else []
        return min(len(evidence) * 0.05, 0.3)

    @property
    def belief_score(self) -> float:
        return max(0.0, self.raw_expected_effectiveness - self.counter_evidence_penalty)
