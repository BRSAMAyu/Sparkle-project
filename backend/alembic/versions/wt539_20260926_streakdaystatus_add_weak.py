"""V3-FIX-259 · streakdaystatus 枚举补 'weak'（引擎活体写 WEAK 的 DB 对齐）

Revision ID: wt539_20260926
Revises: j06_20260925
Create Date: 2026-09-26

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：weak 行收敛为 active（weak 语义=
        活动日但低于质量阈，仍是真实活动），再整型重建三值枚举
        （r20807_20260918 模板；PG 无法从枚举删除值）。"
    verification_query: "SELECT unnest(enum_range(NULL::streakdaystatus));"
    backfill_plan: "无回填（值集补齐，存量行不动）。"
    owner: "wt539 (fleet impl)"
    ticket: "V3-FIX-259（wt534 B-06 实体真源审计 §2.1）——
        StreakDayStatus.WEAK 四层断链之 DB 层：f2b3c4d5e6f7 建的 PG 原生
        枚举只有 active/frozen/missed 三值，而引擎
        achievement_engine._update_streak_stats 在质量分 <0.4 时活体写
        StreakDayStatus.WEAK，迁移库上触发 enum DataError 且曾被引擎
        except 以 debug 级静默吞掉（质量连胜静默死亡 + 会话投毒）。
        本迁移只补值集；engine 写面 savepoint 隔离与 wire/mobile 兜底
        由同卡其余修序承担。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "wt539_20260926"
down_revision: Union[str, None] = "f258_20260925"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PG 12+ 允许事务内 ADD VALUE（本迁移不使用新值，无同事务使用限制）。
    op.execute("ALTER TYPE streakdaystatus ADD VALUE IF NOT EXISTS 'weak'")


def downgrade() -> None:
    # PG 无法从枚举删除值：weak 行收敛为 active（仍是真实活动日）后整型重建。
    op.execute("UPDATE user_streak_days SET status = 'active' WHERE status = 'weak'")
    op.execute("CREATE TYPE streakdaystatus_without_weak AS ENUM ('active', 'frozen', 'missed')")
    op.execute(
        "ALTER TABLE user_streak_days ALTER COLUMN status TYPE streakdaystatus_without_weak "
        "USING status::text::streakdaystatus_without_weak"
    )
    op.execute("DROP TYPE streakdaystatus")
    op.execute("ALTER TYPE streakdaystatus_without_weak RENAME TO streakdaystatus")
