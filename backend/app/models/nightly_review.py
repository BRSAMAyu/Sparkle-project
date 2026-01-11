"""
Nightly Review Models
Phase 2 nightly reviewer output.
"""
from sqlalchemy import Column, String, JSON, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class NightlyReview(BaseModel):
    __tablename__ = "nightly_reviews"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    review_date = Column(Date, nullable=False, index=True)
    summary_text = Column(String(2000), nullable=True)
    todo_items = Column(JSON, nullable=True)
    evidence_refs = Column(JSON, nullable=True)
    model_version = Column(String(50), nullable=True)
    status = Column(String(30), default="generated", nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="nightly_reviews")
