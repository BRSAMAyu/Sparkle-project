# TEST-DBGUARD 收工报告：pytest 数据库连接隔离审计与防泔染守卫

- Worker 卡：TEST-DBGUARD ｜ worktree：`wt148` ｜ 基线：`1d79842c`
- 交付物：本报告 + `changes.patch`（同目录）
- 红线遵守：未 commit/push；演示 DB 零连接（自测全用假串+死端口 :59999）；worktree 无 .env

---

## ① 连接面审计表（fixture → 串来源 → 写库与否）

配置链路事实（`backend/app/config/settings.py`）：
pydantic Settings 按 `repo根/.env → backend/.env → backend/app/.env` 顺序加载；`DATABASE_URL` 为空时由 `POSTGRES_*` 默认值构造（库名默认 **sparkle**，host `sparkle_db` 在宿主机规范化为 `127.0.0.1`）。即：**主仓跑测试 = settings.DATABASE_URL 指向演示库**；**裸 worktree = 同形状串但空密码（必认证失败）**。全局引擎 `app/db/session.py::engine` 于 import 期绑定该 URL（惰性连接）。

| # | 入口 | 串来源 | 真建连 | 写库 | 风险评级 |
|---|---|---|---|---|---|
| 1 | `backend/tests/conftest.py::db_session/db/test_user`（unit 域默认） | 硬编码 `sqlite+aiosqlite:///:memory:` | 是 | 内存 sqlite，进程即焚 | 无 |
| 2 | `backend/tests/integration/conftest.py::db_session/test_user` | **`settings.DATABASE_URL`** | 是 | 是（测试用户/KnowledgeNode/通知/成就） | **事故入口**：主仓 .env → 直写演示库（`journey_milestone_*` 账号、`node-*` 节点即经此泄漏，见 `tests/integration/test_north_star_journey.py::test_milestone_achievement_unlock_notification` 与 `tests/unit/test_achievement_event_consumer.py::test_milestone_notification_contains_personalized_numbers`） |
| 3 | `backend/tests/test_migrations.py` | `settings.DATABASE_URL` | 是 | **DDL 级**（`alembic upgrade head`） | **最高危**：库名以 postgres 开头即执行，可直接改演示库 schema |
| 4 | `backend/tests/test_db_partitioning.py` | 全局 `AsyncSessionLocal` | 是（**import 期**探活 + 用例 INSERT 用户行） | 是 | 主仓 .env → 演示库写用户 |
| 5 | `tests/integration/test_event_pipeline_integration.py`、`test_p0_fixes_simple.py`、`test_p0_fixes_validation.py` | 全局 `AsyncSessionLocal` | 是 | 是 | 同 #4（worktree 下连接失败自然报错） |
| 6 | `tests/integration/test_plan_state_jsonb_pg.py::pg_sessions` | `settings.DATABASE_URL`（非 PG 即 skip） | 是 | 是（`r2g2_p101_*` 用户+plan，finally 自清） | 主仓 .env → 演示库短暂写入 |
| 7 | `tests/integration/test_shop_acceptance.py::main()` | `settings.DATABASE_URL` | 是 | 是 | **pytest 不触发**（`test_1..test_7` 走根 conftest 的 sqlite `db` fixture；`main()` 仅 `__main__`） |
| 8 | `tests/services/test_document_retrieval_isolation.py` | `settings.DATABASE_URL` | 是 | 是（pgvector 数据） | `E05_LIVE=1` 显式 opt-in；声明需 PG 库但未防演示库 |
| 9 | `tests_e2e/conftest.py::test_engine/db_session` | `TEST_DATABASE_URL` env，**默认硬编码 `…@localhost:5432/sparkle`** | 是 | 是（建表+写） | **默认值即演示库+默认密码**（compose `change-me` 可直接连通）→ 已修 |
| 10 | `tests_e2e/test_integration.py`、`test_full_e2e.py` | `settings.DATABASE_URL` | 是 | 是 | 同类风险 → 已纳入 tests_e2e 门第二查 |

安全面（审计确认无风险，未改动）：根 conftest 之外的全部自建 engine 测试均为硬编码 sqlite（`test_analytics_service`、`test_error_mastery_*`、`stage35/38`、`community`、`photon`、`shop_idempotency`、`thermodynamics`、`phase5_orchestrator`、`x09`、`v3_action_eval/dbfixture`、`api/*`、`services/*_isolation`）；monkeypatch `AsyncSessionLocal` 的 unit 家族（stage34 consumers 等）注入 sqlite session，安全；`test_credential_routing` 仅本地构造 Settings 对象（假串不建连、不污染进程 settings），与守卫无交互。api/golden/unit-spine 三个子 conftest 均无真连。

