#!/usr/bin/env python3
"""db_debris_cleanup.py — dev 库 schema 碎片清理（29 张会话遗留整表 + tasks 三列 db-only 残留）。

背景（挂账来源）：
  round2 schema 一致性审计（commit b21dce46，报告
  docs/competition/2026-tmall-hackathon/系统审查/round2/schema-consistency-audit.md §三 P1 /
  §四处置 3）定性：dev 库 262 表 vs 迁移链 233 表，差值 29 张为 DB-only 会话遗留表
  （仓库内无迁移/模型/脚本 DDL 来源，疑为历次审查/探针会话 create_all 或手建产物，
  同实例 sparkle_rt02_probe / sparkle_repro_t42 残库可佐证）；另有 tasks 表三列
  （scheduled_at/timezone/version）迁移链从未创建（迁移链上 scheduled_at 仅存在于
  aurora_scheduled_wakes，不同表）、ORM/网关均无引用 → 历史 create_all/手改库残留。

清理清单唯一来源：
  本文件下方 DEBRIS_TABLES / DEBRIS_COLUMNS 誊抄自
  scripts/devtools/orm_migration_audit.py 的 WHITELIST_DB_ONLY_TABLES 与
  WHITELIST_COLUMNS 的 DB-only 子集（誊抄基线 main@b8f4e7d8，白名单登记于 b21dce46）。
  脚本只能删这份清单上明确列出的对象——清单外的任何对象受结构性保护，绝不可碰：
    1. 代码仅对常量内名字生成 DDL，无任何动态拼接目标；
    2. DROP TABLE 前检查入边依赖：若有白名单外表的 FK 或视图依赖 → 拒删该项
       （防止 CASCADE 波及主业务对象）；
    3. DROP COLUMN 不带 CASCADE（同表索引随列自动删除属表内行为，允许）。
  注意不清理白名单中另外三列（cards.archived_at / chat_messages.metadata /
  user_settings.accessibility_settings）：它们是迁移链上的 MIG-only 死列，删除必须走
  alembic drop 迁移（审计移交清单第 1 条），绝不能由本脚本动 DB。

用法：
  cd <repo-root>
  # 默认 dry-run：只读探测，列出将删的表/列 + 行数 + 磁盘占用估算
  /opt/homebrew/bin/python3.11 scripts/devtools/db_debris_cleanup.py
  # 实删（先在演练库验证过！交互式终端会要求输入目标库名确认）
  /opt/homebrew/bin/python3.11 scripts/devtools/db_debris_cleanup.py --apply
选项：--database-url / --apply / --non-interactive（演练/CI 用，跳过确认）
退出码：0 = 全部清理项已处理（含幂等空转）；1 = 存在被拒删项（依赖保护触发，需人工）；
        2 = 环境错误。

幂等性：全部语句带 IF EXISTS 且执行前后校验存在性，重复执行无害（第二次空转 exit 0）。
"""
from __future__ import annotations

import argparse
import importlib
import os
import re
import sys
import time
from dataclasses import dataclass, field

# dev 默认连接（与 scripts/devtools/orm_migration_audit.py 同源）；已设置的环境变量不覆盖。
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:sparkle_dev_pg_2026@localhost:5432/sparkle",
)

# ---------------- 清理清单（唯一授权范围；见模块 docstring 来源说明） ----------------
# 29 张 DB-only 会话遗留表（DB 领先迁移链/ORM = 仓库内无创建来源，audit b21dce46 登记）。
# 誊抄自 orm_migration_audit.py WHITELIST_DB_ONLY_TABLES（main@b8f4e7d8）。逐字母对齐，勿手改。
DEBRIS_TABLES: frozenset[str] = frozenset(
    {
        "agent_run_receipts",
        "agent_run_steps",
        "agent_runs",
        "billing_collection_approvals",
        "billing_entitlements",
        "billing_ledger",
        "billing_orders",
        "billing_subscriptions",
        "billing_webhook_events",
        "document_source_fragments",
        "document_source_versions",
        "knowledge_lineage_edges",
        "knowledge_lineage_epochs",
        "llm_attempt_lineages",
        "llm_usage_ledger",
        "material_citations",
        "memory_candidates",
        "memory_claims",
        "outbox_dead_letters",
        "outbox_deliveries",
        "room_invites",
        "room_members",
        "room_share_grants",
        "saga_instances",
        "source_acl_grants",
        "study_rooms",
        "task_command_compensations",
        "task_command_receipts",
        "user_memory_epochs",
    }
)
# DB-only 残留列（迁移链从未在 tasks 上创建过这三列，audit b21dce46 §三 P1）。
DEBRIS_COLUMNS: frozenset[tuple[str, str]] = frozenset(
    {
        ("tasks", "scheduled_at"),
        ("tasks", "timezone"),
        ("tasks", "version"),
    }
)

