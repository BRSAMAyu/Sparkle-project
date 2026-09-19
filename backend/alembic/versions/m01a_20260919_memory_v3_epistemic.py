"""Memory V3 (M-01)：epistemic class / episodic supersede 链 / memory epoch

Revision ID: m01a_20260919
Revises: ud01_20260919
Create Date: 2026-09-19

内容（全部为加法，可逆）：
1. episodic_memories.epistemic_class  —— V3 五类型的显式标注列
   （FACT/OBSERVATION/HYPOTHESIS/EXPERIENCE；NULL=按 lane+source_type 派生）。
   HYPOTHESIS 此前由 inferred lane 隐式承载、无显式字段（B-06 §1.2 缺口）。
   回填（R2-F1 收紧）：FACT 仅限用户陈述——user_confirmed lane（确认动作
   即用户陈述）或 direct_capture lane 且 source_type ∈ 用户陈述集
   （user_registered，见 memory_epistemic_contract.USER_STATEMENT_SOURCE_TYPES，
   本 SQL 须与其保持同步）；direct_capture 的机器写入行（chat_turn/analysis/
   reflection/error_analysis/practice_outcome 等，dev 库 184 行中 183 行）
   落 OBSERVATION——按契约自身定义它们是系统观察事件；其余 lane（含
   aurora_calibration_receipt 等未登记 lane）→HYPOTHESIS（保守档）。
   CONFIRMED_PREFERENCE 不入本列：由 memory_preferences/memory_goals 表
   成员资格承载（不建第二库铁律）。
2. episodic_memories.superseded_by_id —— 冲突裁决败者指向胜者的 supersede 链，
   与 memory_preferences.replaced_by_id 对称；配套索引。
3. user_memory_settings.memory_epoch / memory_epoch_bumped_at /
   memory_epoch_reason —— 每用户单调递增 epoch（MEMORY_V3 §6 删除→bump，
   缓存失效契约），M-07/C-07 消费。

验证：单迁移在本地 sqlite 基座隔离重放
（tests/unit/test_memory_v3_migration_sqlite.py，含 dev 库 source_type
构成的回填期望矩阵）；
主库只读纪律 —— 本迁移**不得**对主仓 PostgreSQL 直接 apply，随常规发布走
make sync-db / alembic upgrade head。加列均 nullable / 带 server_default，
对在跑旧代码零破坏（旧读写不感知新列）。

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1（drop 三组加法列+索引；回填为幂等 UPDATE，无数据损失）"
#   verification_query: "SELECT column_name FROM information_schema.columns WHERE table_name='episodic_memories' AND column_name IN ('epistemic_class','superseded_by_id');"
#   backfill_plan: "epistemic_class 按 lane+source_type CASE 回填（本迁移内联，幂等，仅填 NULL 行）；FACT 用户陈述集与 app/services/memory_epistemic_contract.py:USER_STATEMENT_SOURCE_TYPES 同步"
#   owner: "backend"
#   ticket: "V3-2 / M-01 Memory V3 实体映射与 Epistemic Types（R2-F1 返修）"
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

import app.models.base
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m01a_20260919"
down_revision: str | None = "e05_20260919"  # 合入窗口重挂: E-05 已先行 apply e05
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. episodic_memories.epistemic_class（nullable，旧行 NULL=派生）
    op.add_column(
        "episodic_memories",
        sa.Column("epistemic_class", sa.String(length=24), nullable=True),
    )
    # 2. episodic_memories.superseded_by_id（supersede 链，nullable）
    op.add_column(
        "episodic_memories",
        sa.Column("superseded_by_id", app.models.base.GUID(), nullable=True),
    )
    op.create_index(
        "idx_episodic_memories_epistemic_class",
        "episodic_memories",
        ["user_id", "epistemic_class"],
        unique=False,
    )
    op.create_index(
        "idx_episodic_memories_superseded_by_id",
        "episodic_memories",
        ["superseded_by_id"],
        unique=False,
    )
    # 回填（幂等：只填 NULL 行）。R2-F1 收紧：FACT 仅限用户陈述——
    # user_confirmed lane，或 direct_capture lane 且 source_type 为用户
    # 陈述集（dev 库 184 direct_capture 行里仅 user_registered=1 行是
    # 用户陈述，chat_turn=164/analysis=9/reflection=6/error_analysis=2/
    # practice_outcome=2 均为机器写入事件记录，按契约定义落 OBSERVATION）。
    # 用户陈述集须与 memory_epistemic_contract.USER_STATEMENT_SOURCE_TYPES 同步。
    op.execute(
        """
        UPDATE episodic_memories
        SET epistemic_class = CASE
            WHEN source_lane = 'user_confirmed' THEN 'FACT'
            WHEN source_lane = 'direct_capture'
                 AND source_type IN ('user_registered') THEN 'FACT'
            WHEN source_lane IN ('direct_capture', 'user_confirmed') THEN 'OBSERVATION'
            ELSE 'HYPOTHESIS'
        END
        WHERE epistemic_class IS NULL
        """
    )

    # 3. user_memory_settings.memory_epoch（默认 1 = 从未 bump）
    op.add_column(
        "user_memory_settings",
        sa.Column("memory_epoch", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "user_memory_settings",
        sa.Column("memory_epoch_bumped_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "user_memory_settings",
        sa.Column("memory_epoch_reason", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_memory_settings", "memory_epoch_reason")
    op.drop_column("user_memory_settings", "memory_epoch_bumped_at")
    op.drop_column("user_memory_settings", "memory_epoch")
    op.drop_index("idx_episodic_memories_superseded_by_id", table_name="episodic_memories")
    op.drop_index("idx_episodic_memories_epistemic_class", table_name="episodic_memories")
    op.drop_column("episodic_memories", "superseded_by_id")
    op.drop_column("episodic_memories", "epistemic_class")
