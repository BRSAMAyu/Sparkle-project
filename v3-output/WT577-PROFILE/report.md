# WT577-PROFILE — Backend Tests 全量套件时长画像与分片提案

- 工位：wt577 ｜ 分支：`agent/node-b/wt577/profile`（基线 e82890b4）
- 日期：2026-09-25（本地）｜ 只分析+提案，不改任何代码/测试/CI 配置
- 上游依据：[WT572-CIREPRO](../WT572-CIREPRO/report.md)——"冻结"实为观测失明+套件 84 分钟超长+人工取消的叠加误诊；本卡把"套件时长"这个真实痛点量化到测试/文件/目录粒度，并给出分片方案。

---

## 0. 数据源与方法

**样本**：GitHub Actions run **36253679384**（run #525，main @ `cfaefe63`）attempt 2 的 **Backend Tests** job **108452479615**（2026-09-26 17:34:24→19:05:12Z，90m48s，failure）。选它的原因：pytest 步**跑完了全程**（`=== 13 failed, 12989 passed, 204 skipped, 599 warnings in 5043.68s (1:24:03) ===`），时间线完整。

> 任务书勘误：候选 run 36267475092（cd0b2440）实为迁移步快速失败 run（5m50s，无 pytest 时间线，见 WT572 §2.1），不可用作画像样本；按 WT572 取证改用 36253679384 a2。

**方法**：`gh api .../actions/jobs/108452479615/logs` 下载全量日志（27,701 行）→ 解析脚本 [scripts/devtools/ci_suite_profile.py](../../scripts/devtools/ci_suite_profile.py) 剥 ISO 时间戳前缀，对相邻结果行（`<nodeid> PASSED [ NN%]`，13201 行）做差得每测试估算耗时，聚合到文件/目录粒度。

**账目自洽校验**（三项吻合，画像可信）：

| 项 | 值 | 来源 |
|---|---|---|
| pytest 自报总时长 | 5043.7s = 84.1m | 日志 summary 行 |
| collection（session start → collected） | 76.1s | 17:40:26.714 → 17:41:42.820 |
| 逐测试净时长合计 | 4967.5s = 82.8m | 相邻行差求和 |
| 收尾（末结果行 → short summary） | 0.1s | 19:04:30.349 → 19:04:30.445 |
| 校验：76.1 + 4967.5 + 0.1 | **5043.7s = 自报值** | 完全对平 |

结果行计数：PASSED 12988 + FAILED 13 + SKIPPED 200 = 13201（进度区应为 13202，差 1 行为 short-summary 区断言文本中恰好含 `[ NN%]` 的干扰行，对时长无影响）。

**已知噪声**：相邻行差会把"行间穿插的 warning 输出"记入下一测试、把"首个请求 module 级 fixture 的 setup"记入该 fixture 的第一个用例（下文 test_all_six_lanes_driven 即此例）；单测试粒度是估算值，文件/目录级聚合和总量是精确的。

---

## 1. Top 20 最慢单测

| # | 测试 | 结果 | 估算耗时 |
|---|---|---|---|
| 1 | `tests/load/test_performance_load.py::TestPercentileAnalysis::test_latency_percentiles` | PASSED | 100.3s |
| 2 | `tests/workflow/test_orchestrator_resilience_workflow.py::test_shutdown_cancels_tracked_background_tasks` | PASSED | 61.9s |
| 3 | `tests/unit/test_a08_aurora_ablation_contract.py::test_population_two_arms_end_to_end` | PASSED | 33.1s |
| 4 | `tests/unit/test_openclaw_phase2.py::test_confirm_result_uses_gateway_approval_resolution` | PASSED | 16.0s |
| 5 | `tests/q04_personal_redteam/test_q04_redteam_final.py::test_all_six_lanes_driven` | PASSED | 15.9s |
| 6 | `tests/unit/test_v3_fix54_document_delete_route.py::test_delete_document_soft_deletes_and_excludes_from_recall` | PASSED | 13.3s |
| 7 | `tests/services/test_cognitive_service_core.py::TestHyDEStrategy::test_hyde_timeout_handling` | PASSED | 11.5s |
| 8 | `tests/contract/test_api_router_openapi_contract.py::test_openapi_marks_health_live_with_get_operation` | PASSED | 10.6s |
| 9 | `tests/integration/test_task_manager_integration.py::TestTaskManagerIntegration::test_memory_leak_prevention` | PASSED | 10.5s |
| 10 | `tests/load/test_performance_load.py::TestLatencyAndThroughput::test_sequential_requests_latency` | PASSED | 10.0s |
| 11 | `tests/load/test_performance_load.py::TestTokenConsumption::test_total_token_budget` | PASSED | 10.0s |
| 12 | `tests/v3_action_eval/test_x10_action_eval_gate.py::test_inline_rerun_core_cases_all_families` | PASSED | 9.4s |
| 13 | `tests/security/test_q05_redteam_final.py::TestPromptInjection::test_db_row_carried_injection_…[{user_context}…]` | PASSED | 9.0s |
| 14 | `tests/unit/test_release_flag_authority.py::…::test_openapi_contains_release_flags_get_operation` | PASSED | 9.0s |
| 15 | `tests/contract/test_api_router_openapi_contract.py::test_openapi_contains_critical_v1_paths` | PASSED | 9.0s |
| 16 | `tests/memory_eval/test_memory_eval_gate.py::test_full_suite_gate_signature` | PASSED | 8.6s |
| 17–20 | `tests/unit/test_bi_hardcoded_secrets_guard.py::TestBIHardcodedSecretsGuard::test_bi_*`（4 例） | PASSED | 各 8.3–8.4s |

