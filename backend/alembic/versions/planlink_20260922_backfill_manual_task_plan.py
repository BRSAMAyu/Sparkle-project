"""PLAN-LINK · 存量 NULL plan_id 手动任务回填（plan→task 关联链补齐）

Revision ID: planlink_20260922
Revises: 463923b1704e
Create Date: 2026-09-22

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1（按 tasks.guide_json['plan_link_backfill']
        回填标记精确还原：只回滚本迁移回填过的行，清 plan_id + 剥标记；intake/goal
        等原生带 plan_id 的任务永不被触碰）"
    verification_query: "SELECT COUNT(*) FROM tasks WHERE plan_id IS NOT NULL AND guide_json ? 'plan_link_backfill';"
    backfill_plan: "本迁移即回填——条件从严（见下），逐行带窗口守卫
        `AND plan_id IS NULL`，可重复执行（幂等）。回填行数见迁移日志与
        v3-output/PLAN-LINK/REPORT.md 存量统计。"
    owner: "PLAN-LINK"
    ticket: "P1-4 遗留根治卡 PLAN-LINK（LOOP1 证据 C1b）"

背景：手动创建的任务（POST /tasks、omnibar、agent 工具、错题模板实例化等）
plan_id 落 NULL，脱离计划域——按计划维度的进度聚合（计划完成率/里程碑视图）
对手动任务不可见（P1-4 仪表盘事故的根子）。运行时侧由 TaskService.create 的
默认关联兜住（PLAN-LINK 服务面修复），本迁移补存量。

回填条件（从严，四条全满足才回填）：
  1. task.plan_id IS NULL 且 task 未软删（deleted_at IS NULL）；
  2. 同 user 存在**恰好一个** active、未软删的 SPRINT 计划（type='SPRINT'，
     is_active，deleted_at IS NULL）——多个活跃冲刺计划并存时归属有歧义，
     宁缺勿错（不回填）；
  3. 任务创建时间在计划期内：task.created_at >= plan.created_at，
     且 plan.target_date 非空时 task.created_at 的日期 <= target_date
     （目标日期已过的计划不吸收后来任务）；
  4. 仅 SPRINT 优先域回填——goal plan 回落只在运行时默认关联生效
     （迁移侧只做无歧义、可精确判定的域）。

可逆性设计（为何用 guide_json 标记而非按窗口条件反推）：回填窗口
[plan.created_at, target_date] 与 intake day 卡的落窗完全重叠，downgrade 若按
「plan_id = 冲刺计划 ∧ 窗口内」反推会把 intake 原生任务一并误清。故 upgrade
在回填行的 guide_json 写入 plan_link_backfill 标记（bookkeeping 键，与
pause_state/stuck_runtime 等既有运行时键同级共存，应用层各消费面按已知键
取值、不遍历禁止），downgrade 只处理带标记的行：plan_id 仍等于标记内
plan_id 才清空（防覆盖迁移后用户的重新挂靠），随后剥除标记。零 schema 变更，
round-trip 后 schema 与数据语义均还原。

方言可移植性：全部逐行 Python 侧判定 + 绑定参数更新（PG JSONB 用显式
CAST，SQLite 基座直写 TEXT），不在 SQL 层做 JSON 谓词与日期运算；
时间/日期字段以 datetime/date 或 ISO 字符串两种形态防御性解析。
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any, Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "planlink_20260922"
down_revision: str | None = "463923b1704e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MARKER_KEY = "plan_link_backfill"
_REVISION = revision


def _log(message: str, *args: Any) -> None:
    logging.getLogger("alembic.runtime.migration").info("PLAN-LINK: %s", message % args if args else message)


def _as_datetime(value: Any) -> datetime | None:
    """PG 驱动返回 datetime，SQLite 返回 ISO 字符串——统一成 naive datetime。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    return None


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, (str, bytes)):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _in_plan_window(
    task_created_at: datetime | None, plan_created_at: datetime | None, target_date: date | None
) -> bool:
    """回填条件 3：任务创建时间落在计划期内（开始之后、目标日当天及之前）。"""
    if task_created_at is None or plan_created_at is None:
        return False  # 无法判定窗口 → 从严不回填
    if task_created_at < plan_created_at:
        return False
    if target_date is not None and task_created_at.date() > target_date:
        return False
    return True


def _update_task(bind, task_id: str, plan_id: str, guide_json_text: str) -> None:
    dialect = bind.dialect.name
    if dialect == "postgresql":
        bind.execute(
            sa.text(
                "UPDATE tasks SET plan_id = :pid, guide_json = CAST(:gj AS jsonb) "
                "WHERE id = :tid AND plan_id IS NULL"
            ),
            {"pid": plan_id, "gj": guide_json_text, "tid": task_id},
        )
    else:
        bind.execute(
            sa.text("UPDATE tasks SET plan_id = :pid, guide_json = :gj WHERE id = :tid AND plan_id IS NULL"),
            {"pid": plan_id, "gj": guide_json_text, "tid": task_id},
        )


