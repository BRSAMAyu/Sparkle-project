"""
Core: <execution|infra>
Phase: <execute>
Stage: D-REDEEM

兑换码模型 —— 参赛期付费闭环（MONETIZATION 第 0 期）。

安全约定（红线）：
- **明文永不落库**：``code_hash`` 只存 SHA-256（域分隔前缀见
  app/services/redeem_service.py）；明文仅在 admin 生成响应中出现一次。
- ``code_prefix`` 是展示用前缀（如 ``SPARK-AB3D``，缺末段），供客服/对账
  定位批次，不含完整明文。
- 原子核销：核销走条件 UPDATE（``used_count < max_uses`` 行内守卫），
  并发同码只成功 max_uses 次；服务层不得先读后写。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel


class RedeemCode(BaseModel):
    """兑换码（批次生成 → 用户核销 → entitlement 升级）。"""

    __tablename__ = "redeem_codes"

    # 哈希唯一键（归一化明文的域分隔 SHA-256，hex 64）
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # 展示用前缀（缺末段，非明文）
    code_prefix: Mapped[str] = mapped_column(String(16), nullable=True)

    # 权益面：核销成功后授予的档位（值域与 users.entitlement 同约定 'free'|'pro'）
    tier: Mapped[str] = mapped_column(String(32), default="pro", nullable=False, server_default="pro")
    # 授予时长（天）；核销叠加语义见服务层
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # 核销状态（单用户 1 次：max_uses=1 + used_by/used_at）
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    used_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    used_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 审计面
    created_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # 码有效期（NULL = 永不过期）
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("idx_redeem_codes_batch", "batch_id", "created_at"),)

    def __repr__(self):
        return f"<RedeemCode(prefix={self.code_prefix}, batch={self.batch_id}, used={self.used_count}/{self.max_uses})>"
