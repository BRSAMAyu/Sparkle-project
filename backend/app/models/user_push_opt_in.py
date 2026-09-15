from sqlalchemy import Boolean, Column, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class UserPushOptIn(BaseModel):
    __tablename__ = "user_push_opt_in"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    allow_commitment_follow_up = Column(Boolean, nullable=False, default=False)
    allow_engagement_recovery = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(String(5), nullable=False, default="22:00")
    quiet_hours_end = Column(String(5), nullable=False, default="08:00")
    timezone = Column(String(64), nullable=False, default="Asia/Shanghai")

    user = relationship("User", backref="push_opt_in")


Index("idx_user_push_opt_in_user", UserPushOptIn.user_id, unique=True)

