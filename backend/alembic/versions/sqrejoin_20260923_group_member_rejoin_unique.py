"""SQUAD-REJOIN · group_members 软删+重加入唯一键收口——活跃行部分唯一索引

Revision ID: sqrejoin_20260923
Revises: photidem_20260923
Create Date: 2026-09-23

Migration Contract:
    type: reversible（downgrade 数据有前提，见下）
    rollback_plan: "alembic downgrade -1"
    verification_query: "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_group_member_active';"
    backfill_plan: "无需回填。原全列唯一约束 uq_group_member 下 (group_id,user_id)
        重复对不可能存在（演示库 2026-09-23 只读实测：693 行 / 693 去重对 / 软删
        0 行）；预检仅作 schema 漂移防御，发现违反组即 fail-loudly 拒绝执行——
        成员行承载用户可见统计（flame_contribution 等），不做静默自动手术。"
    owner: "SQUAD-REJOIN"

债务形状（v3-output/SQUAD-REJOIN/REPORT.md）：leave/kick/dissolve 全是软删
（deleted_at），但 ``uq_group_member(group_id, user_id)`` 全列唯一约束让软删行
依然占键——退队/被踢用户重加入时 join_group INSERT 撞键，IntegrityError 被误报
为「已是群组成员」（HTTP 400），**退出即永久无法回归**。

本迁移在 DB 层换闸：

    UNIQUE INDEX uq_group_member_active
        ON group_members (group_id, user_id)
        WHERE deleted_at IS NULL

- 谓词与全仓 not_deleted_filter() 读口径严格同域（成员列表/打卡门/贡献榜/
  冲刺聚合全部过滤软删行）；
- 与模型 app/models/community.py GroupMember.__table_args__ 声明一字不差
  （postgresql_where + sqlite_where 双 where，INTAKE-IDX 先例），
  sqlite 测试基座 create_all 后语义一致；
- 写侧配套（同卡）：join_group 查任意状态成员行，软删行复活原行
  （继承本人累计统计、角色复位 MEMBER），并发竞态由本索引仲裁；
- downgrade 重建全列唯一约束 uq_group_member——**数据前提**：库中不得存在
  同 (group_id,user_id) 多行（即已有过重加入）。若违反，batch 建约束会以
  IntegrityError 失败，属预期防护：先人工归并历史行再降级。

升级步骤：先删全列唯一约束（batch_alter_table，PG 渲染 ALTER TABLE DROP
CONSTRAINT，SQLite 走表重建），再建部分唯一索引（checkfirst 可重入）。
"""

from __future__ import annotations

import logging
from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "sqrejoin_20260923"
down_revision: str | None = "photidem_20260923"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "group_members"
_OLD_CONSTRAINT = "uq_group_member"
_INDEX = "uq_group_member_active"
_PREDICATE = "deleted_at IS NULL"


def _log(message: str) -> None:
    logging.getLogger("alembic.runtime.migration").info("SQUAD-REJOIN: %s", message)


def _assert_no_duplicate_pairs(bind) -> None:
    """预检：活跃 (group_id, user_id) 重复组必须为 0。

    原全列唯一约束在数学上排除重复对；若此处非零即 schema 漂移（约束曾被
    人为移除），迁移拒绝执行而非静默归并用户统计。"""
    row = bind.execute(
        sa.text(f"""
            SELECT COUNT(*) AS groups, COALESCE(SUM(cnt - 1), 0) AS excess
            FROM (
                SELECT group_id, user_id, COUNT(*) AS cnt
                FROM {_TABLE}
                GROUP BY group_id, user_id
                HAVING COUNT(*) > 1
            ) AS dup_groups
        """)
    ).one()
    mapping = row._mapping
    groups = int(mapping["groups"] or 0)
    if groups:
        raise RuntimeError(
            f"group_members 存在 {groups} 组 (group_id,user_id) 重复对"
            f"（超额 {int(mapping['excess'] or 0)} 行）——原全列唯一约束下不应出现，"
            "属 schema 漂移；请先人工归并成员历史行（承载用户统计，不自动手术），再重试迁移"
        )
    _log("pre-check passed: no duplicate (group_id,user_id) pairs")


def upgrade() -> None:
    bind = op.get_bind()
    _assert_no_duplicate_pairs(bind)

    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_constraint(_OLD_CONSTRAINT, type_="unique")

    op.create_index(
        _INDEX,
        _TABLE,
        ["group_id", "user_id"],
        unique=True,
        postgresql_where=sa.text(_PREDICATE),
        sqlite_where=sa.text(_PREDICATE),
    )
    _log("dropped uq_group_member full unique constraint; created uq_group_member_active partial unique index")


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE)
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.create_unique_constraint(_OLD_CONSTRAINT, ["group_id", "user_id"])
    _log("restored uq_group_member full unique constraint (requires no multi-row pairs, see docstring)")
