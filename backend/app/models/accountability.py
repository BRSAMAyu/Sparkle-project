"""
责任伙伴系统 (Accountability Partnership System)

Models:
- AccountabilityPartnership: 伙伴关系
- AccountabilityCheckin: 每日打卡记录
"""

import enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    DDL,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class AccountabilityStatus(enum.StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class AccountabilitySlotType(enum.StrEnum):
    CORE = "core"


class AccountabilityPartnership(BaseModel):
    """责任伙伴关系"""

    __tablename__ = "accountability_partnership"

    initiator_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    friendship_id = Column(
        GUID(),
        ForeignKey("friendships.id", ondelete="SET NULL"),
        nullable=True,
    )
    initiator_goal = Column(Text, nullable=False)
    partner_goal = Column(Text, nullable=True)
    check_in_days = Column(Integer, nullable=False, default=1)
    slot_type = Column(
        Enum(AccountabilitySlotType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AccountabilitySlotType.CORE,
        index=True,
    )
    status = Column(
        Enum(AccountabilityStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AccountabilityStatus.PENDING,
        index=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    initiator = relationship("User", foreign_keys=[initiator_id], lazy="selectin")
    partner = relationship("User", foreign_keys=[partner_id], lazy="selectin")
    checkins = relationship(
        "AccountabilityCheckin",
        back_populates="partnership",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(
            "initiator_id",
            "partner_id",
            name="uq_accountability_partnership_pair",
        ),
        Index(
            "idx_accountability_initiator_status",
            "initiator_id",
            "status",
        ),
        Index(
            "idx_accountability_partner_status",
            "partner_id",
            "status",
        ),
        Index(
            "idx_accountability_slot_status",
            "slot_type",
            "status",
        ),
    )


# 双向活跃伙伴唯一约束依赖 LEAST/GREATEST 方言函数，SQLite 等方言不支持，
# 故从 __table_args__ 移出，改为仅在 postgresql 方言上创建（生产 schema 由 Alembic 迁移管理，
# 此处等价约束服务于 create_all 测试路径）。
event.listen(
    AccountabilityPartnership.__table__,
    "after_create",
    DDL(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_partnership_active_pair_bidirectional "
        "ON accountability_partnership "
        "(LEAST(initiator_id, partner_id), GREATEST(initiator_id, partner_id)) "
        "WHERE deleted_at IS NULL"
    ).execute_if(dialect="postgresql"),
)


class AccountabilityCheckin(BaseModel):
    """责任打卡记录"""

    __tablename__ = "accountability_checkin"

    partnership_id = Column(
        GUID(),
        ForeignKey("accountability_partnership.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    mood = Column(Integer, nullable=False, default=3)  # 1-5
    minutes = Column(Integer, nullable=False, default=0)

    # 互动字段
    likes = Column(Integer, nullable=False, default=0)  # 点赞数
    liked_by = Column(JSONBCompat, nullable=False, default=list)  # 点赞用户ID列表
    encouragements = Column(JSONBCompat, nullable=False, default=list)  # 鼓励消息列表

    # Relationships
    partnership = relationship("AccountabilityPartnership", back_populates="checkins")
    user = relationship("User", lazy="selectin")

    __table_args__ = (
        Index(
            "idx_accountability_checkin_partnership_user",
            "partnership_id",
            "user_id",
        ),
        Index(
            "idx_accountability_checkin_created_at",
            "created_at",
        ),
        Index(
            "idx_checkin_partnership_user_created",
            "partnership_id",
            "user_id",
            "created_at",
        ),
    )
