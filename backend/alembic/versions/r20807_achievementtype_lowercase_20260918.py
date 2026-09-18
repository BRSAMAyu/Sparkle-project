"""fix_achievementtype_enum_lowercase (R2-08-07)

Revision ID: r20807_20260918
Revises: 0150e391736a
Create Date: 2026-09-18

统一 achievementtype 枚举的大小写契约到引擎侧（SQLAlchemy 模型）的小写值。

背景（R2-08-07 / N-2 诊断）：
- 基线迁移建出的 PG 枚举 achievementtype 是 10 个大写值（无 planning）；
- 引擎模型 app/models/achievement.py 的 AchievementType 是 11 个小写值，
  且列声明带 values_callable（显式产出 e.value）→ 每次写入直发小写字符串；
- fresh 迁移库上成就子系统全量写入必炸（invalid input value for enum
  achievementtype）；dev 库靠 21 值污染枚举（10 大写+10 小写+planning）掩盖。

方向取舍：PostgreSQL 无法从枚举删除值，"大写改小写"只能整型重建。选择把
DB 收敛到引擎小写契约（11 值，含 planning），原因：
1. 引擎/API/seeds 全链已按小写产消（API payload 与移动端契约不变）；
2. 大写值从未被引擎成功写入过（fresh 库写入即炸），无真实数据依赖；
3. 同库同表 rarity 等枚举走 SQLAlchemy 默认（member NAME，本 repo 模型
   成员名即大写）之外，业务产消面统一小写，本迁移消除唯一的反例。

行数据兼容：USING lower(type::text) 把假想存在的大写存量行一并收敛到
小写；planning 行原样保留（新枚举包含该值）。

注意：dev 库存在 21 值污染枚举（基线外 revision 桩 t32_community_rooms），
不会走到本迁移；其收敛由一次性运维脚本/重建流程处理（见 round2/08-r2-fixes.md）。
"""
from typing import Sequence, Union

from alembic import op


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1（先收敛 planning 行到 milestone，再重建 10 值大写枚举并用 upper() 转回行值）"
#   verification_query: "SELECT unnest(enum_range(NULL::achievementtype));"
#   owner: "backend"
#   ticket: "R2-08-07"

revision: str = 'r20807_20260918'
down_revision: Union[str, None] = '0150e391736a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_LOWERCASE_VALUES = (
    'milestone', 'streak', 'mastery', 'task_complete', 'hidden', 'social',
    'contract', 'study_time', 'node_explore', 'sprint', 'planning',
)

_UPPERCASE_VALUES = (
    'MILESTONE', 'STREAK', 'MASTERY', 'TASK_COMPLETE', 'HIDDEN', 'SOCIAL',
    'CONTRACT', 'STUDY_TIME', 'NODE_EXPLORE', 'SPRINT',
)


def _values_literal(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.execute(f"CREATE TYPE achievementtype_new AS ENUM ({_values_literal(_LOWERCASE_VALUES)})")
    op.execute(
        "ALTER TABLE achievements ALTER COLUMN type TYPE achievementtype_new "
        "USING lower(type::text)::achievementtype_new"
    )
    op.execute("DROP TYPE achievementtype")
    op.execute("ALTER TYPE achievementtype_new RENAME TO achievementtype")


def downgrade() -> None:
    # 大写契约没有 planning：先收敛该类型行到 milestone，避免转换失败。
    op.execute("UPDATE achievements SET type = 'milestone' WHERE type::text = 'planning'")
    op.execute(f"CREATE TYPE achievementtype_old AS ENUM ({_values_literal(_UPPERCASE_VALUES)})")
    op.execute(
        "ALTER TABLE achievements ALTER COLUMN type TYPE achievementtype_old "
        "USING upper(type::text)::achievementtype_old"
    )
    op.execute("DROP TYPE achievementtype")
    op.execute("ALTER TYPE achievementtype_old RENAME TO achievementtype")
