#!/usr/bin/env python3
"""orm_migration_audit.py — ORM ↔ Alembic 迁移链 ↔ 实库 三方列集一致性审计（一次性 devtools）。

背景（系统性缺口，两次咬人）：
  1. gfix01：shared_resources 表 ORM 有 adoption_count 等 4 列而迁移链上没有
     （ORM 领先迁移）→ G8 收敛到迁移真值后游客模式 500（UndefinedColumn 毒化事务）。
  2. G2/G8：两个 agent 各自建迁移 parented 同一节点 → alembic 双头数周无人发现。
结论：三方一致性此前没有任何自动防线。本脚本把三方列集拉平做 diff，退出码非零
当且仅当存在白名单之外的漂移，可挂 CI / 提交前守卫。

三个事实源（Sources of Truth）：
  ORM       backend/app/models/ 全量 SQLAlchemy 模型（含 mixin、关联表；通过
            importlib 遍历 app.models.* 注册进 Base.metadata）。项目内事件监听
            （pii_encryption_listeners）只做数据级加密、不产生 DDL，无需特殊处理。
  MIGRATION 对 throwaway scratch 库（默认 sparkle_orm_audit_scratch，用后即删）
            从零 `alembic upgrade head` 重放整条迁移链后读 information_schema。
            不做静态文本解析——链上存在 op.execute 裸 SQL 与 inspector 内省迁移
            （如 5f2b9b3c0e6f），alembic --sql 离线模式跑不通；真重放语义最准，
            与 Makefile db-dump 既有工作流一致（它同样建 fresh 库重放后导出）。
  DB        实连 DATABASE_URL（默认 dev 库 sparkle），读 information_schema.columns。

为什么不用 alembic upgrade head --sql 静态推导：
  实测离线模式在 5f2b9b3c0e6f（create_event_outbox_tables）因 `inspect(bind)`
  直接抛 NoInspectionAvailable；且 op.execute 裸 SQL 需要真解析器。真重放让
  PostgreSQL 自己当解析器，语义与生产迁移完全一致。

diff 语义与定性：
  ORM-only   列/表只在 ORM → ORM 领先迁移 = 缺迁移（gfix01 类）。P0：SQLAlchemy
             默认 SELECT/INSERT 会带上这些列 → 运行时 UndefinedColumn。
  MIG-only   列/表只在迁移链 → 迁移领先 = 残留死列/死表（模型已删但迁移未删）。
             P1：不崩，但 schema.sql 快照与 ORM 语义漂移。
  DB-only    只在实库 → DB 领先 = 手改库 / 测试或脚本 create_all 产物。P1。

已知允许差异白名单（文档化于下，勿无脑扩充；新增须写明理由与登记日期）：
  - AGE 图数据库相关：ag_catalog / sparkle_galaxy 两个非 public schema 整体忽略
    （Apache AGE 顶点/边表由图引擎管理，不走 Alembic）。
  - alembic_version 表本身（迁移状态表，三方语义不同属正常）。
  - （2026-09-18 初次审计登记）dev 库 public schema 中由测试/脚本 create_all
    或历史手建、且 ORM 侧已声明但迁移链上不存在的整表——见审计报告
    docs/competition/2026-tmall-hackathon/系统审查/round2/schema-consistency-audit.md
    的处置结论；白名单只豁免"表存在性/列存在性报警噪音"，P0 UndefinedColumn
    风险仍如实列出。

用法：
  cd <repo-root>
  /opt/homebrew/bin/python3.11 scripts/devtools/orm_migration_audit.py
选项：--database-url / --scratch-db / --json / --verbose
退出码：0 = 三方一致（白名单外无漂移）；1 = 有漂移；2 = 环境错误。
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import pkgutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# dev 默认环境（与测试纪律一致的守卫值）；已设置的环境变量不覆盖。
os.environ.setdefault("SECRET_KEY", "rule-guard-secret-0123456789abcdef0")
os.environ.setdefault("JWT_SECRET", "rule-guard-jwt-0123456789abcdef0")
os.environ.setdefault("REDIS_URL", "redis://:sparkle_dev_redis_2026@localhost:6379/1")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:sparkle_dev_pg_2026@localhost:5432/sparkle",
)

DEFAULT_SCRATCH_DB = "sparkle_orm_audit_scratch"

# ---------------- 白名单（见模块 docstring；新增必须写理由+日期） ----------------
# 非 public schema 整体忽略（AGE 图引擎管理）。
IGNORED_SCHEMAS = {"ag_catalog", "sparkle_galaxy", "information_schema", "pg_catalog"}
# 迁移状态表：三方各语义不同，属正常。
IGNORED_TABLES = {"alembic_version"}
# (table, column) 级豁免：即使出现在某个 diff 桶也不算漂移。
# 2026-09-18 初次审计登记（round2，处置见 schema-consistency-audit.md）：
WHITELIST_COLUMNS: set[tuple[str, str]] = {
    # 迁移领先 ORM = 模型已删、迁移未删的死列（P1 挂账，无运行时风险）：
    ("cards", "archived_at"),
    ("chat_messages", "metadata"),
    ("user_settings", "accessibility_settings"),
    # DB 领先 = dev 库遗留列，ORM/迁移/网关三方均无引用（P1 挂账，可清理 DB 列）：
    ("tasks", "scheduled_at"),
    ("tasks", "timezone"),
    ("tasks", "version"),
}
# 表级豁免：整表只存在于某一方时豁免报警（仍会在报告中标注）。
# 2026-09-18 初次审计登记（round2，处置见 schema-consistency-audit.md）：
# ① 迁移链有而 ORM 无 —— 其中 5 张为 Go 网关 CQRS 读模型（gateway/internal/db/
#    query.sql 引用，Python ORM 有意不映射）；其余 12 张为退役 spine/projection
#    设计的死 schema（迁移领先，P1 挂账评估退役）。
WHITELIST_MIG_ONLY_TABLES: set[str] = {
    # 网关 CQRS（活）：
    "event_outbox",
    "event_store",
    "projection_snapshots",
    "processed_events",
    "projection_metadata",
    # 退役 spine / decision-contract 设计（死 schema，P1）：
    "aurora_policy_versions",
    "commitments",
    "event_sequence_counters",
    "focus_contracts",
    "identity_evidence",
    "insight_claims",
    "mastery_audit_log",
    "probe_outcomes",
    "release_approval_requests",
    "transition_decision_records",
    "user_scenario_states",
    "window_states",
}
# ② dev 库有而迁移链/ORM 均无 —— 29 张会话遗留表（疑似历次审查/探针会话或
#    手建 DDL 产物，仓库内无创建来源），P1 挂账清理；另有任务清单见审计报告。
WHITELIST_DB_ONLY_TABLES: set[str] = {
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
WHITELIST_ORM_ONLY_TABLES: set[str] = set()


def _pick_driver() -> str:
    """返回可用的 psycopg 驱动模块名（优先 v3，回退 v2）。"""
    try:
        importlib.import_module("psycopg")
        return "psycopg"
    except ImportError:
        importlib.import_module("psycopg2")
        return "psycopg2"


def _connect(db_url_or_name: str):
    """连 postgres URL 或（不含 :// 时视为）本机 sparkle 实例上的库名。"""
    driver = _pick_driver()
    if "://" not in db_url_or_name:
        db_url_or_name = (
            f"postgresql://postgres:sparkle_dev_pg_2026@localhost:5432/{db_url_or_name}"
        )
    db_url_or_name = db_url_or_name.replace("postgresql+psycopg2://", "postgresql://")
    db_url_or_name = db_url_or_name.replace("postgresql+psycopg://", "postgresql://")
    if driver == "psycopg":
        psycopg = importlib.import_module("psycopg")
        return psycopg.connect(db_url_or_name, connect_timeout=10)
    psycopg2 = importlib.import_module("psycopg2")
    return psycopg2.connect(db_url_or_name, connect_timeout=10)


