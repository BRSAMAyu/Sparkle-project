# WT342 — test_galaxy_concurrency「需 live Postgres」定界

日期：2026-09-25 ｜ 工号：wt342 ｜ 分支：wt342-galaxy-concurrency ｜ 等级：LIGHT

## 一、任务

wt330/340 登记 `backend/tests/unit/test_galaxy_concurrency.py` 3F3E「需 live Postgres」环境限制债。未知数：CI（Backend Tests 有 PG service）会不会红？本地 sqlite 下失败形态是什么？

## 二、机制判定（测试如何失败）

- 该文件**不经 conftest 的 sqlite `db_session` fixture**，直接 `from app.db.session import AsyncSessionLocal, engine`（应用侧引擎，绑 `settings.DATABASE_URL`）。
- **全文件原本无任何 skip 机制**（无 skipif / fixture 条件 / marker 门）→ 任何环境缺 PG/缺表都硬失败。
- 本地各卡所见失败形态（假信号，非产品回归）：sqlite 强制环境下 `no such table: user_node_status`；裸 worktree 默认 URL（postgresql+asyncpg://postgres:@sparkle_db:5432/sparkle，空密码）下 asyncpg 认证失败（ERR-IDEM-CONCUR/GRAPH-GRPC-SHAPE 报告同证）。
- 产品侧被测逻辑（`GalaxyService.update_node_mastery` revision 路径）是 PostgreSQL 专用原子 CTE（`FOR UPDATE`/`RETURNING`），SQLite 无行锁语义——"必须 PG"是测试的硬需求，非可绕装配问题。

## 三、CI 行为判定：**不会红，真跑且通过（有证据）**

Backend Tests（.github/workflows/ci.yml job `backend-test`）环境：
- `DATABASE_URL=postgresql://postgres:password@localhost:5432/sparkle_test`（AGE 镜像 step 托管 PG + Redis service）；该 job 本身不跑 alembic（`db-schema-check` 是独立 job）。
- **schema 在会话内由测试自己建**：`tests/test_migrations.py`（收集序在 tests/unit/ 之前，约 25% 进度处）对 sparkle_test 执行 `alembic upgrade head`——run 36015155771 日志 25% 处 `test_migrations` 5 项全 PASSED（含 `test_migration_idempotent_upgrade`/`test_critical_tables_exist`）为证。
- 该 run 于 51% 处被外部取消，`test_galaxy_concurrency`（按字母序在其后）未及执行——即 CI 从未观测到它的结果，这正是本卡的未知数。
- **本地同构复现闭环**：在 sparkle_db 容器内 `CREATE DATABASE wt342_galca7k`（独立库，未触碰应用库 sparkle）→ `alembic upgrade head` 建全 schema（镜像 CI test_migrations 行为）→ 以 CI 同构 env（postgres URL + Redis）跑该文件：**3/3 passed**（1.0s）。teardown 后 `galaxy_concurrency_test` 前缀行数 0（cleanup fixture 有效）。

## 四、修复（测试装配层，非产品）

按 `test_db_partitioning.py` / `test_document_retrieval_isolation.py` 既有先例，给文件加**整模块环境定界门**（`pytest.mark.postgres` + 三判据 module-level skip）：
1. DATABASE_URL 指向演示库（库名==sparkle）→ TEST-DBGUARD 跳过（安全纪律同 _dbguard.py）；
2. 后端非 PostgreSQL（`make_url().get_backend_name()`）→ 跳过并写明 C1 行锁语义硬需求与 CI 不受影响；
3. live PG 探活（SELECT 1）失败 → 跳过并附指路（*_test 库 + test_migrations 先行建表）。
另：文件历史即不满足 black（存量），随本次触碰一并 black(120) 格式化（纯空白/折行，语义零变化）。产品代码零改动。

四形态验证矩阵：

| 形态 | 结果 |
|---|---|
| CI 同构（live PG wt342_galca7k 全 schema + Redis） | 3 passed |
| sqlite 强制（worker 标准环境） | 1 skipped（方言判据，理由写明） |
| 裸 worktree 默认（sparkle 形状 URL） | 1 skipped（TEST-DBGUARD 判据） |
| PG 后端但不可达（错端口） | 1 skipped（探活判据） |

## 五、回归

- galaxy 相邻批（标准 sqlite 环境）：unit 10 文件 + services 3 + api 2 + test_api 3 + integration 1 = **110 passed**（含 test_galaxy_concurrency 自身准确 skip；error_book_galaxy_mastery_sync 21 passed）。
- 收工门：`run_all_rule_guards.sh` **exit 0（83 rules）**；冷 mypy **1278 = 基线 1278**（零漂移，tests/ 不在 `mypy app` 范围）；被碰文件 ruff 0 + black clean。

## 六、定界结论（一句话）

CI Backend Tests 中该文件会真跑且通过（schema 由同会话 test_migrations 提前建好）；本地 3F3E 是"无 skip 机制 + 非PG环境"的假信号，已加三判据整模块 skip 门收口——CI 路径不变，本地不再误导。

## 七、Forbidden 区核查

未触碰应用库 sparkle（仅 CREATE/DROP 自己的 wt342_galca7k）；未改 galaxy 业务逻辑（纯测试文件 + 格式化）；未碰 mobile 业务代码（仅拷贝 gitignored gen）；未重启任何容器；主仓只读。
