# WT660 — 今日集成波合并态横向冒烟报告

- 日期：2026-09-25
- 会话：wt660（node-b，smoke 卡）
- 分支：`agent/node-b/wt660/smoke`（基于 main HEAD `c72a8c45`，本分支除本报告外零改动、零产品代码改动）
- 参照 base：`4bc62af7`（mypy 棘轮批二）；本波集成主体为其前后的 FIX-330~355 链（agent-stats 如实化 330、dashboard 键改名 332、能力五态 333、三态回放 334、幂等断通道 335/336、死链 337-342、L3 桥 343、mock 删除断轨 345-347、analytics 真轨 345-352 批）
- 结论先行：**零红**。三条轨（交界矩阵 113/113、全量守卫 86 规则 exit 0、抽样组合 262 项 261 过 1 跳）全部绿。无需归因，无新登记项。

## 0. 环境（CI 同形）

- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt660-smoke`，gitignored 产物（`backend/app/gen`、`backend/gateway/gen`）按 CI 流程以 `make proto-gen` 独立重生产（docker 工具链镜像缺席自动回落 host 工具链，脚本内置路径）。
- 独立重生产物一致性旁证：守卫 BG（proto 三语言新鲜度）PASS "checked 7 proto files across Go/Python/Dart (0 staleness warnings)"、AQ（Python 手写 UserStateV1 对齐 proto 生成物）PASS——**独立重生 gen 与契约零漂移**。
- 测试口径：`DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v python -m pytest -q`（复用主仓 backend/.venv 解释器，cwd 在 worktree backend，`import app` 解析到 worktree 代码）；mobile 用 `flutter test --concurrency=1`。

## 1. 跨家族交界抽样矩阵（17 文件，113 用例全绿）

抽样原则：只挑"两个家族在同一次状态迁移/同一条请求链上交界"的文件，不重复各卡的定向复验。

### 族 A：三态回放(334) × 幂等断通道(335/336) — 4 文件 70 用例 ✅

| 文件 | 交界点 |
|---|---|
| `backend/tests/unit/test_v3_fix335_plan_checkpoint_resume.py` | FIX-335/336 本体：打断-重试 duplicate side effect 通道 × checkpoint 恢复（触及 redis_checkpointer/statechart_engine/schemas） |
| `backend/tests/unit/services/test_agent_grpc_service_request_result.py` | FIX-334 三态回放去重命中改返结果/状态 × 新 RPC GetRequestResult 契约 |
| `backend/tests/unit/test_state_manager_concurrency.py` | state_manager 并发面（回放与幂等的共同底座） |
| `backend/tests/unit/test_redis_checkpointer_allowlist.py` | checkpointer 序列化 allowlist（335/336 改动的同一文件族） |

### 族 B：能力五态(333) × L3 桥(343) — 3 文件 ✅

| 文件 | 交界点 |
|---|---|
| `backend/tests/services/test_capability_claims_realism.py` | FIX-333 五族终态状态机 |
| `backend/tests/unit/test_v343_l3_closure_bridge_activation.py` | FIX-343 L3 closure→Spine 死桥激活（三断桥+facade 会话旁路） |
| `backend/tests/unit/test_aurora_core_session_entry.py` | core_session 入口（五态宣称 × L3 桥共同消费面） |

### 族 C：死链修复(337) × analytics 真轨(345-347/350-352) — 4 文件 20 用例 ✅

| 文件 | 交界点 |
|---|---|
| `backend/tests/api/test_push_interaction_api.py` | FIX-337 网关 /push 代理组接通回执链 × push_feedback 入口 |
| `backend/tests/unit/test_analytics_truth_batch1.py` | FIX-345/346/347 删 Mock 红转绿真值测试（enhanced_orchestrator 退役轨、streak 冒充字段、predictive 空承诺键） |
| `backend/tests/api/test_statistics_api.py` | /stats 面与删 Mock 后的真值契约交界 |
| `backend/tests/unit/test_predictive_focus_window_local.py` | predictive 真轨（FIX-347 删键后的存活面） |

### 族 D：celery 接线(338/340) × 既有任务族 — 3 文件 ✅

| 文件 | 交界点 |
|---|---|
| `backend/tests/core/test_celery_beat_registration_guard.py` | FIX-338 login_attempt_cleanup 注册面守卫 |
| `backend/tests/core/test_similarity_tasks_disposition.py` | FIX-340 相似度双任务退役+画像/缓存清理真接线处置 |
| `backend/tests/core/test_celery_dispatch_async.py` | 既有 dispatch 族（接线改动不得破坏的既有轨） |

### 族 E：mobile 三交界 — 3 文件 23 用例 ✅

| 文件 | 交界点 |
|---|---|
| `mobile/test/features/home/presentation/providers/dashboard_provider_test.dart` | FIX-332 today_focus_minutes→today_completed_task_minutes 键改名 × provider 消费 |
| `mobile/test/unit/statistics/statistics_truth_test.dart` | FIX-330 agent-stats 如实化 truth 契约（错误上抛不落 mock、unavailable 语义、server 聚合映射） |
| `mobile/test/widget/chat_history_sheet_regression_test.dart` | chat history sheet 回归（空态不冻结/内联错误可刷新/换会话自关） |

**小计：17 文件，113 passed，0 failed，0 error。**

## 2. 全量守卫（`bash scripts/run_all_rule_guards.sh`）

- **exit=0，`all rule guards passed (86 rules)`**。
- AQ（UserStateV1 对 proto 生成物）PASS、BG（三语言 proto 新鲜度）PASS——worktree 缺 gen 的环境红未出现（因已按 CI 流程独立重生 gen），无需豁免口径。
- 唯一带 WARN 的守卫：ENUM-PARITY `FAIL=0 WARN=7 豁免=0`——7 条 EP002 为 mobile 侧 wire `unknown`/扩展值既有漂移（MessageType/PatternType/PhotonTransactionType/StreakDayStatus 的 `unknown`、SharedResourceType 扩展值等），属守卫设计的非阻断 WARN 既有形态，非本波新增。
- 其余 ratchet 类守卫（ui-tokens/ux-comp/dl-spec/typo-rhythm/spacing/fs-carry/n9/n18/n37/dup-title）全部 holds；AX/BJ diff 类守卫 scope-empty PASS。
- 日志存档：本报告同会话留档 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt660-guard.log`（worktree 外，不入库）。

