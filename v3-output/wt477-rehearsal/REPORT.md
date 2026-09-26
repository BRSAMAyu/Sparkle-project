# wt477 — 当前合并态全量本地预演报告（CI 无 .env 形状）

- Agent：wt477（Sparkle v3 舰队验证）
- 预演 SHA：`de3f63a5`（wt466 + wt467 + wt472 三笔产品改动合并后、任何全量门之前）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt477-rehearsal`（branch `wt477-rehearsal`）
- 环境形状：backend 无 `.env`（CI 形状）；`backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen` 按先例自主仓 `cp -RL` 补齐（三处 gen 均不入库）；backend 用主仓 venv Python 3.11.15
- 日期：2026-09-26

## 一、五面结果一览

| 面 | 命令 | 结果 | 备注 |
|---|---|---|---|
| backend 全量 | `cd backend && DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v pytest -q`（主仓 venv） | ⚠️ exit 1：**12582 passed / 263 skipped / 33 failed / 76 errors**（1:16:54） | 失败/错误 109 条全部归类（见二），0 条指向 wt466/467/472 产品码回归；70 条 no-table 族与 ci.yml 注释记载的 run 36178015150「~70 例」精确同族 |
| mypy 棘轮 | `bash scripts/ci/mypy_ratchet.sh` | ✅ **1095 = 1095** | wt467 基线保持，零漂移 |
| gateway | `go build ./... && go vet ./... && go test ./...` | ✅ 全绿 | build/vet 零输出；12 包全 ok（handler 29.8s 最重） |
| mobile | `flutter analyze` + 官方门 `scripts/check_flutter_analyze_gate.py`；`flutter test --reporter compact` | ✅ analyze 门 PASS（**ERROR=0 / WARNING=16 / INFO=595**，容差 ±5）；⚠️ 全量 test 在**协调方磁盘红线指令到达前已跑完两轮**，干净轮 **+2497 / ~26 skipped / -2 failed** | 2 红根因已定位并已在主线修复（见三）；指令后零 flutter 运行，`mobile/build`(132M)+`.dart_tool` 已清除归还磁盘 |
| 守卫 | `bash scripts/run_all_rule_guards.sh` | ✅ **84/84 PASS** | 首轮 BG FAIL=worktree 缺 gitignored `mobile/lib/gen`（环境面，cp -RL 主仓后过；非产品问题，与 wt408b/wt466 记载的先例同形） |

## 二、backend 失败/错误逐类（33 failed + 76 errors = 109 条，全部归类）

### A. 既有环境形状：no-table 族 — 70 条（30 FAILED + 40 ERROR），非阻塞，未修
根因单一：`sqlite3.OperationalError: no such table: users`。`tests/integration/conftest.py` 契约是「表来自迁移、fixture 不建表」；本地 sqlite 内存形状无 alembic 迁移可施。**ci.yml L263-269 注释明文记载同族史**：首次完整全量（run 36178015150）暴露 ~70 例 relation "users" does not exist，定性「非测试或产品回归，是 ci.yml 缺迁移步骤的环境面缺口」，CI 以 PostgreSQL service + `alembic upgrade head` 补齐。本次 30+40=70 条与该记载精确同量同族。
- FAILED 30：test_adaptive_replanning_integration 9、test_north_star_journey 8、test_preference_to_plan_e2e 7、test_p0_fixes_validation 2、test_ltm_e2e 2、test_shop_acceptance 1、test_auth_flow_integration 1
- ERROR 40（fixture setup 同错）：test_auth_flow_integration 15、test_shop_end_to_end 8、test_cache_consistency_integration 7、test_shop_acceptance 5、test_north_star_journey 2、test_checkpoint_nudge_runtime 1、test_capsule_ai_personalization 1、test_achievement_progress_context 1

### B. 既有缺陷（引用既有记录）：bert 36 ERROR，非阻塞，未修
`tests/core/test_bert_intent_classifier.py` 36 错=卡面既有记载「bert 36 errors=transformers 缺失环境面」。机理核实：本机 venv **torch 2.11.0 在装、transformers 不在**→模块级 `pytestmark.skipif(not HAS_TORCH)` 不触发→`mock_transformers` fixture `patch('...AutoTokenizer')` 打在因 ImportError 未曾设置的属性上→AttributeError。CI 侧 requirements.lock **torch 与 transformers 均无**→HAS_TORCH=False→全模块 skip→CI 不受影响。

### C. 错标准门（测试假设/隔离问题，预存，非本窗回归）：2 条，非阻塞
1. `tests/services/test_dashboard_service.py::test_get_spine_status_returns_none_on_exception`：patch 目标是死符号——测试 patch `app.signals.spine_orchestrator.SpineOrchestrator`（类），而产品码（dashboard_service.py:359 `_get_spine_status`）函数内 `from ... import get_spine_orchestrator` 走单例 getter；全量序下单例已由更早测试建立→注入不生效→happy path 返回默认 dict→`assert {...} is None` 红。**隔离复跑 PASS**（该文件单独跑绿）。两文件自 initial commit（1722e6dc）零改动，与 wt466/467/472 零交集。
2. `tests/integration/test_task_manager_integration.py::TestTaskManagerIntegration::test_task_to_celery_migration`：测试假设「Redis 不可用时异常消息含 broker/connection」；本机 Redis 可达但带密码→走失败分支→`celery_dispatch` 包装消息为 `Task dispatch rejected or failed: ...` 不含关键词→断言红。**隔离复跑同红=本地确定性**；CI Redis（`redis://localhost:6379/0` 无密码）走 happy path（`task_id is not None`）绿。celery_dispatch.py 最后触碰 wt285、测试文件最后触碰 6bf07877，均非本窗。