def upgrade() -> None:
    bind = op.get_bind()

    # 候选集：NULL plan 的未删任务 × 其用户的 active 未删 SPRINT 计划。
    # SQLite 无布尔字面量歧义（is_active 存 1/0），PG 原生 boolean——裸列真值判定两方言通用。
    rows = bind.execute(sa.text("""
            SELECT t.id AS task_id, t.user_id AS user_id, t.created_at AS task_created_at,
                   t.guide_json AS guide_json, p.id AS plan_id,
                   p.created_at AS plan_created_at, p.target_date AS target_date
            FROM tasks t
            JOIN plans p ON p.user_id = t.user_id
            WHERE t.plan_id IS NULL
              AND t.deleted_at IS NULL
              AND p.type = 'SPRINT'
              AND p.is_active
              AND p.deleted_at IS NULL
            """)).mappings().all()

    plans_by_user: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        plans_by_user[row["user_id"]].append(dict(row))

    backfilled = 0
    skipped_multi_plan_users = 0
    skipped_out_of_window = 0
    for _user_id, user_rows in plans_by_user.items():
        distinct_plans = {row["plan_id"] for row in user_rows}
        if len(distinct_plans) != 1:
            # 条件 2：多个 active SPRINT 计划并存 → 归属歧义，宁缺勿错
            skipped_multi_plan_users += 1
            continue
        plan = user_rows[0]
        plan_id = plan["plan_id"]
        plan_created_at = _as_datetime(plan["plan_created_at"])
        target_date = _as_date(plan["target_date"])
        for row in user_rows:
            task_created_at = _as_datetime(row["task_created_at"])
            if not _in_plan_window(task_created_at, plan_created_at, target_date):
                skipped_out_of_window += 1
                continue
            guide_json = _as_dict(row["guide_json"])
            if _MARKER_KEY in guide_json:
                continue  # 已回填过（重放幂等）
            guide_json[_MARKER_KEY] = {
                "plan_id": str(plan_id),
                "migration": _REVISION,
                "backfilled_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
            _update_task(bind, str(row["task_id"]), str(plan_id), json.dumps(guide_json, ensure_ascii=False))
            backfilled += 1

    _log(
        "backfill done: rows=%d, users_skipped_multi_sprint_plan=%d, rows_skipped_out_of_window=%d",
        backfilled,
        skipped_multi_plan_users,
        skipped_out_of_window,
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 只取带回填标记的行（intake/goal 等原生任务无标记，永不被触碰）
    if dialect == "postgresql":
        rows = (
            bind.execute(
                sa.text("SELECT id, plan_id, guide_json FROM tasks WHERE guide_json ? :key"),
                {"key": _MARKER_KEY},
            )
            .mappings()
            .all()
        )
    else:
        rows = (
            bind.execute(
                sa.text("SELECT id, plan_id, guide_json FROM tasks WHERE guide_json LIKE :pattern"),
                {"pattern": f'%"{_MARKER_KEY}"%'},
            )
            .mappings()
            .all()
        )

    restored = 0
    for row in rows:
        guide_json = _as_dict(row["guide_json"])
        marker = _as_dict(guide_json.get(_MARKER_KEY))
        marked_plan_id = marker.get("plan_id")
        current_plan_id = row["plan_id"]
        # 防覆盖：迁移后用户/系统若已重新挂靠到别的计划，尊重现状，只剥标记
        plan_matches = current_plan_id is None or (
            marked_plan_id is not None and str(current_plan_id) == str(marked_plan_id)
        )
        guide_json.pop(_MARKER_KEY, None)
        if dialect == "postgresql":
            if plan_matches:
                bind.execute(
                    sa.text("UPDATE tasks SET plan_id = NULL, guide_json = CAST(:gj AS jsonb) WHERE id = :tid"),
                    {"gj": json.dumps(guide_json, ensure_ascii=False), "tid": str(row["id"])},
                )
            else:
                bind.execute(
                    sa.text("UPDATE tasks SET guide_json = CAST(:gj AS jsonb) WHERE id = :tid"),
                    {"gj": json.dumps(guide_json, ensure_ascii=False), "tid": str(row["id"])},
                )
        else:
            if plan_matches:
                bind.execute(
                    sa.text("UPDATE tasks SET plan_id = NULL, guide_json = :gj WHERE id = :tid"),
                    {"gj": json.dumps(guide_json, ensure_ascii=False), "tid": str(row["id"])},
                )
            else:
                bind.execute(
                    sa.text("UPDATE tasks SET guide_json = :gj WHERE id = :tid"),
                    {"gj": json.dumps(guide_json, ensure_ascii=False), "tid": str(row["id"])},
                )
        restored += 1

    _log("downgrade done: reverted_rows=%d (marker-guided, intake/native rows untouched)", restored)