def _sqlalchemy_url() -> str:
    """把 DATABASE_URL 归一为本机可用的 SQLAlchemy URL（驱动回退 psycopg2）。"""
    url = os.environ["DATABASE_URL"]
    if _pick_driver() == "psycopg2":
        url = url.replace("postgresql+psycopg://", "postgresql+psycopg2://")
    return url


def collect_orm_columns() -> dict[str, set[str]]:
    """import 全部 app.models.* 模块，取 Base.metadata 列集（含 mixin/关联表）。"""
    import app.models as models_pkg  # noqa: PLC0415  (延迟导入，先配好环境)
    from app.db.session import Base  # noqa: PLC0415

    for mod_info in pkgutil.iter_modules(models_pkg.__path__):
        importlib.import_module(f"app.models.{mod_info.name}")

    out: dict[str, set[str]] = {}
    for table_name, table in Base.metadata.tables.items():
        if table_name in IGNORED_TABLES:
            continue
        out[table_name] = {col.name for col in table.columns}
    return out


def collect_migration_columns(scratch_db: str, verbose: bool) -> dict[str, set[str]]:
    """建 throwaway 库重放整条迁移链，读 information_schema 得链终态列集。"""
    admin = _connect("postgres")
    admin.autocommit = True
    try:
        with admin.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{scratch_db}" WITH (FORCE)')  # noqa: S608
            cur.execute(f'CREATE DATABASE "{scratch_db}"')  # noqa: S608
    finally:
        admin.close()

    scratch_url = _sqlalchemy_url().rsplit("/", 1)[0] + f"/{scratch_db}"
    env = dict(os.environ)
    env["DATABASE_URL"] = scratch_url
    py = sys.executable
    proc = subprocess.run(
        [py, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout[-2000:], file=sys.stderr)
        print(proc.stderr[-2000:], file=sys.stderr)
        raise RuntimeError(f"scratch 库迁移重放失败（{scratch_db}），见上方 alembic 输出")

    try:
        conn = _connect(scratch_db)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT version_num FROM alembic_version")
                heads = [r[0] for r in cur.fetchall()]
                if len(heads) != 1:
                    raise RuntimeError(f"scratch 重放后 head 数异常: {heads}")
                if verbose:
                    print(f"[migration] scratch 重放完成，head={heads[0]}", file=sys.stderr)
                cur.execute(
                    "SELECT c.table_name, c.column_name FROM information_schema.columns c "
                    "JOIN information_schema.tables t "
                    "  ON c.table_schema = t.table_schema AND c.table_name = t.table_name "
                    "WHERE t.table_type = 'BASE TABLE' AND t.table_schema = 'public' "
                    "  AND c.table_schema = 'public'"
                )
                return _group(cur.fetchall())
        finally:
            conn.close()
    finally:
        admin = _connect("postgres")
        admin.autocommit = True
        try:
            with admin.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS "{scratch_db}" WITH (FORCE)')  # noqa: S608
        finally:
            admin.close()


def collect_db_columns(database_url: str) -> dict[str, set[str]]:
    """实连目标库读 public schema 基表列集（AGE 等非 public schema 在白名单忽略）。"""
    conn = _connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.table_name, c.column_name FROM information_schema.columns c "
                "JOIN information_schema.tables t "
                "  ON c.table_schema = t.table_schema AND c.table_name = t.table_name "
                "WHERE t.table_type = 'BASE TABLE' AND t.table_schema = 'public' "
                "  AND c.table_schema = 'public'"
            )
            return _group(cur.fetchall())
    finally:
        conn.close()


