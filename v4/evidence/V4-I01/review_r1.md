# V4-I01 独立审查 receipt（一审 · wtI01R1）

- 审查对象：commit `23989050`（branch `agent/v4/i01`，base `1a53b8c3`，16 files +2196/−4）
- 审查人：wtI01R1（未参与 I01 任何实现；只读审查 + 本 receipt；不 push）
- 卡标准：`Sparkle-project/v4/04_tasks/cards/V4-I01.md`；契约：`v4/evidence/V4-B05/contract_receipt_min.md` §5 `episode_resume_view.v1`（三契约之三）+ §4/§4.1 why_now 字段位 + §9 反例
- 方法：审查靶 8 项逐条对照；全部权威引用行号级打开核验；BA-ROUTES 挂账做**带/不带条目双跑实验**；测试全量复跑（非采信自报）。

---

## 1. 零第二真源声明 — CONFIRMED

- **DB 表集合 == ORM metadata 断言在库且亲验绿**：`tests/integration/test_episode_resume_cross_process.py::test_view_build_persists_no_rows` 以 `SELECT name FROM sqlite_master WHERE type='table'` 摸底，断言 `tables - Base.metadata.tables == set()` 且 tasks 行数不增。范围说明：该断言证明「视图聚合不落任何新表/新行」，非全局 schema parity（create_all 本以导入 metadata 为界）——零写路径另有服务面独立佐证（见下），二者合取成立。
- **服务唯一公开方法**：`grep -n "async def \|    def "` 全量列出 `EpisodeResumeService` = `build_resume_view` + 4 个下划线私有（`_last_confirmed_step`/`_pending_human_step`/`_last_valid_outcome`/`_memory_epoch`）；`EpisodeResumeResult` 仅 `degraded` property。全仓 grep 该服务仅 `app/api/v1/episode_resume.py` 一处消费。服务内 5 处 `self.db.execute` **全部为 `select(...)`**，零 insert/update/commit/flush/add；`test_endpoint_404_on_missing_and_cross_user` 侧另有 `test_service_is_read_only_surface` 钉 `dir()` 公开面 == `["build_resume_view"]` 且无写词根方法名。
- 跨进程集成测 `_build` 显式 `db.rollback()` 只读留痕；无迁移、无 `gen/` 手改（diffstat 零 proto/零 alembic 文件）。

## 2. 契约逐条 — CONFIRMED

| 契约项 | 核验 |
|---|---|
| `last_confirmed_step` | subtask（status=COMPLETED + completed_at 非空，`completed_at desc, id desc`）优先，task 级 `max(completed_at, confirmed_at)` 兜底，无则 null；`version_token` 复用 X-03 `action_command.version_token`（`action_command.py:241`，updated_at ISO 微秒）——**import 不自造**，测试逐字符断言 token 值 |
| `pending_human_step` | **真调 X-01 统一读侧门**：`action_plan_projection(task)`（`action_plan.py:315`，版本门+词表+结构完整门原样生效，脏/legacy → None+WARN），服务读其 `smallest_useful_step.description`/`cognitive_ownership`/`execution_mode` 三键（投影函数保证非空/合法后才返回）；`CognitiveOwnership`/`ExecutionMode` 均 import（`app.models.task`/`app.models.execution_intent`），无词表复制。COMPLETED/ABANDONED 恒 null（测试钉死） |
| `why_now` | `getattr(task, "why_now", None)`——Task 模型 grep `why_now` **0 命中**（无该列），v1 行=null 不臆测回填属实；`normalize_why_now` 8 类字段级降级原因封闭（not_object/unknown_keys/statement/basis_refs_empty/scheme/band/expires_at_invalid/expired），过期不复用（`why_now_expired`）；降级仅 why_now 置 null + WARN（带 task_id），视图其余字段逐字节不变（契约测 `test_why_now_degrade_leaves_rest_of_view_byte_identical` + v1 双读等价测试） |
| `last_valid_outcome` | `TRUTH_CLASS_VALUES = frozenset(member.value for member in TruthClass)`——**真 import**（`outcome_ledger.py:104`，5 值含 demo）；`OutcomeLedgerService.query` 调用**不带** truth_class 过滤、不带 `exclude_seed_cohort`（默认 False）→ demo 行透传不排除，**无偷滤波**；词表外值 `ValueError` fail-loud（测试钉死 `mastered` 拒）；demo 透传有专测；null 不造「练了 N 分钟」（无历史三 null 测试 + 冻结键集断言无 progress/mastery/minutes） |
| `run_ref` | `ACTIVE_RUN_STATUSES = RunStatus - TERMINAL_RUN_STATUSES`（`run_state_machine.py:121`）且 `AgentRun.user_id == task.user_id` 属主双校验；终态 run → null 有专测 |
| `goal_ref`/`task_ref` | 存在+未软删+属主三重门；goal 经显式参数或 `task.plan_id → plans.goal_id` 既有链路；plan/goal 属主不符 → `cross_object_access` |

