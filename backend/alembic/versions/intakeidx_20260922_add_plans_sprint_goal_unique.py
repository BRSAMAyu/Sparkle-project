"""INTAKE-IDX · plans 同目标部分唯一索引——intake 查询-创建竞态根治

Revision ID: intakeidx_20260922
Revises: x07_20260921
Create Date: 2026-09-22

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1"
    verification_query: "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_plans_user_sprint_goal_active';"
    backfill_plan: "收敛式——同目标活跃双计划保留最新（对齐
        ExamSprintIntakeService._find_reusable_sprint_plan 的 created_at DESC
        语义），旧者仅置 is_active=false：不删行、不改内容、不占配额（与配额
        语义一致），可随时人工恢复。存量违反组计数见
        v3-output/INTAKE-IDX/REPORT.md（执行前快照）。"
    owner: "INTAKE-IDX"

BP-7 后续（INTAKE 卡申报残留）：intake 的「同目标复用既有计划」此前只有
顺序重放语义——两个并发 intake 都可能在复用查询落空后各自走创建路径
（查询-创建竞态窗口）。本迁移在 DB 层关闸：

    UNIQUE INDEX uq_plans_user_sprint_goal_active
        ON plans (user_id, subject, target_date)
        WHERE type = 'SPRINT' AND is_active AND deleted_at IS NULL

设计要点：

- 键与谓词精确对齐 intake 的同目标同一性定义
  ``(user, SPRINT, subject, exam_date, is_active, 未软删)``（INTAKE 卡
  幂等语义），服务层撞索引时捕获 IntegrityError 回查复用（闭环）；
- 枚举字面量用 ``'SPRINT'``：``Enum(PlanType)`` 未给 values_callable 时
  持久化的是成员名，与基线 schema ``plantype AS ENUM ('SPRINT','GROWTH')``
  及 gateway schema.sql 一致；
- subject/target_date 为 NULL 的行不参与：PG/SQLite 唯一索引中 NULL 互异
  （非冲刺场景、无考试日的计划零影响）；GROWTH 类型被谓词排除（intake
  幂等语义只定义在 SPRINT 上，收敛半径最小化）；
- 索引同时声明 ``postgresql_where`` 与 ``sqlite_where``（同一谓词），模型
  元数据（app/models/plan.py）与迁移保持一字不差，sqlite 测试基座
  create_all 后语义一致；
- SQLite 无 DISTINCT ON，收敛用 EXISTS 相关子查询，两方言各自渲染。

downgrade 只删索引；已收敛的行不自动回滚（数据收敛是单向的、非破坏性，
恢复属人工操作）。
"""

from __future__ import annotations

import logging
from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "intakeidx_20260922"
down_revision: str | None = "x07_20260921"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "plans"
_INDEX = "uq_plans_user_sprint_goal_active"
# 同目标同一性谓词（对齐 _find_reusable_sprint_plan；'SPRINT' 为 Enum 成员名）
_GOAL_PREDICATE = "type = 'SPRINT' AND is_active AND deleted_at IS NULL"
# SQLite EXISTS 分支的限定别名版本（语义与 _GOAL_PREDICATE 一致）
_GOAL_PREDICATE_NEWER = "newer.type = 'SPRINT' AND newer.is_active AND newer.deleted_at IS NULL"
# 键列非空才参与唯一性（NULL 在唯一索引中本就互异，收敛时同样跳过）
_KEYED = "subject IS NOT NULL AND target_date IS NOT NULL"


def _log(message: str) -> None:
    logging.getLogger("alembic.runtime.migration").info("INTAKE-IDX: %s", message)


def _count_duplicate_groups(bind) -> tuple[int, int]:
    """执行前现状计数：违反组数与超出唯一性的多余行数（写进迁移日志）。"""
    row = bind.execute(sa.text(f"""
            SELECT COUNT(*) AS groups, COALESCE(SUM(cnt - 1), 0) AS excess
            FROM (
                SELECT user_id, subject, target_date, COUNT(*) AS cnt
                FROM {_TABLE}
                WHERE {_GOAL_PREDICATE} AND {_KEYED}
                GROUP BY user_id, subject, target_date
                HAVING COUNT(*) > 1
            ) AS dup_groups
            """)).one()
    mapping = row._mapping
    return int(mapping["groups"] or 0), int(mapping["excess"] or 0)


def _converge_legacy_duplicates(bind) -> None:
    """存量收敛：每组同目标活跃双计划保留最新（created_at DESC, id DESC），
    旧者置 is_active=false。行不删除、内容不改，属非破坏性收敛。"""
    if bind.dialect.name == "postgresql":
        # DISTINCT ON 取每组最新 active；不在其内的行即为待收敛的旧者
        statement = f"""
            UPDATE {_TABLE}
            SET is_active = FALSE, updated_at = timezone('utc', now())
            WHERE {_GOAL_PREDICATE} AND {_KEYED}
              AND id NOT IN (
                  SELECT DISTINCT ON (user_id, subject, target_date) id
                  FROM {_TABLE}
                  WHERE {_GOAL_PREDICATE} AND {_KEYED}
                  ORDER BY user_id, subject, target_date, created_at DESC, id DESC
              )
        """
    else:
        # SQLite：EXISTS 相关子查询找"存在更新者"的行（created_at DESC, id DESC）
        statement = f"""
            UPDATE {_TABLE}
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE {_GOAL_PREDICATE} AND {_KEYED}
              AND EXISTS (
                  SELECT 1 FROM {_TABLE} AS newer
                  WHERE newer.user_id = {_TABLE}.user_id
                    AND newer.subject = {_TABLE}.subject
                    AND newer.target_date = {_TABLE}.target_date
                    AND {_GOAL_PREDICATE_NEWER}
                    AND (
                        newer.created_at > {_TABLE}.created_at
                        OR (newer.created_at = {_TABLE}.created_at AND newer.id > {_TABLE}.id)
                    )
              )
        """
    result = bind.execute(sa.text(statement))
    _log(f"converged {result.rowcount} legacy duplicate sprint plan(s) to is_active=false (kept newest per goal)")


def upgrade() -> None:
    bind = op.get_bind()

    groups, excess = _count_duplicate_groups(bind)
    if groups:
        _log(f"found {groups} duplicate goal group(s) ({excess} excess active row(s)); converging (keep newest)")
        _converge_legacy_duplicates(bind)
    else:
        _log("no duplicate goal groups found; nothing to converge")

    op.create_index(
        _INDEX,
        _TABLE,
        ["user_id", "subject", "target_date"],
        unique=True,
        postgresql_where=sa.text(_GOAL_PREDICATE),
        sqlite_where=sa.text(_GOAL_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE)