### D. 负载时序 flake（wt467 自家测试）：1 条，非阻塞
`tests/core/test_pool_governance_v3fix156.py::test_age_pool_acquire_timeout_honest_failure`：断言「诚实失败应在预算内 <2.0s」，全量跑时与 mobile 全量/守卫同机并行，实测 5.20s → 红；**隔离复跑 PASS**（该文件 13 passed 含它）。wt467 产品码无嫌疑；记录：该 2.0s 预算对负载敏感，CI 单进程低负载形状预期绿，若 CI 复现再立卡调预算或加隔离标记。

### 分类计数汇总
| 分类 | 条数 | 阻塞 push？ |
|---|---|---|
| 既有环境形状（no-table 族，ci.yml 记载同族） | 70 | 否（CI alembic+PG 覆盖） |
| 既有缺陷（bert=transformers 缺失环境面，卡面既有） | 36 | 否（CI 无 torch→skip） |
| 错标准门（预存：dashboard 死符号 patch / celery 消息关键词假设） | 2 | 否（本地形状限定，CI 形状绿） |
| 负载时序 flake（wt467 测试 2s 预算，隔离绿） | 1 | 否 |
| **真测试门（产品码坏）** | **0** | — |
| 风格门（lint/格式） | 0 | — |

wt466/467/472 三笔自身测试面在本地已覆盖声明：wt466 `test_v3_fix155_stream_eof_sentinel.py` 9/9 全量跑内绿；wt467 池治理全文件隔离 13 passed+棘轮 1095 保持；wt472 community_signal `.all()` 修复面全量跑内零失败（privacy/community 族除 no-table 族外无红）。

## 三、mobile 面细节（含协调方磁盘红线指令的执行情况）

1. 首轮（`mobile/lib/gen` 缺失期启动）：analyze 636（25E/16W/595I，E 全系 gen 缺失）、test +2459 −10（8 个 loading [E]=gen 竞态编译错、2 个真红）——该轮作废，仅作竞态证据。
2. `cp -RL` 主仓 `mobile/lib/gen` 后干净轮：analyze **门 PASS**（官方 `check_flutter_analyze_gate.py` exit 0：ERROR=0、WARNING=16≤16+5、INFO=595≤594+5；info 逐码预算零超出）；全量 test **+2497 passed / ~26 skipped / -2 failed**（两轮真红集合恒定同 2 测，确定性成立）。
3. 2 红定位：`test/unit/chat_notifier_stream_test.dart` 两条 B-01 在途守卫测钉 wt466 前旧 EOF 语义（假流 close 无终态帧仍断言部分文本落 assistant 消息；wt466 V3-FIX-155 客户端面有意改为 failed+STREAM_INTERRUPTED、裸文本不落消息，chat_provider_test.dart 已红绿锁定新契约）——**错标准门，产品码无恙**。已在台账登记 **V3-FIX-179**；协调方已在主线 test-only 修复（**commit 3013a7d3**，改用 DoneEvent 正常收束，8/8 绿），本报告按指令引用该 SHA、不复跑验证。
4. allowlist 观察项（非阻塞）：INFO=595 对 `max_info=594` 漂 +1，主仓同 SHA 同计数（611/0/16/595）→环境基线漂移非本预演产物；官方门 ±5 容差内绿，35 个逐码预算零超出。后续若累计 +4 将触容差，建议下张质量卡顺手重冻 max_info。
5. 磁红线遵从：指令到达时全量段已跑完（两轮，完成于指令前），此后**零 flutter 运行**；`mobile/build`（132M）与 `.dart_tool` 已删，v3-output 探针文件（Q03 golden 运行时回写）已 `git checkout --` 还原。

## 四、与 CI（现跑旧 SHA 91cf83e7）的预期差异

新 SHA（含 wt466/467/472 与 3013a7d3）push 后 CI 各 job 预期：
- **flutter-test**：de3f63a5 裸 push 必红（2 条 B-01 旧语义测，CI `flutter test --coverage` 全量会跑到）——**主线已含 3013a7d3 修复，预期绿**；analyze 门同容差内绿。
- **backend-test**：本地 70 条 no-table 族由 CI 迁移步骤覆盖（同族史已验证）；bert 族 CI 无 torch→模块 skip；dashboard/celery/pool-governance 三单条均为本地形状限定，CI 形状（PG+无密码 Redis+低负载）预期绿 → **预期绿**。
- **mypy 棘轮 / go 全家 / 84 守卫**：本地即同形全绿 → 预期绿。

## 五、push 就绪结论

**READY（附一项条件）**：五面无产品码回归、无新增阻塞缺陷；唯一 CI 可见雷（2 条 B-01 旧语义测）已在主线 `3013a7d3` test-only 排除。条件：**push 的必须是包含 3013a7d3 的主线头**（裸 de3f63a5 push 会使 CI flutter-test 必红）。附带登记：V3-FIX-179（FIXED@3013a7d3，留审计链）。

## 附：证据文件
- backend 全量日志：`/tmp/wt477/backend_pytest.log`（109 条 FAILED/ERROR 清单+完整 traceback）
- 隔离复跑：pool_governance + dashboard + celery 三文件 13 passed / 1 failed（celery 本地确定性红）
- analyze 门：`/tmp/wt477/analyze_gate.log`（exit 0）；主仓对照 `/tmp/wt477/flutter_analyze_main.log`
- 干净轮 flutter test：`/tmp/wt477/flutter_test2.log`（+2497 ~26 -2）
- 守卫：`/tmp/wt477/rule_guards2.log`（84/84）；mypy：`/tmp/wt477/mypy_ratchet.log`（1095/1095）
- gateway：`/tmp/wt477/gateway_test.log`（12 包全 ok）
