"""M-08 R2 · memory_goals.source_type 溯源列（additive single column）

Revision ID: m08_20260920
Revises: d05_20260919
Create Date: 2026-09-20

R2 验收 P2-2：``MemoryService.create_goal`` 一直接收 ``source_type`` 却不落库
（MemoryGoal 无该列），导致 ``plan_review_service._capture`` 的计划审批自动
捕获 goal（source_type="event"）在 U-03 provenance 面被错标「你告诉我的 /
已确认」。本迁移补上 goal 域缺失的溯源列，与 episodic_memories.source_type /
memory_preferences.source_type 同构：

- ``NULL``：既有行 + 用户公共创建路径（创建动作本身即用户陈述）→ told 桶；
- ``"event"`` 等系统捕获值 → provenance 面分流「系统写入」标签 + 置信降档
  （推断/捕获永不报「已确认」，M-01 对外口径）。

挂点声明：down_revision 挂主仓链尾 ``a05_20260919``（A-05 合入后的链尾；
worktree 基线 238abe22 时为 d05，Leader 合入时按实际链尾重挂——R2 delta 配方）。

词表：列值域不设 DB CHECK（X-01/X-05 同款纪律——封闭词表由应用层契约强制）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m08_20260920"
down_revision: str | None = "a05_20260919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("memory_goals", sa.Column("source_type", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("memory_goals", "source_type")