# 主业务表硬保护断言：tasks 是核心业务表，只允许按 DEBRIS_COLUMNS 删列，绝不允许整表删。
assert "tasks" not in DEBRIS_TABLES, "保护规则失效：tasks 不得出现在整表清理清单"
_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def _q(ident: str) -> str:
    """标识符白名单校验 + 引号包裹（清单是常量，这里只是纵深防御）。"""
    if not _IDENT_RE.match(ident):
        raise ValueError(f"非法标识符: {ident!r}")
    return f'"{ident}"'


def _pick_driver() -> str:
    """返回可用的 psycopg 驱动模块名（优先 v3，回退 v2），与审计脚本同构。"""
    try:
        importlib.import_module("psycopg")
        return "psycopg"
    except ImportError:
        importlib.import_module("psycopg2")
        return "psycopg2"


def _connect(db_url: str):
    driver = _pick_driver()
    url = db_url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    if driver == "psycopg":
        psycopg = importlib.import_module("psycopg")
        return psycopg.connect(url, connect_timeout=10)
    psycopg2 = importlib.import_module("psycopg2")
    return psycopg2.connect(url, connect_timeout=10)


def _db_name(db_url: str) -> str:
    return db_url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]


@dataclass
class Target:
    kind: str  # 'table' | 'column'
    table: str
    column: str | None
    exists: bool
    rows: int | None = None
    bytes_est: int | None = None
    refusals: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.table if self.kind == "table" else f"{self.table}.{self.column}"


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        "SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)
    )
    return bool(cur.fetchone()[0])


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s AND column_name=%s",
        (table, column),
    )
    return cur.fetchone() is not None