分布关键数字：**中位数单测仅 0.003s**；>10s 的只有 11 个，>60s 的只有 2 个；Top 20 测试合计仅占净时长 7.5%。**套件不是少数巨兽主导，而是 1,320 个文件 × 13,202 个用例的"海量微小 + 肥中段"结构**——这直接决定了提案方向（§5）。

## 2. Top 10 最慢测试文件

| # | 文件 | 用例数 | 失败 | 估算总耗时 | 占全量 |
|---|---|---|---|---|---|
| 1 | `tests/load/test_performance_load.py` | 24 | 0 | 124.8s | 2.5% |
| 2 | `tests/unit/test_o03_adversarial_security.py` | 222 | 0 | 93.8s | 1.9% |
| 3 | `tests/unit/test_conflict_resolver_categories.py` | 64 | 0 | 85.1s | 1.7% |
| 4 | `tests/services/test_outcome_ledger_service.py` | 53 | 0 | 76.1s | 1.5% |
| 5 | `tests/test_plan_task_service_production.py` | 55 | 0 | 69.8s | 1.4% |
| 6 | `tests/workflow/test_orchestrator_resilience_workflow.py` | 3 | 0 | 61.9s | 1.2% |
| 7 | `tests/test_plan_task_tools_production.py` | 72 | 0 | 58.8s | 1.2% |
| 8 | `tests/services/test_policy_patch_service.py` | 39 | 0 | 54.7s | 1.1% |
| 9 | `tests/security/test_q05_redteam_final.py` | 31 | 0 | 53.0s | 1.1% |
| 10 | `tests/unit/test_bi_hardcoded_secrets_guard.py` | 9 | 0 | 50.0s | 1.0% |

文件集中度：Top 10 文件 = 14.7%，Top 20 = 24.1%，Top 50 = 40.7%，Top 100 = 56.4%。"把慢测试单列"能搬走的上限就是这 ~15%（见 §6 轻量方案收益测算）。

## 3. 目录占比（分片的均衡依据）

`backend/tests` 一级目录，净时长占比（前 10 + 其余合并；完整 31 行见脚本输出）：

| 目录 | 用例数 | 失败 | 估算总耗时 | 占比 | 累计 |
|---|---|---|---|---|---|
| `unit` | 9,414 | 7 | 50.6m | **61.2%** | 61.2% |
| `services` | 894 | 0 | 583.2s | 11.7% | 72.9% |
| `api` | 374 | 5 | 432.7s | 8.7% | 81.6% |
| `<tests-root>`（根级散文件） | 531 | 0 | 247.9s | 5.0% | 86.6% |
| `integration` | 284 | 0 | 141.7s | 2.9% | 89.4% |
| `load` | 24 | 0 | 124.8s | 2.5% | 92.0% |
| `aurora` | 406 | 0 | 98.5s | 2.0% | 93.9% |
| `workflow` | 4 | 0 | 61.9s | 1.2% | 95.2% |
| `security` | 84 | 0 | 53.1s | 1.1% | 96.3% |
| `contract` | 304 | 0 | 35.4s | 0.7% | 97.0% |
| 其余 21 个目录合计 | 465 | 1 | ~102s | ~3.4% | 100% |

**结论：目录粒度无法均衡分片**——unit 独占 61.2%，是其余所有目录之和的 1.6 倍。任何"按目录切"的 2-shard 只能是 50.6m | 32.2m（最慢片 governs）；3-shard 也绕不开 unit 这座山。**均衡必须下沉到文件粒度**（文件是天然原子单位，见 §5 有状态性讨论）。

