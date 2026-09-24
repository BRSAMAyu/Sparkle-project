from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class UserPushOptIn(BaseModel):
    __tablename__ = "user_push_opt_in"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_commitment_follow_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_engagement_recovery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(5), nullable=False, default="22:00")
    quiet_hours_end: Mapped[str] = mapped_column(String(5), nullable=False, default="08:00")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Shanghai")

    user = relationship("User", backref="push_opt_in")


Index("idx_user_push_opt_in_user", UserPushOptIn.user_id, unique=True)