## ② 守卫方案与设计论证

**判定器单一事实源**：新增 `backend/tests/_dbguard.py`（零凭据、零连接，纯字符串解析 + .env 键扫描）。
- `is_demo_db_url(url)`：postgres 系 **且 库名恰为 `sparkle`**（compose `POSTGRES_DB` 默认值=演示库；测试库约定 `sparkle_test`/`*_test`/`*_e2e`，CI `e2e-tests.yml` 已用 `sparkle_test`）。
- `explicit_db_config()`：env（DATABASE_URL/POSTGRES_*/DB_*）或任一 .env 文件出现非空 DB 键才算"显式配置"。
- 白名单：`SPARKLE_TEST_DB_ALLOW_NAMED_SPARKLE=1`（仅 CI 一次性容器栈；把会话门拒绝降级为告警）。

**三层接入（纵深防御）**：
1. **会话门**（root conftest `pytest_configure`）：demo 形状 **且** 显式配置 → `pytest.UsageError` 整进程拒跑（exit 4）。裸 worktree（无 .env）的同形状默认串 → 只打印 2 行告警，**行为零变化**（空密码必认证失败，该场景需真库的测试本就按原样失败/跳过）。
2. **域守卫**（真实建连点自查）：integration `db_session` fixture → `pytest.fail`（该 fixture 职责就是真写，无条件拒）；`test_migrations._sync_database_url` → 连接前 `pytest.skip`（migration 会 DDL，绝不落演示库）；`test_db_partitioning` → import 期探活**之前**模块级 skip；`tests_e2e/conftest.py` 会话门（独立 rootdir 不加载 backend conftest）双查 `TEST_DATABASE_URL` **和** `settings.DATABASE_URL`。
3. **默认值纠偏**：tests_e2e 默认库 `sparkle` → `sparkle_test`（与 `run_e2e_tests.py` 建库脚本一致）。

**为何不误伤合法测试**：
- 为什么不用"fixture 强制覆盖 DATABASE_URL 到 sqlite"：integration/迁移/PG 专属测试的语义就是"需要真库"（JSONB/pgvector/真并发/与 gRPC 共库），覆盖成 sqlite 会把"连不上"变成"静默跳过或假绿"，违反零行为变化红线。
- unit 域（硬编码 sqlite）不读 DATABASE_URL，完全无感；worktree 无 .env 的全舰队常态 = 告警一行 + 原行为。
- 合法 integration 用法 = 指向 `*_test` 专属库（如本卡回归用的死端口 `sparkle_test` 串，8F/2P/2E 与基线逐项一致，证明守卫不干预合法真库路径）。
- CI：`e2e-tests.yml` 已用 `sparkle_test` 不受影响；`e2e-smoke.yml`（暂停态，一次性容器栈库名沿用 sparkle）→ 已在 workflow 显式加白名单变量并注释原因。
- 无静默逃生门：白名单是显式具名 env，本地误设即事故场景本身，且有据可查。

## ③ 守卫自测（三态 + 纵深，全部假串零真连）

| 态 | 环境 | 期望 | 实测 |
|---|---|---|---|
| 0 | 判定器单元断言（7 组 URL 形状 + .env 三情形：有 DATABASE_URL / 仅注释+空值 / 无文件） | 全对 | ✅ 通过 |
| A | `DATABASE_URL=…@127.0.0.1:59999/sparkle_test`（test 库串） | 正常跑 | ✅ 4 passed，exit 0，无横幅 |
| B | `DATABASE_URL=…:fake-never-connect@127.0.0.1:5432/sparkle`（演示库假串） | 拒跑 | ✅ UsageError，exit 4，消息含修复指引，零连接尝试 |
| C | 裸 worktree（无任何 DB 变量/.env） | 告警+原行为 | ✅ 告警横幅 + 4 passed，exit 0 |
| D | 演示串 + `SPARKLE_TEST_DB_ALLOW_NAMED_SPARKLE=1` | 会话门降级、域守卫仍拦 | ✅ 事故同款用例被 fixture 守卫拦成 error，11 条 TEST-DBGUARD 消息 |
| E | tests_e2e：默认 / `TEST_DATABASE_URL`=演示串 / env `DATABASE_URL`=演示串 | 过门 / 拒 / 拒 | ✅ 36 collected（+1 存量错误） / exit 4 / exit 4 |

## ④ 回归矩阵（对比法，零新增失败）