## 4. 慢的共性诊断（抽最慢 5 个看代码，只描述不修）

| 测试 | 耗时 | 根源归类 | 代码事实 |
|---|---|---|---|
| `test_latency_percentiles` | 100.3s | **合成压测伪装成单测** | `tests/load/test_performance_load.py:690` 起：`for i in range(1000): await orchestrator.process_chat(...)` 顺序跑 1000 轮后只断言分位数单调性。这是 benchmark，不是正确性测试，却在每个 PR 的关键路径上。 |
| `test_shutdown_cancels_tracked_background_tasks` | 61.9s | **疑似后台任务排空等满宽限（未证实）** | 测试体仅 ~10 行（`tests/workflow/test_orchestrator_resilience_workflow.py:62`）；`ChatOrchestrator.shutdown()`（`app/orchestration/orchestrator.py:1657`）只有 cancel+gather，无 sleep。但日志显示上一结果行 19:03:28.455 → 本行 19:04:30.349 之间 **62 秒零日志输出**，其后 96ms 即收尾。fixture 只 patch 了 `orchestrator.asyncio.create_task`，若存在经其他引用创建的真实后台任务带 ~60s 量级 deadline/重试，gather 就会等满。日志证据不足以定位，建议单列复跑（`--durations` + py-spy）验证，本卡不动。 |
| `test_population_two_arms_end_to_end` | 33.1s | **全人口模拟，设计使然的重** | `tests/unit/test_a08_aurora_ablation_contract.py:212`：2 臂 × 全量 persona × 每臂 20 episodes 的完整时间线仿真（`tests/aurora_ablation/engine.py`）。零 LLM 但计算量真实，属"该重的测试"，适合放夜间/慢车道而非每 PR。 |
| `test_all_six_lanes_driven` | 15.9s | **module fixture 一次性跑完整模拟** | `tests/q04_personal_redteam/test_q04_redteam_final.py:49` 的 `redteam_records` 是 `scope="module"`，第一次被请求时 `asyncio.run(run_persona_redteam(spec))` 跑完 6 条车道仿真——成本记在第一个用例头上（解析噪声的实例，实际是该文件整体的 fixture 成本）。 |
| `test_confirm_result_uses_gateway_approval_resolution` | 16.0s | **app/DB fixture 链 + 全量 import** | 测试体（`tests/unit/test_openclaw_phase2.py:470`）全 mock；成本在 `db_session`/`openclaw_settings` fixture 链与 app 模块导入。同型的还有两个 OpenAPI contract 测试（10.6s/9.0s，各触发一次完整 FastAPI app 构建）。第 17–20 名的 `test_bi_hardcoded_secrets_guard.py` 每例 ~8.3s 则是**每个用例 subprocess 启动 guard 扫全仓**（且该 guard 在 All Rule Guards job 已跑过一遍，属双重覆盖）。 |

**共性总结**：(a) 少数"设计使然的重"（压测/全人口模拟/六车道仿真）约 3–4 分钟/PR；(b) 全仓 subprocess 扫描类守卫测试在测试侧重复劳动；(c) 一例未证实的 ~62s shutdown 等待；(d) 占大头的 82.8m 净时长没有单点元凶——是 13k 个 3ms 级用例 × coverage 追踪的乘积。这解释了 WT572 观察到的"75→84 分钟持续恶化"：恶化来自用例数增长（与近期大量新增卡片测试一致），不会有"修掉一个慢测试就变快"的捷径。

## 5. 分片方案提案（不实施）

### 5.0 公共要点（两方案共用）