def _count_rows(cur, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {_q(table)}")  # noqa: S608 (表名来自常量白名单)
    return int(cur.fetchone()[0])


def _table_bytes(cur, table: str) -> int:
    cur.execute(
        "SELECT COALESCE(pg_total_relation_size(to_regclass(%s)), 0)",
        (f"public.{table}",),
    )
    return int(cur.fetchone()[0])


def _column_bytes_est(cur, table: str, column: str, rows: int) -> int:
    """列级磁盘估算：取样 10000 行求平均列宽 × 总行数（标注为估算值，非精确）。"""
    cur.execute(
        f"SELECT COALESCE(avg(pg_column_size(s.v)), 0) FROM "  # noqa: S608
        f"(SELECT {_q(column)} AS v FROM {_q(table)} LIMIT 10000) s"
    )
    avg = float(cur.fetchone()[0] or 0)
    return int(avg * max(rows, 0))


def _protected_dependents(cur, table: str) -> list[str]:
    """找白名单外表对本表的依赖（入边 FK + 视图/物化视图）。返回受保护依赖对象名。"""
    dependents: set[str] = set()
    cur.execute(
        "SELECT conrelid::regclass::text FROM pg_constraint "
        "WHERE contype='f' AND confrelid = to_regclass(%s) AND conrelid <> to_regclass(%s)",
        (f"public.{table}", f"public.{table}"),
    )
    dependents.update(r[0].split(".")[-1] for r in cur.fetchall())
    cur.execute(
        "SELECT DISTINCT r.ev_class::regclass::text FROM pg_depend d "
        "JOIN pg_rewrite r ON r.oid = d.objid "
        "WHERE d.refclassid='pg_class'::regclass AND d.refobjid = to_regclass(%s) "
        "  AND d.deptype='n' AND r.ev_class <> to_regclass(%s)",
        (f"public.{table}", f"public.{table}"),
    )
    dependents.update(r[0].split(".")[-1] for r in cur.fetchall())
    return sorted(d for d in dependents if d not in DEBRIS_TABLES)


def _protected_dependents_of_column(cur, table: str, column: str) -> list[str]:
    """找依赖该列的视图（FK 视列定义而定，列删走非 CASCADE，只需挡视图/物化视图）。"""
    cur.execute(
        "SELECT att.attnum FROM pg_attribute att "
        "JOIN pg_class cls ON cls.oid = att.attrelid "
        "WHERE cls.oid = to_regclass(%s) AND att.attname = %s",
        (f"public.{table}", column),
    )
    row = cur.fetchone()
    if row is None:
        return []
    attnum = row[0]
    cur.execute(
        "SELECT DISTINCT r.ev_class::regclass::text FROM pg_depend d "
        "JOIN pg_rewrite r ON r.oid = d.objid "
        "WHERE d.refclassid='pg_class'::regclass AND d.refobjid = to_regclass(%s) "
        f" AND d.refobjsubid = {int(attnum)} AND d.deptype='n' "  # noqa: S608 (int 强转后内插)
        "  AND r.ev_class <> to_regclass(%s)",
        (f"public.{table}", f"public.{table}"),
    )
    return sorted({r[0].split(".")[-1] for r in cur.fetchall()} - DEBRIS_TABLES)


def build_targets(conn) -> list[Target]:
    """只读探测全部清理项的存在性/行数/体积估算/依赖保护。"""
    targets: list[Target] = []
    with conn.cursor() as cur:
        for table in sorted(DEBRIS_TABLES):
            exists = _table_exists(cur, table)
            t = Target("table", table, None, exists)
            if exists:
                t.rows = _count_rows(cur, table)
                t.bytes_est = _table_bytes(cur, table)
                for dep in _protected_dependents(cur, table):
                    t.refusals.append(f"白名单外依赖对象: {dep}（FK 或视图），CASCADE 会波及 → 拒删")
            targets.append(t)
        for table, column in sorted(DEBRIS_COLUMNS):
            exists = _column_exists(cur, table, column)
            t = Target("column", table, column, exists)
            if exists:
                if not _table_exists(cur, table):
                    t.exists = False
                else:
                    t.rows = _count_rows(cur, table)
                    t.bytes_est = _column_bytes_est(cur, table, column, t.rows)
                    for dep in _protected_dependents_of_column(cur, table, column):
                        t.refusals.append(f"白名单外依赖对象: {dep}（视图引用该列）→ 拒删")
            targets.append(t)
    return targets


def _fmt_bytes(n: int | None) -> str:
    if n is None:
        return "-"
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024 or unit == "GiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n} B"


def print_plan(targets: list[Target], db: str) -> tuple[int, int, int]:
    """打印执行计划，返回 (现存待删项数, 拒删项数, 已缺席项数)。"""
    todo = [t for t in targets if t.exists]
    refused = [t for t in todo if t.refusals]
    gone = [t for t in targets if not t.exists]
    total_rows = sum(t.rows or 0 for t in todo if not t.refusals)
    total_bytes = sum(t.bytes_est or 0 for t in todo if not t.refusals)
    print(f"目标库: {db} ｜ 清理清单: {len(DEBRIS_TABLES)} 整表 + {len(DEBRIS_COLUMNS)} 列")
    print(f"现存待删 {len(todo)} 项（拒删 {len(refused)}，已缺席 {len(gone)}）｜ "
          f"可删行数合计 {total_rows} ｜ 可回收磁盘估算 {_fmt_bytes(total_bytes)}")
    print("-" * 88)
    for t in targets:
        if not t.exists:
            print(f"  [已缺席/幂等跳过] {t.kind:<6} {t.label}")
            continue
        tag = "拒删" if t.refusals else ("列" if t.kind == "column" else "表")
        size = _fmt_bytes(t.bytes_est)
        rows = "-" if t.rows is None else str(t.rows)
        print(f"  [{tag}] {t.kind:<6} {t.label:<38} rows={rows:<8} bytes≈{size:<12}", end="")
        if t.refusals:
            print("；".join(t.refusals), end="")
        print()
    print("-" * 88)
    return len(todo) - len(refused), len(refused), len(gone)


def apply_targets(conn, targets: list[Target]) -> int:
    """逐项删除，前后校验存在性，输出操作日志。返回拒删/失败项数。"""
    log = lambda msg: print(f"[{time.strftime('%H:%M:%S')}] {msg}")  # noqa: E731
    failed = 0
    dropped_tables = dropped_columns = 0
    with conn.cursor() as cur:
        for t in targets:
            if not t.exists:
                log(f"SKIP  {t.label:<38} 已不存在（幂等）")
                continue
            if t.refusals:
                log(f"REFUSE {t.label:<37} {'；'.join(t.refusals)}")
                failed += 1
                continue
            if t.kind == "table":
                sql = f"DROP TABLE IF EXISTS public.{_q(t.table)} CASCADE"  # noqa: S608
            else:
                sql = f"ALTER TABLE public.{_q(t.table)} DROP COLUMN IF EXISTS {_q(t.column)}"  # noqa: S608
            # 前置校验
            pre = _table_exists(cur, t.table) if t.kind == "table" else _column_exists(cur, t.table, t.column)
            if not pre:
                log(f"SKIP  {t.label:<38} 执行前复检已不存在（幂等）")
                continue
            cur.execute(sql)
            # 后置校验
            post = _table_exists(cur, t.table) if t.kind == "table" else _column_exists(cur, t.table, t.column)
            reclaimed = _table_bytes(cur, t.table) if t.kind == "column" else None
            if post:
                log(f"FAIL  {t.label:<38} 删除后仍存在！")
                failed += 1
                continue
            if t.kind == "table":
                dropped_tables += 1
                log(f"DROP  {t.label:<38} OK（rows={t.rows}, bytes≈{_fmt_bytes(t.bytes_est)}）")
            else:
                dropped_columns += 1
                log(f"DROP  {t.label:<38} OK（列估算 bytes≈{_fmt_bytes(t.bytes_est)}；"
                    f"表剩余体积 {_fmt_bytes(reclaimed)}）")
    conn.commit()
    print("=" * 88)
    print(f"完成：DROP TABLE ×{dropped_tables}，DROP COLUMN ×{dropped_columns}，拒删/失败 {failed}")
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database-url", default=os.environ["DATABASE_URL"],
                        help="目标库 URL（默认 dev 库 sparkle；演练时指向演练库）")
    parser.add_argument("--apply", action="store_true", help="实际执行删除（默认 dry-run 只读）")
    parser.add_argument("--non-interactive", action="store_true",
                        help="跳过交互确认（演练/CI 用；交互终端下 --apply 必须确认）")
    args = parser.parse_args()
    db = _db_name(args.database_url)

    conn = _connect(args.database_url)
    try:
        targets = build_targets(conn)
        allowed, refused, gone = print_plan(targets, db)

        if not args.apply:
            print(f"DRY-RUN（默认）：以上 {allowed} 项将被删除。确认无误后加 --apply 执行。")
            return 0

        if refused:
            print("存在拒删项（依赖保护触发）：--apply 只处理无拒删标记的项；请先人工核查上方拒删原因。")
        if not args.non_interactive and sys.stdin.isatty():
            answer = input(f"将对 {db} 实删 {allowed} 项，且不可回滚。输入目标库名确认: ").strip()
            if answer != db:
                print("库名不匹配，中止。", file=sys.stderr)
                return 2
        print(f"APPLY 到 {db} ...")
        failed = apply_targets(conn, targets)

        # 收尾复核：全部清理项应均已缺席
        remaining = [t.label for t in build_targets(conn) if t.exists and not t.refusals]
        if remaining:
            print(f"复核失败：仍存在 {len(remaining)} 项: {remaining}", file=sys.stderr)
            return 1
        print("复核通过：清单内对象已全部清理（或本就不在）。")
        return 1 if (failed or refused) else 0
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"环境错误: {exc}", file=sys.stderr)
        sys.exit(2)