def _group(rows) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for table_name, column_name in rows:
        if table_name in IGNORED_TABLES:
            continue
        out.setdefault(table_name, set()).add(column_name)
    return out


def diff_tables(
    label_a: str,
    a: dict[str, set[str]],
    label_b: str,
    b: dict[str, set[str]],
) -> tuple[dict[str, set[str]], dict[str, set[str]], list[str], list[str]]:
    """按表分组 diff；返回 (a_only 列, b_only 列, 仅 a 存在的表, 仅 b 存在的表)。"""
    a_only: dict[str, set[str]] = {}
    b_only: dict[str, set[str]] = {}
    tables_only_a: list[str] = []
    tables_only_b: list[str] = []
    for name in sorted(set(a) | set(b)):
        ca, cb = a.get(name), b.get(name)
        if ca is not None and cb is None:
            tables_only_a.append(name)
            a_only[name] = set(ca)
            continue
        if ca is None and cb is not None:
            tables_only_b.append(name)
            b_only[name] = set(cb)
            continue
        only_a = ca - cb
        only_b = cb - ca
        if only_a:
            a_only[name] = only_a
        if only_b:
            b_only[name] = only_b
    return a_only, b_only, tables_only_a, tables_only_b


def _strip_wl(cols: dict[str, set[str]]) -> dict[str, set[str]]:
    return {
        t: {c for c in cs if (t, c) not in WHITELIST_COLUMNS}
        for t, cs in cols.items()
        if {c for c in cs if (t, c) not in WHITELIST_COLUMNS}
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database-url", default=os.environ["DATABASE_URL"])
    parser.add_argument("--scratch-db", default=DEFAULT_SCRATCH_DB)
    parser.add_argument("--json", action="store_true", help="输出 JSON（供守卫消费）")
    parser.add_argument("--skip-replay", action="store_true", help="跳过迁移重放（调试用）")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        print(f"[orm] repo={REPO_ROOT}", file=sys.stderr)

    orm = collect_orm_columns()
    if args.verbose:
        print(f"[orm] tables={len(orm)}", file=sys.stderr)

    mig: dict[str, set[str]] = {}
    if args.skip_replay:
        print("[migration] --skip-replay：迁移侧留空（调试模式）", file=sys.stderr)
    else:
        mig = collect_migration_columns(args.scratch_db, verbose=True)
        if args.verbose:
            print(f"[migration] tables={len(mig)}", file=sys.stderr)

    db = collect_db_columns(args.database_url)
    if args.verbose:
        print(f"[db] tables={len(db)}", file=sys.stderr)

    orm_vs_mig_a, orm_vs_mig_b, orm_only_tbls, mig_only_tbls = diff_tables("ORM", orm, "MIG", mig)
    mig_vs_db_a, mig_vs_db_b, _, db_only_tbls = diff_tables("MIG", mig, "DB", db)
    orm_vs_db_a, orm_vs_db_b, _, db_only_tbls_vs_orm = diff_tables("ORM", orm, "DB", db)

    # 白名单过滤
    orm_only_cols = _strip_wl(orm_vs_mig_a)
    mig_only_cols = _strip_wl(orm_vs_mig_b)
    db_only_cols_vs_mig = _strip_wl(mig_vs_db_b)
    db_only_cols_vs_orm = _strip_wl(orm_vs_db_b)

    # 整表级：只单侧存在的表（其全部列已在上面桶里，报告单列出来防止双重计数误导）。
    orm_only_tables = sorted(set(orm_only_tbls) - WHITELIST_ORM_ONLY_TABLES)
    mig_only_tables = sorted(set(mig_only_tbls) - WHITELIST_MIG_ONLY_TABLES)
    db_only_tables_mig = sorted(set(db_only_tbls) - WHITELIST_DB_ONLY_TABLES)
    db_only_tables_orm = sorted(set(db_only_tbls_vs_orm) - WHITELIST_DB_ONLY_TABLES)

    # 列级（仅双方都存在的表）再细分，避免整表列淹没真实列漂移。
    # 整表白名单里的表同样从列桶剔除（其列已随整表豁免，不重复计数）。
    def shared_only(
        cols: dict[str, set[str]],
        only_tables: set[str],
        whitelisted: set[str],
    ) -> dict[str, set[str]]:
        skip = only_tables | whitelisted
        return {t: cs for t, cs in cols.items() if t not in skip}

    orm_only_cols_shared = shared_only(orm_only_cols, set(orm_only_tbls), WHITELIST_ORM_ONLY_TABLES)
    mig_only_cols_shared = shared_only(mig_only_cols, set(mig_only_tbls), WHITELIST_MIG_ONLY_TABLES)
    db_only_cols_mig_shared = shared_only(
        db_only_cols_vs_mig, set(db_only_tbls), WHITELIST_DB_ONLY_TABLES
    )

    def fmt(cols: dict[str, set[str]]) -> list[str]:
        return [f"    {t}: {', '.join(sorted(cs))}" for t, cs in sorted(cols.items())]

    drift_total = (
        sum(len(v) for v in orm_only_cols_shared.values())
        + sum(len(v) for v in mig_only_cols_shared.values())
        + sum(len(v) for v in db_only_cols_mig_shared.values())
        + len(orm_only_tables)
        + len(mig_only_tables)
        + len(db_only_tables_mig)
    )

    if args.json:
        print(
            json.dumps(
                {
                    "drift_count": drift_total,
                    "orm_only_tables": orm_only_tables,
                    "migration_only_tables": mig_only_tables,
                    "db_only_tables_vs_migration": db_only_tables_mig,
                    "orm_only_columns_on_shared_tables": {
                        k: sorted(v) for k, v in orm_only_cols_shared.items()
                    },
                    "migration_only_columns_on_shared_tables": {
                        k: sorted(v) for k, v in mig_only_cols_shared.items()
                    },
                    "db_only_columns_on_shared_tables": {
                        k: sorted(v) for k, v in db_only_cols_mig_shared.items()
                    },
                    "db_only_columns_vs_orm_all": {
                        k: sorted(v) for k, v in db_only_cols_vs_orm.items()
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0 if drift_total == 0 else 1

    print("=" * 72)
    print("ORM ↔ 迁移链 ↔ 实库 三方列集审计")
    print(f"  ORM tables={len(orm)}  MIGRATION tables={len(mig)}  DB tables={len(db)}")
    print("=" * 72)

    print("\n[A] 整表漂移")
    print(f"  ORM 有而迁移链无（ORM 领先 = 整表缺迁移，若被查询则 P0）: {len(orm_only_tables)}")
    for t in orm_only_tables:
        print(f"    {t} ({len(orm[t])} 列)")
    print(f"  迁移链有而 ORM 无（迁移领先 = 死表/纯迁移 schema，P1）: {len(mig_only_tables)}")
    for t in mig_only_tables:
        print(f"    {t} ({len(mig[t])} 列)")
    print(f"  DB 有而迁移链无（DB 领先 = 手建/create_all 产物，P1）: {len(db_only_tables_mig)}")
    for t in db_only_tables_mig:
        print(f"    {t} ({len(db[t])} 列)")

    print("\n[B] 共享表上的列漂移")
    print(f"  [B1] ORM-only 列（缺迁移，P0 UndefinedColumn 风险）: "
          f"{sum(len(v) for v in orm_only_cols_shared.values())} 列 / "
          f"{len(orm_only_cols_shared)} 表")
    print("\n".join(fmt(orm_only_cols_shared)))
    print(f"  [B2] 迁移-only 列（残留死列，P1）: "
          f"{sum(len(v) for v in mig_only_cols_shared.values())} 列 / "
          f"{len(mig_only_cols_shared)} 表")
    print("\n".join(fmt(mig_only_cols_shared)))
    print(f"  [B3] DB-only 列 vs 迁移链（手改库，P1）: "
          f"{sum(len(v) for v in db_only_cols_mig_shared.values())} 列 / "
          f"{len(db_only_cols_mig_shared)} 表")
    print("\n".join(fmt(db_only_cols_mig_shared)))

    print("\n" + "=" * 72)
    if drift_total == 0:
        print("✅ 三方一致（白名单口径内无漂移）")
        return 0
    print(f"❌ 漂移总计 {drift_total} 项（整表 + 共享表列），退出码 1")
    print("   定性口径见脚本头注释；处置结论见 round2 审计报告。")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"环境错误: {exc}", file=sys.stderr)
        sys.exit(2)