- **切分单位 = 测试文件**（`--cov`/`pytest backend/tests/...` 按文件列表传参）。理由：文件是 session/module fixture 与 import 副作用的天然边界；跨文件只有目录级 conftest（每片独立进程+独立 DB service，天然满足）。目录粒度无法均衡（§3 已证）。
- **每片完整复制现有环境步**：AGE PostgreSQL 容器（ci.yml:187）、`init_age_extension`、`alembic upgrade head`（ci.yml:263，run 36178015150 已证明缺它会让 integration 侧 ~70 例报 relation does not exist）、proto 生成。任何一片省掉环境步都会重演那类"环境面缺口"。
- **`strategy.fail-fast: false`**：一片红不能取消其他片，否则又回到"只见部分信息→误判"的老路（WT572 的教训之一）。
- **matrix 传播失败**：合并 job `needs: [backend-tests]` + `if: always()`，并显式检查 `needs.backend-tests.result == 'success'` 决定是否继续，保证红不可被吞。
- **顺手的免费优化**（各方案通用，~3–4m）：① `tests/golden`、`tests/contract`、`tests/workflow` 目前在 `pytest backend/tests` 全量扫里跑一遍后，又由专用步（ci.yml:285–299、313）**重跑第二遍**（净浪费 ~1.7m + 步开销）；② Go test -race（ci.yml:210）从 Backend Tests job 拆出去并行，给每片关键路径再省 ~2–3m。
- **coverage 合并方式**：每片 `pytest ... -v --cov=backend/app --cov-report=` （只留数据文件不写报告），以 **`COVERAGE_FILE=/tmp/cov/.coverage.<shard>`** 起唯一名；`actions/upload-artifact@v4` 按片名上传（v4 禁止重名 artifact）。独立 `coverage-merge` job：`actions/download-artifact@v4` 用 `pattern: cov-shard-*` + `merge-multiple: true` 收拢到同一目录 → `python -m coverage combine` → `coverage xml` → 现有 `scripts/check_coverage_thresholds.py --kind python --report coverage.xml --rules-file quality/coverage_thresholds.json` 照旧。仓库无 `.coveragerc`/`[tool.coverage]` 自定义（已核），combine 用默认数据文件名即可；hosted runner 检出路径一致，无需 `[paths]` 重映射。

### 5.1 方案 B：2-shard（文件粒度 LPT 均衡）

模拟结果（脚本按文件时长 LPT 贪心装箱，文件不拆）：

| shard | 用例数 | 测试净时长 | 预估 pytest 墙钟* |
|---|---|---|---|
| 1 | 7,121 | 41.4m | 42.3m |
| 2 | 6,080 | 41.4m | 42.3m |

*含按片分摊的 collection（~1m）与收尾。job 级墙钟 ≈ 6.0m 环境步 + 42.3m + ~2m 收尾/阈值步 ≈ **50m**（现状 90m48s → **-45%**）。

严格按目录切的对照片：`[unit]` 50.6m | `[其余全部]` 32.2m → 最慢片决定墙钟 ≈ 58m，且片间失衡 22m。**不推荐**，仅作对照说明目录粒度不可行。

### 5.2 方案 C（推荐）：3-shard

| shard | 用例数 | 测试净时长 | 预估 pytest 墙钟* | 片内最慢文件（示例） |
|---|---|---|---|---|
| 1 | 3,861 | 27.6m | 28.3m | test_performance_load.py、test_orchestrator_resilience_workflow.py、test_q05_redteam_final.py |
| 2 | 5,109 | 27.6m | 28.4m | test_o03_adversarial_security.py、test_plan_task_service_production.py、test_policy_patch_service.py |
| 3 | 4,231 | 27.6m | 28.3m | test_conflict_resolver_categories.py、test_outcome_ledger_service.py、test_plan_task_tools_production.py |

job 级墙钟 ≈ 6.0m + 28.4m + ~2m ≈ **36m**（现状 → **-60%**，反馈时间约 2.5 倍速）。三片完全均衡（27.6m×3），落差 <0.2m。

- **coverage 合并**：§5.0 三片合一后跑一次阈值检查。
- **预估改善**：取消/重跑浪费从"40–90 分钟/次"（WT572 §2.1 实录）降到"36 分钟/次"；两片红时并行取证，不再有 75–90 分钟的"观测空窗"。
- **实施注意**：matrix shard→文件清单的映射建议由脚本生成并落盘到仓库（可复现、可 review diff），不要在 ci.yml 里手写 1,320 个文件名。

### 5.3 备选轻量方案：`--durations` + 慢测单列 pre-merge job

- 做法：pytest 命令加 `--durations=20`（零风险，时长表直接落日志，消灭"日志考古"）；把 Top 10 慢文件（14.7% ≈ 12.2m）搬到并行 `slow-tests` job，主 sweep 排除之。
- 预估：主 job ≈ 6 + (84.1−12.2) ≈ **78m**；slow job ≈ 6 + 12.2 ≈ 18m；总反馈 ≈ max(78, 18) ≈ **78m，仅 -13%**。
- 结论：**便宜但收益小**（§1 已证 Top 20 测试仅占 7.5%，长尾在"肥中段"）。值得做的是 `--durations=20` 这一行的观测面部分；"搬走慢文件"不足以解决 84 分钟问题，仅当 transition 方案。

### 5.4 各方案反馈时长对比

