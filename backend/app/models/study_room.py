"""共学自习室在场证明模型（D-COMM-4 · beacon 式在场，服务端 TTL 真源）。

复用裁决（vs 既有表）：社群域无 presence/session 类模型——
``GroupMember.last_active_at`` 是成员级单时间戳（无会话语义、算不出时长）、
``models/focus.py::FocusSession`` 是个人番茄钟结算记录（写入即要求
end_time/duration，无群组归属，撑不起「谁正在自习」的活体在场面）、
``User.status`` 是全局在线状态（非小队作用域）。故按设计卡 §3.3
「落库最小记录」立最小新表：一条记录 = 一次进出场（entered_at →
exited_at），exited_at IS NULL 即开放记录。

ROOM-PRESENCE 修订：在场判定 = 开放记录 **且** last_heartbeat_at 在
``STUDY_ROOM_PRESENCE_TTL_SECONDS``（90s）内——TTL 过期即诚实离场
（读路径惰性判定，无需后台清理任务），杀进程/切后台后最多 TTL 内残留。
续期信号 = 前台房间轮询（30s 一拍，绝不要求后台 Timer）；显式进出为主、
心跳续命。离开不惩罚——在场时长如实记录（时长按 last_heartbeat_at + TTL
诚实封顶，decay 不虚增），不进任何榜分（小队榜口径唯一是 sprint 完成度，
见 services/community_squad_board_service.py；防 Duolingo 式挂机刷时长）。
零迁移：TTL 复用既有 ``last_heartbeat_at`` 列，无 schema 变更。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel


class StudyRoomSession(BaseModel):
    """一次自习进出场（beacon 式在场证明，最小记录）。

    - ``entered_at``：进入时刻（naive UTC，与社群域既有列约定一致）；
    - ``exited_at``：离开时刻；NULL = 开放记录（在场与否由 TTL 判定）；
    - ``last_heartbeat_at``：最后活性证明（前台房间轮询/显式心跳续写；
      也是 TTL 时间戳与时长封顶基准——零迁移复用本列）。
    """

    __tablename__ = "study_room_sessions"

    group_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    entered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    exited_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        # 一人一小队同时至多一个开放会话。部分索引带 exited_at/deleted_at
        # 谓词，PG 生产由 Alembic 等价迁移创建；sqlite 同样支持部分索引
        # （sqlite_where 与迁移 dc4room_20260922 双方言等价），测试路径的
        # 开放会话唯一性由本索引 + 服务层 enter 幂等语义共同保证。
        Index(
            "uq_study_room_open_session",
            "group_id",
            "user_id",
            unique=True,
            sqlite_where=text("exited_at IS NULL AND deleted_at IS NULL"),
            postgresql_where=text("exited_at IS NULL AND deleted_at IS NULL"),
        ),
        Index("idx_study_room_group_entered", "group_id", "entered_at"),
        Index("idx_study_room_user_entered", "user_id", "entered_at"),
    )

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"<StudyRoomSession(id={self.id}, group_id={self.group_id}, user_id={self.user_id}, "
            f"entered_at={self.entered_at}, exited_at={self.exited_at})>"
        )