| 家族 | 环境 | 基线（改动前/克隆 HEAD） | 改动后 | 差异 |
|---|---|---|---|---|
| `tests/unit/test_achievement_event_consumer.py`（事故文件族，根 conftest sqlite） | 裸 worktree | 4 passed | 4 passed | 0 |
| 同上 | 显式 test 库串（死端口） | 4 passed | 4 passed | 0 |
| `tests/integration/test_north_star_journey.py`（事故入口族，integration 真库 fixture） | 显式 test 库串（死端口 :59999，gen 已生成） | 8 failed / 2 passed / 2 errors | 8 failed / 2 passed / 2 errors | **逐项一致** |
| `tests/integration/test_event_pipeline_integration.py`（AsyncSessionLocal 向量） | 同上 | 2 skipped | 2 skipped | 0 |
| `tests/test_migrations.py`（守卫路径） | 裸 worktree | 3 passed / 4 skipped（克隆基线） | 3 passed / 4 skipped | 0（4 skip 现由守卫在连接前给出） |
| `tests/test_db_partitioning.py`（守卫路径） | 裸 worktree | 1 skipped（克隆基线） | 1 skipped | 0（现跳过在探活连接之前） |
| `tests_e2e`（collect-only） | 默认 | 36 collected + 1 存量 import 错误 | 同左 | 0（门不干预） |

说明：north_star 家族的 8 个 failed 在"主仓 .env（真实密码）"环境下历史上会变成**通过但写演示库**；守卫后该场景 = 会话门 exit 4 拒跑，属本卡目标行为而非回归。

## ⑤ Worker 五要素

**① 审计表**：见上节①。
**② 守卫方案**：见上节②③④。
**③ 冲突面**：改动文件 = `backend/tests/_dbguard.py`(新)、`backend/tests/conftest.py`、`backend/tests/integration/conftest.py`、`backend/tests/test_migrations.py`、`backend/tests/test_db_partitioning.py`、`tests_e2e/conftest.py`、`.github/workflows/e2e-smoke.yml`。未动任何 `test_*.py` 用例体。
- wt140 galaxy API / wt147 sector：若在 `backend/tests` 新增测试文件→无冲突；若他们要动 `test_migrations.py`/`test_db_partitioning.py` 或新增 conftest→需 rebase 本 patch（概率低）。
- wt144 events：若加 integration 测试并使用 `db_session` fixture→fixture 对外语义不变（合法 test 库照常可用），无行为冲突；请勿在同一轮改 `integration/conftest.py`。
- wt146 词库：`api/conftest.py`（mock 域）未动，无冲突。
- 合并顺序建议：本卡先行或最后均可；冲突点仅在上述 7 文件。

**④ 诚实申报**：
1. 本机 worktree 无 .env，"演示库串"自测全部使用**假串+死端口**，从未对演示库发起任何连接（状态 B/D 的串密码为 `fake-never-connect`）。
2. 为使事故家族可导入，在本 worktree 跑过 `make proto-gen`（生成 `backend/app/gen`，gitignore 构建产物，不入库，随 worktree 回收）。
3. `tests_e2e/test_galaxy_e2e.py` 存在 1 个存量 collection ImportError（克隆 HEAD 同样复现，疑与 in-flight galaxy 卡/缺依赖有关），与本卡无关，未修。
4. **域外发现未修**：(a) 根 conftest `redis_client` fixture teardown 会 `flushdb()`——本地 dev redis 即 127.0.0.1:6379，等于清演示缓存（域外，建议后续卡：flush 前校验或限定测试 db 编号）；(b) `tests_e2e/run_e2e_tests.py:108` 会创建 `sparkle_test`（行为正确，仅登记）；(c) `test_shop_acceptance.py` 的 `__main__` 直连模式在主仓 .env 下仍会写演示库（pytest 不可达，属手动脚本，建议后续加同款守卫）。
5. 基线方法学：前两家族用 worktree 改动前实跑；`test_migrations`/`test_db_partitioning` 因发现缺基线，按纪律用 `git clone <worktree> /tmp/dbguard-baseline`（只含 HEAD）补齐对照。

**⑤ 收工核查**：无 commit/push；无遗留进程（未起服务/模拟器）；`/tmp/dbguard-baseline`、`/tmp/dbguard_*.out`、`/tmp/e2e_gate*.out`、`/tmp/dbguard_tracked.diff`、`/tmp/dbguard_newfile.diff` 已清理（见下方执行记录）；worktree 内仅交付物 `v3-output/TEST-DBGUARD/`（规范目录，未登记 README——v3-output 为会话产物约定目录）+ 7 处代码改动；零凭据入库（patch 内无任何真实密码/密钥）。