## 3. TTL/freshness 语义 — CONFIRMED

- `resume_view_stale_reason` 为纯函数可判定出口：`expires_at_passed`（≥ 到期即过期，含 garbled/缺 expires_at/非 dict 一律 fail-closed 判过期——不强行接续）/ `memory_epoch_changed`（钉住 epoch ≠ 当前 epoch，含类型坏值）。封闭二值，契约测+服务测+集成测三面覆盖。
- epoch 读失败按 0（`_memory_epoch` 与 context_manager 同口径）→ 与任何真实 epoch（默认 1 起）必不一致 → stale 强制重算：fail-safe 方向正确。
- 读侧消费面现状：服务端每次按需现算、不缓存不续期（GET 无自动续期），过期视图只存在于客户端手中——消费端（F 线）未落地，`resume_view_stale_reason` 即其可判定契约，测试钉死。API docstring 明示「GET 不自动续期、不静默接续」。

## 4. 安全面 — CONFIRMED

- `GET /episode-resume/tasks/{task_id}`：`Depends(get_current_user)` + `# route-tier: authed`；gateway 组 `authMiddleware` 组级生效（含 `registerREST` 裸路径 5 动词）。
- 越权抽验：不存在与跨用户**同一 404 同一 detail**（`"episode resume target not found"`），无存在性泄露——API 测 `test_endpoint_404_on_missing_and_cross_user` 双断言亲验绿；服务层 `cross_object_access` 另记 WARN 安全遥测（含 caller/owner，日志留痕）。task/plan/goal 三级属主逐环校验，`run` 查询绑定 `AgentRun.user_id == task.user_id`。
- `context_receipt_ref` 仅 scheme 形态门、ref 值仅回显进 `freshness`（无解析、无注入面）；「存在性门」缺位已在 limitations #3 如实登记（receipt 本体归后续卡）。

## 5. 降级诚实 — CONFIRMED（1 处测试缺口见 CHALLENGED-C1）

- 类型化降级词表 5 值封闭且有专测；`EpisodeResumeResult` view/reason_code 互斥（有视图必有权威面，降级必有原因），**无整体 500、无静默吞**：API 把 `object_not_found/cross_object_access` 映射 404，其余降级 200 + 类型化原因；`goal_unresolved`/`goal_changed_requires_calibration`/`context_receipt_missing` 均有测试。
- why_now 字段级降级 WARN 收集进 `result.warnings` 并 logger.warning 留痕；pending 投影不可得 → null + warning（不造步）。
- **CHALLENGED-C1（有界扫描 300+ 压顶诚实 null 无测试在库）**：`_last_valid_outcome` 有界扫描（100/页 × 3 页）实现属实、limitations #4 如实登记，且证据文件（test_results.json covers）**未**声称有该测试——无证据虚报；但审查靶要求「300+ 压顶诚实 null 的测试在库」**不成立**：4 个测试文件 grep `MAX_PAGES/PAGE_SIZE/monkeypatch/next_cursor/300` 零命中，仅零 outcome 的 null 路径被测（`test_no_history_yields_nulls_no_fabricated_scores`）。压顶即「最新关联 outcome 被 300+ 更晚条目压住 → null」的边界行为未被任何测试钉死——若未来回归为无界扫描或扫描耗尽即抛错，现库不报警。修复建议（1 个测试即可，非合并阻塞）：monkeypatch 页参为小值 + 插入更晚的他任务 outcome + 断言该任务 outcome 被压顶后视图 `last_valid_outcome=null` 且视图照常组成。

## 6. 复跑 — CONFIRMED（全部本机 wtI01 重跑，非采信自报）

| 命令 | 结果 |
|---|---|
| `SECRET_KEY=ci-test-key JWT_SECRET=ci-test-key DATABASE_URL="sqlite://" TESTING=true pytest <4 文件>` | **56 passed**（11.92s；unit 30 + services 17 + integration 4 + api 5，与自报分账一致） |
| 邻接权威回归（action_plan/outcome_ledger/run_steps 五文件） | **141 passed**（29.29s） |
| gateway `go build ./... && go test ./internal/handler/` | build ok；handler test ok |
| `mypy app --ignore-missing-imports --no-error-summary` | 55 = 改前基线 55（零漂移）；grep `episode_resume` **0 条** |
| `ruff check`（改动 3 文件）/ `black --check`（120） | All checks passed / unchanged |
| 产物 sha256 ×7（core/service/api + 4 测试文件） | 与 run_manifest.json `artifacts_sha256` **逐一相符** |

