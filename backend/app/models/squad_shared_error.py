"""小队错题卡分享模型（D-COMM-5 · 错题卡互助分享）。

复用裁决（vs 既有表）：社群域没有「把我的错题挂到小队」的分发记录——
``GroupMessage`` 是消息流（内容客户端给、无错题引用语义）、
``SharedResource`` 是公共目录资源（与本卡「无公共目录泄露，仅小队成员
可见」的隐私裁决相悖）、``community_error_aggregation_service`` 是匿名
跨用户聚合（≥3 人才出模式，非小队作用域）。故按 D-COMM-4 先例立最小
新表 ``squad_shared_errors``：一条记录 = 一次分享（引用 error_id +
分享时刻的服务端快照），撤回 = 软删。

快照语义（设计裁决）：分享内容在 POST 时刻由服务端从 error_records
取真实内容投影成**可分享白名单**并冻结——
1. 安全过滤（SAFETY 词库面）检查的就是这份快照，快照即所服务内容，
   关闭「先分享良性内容→再 PATCH 错题夹带违规内容」的 TOCTOU 绕过；
2. 掌握度是快照（mastery_level/mastery_delta/review_count），如实呈现
   分享时刻的「卡在哪」，不随此后复习波动粉饰/塌陷；
3. 列表读取时对源错题做 liveness 联查（源错题被主人软删 → 分享自动
   从小队流中消失），隐私上尊重「删错题=撤回所有下游曝光」。

红线（D20 防刷）：分享不产生光子/不进任何榜——本表是纯分发记录，
与 photon_transaction_history / XP / leaderboard 无任何写路径关联。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class SquadSharedError(BaseModel):
    """一次错题卡分享（引用 + 分享时刻快照；撤回 = 软删）。

    - ``error_id``：源错题引用（ON DELETE CASCADE：源错题硬删则分享
      记录随之消失；软删由服务层 liveness 联查处理）；
    - ``content``：可分享白名单快照（题目/科目/知识点/错因，见服务层
      ``_build_content_snapshot``；**不含**答案/解析——抄答案防线）；
    - ``mastery_level`` / ``mastery_delta`` / ``review_count``：分享时刻
      掌握度快照（delta 负数=错题诊断扣分，诚实呈现不粉饰）。
    """

    __tablename__ = "squad_shared_errors"

    group_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    error_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("error_records.id", ondelete="CASCADE"), nullable=False, index=True)
    sharer_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    content: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    snapshot_note: Mapped[str] = mapped_column(Text, nullable=True)  # 分享者附言（可空；同样过安全过滤）

    mastery_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mastery_delta: Mapped[float] = mapped_column(Float, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        # 同一张错题在同一小队同时至多一条在册分享（撤回后可再分享）。
        # 部分唯一索引 PG/SQLite 双方言支持，谓词与迁移 dc5share_20260922
        # 等价（照 D-COMM-4 uq_study_room_open_session 先例）。
        Index(
            "uq_squad_shared_error_active",
            "group_id",
            "error_id",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("idx_squad_shared_error_group_time", "group_id", "created_at"),
        Index("idx_squad_shared_error_sharer", "sharer_id", "group_id"),
    )

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"<SquadSharedError(id={self.id}, group_id={self.group_id}, error_id={self.error_id}, "
            f"sharer_id={self.sharer_id})>"
        )