## 3. 后端关键族组合抽样（tests/unit 前 100 抽 20 + tests/services 全量 107 抽 10）

- **抽样原则**：`find tests/unit -maxdepth 1 -name 'test_*.py' | sort | head -100` 后**等步长抽第 1,6,11,…,96 个（NR%5==1）共 20 个**；`find tests/services -name 'test_*.py' | sort`（107 个）等步长抽第 1,12,23,…,100 个（NR%11==1）共 10 个。等步长避免按主题聚簇偏置，字母序前 100 限定覆盖 a-b 字头段。
- 结果：**261 passed，1 skipped，0 failed**（64.7s，sqlite 内存口径）。
- 唯一 skip：`tests/services/test_embedding_live_green.py` 模块级 `pytest.skip("live green test requires E05_LIVE=1 (real provider key)")`——真实凭据门，既有设计，非回归。
- unit 抽中 20 个：test_a01_aurora_decision_l2_wiring / test_a04_l2_joint_spine_wiring / test_ab_test_framework / test_accountability_reminder_cadence / test_achievement_event_consumer / test_action_allocation_eval / test_action_plan_migration_sqlite / test_adaptive_replanner_stage34 / test_aggregator_backed_social_context_provider / test_aggregator_schema_v1_6 / test_ai_ops_dashboard / test_analytics_truth_batch1 / test_aurora_confirm_bridge / test_aurora_language_principles / test_aurora_runtime_self_model / test_aurora_sleep_guard_user_timezone / test_b06_entitlement_tier_parity / test_bayesian_rollback_parity / test_behavioral_outcome_tracker / test_bh_guard_registered
- services 抽中 10 个：galaxy/test_delete_correction_consistency / stt/providers/test_xunfei_provider / test_cognitive_service / test_embedding_live_green(skip) / test_friend_match_public_candidates_cohort_filter / test_intervention_lifecycle_service / test_ocr_service / test_policy_scheduler / test_semantic_cache_pydantic_payload / test_understanding_calibration_service

## 4. 红项与归因

- **本会话零红**，无归因需要，无 base 4bc62af7 前后对照触发。
- 与已知 OPEN 项的一致性观察（非本会话发现，不重复登记）：V3-FIX-355（PlanFeedback.decision 四套词汇、过滤静默丢决策，wt658 登记 OPEN）、FIX-348/349（UserDailyMetric 写侧真空、mobile UserAnalyticsEvent 死集合，台账 181/183 登记 OPEN）在本次矩阵中均未表现为测试红——它们是"宣称面/写侧缺失"类债，现有测试不覆盖，与台账定性一致。

## 5. 遗留与建议

1. 合并态冒烟三轨全绿，支持今日集成波（FIX-330~355 链 + wt654 B-03）**通过合并态横向冒烟**判定。
2. 浮动提示（不阻塞）：CI 分片各卡定向复验 + 本轮交界冒烟均为绿，但 `test_embedding_live_green` 等真实凭据门在本地永远 skip，真实 provider 轨仍只有 CI/升栈可验。
3. 本分支仅含本报告（`v3-output/WT660-SMOKE/report.md`），零产品代码改动，未 push。