## 7. 挂账核 — CONFIRMED

- **BA-ROUTES GATEWAY_ONLY 恰 1 行**（`/api/v1/episode-resume`，含日期与理由），非绕守卫：**双跑实验**——带条目 `RULE BA-ROUTES OK: 616 gateway ↔ 1009 engine, 60 catch-all, 165 ledgered`（exit 0）；剥除该行复制脚本重跑 exit 1（Direction A 报 gateway-only 裸路径）。条目 load-bearing 且只覆盖 `registerREST` 裸组面 artifact；子路径 `/episode-resume/tasks/{task_id}` 由 engine 真实服务、Direction B 经 catch-all 自证覆盖，**未被挂账遮蔽**。与 `visual-elements`/`executions` 等既有裸组先例同款（`visual-elements` 确在 GATEWAY_ONLY 表中，limitations #6 表述属实）。
- **AQ/BG 说明属实**：AQ 首行 `from app.gen import user_state_pb2`、BG 检查生成产物存在/非陈旧——fresh worktree（生成物 gitignored 不入库）初跑必失败，`make proto-gen` 补齐即过；本卡 diffstat **零 proto 变更**，生成产物未入库（`git status` clean）。环境缺项定性如实。

## 8. limitations×7 如实性 — CONFIRMED（1 处交叉引用计数 nit）

逐条对码核验：#1 goal 内容级变更不可判定（无绑定列，只做终态/source_refs/过期三面）✅；#2 `getattr` 前向兼容（Task 无列实证）✅；#3 receipt 只绑 scheme 形态门非存在性门 ✅；#4 有界扫描非全索引（300+ → 诚实 null）✅；#5 pending 单一来源 X-01、不并 X-07 run awaiting step（词表不同源）✅；#6 gateway registerREST 裸组 + 挂账 1 行 ✅；#7 mypy 平台代际差 + AQ/BG proto 环境缺项 ✅。

- **CHALLENGED-C3（nit）**：`diff_or_evidence_only.md` §7 称「等 5 项」，limitations.md 实为 7 节（#6/#7 为挂账与环境性说明，非行为限制，可辩护但计数不一致）——文档级，随 C1 顺带修正即可。

## CHALLENGED 汇总（均非合并阻塞）

| # | 级别 | 内容 | 处置建议 |
|---|---|---|---|
| C1 | minor | 有界扫描 300+ 压顶诚实 null 无测试钉死（实现与文档属实，证据未虚报） | 补 1 个 monkeypatch 页参测试；可本卡追加或随邻卡 |
| C2 | minor | `normalize_why_now` 仅接受 `datetime` 型 `expires_at`；若 B06 选 JSONB 列形态，反序列化出的 ISO 字符串将整批触发 `why_now_expires_at_invalid` 字段级降级（fail-closed 不出错，但 why_now 全 null）。现无写方、无活 bug；limitations #2 只覆盖落点选择未覆盖此类型差 | 登记 B06 互操作清单：读侧加 ISO 字符串容差，或写方保证 datetime 语义 |
| C3 | nit | diff_or_evidence §7「5 项」vs limitations 7 节计数漂移 | 顺带改 1 字 |
| C4 | 观察 | 「DB 表集合 == ORM metadata」断言以 sqlite/create_all 为界，证明力是「聚合零新表零写行」而非全局 schema parity（零写路径另有服务面 grep + 只读面锚独立佐证，结论不变） | 留档精确表述，无需改动 |

## 总裁决

**PASS（一审通过，可进入集成 SHA 复验/合并流）。** 卡面四条验收全部有可失败测试且亲验绿；「零新表、零写路径、零第二任务真值」三声明经独立 grep、双跑守卫实验与全量复跑成立；证据文件无虚报（self-check 与 test_results 与实物一致，review_receipt.json 如实 PENDING 未自称已审）。C1/C2 建议随后续卡承接，不构成本卡回退理由。

- 复跑环境：worktree 无 .env，`SECRET_KEY=ci-test-key JWT_SECRET=ci-test-key DATABASE_URL="sqlite://" TESTING=true`，Python 3.11.15（主仓 .venv）。