| 方案 | job 墙钟预估 | vs 现状 90m48s | 代价/风险 |
|---|---|---|---|
| 现状（单 job 全量） | ~90m（含 6m setup） | — | 取消重跑浪费 40–90m；观测空窗 75–90m |
| 轻量：durations+慢测单列 | ~78m | -13% | 几乎零风险；收益天花板 15% |
| B：2-shard 文件 LPT | ~50m | -45% | 2 份 runner 成本；coverage 合并链路 |
| **C：3-shard 文件 LPT（推荐）** | **~36m** | **-60%** | 3 份 runner 成本；每多一片付 ~8m 固定成本（setup 6m + collection ~1m + 收尾 ~1m），4-shard ≈ 29m，边际递减，3 是性价比拐点 |
| （对照）2-shard 严格目录 | ~58m | -36% | 片间失衡 22m；不推荐 |

### 5.5 Known pitfalls：有状态测试迹象清单（分片/并行化前必读）

以下迹象**不阻塞文件粒度分片**（每片=独立进程+独立 VM+独立 DB），但说明"同一 workspace 内再并行"（如 pytest-xdist `-n auto`）当前不安全；WT572 也提示过需评估 xdist 与 coverage/顺序依赖的兼容：

1. **workspace 树全局可变**：`tests/unit/test_bi_hardcoded_secrets_guard.py` 在 `backend/app/` 下写临时 `.py` 再 subprocess 扫**全仓**——并行同扫会互相污染结果（job 级分片各自独占 VM 则安全）。
2. **进程级全局注册表**：`circuit_breaker_registry._breakers.pop` / `_track_task` 后台任务（`tests/workflow/…`、`app/orchestration/orchestrator.py:375`）——同片内跨文件共享进程状态，文件不拆则天然安全。
3. **module 级重型 fixture**：`redteam_records`（六车道仿真）等——文件不拆即安全；**不要**把切片单位细到用例级。
4. **环境顺序契约**：integration 侧依赖"先图谱后迁移"（ci.yml:259–262 注释，run 36178015150 的事故）——**每片都必须原样保留** AGE 容器 + `alembic upgrade head` 两步。
5. **墙钟敏感断言**：`test_latency_percentiles` 断言的是记录到的延迟分位数排序（顺序不敏感但对资源竞争敏感）、`test_response_time_under_threshold`（现 SKIPPED）等——同 VM 内并行跑会引入资源竞争噪声，又一个"先 job 级分片、xdist 另立实验卡"的理由。
6. **重排风险兜底**：LPT 会改变文件的相对执行顺序（片间重排）。无法从本日志证明存在跨文件顺序依赖，但为兜底：建议保留一条**夜间全量单进程**跑法作为漂移网（顺带产出下一轮画像样本），并让分片映射脚本对文件清单做"稳定排序"以便 diff 可读。

## 6. 结论与建议顺序

1. **先做观测（一天内可落）**：pytest 命令加 `--durations=20`；本卡工具 `scripts/devtools/ci_suite_profile.py` 可对任何终态 job 日志复算画像。
2. **推荐主方案 C（3-shard 文件 LPT）**：反馈 90m→36m；配 §5.0 的 coverage 合并与 fail-fast 要点；同时摘掉 golden/contract 双跑、拆出 Go test 两个免费项。
3. 对 `test_shutdown_cancels_tracked_background_tasks` 的 ~62s 空窗单立诊断卡（--durations + py-spy 复跑验证），本卡只记录证据。
4. xdist、压测/模拟类测试移夜间车道等，待分片落地后再评估，不在本卡范围。

## 7. 证据清单

- 原始日志（job 108452479615，27,701 行）：会话产物，不入库（`/tmp/wt577-profile/backend_tests_a2_108452479615.log`）
- 解析脚本：`scripts/devtools/ci_suite_profile.py`（含用法说明）
- 解析产物 JSON（逐测试 13,201 行 + meta）：`/tmp/wt577-profile/per_test.json`（会话产物）
- 画像原始输出：`/tmp/wt577-profile/profile_out.md`
- 上游取证：[WT572-CIREPRO/report.md](../WT572-CIREPRO/report.md)（job 清单、观测失明复现、13 个真实失败清单）
- CI 配置引用：`.github/workflows/ci.yml`（:187 AGE 容器、:210 Go test、:263 迁移、:283 pytest 命令、:285–313 双跑步、:324 阈值检查）
- 本报告不修改任何产品代码/测试/CI 配置；worktree 变更仅本报告 + devtools 脚本 + devtools README 一行登记。
