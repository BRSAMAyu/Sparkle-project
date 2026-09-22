"""D-REDEEM · 兑换码付费闭环 —— redeem_codes 表 + users.entitlement_expires_at

Revision ID: rd01_20260922
Revises: x07_20260921
Create Date: 2026-09-22

背景：盈利缺口=支付通道（DL-D-R1 MONETIZATION §5 第 0 期）。参赛期以兑换码
演示完整付费闭环：admin 面批量生成 SPARK-XXXX 码 → app 内核销 →
users.entitlement 升 pro（带到期）。

变更（两段，均加法安全）：
1. 新表 ``redeem_codes``：
   - ``code_hash`` 唯一键存归一化明文的域分隔 SHA-256 —— **明文永不落库
     不进日志**，仅 admin 生成响应返回一次；
   - ``tier``/'pro'、``duration_days``、``max_uses``/``used_count``、
     ``used_by``/``used_at``、``created_by``、``batch_id``、``expires_at``；
   - 原子核销 = 服务层条件 UPDATE（``used_count < max_uses`` 行内守卫），
     并发同码只成功 max_uses 次（防双花），应用层保证、不加 DB CHECK
     （与 execution_intent create_constraint=False 先例一致）。
2. ``users.entitlement_expires_at``（TIMESTAMP NULL，NULL = 永久）：
   - 存量行全部 NULL → 有效判级与既有语义零变化（手工/历史授予的永久 pro
     不受影响）；
   - 非空且已过 → 判级降 free（到期降级）。降级方向恒为 pro→free，与
     ent01「宁降不升」fail-safe 同向：判级故障最多丢权益、绝不送成本。
     判级真源 app/core/entitlement.entitlement_effective；网关同语义
     IsProEntitlementEffective。

验证：sqlite 隔离基座重放（tests 单迁移契约，主库只读纪律）；主库只写纪律
—— 本迁移对共享 dev DB 仅允许 alembic upgrade 这一条写路径。

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name='users' AND column_name='entitlement_expires_at';"
#   backfill_plan: "n/a（新表零存量行；新列 NULL = 永久，无需回填）"
#   owner: "backend"
#   ticket: "D-REDEEM（参赛付费闭环演示）"
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

# revision identifiers, used by Alembic.
revision: str = "rd01_20260922"
down_revision: str | None = "x07_20260921"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "redeem_codes",
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("code_prefix", sa.String(length=16), nullable=True),
        sa.Column("tier", sa.String(length=32), server_default=sa.text("'pro'"), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("max_uses", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("used_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("used_by", GUID(), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", GUID(), nullable=True),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        # BaseModel 公共列（id/created_at/updated_at/deleted_at）
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"], name="fk_redeem_codes_used_by_users"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_redeem_codes_created_by_users"),
    )
    op.create_index("ix_redeem_codes_code_hash", "redeem_codes", ["code_hash"], unique=True)
    op.create_index("idx_redeem_codes_batch", "redeem_codes", ["batch_id", "created_at"])

    op.add_column("users", sa.Column("entitlement_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "entitlement_expires_at")
    op.drop_index("idx_redeem_codes_batch", table_name="redeem_codes")
    op.drop_index("ix_redeem_codes_code_hash", table_name="redeem_codes")
    op.drop_table("redeem_codes")
