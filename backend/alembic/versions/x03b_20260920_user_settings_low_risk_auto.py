"""X-03 R2 返修 · user_settings.low_risk_auto_execute（授权门服务端真源）

Revision ID: x03b_20260920
Revises: x03_20260919
Create Date: 2026-09-20

R2 P2-3（客户端自授）返修：``user_auto_grant`` 的服务端真源落库——用户显式
授予的「低风险可逆命令自动执行」权限（ACTION §3）。proposal command path
（ActionCommandService._user_auto_grant）只读此列；默认 False 保守
（FV-02 ``safe_experiments_opt_out`` 同款先例），客户端/调用方零自授面。

单列 ``ALTER TABLE … ADD COLUMN``（NOT NULL + server_default false），
PG 与 sqlite 双方言兼容，upgrade/downgrade 对称。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "x03b_20260920"
down_revision: str | None = "x03_20260919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column(
            "low_risk_auto_execute",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "low_risk_auto_execute")
