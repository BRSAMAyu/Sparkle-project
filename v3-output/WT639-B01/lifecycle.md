# WT639-B01 · 42 模块产品生死簿与可达性真相（round-1 审计轴）

- 会话：wt639（B-01）｜日期：2026-09-27｜基线：main@34af2acc｜分支：agent/node-b/wt639/b01
- 方法：worktree 只读审计，零产品代码改动。三层模块清单以仓内实际为准：backend/app/services 顶层 410 个 .py 模块 + 20 个子包、backend/app/orchestration 92 个模块、api/v1 路由面 109 个注册组、gateway 代理面 ~84 组（显式组+missing-loop 补注册+原生 Go handler）、mobile/lib/features 44 个 feature。
- 判据=全链四问：①入口可达（router 注册 / 编排图消费 / Celery 实际入队 / gRPC bootstrap / gateway 代理 / GoRouter+UI 入口）②下游消费（生产代码 grep 调用方）③测试在测（测试文件数×引用数）④诚实性（宣称 vs 实现，参照 FIX-330「有表无写入方」形态）。
- 机械扫描：对 502 个后端模块建全仓 import 索引（app/、tests/、tests_e2e/、scripts/），正则匹配 `from app.services.X import` / `services.X.` 等五种引用形；每个 DEAD/PARTIAL 判定均经人工开文件复核（含动态路径加载、gRPC bootstrap、CLI __main__ 等索引盲区校正）。

## 总判（四态分布）

| 层 | 模块数 | ALIVE | PARTIAL | DEAD | ORPHAN |
|---|---|---|---|---|---|
| backend services（顶层） | 410 | 349 | 54 | 6 | 1 |
| backend orchestration | 92 | 87 | 1 | 4 | 0 |
| backend services 子包 | 20 | 20 | 0 | 0 | 0 |
| api/v1 路由组（router.py） | 109 | 107 | 0 | 2（flag 双闸） | 0 |
| gateway 代理面 | 84 | 84 | 0 | 0 | 0 |
| mobile features | 44 | 43 | 0 | 0 | 1 |
| **合计** | **759** | **690** | **55** | **12** | **2** |

> 判定口径：ALIVE=入口可达且有生产消费；PARTIAL=入口弱（仅同层互调/零测试/单消费者）或宣称面大于接线面；DEAD=零生产消费（含 rule-bj 豁免的 v1 未接线组件、flag 双闸不可达面）；ORPHAN=零消费零测试零引用。后端 5 个 gRPC servicer 的入口在仓根 grpc_server.py:40-44,69-87（app/ 扫描盲区，已人工校正为 ALIVE）。

## 一、新发现的不诚实面（本轮登记 V3-FIX-337～342）

| # | 判定 | 一句话 | 详述 |
|---|---|---|---|
| V3-FIX-337 | 断链 | /push/interaction：mobile 唯一写方→网关 404→后端端点不可达 | backend/app/api/v1/push_interaction.py:33 注册 POST /push/interaction；mobile/lib/core/services/notification_service.dart:367 经 api_endpoints.dart:591 POST 该路径并 catch 吞错；gateway proxy_routes.go 无 /push 组、setup.go:905-917 NoRoute 白名单仅 /api/v1/auth/*→永久 404。推送交互回执（打开/关闭）结构性零到达，push_feedback/notification_analytics 属「有端点无到达写方」=FIX-330 同形态 |
| V3-FIX-338 | 宣称执行≠执行 | GDPR login_attempt_cleanup beat 条目未入 worker include | app/celery_schedule.py:7-12 注册每日 04:00 cleanup-old-login-attempts-daily；但 app/core/celery_app.py:64-90 include 列表无 app.tasks.login_attempt_cleanup——按仓内自家 EI-02 学说（celery_app.py:73-75「模块必须随 worker 加载，否则消息按 unregistered task 被静默丢弃」）该 GDPR 宣称（90 天清理）在 worker 侧无注册面 |
| V3-FIX-339 | 孤儿任务模块 | guest_cleanup 两任务零 include/零 beat/零入队/零测试 | app/tasks/guest_cleanup.py:19,52 定义 tasks.cleanup_expired_guests / tasks.cleanup_guest_sessions；include 列表无、celery_schedule 无、全仓无 .delay/send_task；app/orchestration/context_sources.py:52 注释仍以 guest_cleanup 为活机制口径（游客过期行无清理执行方） |
| V3-FIX-340 | 测试在测死代码 | update_similarities 4 任务不可达，协同过滤零写入的机制成因 | app/tasks/update_similarities.py:30,61,90,119 四任务无 include/无 beat/无入队，唯一引用=tests/unit/test_stage38_perf_capacity.py:9（容量测试在测永不可达代码）；V3-FIX-07 R6「协同过滤 0 行休眠留观」的机制成因即此——相似度管道结构性零写入 |
| V3-FIX-341 | flag 双闸不可达 | GraphRAG monitor API 翻旗也无法经网关到达 | app/api/v1/router.py:317-319 flag 门注册 graph_monitor(/monitor/graph)+graphrag_trace(/graphrag)；app/config/settings.py:1061 ENABLE_GRAPHRAG_MONITOR_API 默认 False；gateway 无 /graphrag、/monitor 代理组（proxy_routes.go 全文无此段）——即使翻旗客户端仍 404，旗宣称的能力无兑现通道 |
| V3-FIX-342 | 孤儿屏 | features/onboarding 交互式引导 4 屏零路由零引用 | mobile/lib/features/onboarding/presentation/screens/interactive_onboarding_screen.dart 无 GoRoute 注册（routes.dart 无 import 无 path）、barrel onboarding.dart 零外部消费者；活性引导=/onboarding/persona（user feature，routes.dart:162-164）。V3-FIX-198/199 在该屏登记的文案问题，其载体本身不可达 |

## 二、DEAD 模块分节详述（后端 10+1）

### 2.1 rule-bj 豁免族（9 个，v1 未接线组件）

九个模块携带头注 `# rule-bj: exempt v1 未接线组件（评估器/分类器/工具），保留待接线——见 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md`，但 KNOWN_CODE_DEBT_LEDGER.md 全文无任一模块名条目（唯一 bert 提及=wt504 mypy 棘轮行）——**豁免头的台账指针是 dangling 引用**；豁免的真实登记面是 scripts/guards/check_rule_bj_dead_imports.py:14,473（守卫机制）与 接力日志.md:41（「13 个 v1 未接线组件加 rule-bj 豁免头」批次记录）。判定 DEAD（引用不重登，豁免机制本身在账）：

| 模块 | 测试面 | 诚实性注记 |
|---|---|---|
| orchestration/bert_intent_classifier | 1f/23r | /multi-intent 端点实走 LLM（multi_intent_service.py:20,30 import llm_router/LLMService，无 bert）——BERT 意图分类宣称与实现无关 |
| orchestration/intent_cache | 1f/2r | intent_monitor.py:75-110 声明 intent_cache_hits/misses/hit_rate 指标——两模块同死，指标从未注册，观测面不存在 |
| orchestration/intent_monitor | 0 | 同上 |
| orchestration/user_intent_profiler | 0 | — |
| services/capability_selection_evaluator | 0 | session_state_mixin.py:277-289 透传的 capability_selection 报告源自 situation_brief，与本评估器无关 |
| services/experience_phase_evaluator | 1f/1r | — |
| services/five_layer_learning_evaluator | 0 | 同族 contract ALIVE（8 消费者），evaluator 死——五层评估宣称无运行时 |
| services/planning_benchmark_evaluator | 0 | 同族 service 弱活 |
| services/understanding_benchmark_evaluator | 0 | 同族 service 亦零外部消费（双死岛） |

### 2.2 非豁免 DEAD

- **services/community_context_boundary**（DEAD，3f/7r 测试在测）：docstring 自称「S-02 · Community Context Privacy Boundary——群上下文隐私红线（单一守卫面）」，全仓零生产 import。隐私红线守卫未接线=隐私宣称大于保障面。未在台账、无 rule-bj 头。
- **services/profile_eval_runner**（ORPHAN-工具）：argparse CLI（`if __name__ == "__main__"` 尾入口），消费 profile_eval_llm_judge（活）；按仓库整洁标准属一次性/开发工具，宜迁 scripts/devtools/ 或显式登记。

### 2.3 Celery 任务面专节（include 列表为权威，celery_app.py:64-90）

| 任务模块 | 任务数 | include | beat/入队 | 判定 |
|---|---|---|---|---|
| app/core/celery_tasks | 多 | ✓ | beat 多条 | ALIVE |
| app/tasks/accountability_tasks | ✓ | ✓ morning/evening | ALIVE |
| app/tasks/absence_scan_task | ✓ | beat | ALIVE |
| app/tasks/checkpoint_nudge_task | ✓ | beat 两条 | ALIVE |
| app/tasks/community_checkin_reminder | ✓ | beat | ALIVE |
| app/tasks/policy_tasks | ✓ | beat | ALIVE |
| app/tasks/user_session_cleanup | ✓ | beat | ALIVE |
| app/tasks/economy_metrics_snapshot | ✓ | beat | ALIVE |
| app/tasks/login_attempt_cleanup | ✗ | 仅 celery_schedule（worker 侧无注册面） | PARTIAL→V3-FIX-338 |
| app/tasks/guest_cleanup | ✗ | 无 | DEAD→V3-FIX-339 |
| app/tasks/update_similarities | ✗ | 无（仅测试） | DEAD→V3-FIX-340 |
| app/workers/signals_learning_worker / cost_wvpl_worker / aurora.tasks | ✓ | beat | ALIVE |

## 三、路由面与网关覆盖 diff（诚实性主轴）

- router.py 实际 include 117 处/109 个模块组（含 community 5 组同前缀、error_book 双 router）。
- gateway 显式代理组 ~72 + missing-loop 补注册 11 组（proxy_routes.go:1228-1253：/analytics /audit /counterfactual /error-book /release_approvals /release-flags /research /safe-experiments /scenario-packs /skills /subtasks）+ 原生 Go handler 3 面（/me/files 族 file_handler.go:85-89、galaxy 族 galaxy_handler.go:66+、/health 本地 setup.go:495）+ NoRoute 白名单仅 /api/v1/auth/*（setup.go:905-917）。
- **网关未覆盖的后端路由段仅 3 个**：/graphrag、/monitor/graph（=V3-FIX-341 双闸）、/push（=V3-FIX-337 断链）。其余 106 组首段全有代理。
- client 侧反向 diff（mobile/lib/core/network/api_endpoints.dart 全量路径首段 62 个 vs 网关组）：仅 /push 无着落；/me、/reviews、/runs 均有（/me 走 Go 原生 handler）。mobile 幻影端点净额=1。

## 四、mobile features 生死簿（44）

- routes.dart 直连路由的 feature 32 个（imports+GoRoute 实证）。
- 无独立路由但被其他 feature 消费的 11 个：aurora（dashboard/session_refresh）、document（tools/tool_registry+chat_input）、experience（dashboard/memory/community）、file（chat providers）、intent（chat 意图预览）、journey（dashboard first_action_card.dart:65）、knowledge（insights/tools/词库仓库）、mirofish（theater/simulation/report 共用里程碑服务）、recovery（home/task/goal）、settings（openclaw hub）、vocabulary（tools+knowledge 仓库）——判定 ALIVE（库形态复用，非屏）。
- ORPHAN 1 个：onboarding（=V3-FIX-342，屏级孤儿；概念上的引导完成态由 user feature 的 onboardingCompletedProvider 承载，routes.dart:165）。

## 五、services 子包（20，全 ALIVE）

| 子包 | 生产消费 | 测试 | 备注 |
|---|---|---|---|
| personalization | 60 | 26f | 最重 |
| llm | 79 | 20f | 最重消费 |
| galaxy | 49 | 38f | — |
| evidence | 21 | 13f | — |
| cognitive | 25 | 1f | 测试单薄（PARTIAL 边缘，因消费强判 ALIVE） |
| card_protocol | 17 | 18f | KNOWN_CODE_DEBT_LEDGER 已有专条（动前必读） |
| analytics | 8 | 24f | — |
| simulation | 6 | 5f | — |
| report | 4 | 4f | — |
| openclaw | 4 | 2f | — |
| theater | 3 | 5f | — |
| skill_store | 3 | 4f | — |
| stt | 3 | 6f | — |
| compliance | 2 | 2f | — |
| action_commands | 2 | 1f | — |
| skill_share | 1 | 2f | — |
| push_strategies | 1 | 3f | — |
| analysis | 1 | 2f | — |
| ml | 1 | 1f | recall_ranker 经 app/signals/recall_opportunity.py:507 惰性导入（索引盲区已校正） |
| lua | 0 py-import | 0 | **非死**：Redis Lua 脚本按文件路径加载（app/core/llm_quota.py:38、services/quota.py:16-17）——import 索引盲区的实证案例 |

## 六、后端模块总表（502 行，机械证据）

### 6.1 app/services（410）

| 模块 | 判定 | 入口证据 | 生产消费数 | 测试 | 注记 |
|---|---|---|---|---|---|
| accountability_achievement_service | ALIVE | tasks:app/tasks/accountability_tasks.py:632; services:app/services/guest_seed_service.py:115 | 8 | 1f/4r | — |
| accountability_mvp_service | ALIVE | api:app/api/v1/experience/community_router.py:25 | 4 | 2f/2r | — |
| accountability_notification_service | ALIVE | tasks:app/tasks/accountability_tasks.py:30; services:app/services/policy_scheduler_service.py:17 | 21 | 7f/28r | — |
| achievement_engine | ALIVE | consumers:app/consumers/achievement_plan_consumer.py:10; services:app/services/achievement_event_consumer.py:28 | 40 | 22f/46r | — |
| achievement_event_consumer | ALIVE | main:app/main.py:53 | 13 | 7f/19r | — |
| achievement_reward_observability | ALIVE | core:app/core/celery_tasks.py:1638; services:app/services/achievement_engine.py:56 | 4 | 1f/1r | — |
| action_allocation_policy | ALIVE | aurora:app/aurora/joint_decision.py:97; services:app/services/first_action_service.py:52 | 21 | 12f/18r | — |
| action_authorization | ALIVE | services:app/services/action_command_service.py:266 | 6 | 4f/4r | — |
| action_command_service | ALIVE | services:app/services/first_action_service.py:53; api:app/api/v1/action_proposals.py:37 | 15 | 8f/11r | — |
| action_permission_service | ALIVE | services:app/services/action_command_service.py:66; api:app/api/v1/action_permissions.py:34 | 11 | 4f/9r | — |
| agent_grpc_service | ALIVE | grpc_server.py:40,69 | 14 | 13f/22r | — |
| agent_run_service | ALIVE | agents:app/agents/standard_workflow.py:3802; orchestration:app/orchestration/executor.py:178 | 36 | 15f/32r | — |
| agent_stats_service | ALIVE | api:app/api/v1/agent_stats.py:24 | 2 | 1f/1r | — |
| analytics_service | ALIVE | services:app/services/analysis/unified_analysis_service.py:15; api:app/api/v1/chat.py:36 | 4 | 3f/7r | — |
| arbitration_service | ALIVE | services:app/services/agent_grpc_service.py:1652 | 5 | 1f/1r | — |
| asset_review_signal_processor | PARTIAL | api:app/api/v1/assets.py:29 | 1 | 0f/0r | 零测试 |
| audit_service | PARTIAL | api:app/api/v1/audit.py:17 | 1 | 0f/0r | 零测试 |
| aurora_calibration_card_service | ALIVE | services:app/services/aurora_confirm_bridge_service.py:34; api:app/api/v1/aurora.py:26 | 4 | 1f/1r | — |
| aurora_calibration_service | PARTIAL | orchestration:app/orchestration/session_state_mixin.py:830 | 1 | 0f/0r | 零测试 |
| aurora_confirm_bridge_service | ALIVE | services:app/services/aurora_control_surface_service.py:200; api:app/api/v1/aurora.py:266 | 6 | 1f/3r | — |
| aurora_control_surface_service | ALIVE | signals:app/signals/spine_orchestrator.py:476; orchestration:app/orchestration/context_builder.py:1010 | 18 | 2f/12r | — |
| aurora_doc_context_kill_switch_service | ALIVE | core:app/core/context_pack.py:69; agents:app/agents/standard_workflow.py:80 | 4 | 1f/1r | — |
| aurora_dual_core_router_kill_switch_service | ALIVE | orchestration:app/orchestration/routing_engine.py:38 | 2 | 2f/2r | — |
| aurora_privacy_kill_switch_service | ALIVE | aurora:app/aurora/privacy.py:117 | 2 | 0f/0r | — |
| aurora_receipt_service | ALIVE | api:app/api/v1/aurora_receipts.py:26 | 3 | 2f/2r | — |
| aurora_stage18_kill_switch_service | ALIVE | core:app/core/context_pack.py:2283; state_aggregator:app/state_aggregator/service.py:43 | 13 | 2f/6r | — |
| aurora_stage19_kill_switch_service | ALIVE | services:app/services/llm_extractor_service.py:13; api:app/api/v1/memory_admin.py:37 | 24 | 10f/18r | — |
| aurora_stage20_kill_switch_service | ALIVE | state_aggregator:app/state_aggregator/service.py:1178; orchestration:app/orchestration/routing_engine.py:39 | 5 | 1f/2r | — |
| aurora_stage21_kill_switch_service | ALIVE | orchestration:app/orchestration/routing_engine.py:40; services:app/services/skill_content_reader.py:9 | 14 | 3f/8r | — |
| aurora_stage23_kill_switch_service | ALIVE | services:app/services/bayesian_routing_wire_service.py:9; api:app/api/v1/memory_admin.py:39 | 6 | 1f/4r | — |
| aurora_stage24_policy_kill_switch_service | ALIVE | services:app/services/policy_compiler_service.py:18; api:app/api/v1/memory_admin.py:40 | 4 | 1f/1r | — |
| aurora_stage25_reflection_kill_switch_service | ALIVE | services:app/services/task_reflection_service.py:26; api:app/api/v1/memory_admin.py:41 | 4 | 2f/2r | — |
| aurora_stage26_scene_kill_switch_service | ALIVE | services:app/services/scene_consolidation_service.py:25; api:app/api/v1/memory_admin.py:42 | 10 | 8f/8r | — |
| aurora_stage27_foresight_kill_switch_service | ALIVE | core:app/core/celery_tasks.py:2357; services:app/services/jitai_trigger_service.py:19 | 9 | 4f/5r | — |
| aurora_stage28_traits_kill_switch_service | ALIVE | services:app/services/traits_coldstart_service.py:11; api:app/api/v1/memory_admin.py:44 | 5 | 2f/2r | — |
| aurora_stage29_srl_kill_switch_service | ALIVE | event_publishers:app/event_publishers/srl_events.py:10; services:app/services/intervention_service.py:31 | 15 | 10f/10r | — |
| aurora_stage30_metacognition_kill_switch_service | ALIVE | services:app/services/intervention_service.py:34; api:app/api/v1/memory_admin.py:46 | 4 | 1f/1r | — |
| aurora_stage31_idiographic_kill_switch_service | ALIVE | services:app/services/idiographic_association_service.py:41; api:app/api/v1/memory_admin.py:47 | 3 | 1f/1r | — |
| aurora_stage33_kill_switch_service | ALIVE | core:app/core/celery_tasks.py:3277; state_aggregator:app/state_aggregator/service.py:44 | 11 | 3f/3r | — |
| aurora_stage34_kill_switch_service | ALIVE | consumers:app/consumers/journey_consumer_base.py:14; orchestration:app/orchestration/context_builder.py:49 | 5 | 1f/1r | — |
| aurora_stage35_kill_switch_service | ALIVE | orchestration:app/orchestration/routing_engine.py:42 | 2 | 1f/1r | — |
| aurora_stage37_llm_safety_kill_switch_service | ALIVE | core:app/core/llm_secure_io.py:11 | 2 | 2f/22r | — |
| aurora_stage38_kill_switch_service | ALIVE | core:app/core/celery_tasks.py:544; services:app/services/error_replan_bridge.py:28 | 8 | 3f/4r | — |
| aurora_stage39_kill_switch_service | ALIVE | orchestration:app/orchestration/context_builder.py:50 | 4 | 3f/3r | — |
| aurora_stage40_calendar_kill_switch_service | ALIVE | core:app/core/context_manager.py:24 | 4 | 1f/3r | — |
| auth_session_service | ALIVE | core:app/core/cache.py:31; api:app/api/deps.py:16 | 10 | 4f/18r | — |
| batch_worklane | ALIVE | core:app/core/celery_app.py:532; services:app/services/task_reflection_service.py:27 | 15 | 2f/38r | — |
| bayesian_routing_wire_service | ALIVE | orchestration:app/orchestration/routing_engine.py:44 | 3 | 2f/2r | — |
| behavior_signal_collector | ALIVE | services:app/services/profile_event_consumer.py:28 | 11 | 3f/9r | — |
| behavioral_outcome_tracker | ALIVE | api:app/api/v1/interventions.py:22 | 2 | 2f/4r | — |
| billing_worker | ALIVE | main:app/main.py:54 | 2 | 1f/1r | — |
| budget_optimization_service | PARTIAL | core:app/core/celery_tasks.py:3801 | 1 | 0f/0r | 零测试 |
| budget_tuning_service | ALIVE | core:app/core/context_budget.py:35; services:app/services/budget_optimization_service.py:15 | 5 | 1f/1r | — |
| calendar_service | ALIVE | core:app/core/context_manager.py:25; orchestration:app/orchestration/adaptive_replanner.py:656 | 8 | 3f/5r | — |
| candidate_generation_service | ALIVE | services:app/services/llm_dispatcher.py:21 | 10 | 1f/13r | — |
| capability_knob_governor | PARTIAL | orchestration:app/orchestration/experience_actuator.py:9 | 1 | 0f/0r | 零测试 |
| capability_registry_service | ALIVE | orchestration:app/orchestration/situation_brief.py:18; services:app/services/capability_selection_evaluator.py:12 | 6 | 3f/3r | — |
| capability_selection_evaluator | DEAD | — | 0 | 0f/0r | rule-bj 豁免头；session_state_mixin.py:277-289 消费的 capability_selection 报告来自 situation_brief，非本模块 |
| capsule_event_consumer | ALIVE | main:app/main.py:55 | 4 | 1f/4r | — |
| capsule_favorite_service | ALIVE | core:app/core/context_manager.py:26; services:app/services/behavior_signal_collector.py:33 | 12 | 4f/9r | — |
| capsule_feedback_service | ALIVE | services:app/services/curiosity_capsule_service.py:20; api:app/api/v1/capsules.py:23 | 4 | 1f/2r | — |
| capsule_generation_service | ALIVE | core:app/core/celery_app.py:455; services:app/services/capsule_event_consumer.py:16 | 11 | 5f/10r | — |
| capsule_share_service | ALIVE | services:app/services/curiosity_capsule_service.py:24; api:app/api/v1/capsules.py:25 | 4 | 1f/2r | — |
| card_edge_service | ALIVE | services:app/services/card_protocol/card_operations_service.py:36 | 12 | 1f/1r | — |
| card_service | ALIVE | services:app/services/card_protocol/behavior_intervention_bridge.py:40 | 18 | 7f/17r | — |
| chat_signal_collector | ALIVE | orchestration:app/orchestration/orchestrator.py:167 | 4 | 3f/3r | — |
| checkpoint_nudge_service | ALIVE | tasks:app/tasks/checkpoint_nudge_task.py:9; orchestration:app/orchestration/orchestrator.py:168 | 17 | 8f/16r | — |
| circuit_breaker | ALIVE | services:app/services/embedding_service.py:33 | 9 | 14f/41r | — |
| cognitive_event_consumer | PARTIAL | main:app/main.py:56 | 1 | 0f/0r | 零测试 |
| cognitive_service | ALIVE | tools:app/tools/prism_tools.py:14; core:app/core/celery_app.py:553 | 113 | 9f/137r | — |
| collaboration_service | ALIVE | api:app/api/v1/community.py:193 | 4 | 3f/3r | — |
| collaborative_filtering_service | ALIVE | api:app/api/v1/recommendations.py:26 | 2 | 1f/1r | — |
| commitment_parser | ALIVE | services:app/services/memory_inferred_write_lane.py:30 | 6 | 5f/5r | — |
| community_advanced_service | ALIVE | services:app/services/community_service.py:1717; api:app/api/v1/community.py:194 | 4 | 1f/1r | — |
| community_context_boundary | DEAD | — | 7 | 3f/7r | S-02 隐私红线守卫自述『单一守卫面』却零生产消费（3 测试文件在测）——隐私宣称与接线不符 |
| community_error_aggregation_service | ALIVE | core:app/core/celery_tasks.py:3085; api:app/api/v1/galaxy.py:1190 | 2 | 0f/0r | — |
| community_feedback_service | ALIVE | api:app/api/v1/community.py:204 | 3 | 4f/5r | — |
| community_service | ALIVE | services:app/services/collaboration_service.py:54; api:app/api/v1/accountability.py:43 | 30 | 12f/27r | — |
| community_shared_error_service | ALIVE | api:app/api/v1/community_squad_shared_errors.py:29 | 2 | 2f/3r | — |
| community_signal_bridge | ALIVE | services:app/services/achievement_event_consumer.py:324; api:app/api/v1/community.py:218 | 15 | 5f/11r | — |
| community_signal_collector | PARTIAL | services:app/services/community_service.py:66 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| community_squad_board_service | ALIVE | api:app/api/v1/community_squad_board.py:19 | 4 | 3f/5r | — |
| community_squad_service | ALIVE | services:app/services/community_shared_error_service.py:55; api:app/api/v1/community_squad.py:27 | 12 | 4f/7r | — |
| community_strategy_service | PARTIAL | api:app/api/v1/community_strategy_outcomes.py:14 | 1 | 0f/0r | 零测试 |
| community_study_room_service | ALIVE | api:app/api/v1/community_study_room.py:29 | 3 | 1f/3r | — |
| companion_state_service | ALIVE | tools:app/tools/companion_tools.py:9; orchestration:app/orchestration/session_state_mixin.py:34 | 3 | 2f/2r | — |
| conflict_resolution_context | ALIVE | core:app/core/context_pack.py:70; orchestration:app/orchestration/sufficiency_checker.py:17 | 5 | 1f/4r | — |
| conflict_resolver_service | ALIVE | core:app/core/context_pack.py:76; services:app/services/conflict_resolution_context.py:58 | 13 | 6f/7r | — |
| constitutional_drift_firewall | ALIVE | services:app/services/capability_registry_service.py:9 | 5 | 1f/1r | — |
| content_quality_evaluator | ALIVE | services:app/services/response_feedback_service.py:29 | 3 | 2f/2r | — |
| context_cache_key | ALIVE | orchestration:app/orchestration/context_builder.py:51 | 3 | 2f/13r | — |
| context_pack_telemetry_service | PARTIAL | core:app/core/context_pack.py:77 | 1 | 0f/0r | 零测试 |
| context_retrieval_pipeline | ALIVE | orchestration:app/orchestration/graph_rag.py:33; services:app/services/galaxy/retrieval_service.py:29 | 8 | 4f/5r | — |
| curiosity_capsule_service | ALIVE | services:app/services/push_service.py:14; api:app/api/v1/capsules.py:26 | 4 | 2f/8r | — |
| custom_expert_service | ALIVE | orchestration:app/orchestration/mode_workflow_config.py:17; api:app/api/v1/multi_agent.py:23 | 14 | 4f/8r | — |
| daily_task_selection_service | ALIVE | services:app/services/growth_dashboard_service.py:22; api:app/api/v1/tasks.py:69 | 15 | 8f/15r | — |
| dashboard_service | ALIVE | core:app/core/celery_app.py:399; api:app/api/v1/dashboard.py:7 | 14 | 2f/12r | — |
| decay_service | ALIVE | services:app/services/scheduler_service.py:19; api:app/api/v1/decay_timemachine.py:18 | 5 | 1f/2r | — |
| decision_record_service | ALIVE | orchestration:app/orchestration/context_builder.py:1618; services:app/services/push_service.py:446 | 6 | 2f/2r | — |
| device_service | ALIVE | core:app/core/websocket.py:47; services:app/services/notification_push_service.py:130 | 3 | 0f/0r | — |
| dictionary_package_service | ALIVE | api:app/api/v1/vocabulary.py:22 | 3 | 2f/3r | — |
| directive_audit_service | PARTIAL | api:app/api/v1/insights.py:10 | 1 | 0f/0r | 零测试 |
| document_feedback_event_consumer | PARTIAL | main:app/main.py:57 | 1 | 0f/0r | 零测试 |
| document_service | ALIVE | agents:app/agents/standard_workflow.py:81; orchestration:app/orchestration/graph_rag.py:1266 | 16 | 10f/35r | — |
| document_upload_storage | ALIVE | other:app/middleware/admin_audit.py:252; services:app/services/file_processing_orchestrator.py:24 | 8 | 5f/8r | — |
| embedding_service | ALIVE | tools:app/tools/material_retrieval_tools.py:10; core:app/core/celery_app.py:230 | 49 | 34f/112r | — |
| equipment_service | ALIVE | other:app/data/migrate_equipment_state.py:8; services:app/services/inventory_service.py:21 | 5 | 1f/1r | — |
| error_book_grpc_service | ALIVE | grpc_server.py:41,73 | 0 | 0f/0r | — |
| error_book_mastery_sync_service | ALIVE | services:app/services/error_book_service.py:1336 | 21 | 9f/19r | — |
| error_book_service | ALIVE | tools:app/tools/error_tools.py:16; core:app/core/celery_app.py:282 | 38 | 12f/30r | — |
| error_book_signal_processor | ALIVE | services:app/services/error_book_service.py:1327 | 7 | 3f/4r | — |
| error_knowledge_linker | PARTIAL | services:app/services/error_book_service.py:301 | 2 | 1f/1r | 仅同层互调、消费/测试单薄 |
| error_pattern_template_service | ALIVE | api:app/api/v1/error_book.py:33 | 8 | 2f/7r | — |
| error_replan_bridge | ALIVE | services:app/services/galaxy_event_consumer.py:146; aurora:app/aurora/runtime_v1/dashboard.py:841 | 43 | 15f/54r | — |
| event_retention_service | PARTIAL | services:app/services/scheduler_service.py:20 | 1 | 0f/0r | 1 服务层消费者、0 测试 |
| event_service | ALIVE | api:app/api/v1/events.py:27 | 3 | 3f/3r | — |
| evidence_health_service | ALIVE | services:app/services/memory_jobs.py:22; api:app/api/v1/memory_admin.py:50 | 6 | 2f/2r | — |
| evidence_insight_service | PARTIAL | api:app/api/v1/insights.py:61 | 1 | 0f/0r | 零测试 |
| evidence_scoring | ALIVE | services:app/services/evidence_health_service.py:21 | 4 | 1f/1r | — |
| exam_sprint_dashboard_service | ALIVE | core:app/core/celery_tasks.py:1937; api:app/api/v1/exam_sprint.py:23 | 9 | 5f/8r | — |
| exam_sprint_diagnostic_service | ALIVE | api:app/api/v1/exam_sprint.py:24 | 7 | 5f/7r | — |
| exam_sprint_intake_service | ALIVE | api:app/api/v1/exam_sprint.py:25 | 6 | 3f/6r | — |
| exam_sprint_review_service | ALIVE | core:app/core/celery_tasks.py:1178; services:app/services/task_service.py:921 | 15 | 5f/10r | — |
| execution_event_consumer | PARTIAL | main:app/main.py:58 | 1 | 0f/0r | 零测试 |
| execution_ingestor | ALIVE | services:app/services/execution_service.py:60 | 18 | 6f/22r | — |
| execution_learning_service | ALIVE | services:app/services/execution_ingestor.py:35 | 8 | 2f/5r | — |
| execution_node_service | PARTIAL | services:app/services/execution_service.py:62 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| execution_preference_service | ALIVE | orchestration:app/orchestration/orchestrator.py:170; services:app/services/execution_service.py:63 | 4 | 1f/1r | — |
| execution_profile_service | ALIVE | api:app/api/v1/executions.py:21 | 4 | 2f/2r | — |
| execution_quality_service | ALIVE | services:app/services/execution_ingestor.py:36 | 3 | 1f/1r | — |
| execution_result_validator | ALIVE | orchestration:app/orchestration/validation_engine.py:945; services:app/services/execution_ingestor.py:37 | 5 | 1f/1r | — |
| execution_risk_assessor | ALIVE | services:app/services/execution_service.py:66; adapters:app/adapters/openclaw/intent_translator.py:8 | 2 | 0f/0r | — |
| execution_run_producer | ALIVE | services:app/services/execution_service.py:67 | 4 | 3f/5r | — |
| execution_schedule_service | ALIVE | services:app/services/scheduler_service.py:21; api:app/api/v1/executions.py:23 | 6 | 2f/4r | — |
| execution_service | ALIVE | orchestration:app/orchestration/execution_engine.py:53; services:app/services/execution_schedule_service.py:181 | 36 | 12f/35r | — |
| execution_template_service | PARTIAL | services:app/services/execution_service.py:68 | 2 | 2f/2r | 仅同层互调、消费/测试单薄 |
| expansion_service | ALIVE | core:app/core/celery_tasks.py:485; workers:app/workers/expansion_worker.py:15 | 21 | 6f/9r | — |
| experience_memory_projector | ALIVE | orchestration:app/orchestration/context_builder.py:52; services:app/services/policy_patch_service.py:88 | 5 | 3f/3r | — |
| experience_phase_evaluator | DEAD | — | 1 | 1f/1r | rule-bj 豁免头；1 测试引用 |
| feature_extraction_service | ALIVE | services:app/services/llm_dispatcher.py:23 | 6 | 2f/7r | — |
| feedback_adjustment_service | ALIVE | services:app/services/achievement_event_consumer.py:135 | 5 | 4f/4r | — |
| feedback_driven_generation | ALIVE | services:app/services/agent_grpc_service.py:1422 | 4 | 1f/2r | — |
| feedback_learning_service | PARTIAL | services:app/services/agent_grpc_service.py:1109 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| feedback_service | ALIVE | api:app/api/v1/tasks.py:70 | 1 | 6f/45r | — |
| file_processing_orchestrator | ALIVE | core:app/core/celery_tasks.py:195 | 3 | 0f/0r | — |
| first_action_service | ALIVE | services:app/services/hybrid_journey_service.py:59; api:app/api/v1/journey.py:41 | 16 | 3f/15r | — |
| five_layer_learning_contract | ALIVE | services:app/services/capability_registry_service.py:10 | 8 | 1f/1r | — |
| five_layer_learning_evaluator | DEAD | — | 0 | 0f/0r | rule-bj 豁免头；同族 five_layer_learning_contract 活（8 消费者），evaluator 死 |
| fme_kill_switch_service | PARTIAL | api:app/api/v1/goal_intent.py:31 | 1 | 0f/0r | 零测试 |
| fme_l3_closure_bridge | PARTIAL | aurora:app/aurora/core_session.py:745 | 1 | 0f/0r | 零测试 |
| fme_strategy_change_emitter | PARTIAL | services:app/services/fme_l3_closure_bridge.py:27 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| focus_context_service | ALIVE | services:app/services/focus_service.py:28; api:app/api/v1/tasks.py:71 | 6 | 1f/2r | — |
| focus_service | ALIVE | tools:app/tools/task_tools.py:15; core:app/core/context_manager.py:28 | 34 | 14f/50r | — |
| focus_signal_processor | ALIVE | services:app/services/profile_event_consumer.py:32 | 4 | 2f/4r | — |
| follow_up_question_service | PARTIAL | orchestration:app/orchestration/routing_engine.py:46 | 1 | 0f/0r | 零测试 |
| foresight_deviation_service | ALIVE | services:app/services/predictive_service.py:66 | 4 | 3f/3r | — |
| friction_chat_wiring | ALIVE | orchestration:app/orchestration/orchestrator.py:2126 | 6 | 5f/6r | — |
| friend_match_service | ALIVE | services:app/services/recommendation_feedback_service.py:117; api:app/api/v1/community.py:219 | 3 | 1f/1r | — |
| galaxy_bootstrap_service | ALIVE | consumers:app/consumers/galaxy_plan_consumer.py:12; api:app/api/v1/profile_transparency.py:1391 | 3 | 1f/1r | — |
| galaxy_event_consumer | ALIVE | main:app/main.py:60 | 6 | 3f/5r | — |
| galaxy_execution_consumer | ALIVE | main:app/main.py:61 | 4 | 2f/3r | — |
| galaxy_feedback_signal_processor | PARTIAL | services:app/services/expansion_service.py:28 | 2 | 1f/1r | 仅同层互调、消费/测试单薄 |
| galaxy_grpc_service | ALIVE | grpc_server.py:42,77 | 10 | 5f/11r | — |
| galaxy_service | ALIVE | core:app/core/context_manager.py:29; signals:app/signals/spine_orchestrator.py:1131 | 66 | 42f/89r | — |
| gateway_client | ALIVE | services:app/services/task_service.py:33 | 5 | 2f/4r | — |
| glm_batch_service | ALIVE | services:app/services/node_sector_service.py:542; api:app/api/v1/capsules.py:27 | 19 | 4f/22r | — |
| goal_decomposition_service | ALIVE | api:app/api/v1/goals.py:28 | 2 | 1f/4r | — |
| goal_today_view | ALIVE | api:app/api/v1/experience/goal_router.py:23 | 8 | 5f/13r | — |
| goal_trajectory_service | ALIVE | api:app/api/v1/journey.py:21 | 9 | 3f/7r | — |
| graph_knowledge_service | ALIVE | api:app/api/v1/graph_monitor.py:21 | 5 | 3f/5r | — |
| graph_reasoning_service | ALIVE | tools:app/tools/growth_strategy_tools.py:10; services:app/services/expansion_service.py:837 | 8 | 3f/5r | — |
| graphrag_trace_store | ALIVE | orchestration:app/orchestration/graph_rag.py:39; api:app/api/v1/graphrag_trace.py:16 | 4 | 1f/1r | — |
| group_file_event_consumer | ALIVE | main:app/main.py:62 | 3 | 1f/2r | — |
| group_file_service | ALIVE | tools:app/tools/material_retrieval_tools.py:12; orchestration:app/orchestration/graph_rag.py:40 | 13 | 3f/7r | — |
| group_recommendation_service | ALIVE | services:app/services/recommendation_feedback_service.py:147; api:app/api/v1/community.py:221 | 6 | 4f/4r | — |
| growth_dashboard_service | ALIVE | services:app/services/dashboard_service.py:25; api:app/api/v1/experience/dashboard_router.py:19 | 17 | 8f/16r | — |
| guest_seed_service | ALIVE | main:app/main.py:546; api:app/api/v1/auth.py:1043 | 23 | 10f/21r | — |
| human_eval_review_service | ALIVE | services:app/services/understanding_benchmark_evaluator.py:10; other:scripts/review_human_eval_run.py:14 | 3 | 1f/1r | — |
| hybrid_journey_service | ALIVE | api:app/api/v1/journey.py:16 | 15 | 2f/13r | — |
| idiographic_association_service | ALIVE | main:app/main.py:63; core:app/core/celery_tasks.py:388 | 8 | 4f/4r | — |
| inference_grpc_service | ALIVE | grpc_server.py:43,87 | 0 | 0f/0r | — |
| insight_copy | ALIVE | orchestration:app/orchestration/context_builder.py:55; services:app/services/dashboard_service.py:26 | 9 | 0f/0r | — |
| insight_gap_detector | ALIVE | orchestration:app/orchestration/situation_brief.py:363 | 3 | 2f/2r | — |
| insight_prediction_service | PARTIAL | services:app/services/user_insight_compiler.py:19 | 2 | 1f/1r | 仅同层互调、消费/测试单薄 |
| insight_signal_registry | PARTIAL | services:app/services/user_insight_compiler.py:20 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| intelligent_task_service | ALIVE | api:app/api/v1/tasks.py:72 | 2 | 1f/1r | — |
| intervention_event_consumer | ALIVE | main:app/main.py:64 | 9 | 3f/9r | — |
| intervention_feedback_binding_service | ALIVE | tools:app/tools/intervention_tools.py:9; orchestration:app/orchestration/experience_actuator.py:11 | 4 | 1f/1r | — |
| intervention_lifecycle_service | ALIVE | services:app/services/evidence_insight_service.py:38 | 11 | 7f/8r | — |
| intervention_outcome_tracker | ALIVE | api:app/api/v1/interventions.py:23 | 7 | 1f/6r | — |
| intervention_record_service | ALIVE | tools:app/tools/intervention_tools.py:10; services:app/services/card_protocol/behavior_intervention_bridge.py:41 | 20 | 8f/8r | — |
| intervention_service | ALIVE | api:app/api/v1/interventions.py:24 | 3 | 2f/2r | — |
| intervention_strategy_learner | ALIVE | tools:app/tools/intervention_tools.py:11; services:app/services/card_protocol/behavior_intervention_bridge.py:42 | 6 | 2f/2r | — |
| inventory_service | ALIVE | api:app/api/v1/inventory.py:21 | 5 | 2f/12r | — |
| jitai_trigger_service | ALIVE | services:app/services/predictive_service.py:67 | 8 | 6f/8r | — |
| job_service | ALIVE | main:app/main.py:65; other:scripts/devtools/test_job_service.py:4 | 2 | 1f/2r | — |
| jpush_sender_service | PARTIAL | services:app/services/notification_push_service.py:131 | 2 | 1f/1r | 仅同层互调、消费/测试单薄 |
| kill_switch_readiness_service | ALIVE | api:app/api/v1/admin_dashboard.py:220 | 3 | 1f/1r | — |
| knowledge_integration_service | ALIVE | api:app/api/v1/galaxy.py:65 | 5 | 3f/3r | — |
| knowledge_service | ALIVE | tools:app/tools/material_retrieval_tools.py:13; core:app/core/celery_app.py:714 | 13 | 8f/19r | — |
| layer_conflict_resolver | ALIVE | services:app/services/companion_state_service.py:18 | 4 | 1f/1r | — |
| leaderboard_self_anchor_service | PARTIAL | api:app/api/v1/leaderboards.py:24 | 1 | 0f/0r | 零测试 |
| leaderboard_service | ALIVE | api:app/api/v1/accountability.py:44 | 12 | 8f/11r | — |
| learning_asset_service | ALIVE | workers:app/workers/cleanup_worker.py:65; api:app/api/v1/assets.py:30 | 15 | 2f/14r | — |
| llm_dispatcher | ALIVE | services:app/services/inference_grpc_service.py:16 | 17 | 5f/16r | — |
| llm_extractor_service | ALIVE | services:app/services/working_memory_pipeline_service.py:10 | 5 | 4f/4r | — |
| llm_fallback_utils | ALIVE | tools:app/tools/plan_tools.py:30; core:app/core/unified_intent_router.py:21 | 48 | 8f/22r | — |
| llm_service | ALIVE | core:app/core/llm_router.py:1878; agents:app/agents/enhanced_agents.py:15 | 164 | 75f/264r | — |
| ltm_health_snapshot | ALIVE | services:app/services/memory_jobs.py:24; api:app/api/v1/memory_admin.py:51 | 3 | 1f/1r | — |
| ltm_release_gate | ALIVE | api:app/api/v1/memory_admin.py:52 | 2 | 1f/1r | — |
| ltm_rollout_service | ALIVE | core:app/core/context_budget.py:29; services:app/services/memory_service.py:34 | 5 | 1f/1r | — |
| main_chain_artifact_consumer | ALIVE | main:app/main.py:66 | 2 | 1f/1r | — |
| mdx_dictionary_service | ALIVE | services:app/services/dictionary_package_service.py:12; api:app/api/v1/vocabulary.py:25 | 2 | 0f/0r | — |
| memory_conflict_resolver | ALIVE | core:app/core/context_pack.py:80 | 3 | 2f/2r | — |
| memory_epistemic_contract | ALIVE | services:app/services/conflict_resolver_service.py:61; api:app/api/v1/memory.py:19 | 17 | 8f/10r | — |
| memory_eval_service | ALIVE | api:app/api/v1/memory_admin.py:54 | 2 | 1f/1r | — |
| memory_evolution_service | ALIVE | services:app/services/memory_service.py:43 | 3 | 2f/2r | — |
| memory_inferred_write_lane | ALIVE | orchestration:app/orchestration/persistence_layer.py:16; services:app/services/llm_extractor_service.py:15 | 37 | 21f/33r | — |
| memory_invalidation_pipeline | ALIVE | services:app/services/conflict_resolver_service.py:69; api:app/api/v1/memory.py:472 | 10 | 5f/5r | — |
| memory_jobs | ALIVE | core:app/core/celery_tasks.py:3448; services:app/services/ltm_health_snapshot.py:117 | 12 | 4f/6r | — |
| memory_policy_evaluator | ALIVE | services:app/services/memory_service.py:45 | 4 | 1f/1r | — |
| memory_provenance_service | ALIVE | services:app/services/aurora_receipt_service.py:31; api:app/api/v1/aurora_receipts.py:27 | 8 | 4f/5r | — |
| memory_rank_policy_service | ALIVE | core:app/core/context_pack.py:81; api:app/api/v1/memory_admin.py:57 | 4 | 2f/2r | — |
| memory_retrieval_prefilter | ALIVE | core:app/core/context_manager.py:30; orchestration:app/orchestration/context_builder.py:56 | 24 | 7f/15r | — |
| memory_service | ALIVE | core:app/core/context_manager.py:31; consumers:app/consumers/user_memory_seed_consumer.py:6 | 134 | 56f/232r | — |
| memory_settings_service | ALIVE | api:app/api/v1/memory_settings.py:11 | 2 | 1f/1r | — |
| memory_storage_gate | ALIVE | services:app/services/memory_service.py:983 | 11 | 6f/12r | — |
| memory_use_selfcheck | ALIVE | core:app/core/context_manager.py:32; orchestration:app/orchestration/context_builder.py:58 | 13 | 9f/13r | — |
| metacognition_guard | ALIVE | services:app/services/metacognition_service.py:32; other:scripts/check_rule_ao_no_diagnostic_labels.py:13 | 3 | 1f/1r | — |
| metacognition_registry | ALIVE | services:app/services/metacognition_service.py:33; other:scripts/check_rule_ao_no_diagnostic_labels.py:14 | 4 | 1f/2r | — |
| metacognition_service | ALIVE | core:app/core/celery_tasks.py:1391; state_aggregator:app/state_aggregator/service.py:47 | 11 | 6f/7r | — |
| milestone_handler | ALIVE | services:app/services/task_state_sync.py:27 | 12 | 5f/11r | — |
| model_fallback_service | PARTIAL | agents:app/agents/graph/nodes/review_nodes.py:49 | 1 | 0f/0r | 零测试 |
| multi_intent_service | ALIVE | api:app/api/v1/multi_intent.py:20 | 2 | 2f/2r | — |
| next_action_selection_service | ALIVE | services:app/services/next_step_service.py:403; api:app/api/v1/tasks.py:1739 | 2 | 0f/0r | — |
| next_step_service | PARTIAL | api:app/api/v1/tasks.py:1465 | 1 | 0f/0r | 零测试 |
| nightly_review_service | ALIVE | services:app/services/scheduler_service.py:23; api:app/api/v1/nightly_reviews.py:9 | 2 | 1f/2r | — |
| node_sector_service | ALIVE | core:app/core/celery_app.py:590; other:app/schemas/galaxy.py:14 | 28 | 7f/17r | — |
| north_star_metrics_service | ALIVE | orchestration:app/orchestration/planning_workflow.py:839; services:app/services/exam_sprint_intake_service.py:42 | 8 | 1f/1r | — |
| north_star_wvpl_service | ALIVE | core:app/core/cost_wvpl_metrics.py:95; api:app/api/v1/north_star_wvpl.py:37 | 9 | 5f/7r | — |
| notification_analytics_service | ALIVE | api:app/api/v1/notification_center.py:31 | 2 | 1f/1r | — |
| notification_center_service | ALIVE | core:app/core/celery_tasks.py:1778; api:app/api/v1/notification_center.py:32 | 7 | 5f/5r | — |
| notification_push_service | ALIVE | services:app/services/community_service.py:930; api:app/api/v1/community.py:1269 | 12 | 3f/4r | — |
| notification_service | ALIVE | tasks:app/tasks/community_checkin_reminder.py:26; core:app/core/celery_app.py:367 | 54 | 14f/27r | — |
| nudge_event_consumer | ALIVE | main:app/main.py:67 | 3 | 1f/2r | — |
| nudge_service | ALIVE | services:app/services/analytics/behavior_pattern_service.py:18 | 18 | 2f/17r | — |
| ocr_service | ALIVE | services:app/services/error_book_service.py:51; api:app/api/v1/error_book.py:63 | 4 | 1f/1r | — |
| omnibar_service | ALIVE | api:app/api/v1/omnibar.py:7 | 6 | 2f/5r | — |
| openclaw_connection_profile_service | ALIVE | services:app/services/execution_service.py:69; api:app/api/v1/executions.py:25 | 3 | 1f/1r | — |
| outcome_capture_service | ALIVE | services:app/services/execution_ingestor.py:649; other:scripts/devtools/p15_outcome_absorption_probe.py:67 | 20 | 9f/18r | — |
| outcome_learning_service | ALIVE | services:app/services/intervention_record_service.py:33 | 4 | 3f/3r | — |
| outcome_ledger_service | ALIVE | services:app/services/goal_trajectory_service.py:48 | 10 | 7f/7r | — |
| outcome_promotion_governor | ALIVE | core:app/core/celery_app.py:1033; services:app/services/behavioral_outcome_tracker.py:12 | 6 | 3f/6r | — |
| passive_signal_tracker | PARTIAL | api:app/api/v1/interventions.py:25 | 1 | 0f/0r | 零测试 |
| perceptible_intelligence_service | ALIVE | core:app/core/celery_tasks.py:524; orchestration:app/orchestration/session_state_mixin.py:36 | 11 | 3f/7r | — |
| permission_service | PARTIAL | api:app/api/v1/auth.py:60 | 1 | 0f/0r | 零测试 |
| persdyn_attractor_service | ALIVE | core:app/core/celery_tasks.py:2348; services:app/services/idiographic_association_service.py:45 | 14 | 8f/11r | — |
| persona_service | ALIVE | tools:app/tools/persona_tools.py:8 | 4 | 4f/4r | — |
| photon_redeem_service | ALIVE | api:app/api/v1/photons.py:20 | 9 | 6f/10r | — |
| photon_service | ALIVE | core:app/core/celery_tasks.py:1639; services:app/services/achievement_engine.py:1754 | 34 | 17f/55r | — |
| plan_adjustment_applier | ALIVE | orchestration:app/orchestration/adaptive_replanner.py:35; services:app/services/intervention_event_consumer.py:41 | 7 | 5f/12r | — |
| plan_execution_record_service | ALIVE | orchestration:app/orchestration/multi_agent_adapter.py:35; services:app/services/execution_ingestor.py:38 | 14 | 4f/9r | — |
| plan_execution_validator | ALIVE | orchestration:app/orchestration/multi_agent_adapter.py:36 | 13 | 6f/10r | — |
| plan_feedback_service | ALIVE | orchestration:app/orchestration/execution_engine.py:2620; services:app/services/agent_grpc_service.py:946 | 4 | 1f/1r | — |
| plan_health_event_consumer | ALIVE | main:app/main.py:68 | 13 | 4f/16r | — |
| plan_health_signal_service | ALIVE | orchestration:app/orchestration/adaptive_replanner.py:36 | 9 | 3f/11r | — |
| plan_matching_service | ALIVE | orchestration:app/orchestration/context_builder.py:1892 | 2 | 0f/0r | — |
| plan_outcome_evaluator | PARTIAL | services:app/services/five_layer_learning_evaluator.py:10 | 2 | 1f/1r | 仅同层互调、消费/测试单薄 |
| plan_outcome_service | ALIVE | services:app/services/behavioral_outcome_tracker.py:13 | 6 | 3f/5r | — |
| plan_progress_service | ALIVE | orchestration:app/orchestration/adaptive_replanner.py:37; services:app/services/growth_dashboard_service.py:24 | 18 | 10f/14r | — |
| plan_quota_service | ALIVE | services:app/services/plan_service.py:389; api:app/api/v1/plans.py:66 | 12 | 6f/8r | — |
| plan_service | ALIVE | tools:app/tools/plan_tools.py:31; core:app/core/celery_app.py:715 | 39 | 13f/30r | — |
| plan_state_service | ALIVE | tools:app/tools/plan_state_tools.py:20; core:app/core/plan_context.py:34 | 48 | 30f/137r | — |
| planning_artifact_service | ALIVE | orchestration:app/orchestration/discovery_manager.py:24; services:app/services/card_protocol/decision_log_service.py:21 | 15 | 4f/4r | — |
| planning_benchmark_evaluator | DEAD | — | 0 | 0f/0r | rule-bj 豁免头；同族 planning_benchmark_service 弱活（4 消费者） |
| planning_benchmark_service | ALIVE | services:app/services/planning_benchmark_evaluator.py:17; other:scripts/run_phase_b_planning_benchmark.py:17 | 4 | 1f/2r | — |
| planning_readiness_gate | ALIVE | orchestration:app/orchestration/situation_brief.py:364 | 2 | 1f/1r | — |
| policy_compiler_service | ALIVE | services:app/services/memory_service.py:46 | 3 | 2f/2r | — |
| policy_ir | ALIVE | services:app/services/policy_compiler_service.py:19; other:scripts/stage24/check_policy_ir_schema.py:14 | 4 | 1f/2r | — |
| policy_patch_service | ALIVE | services:app/services/context_cache_key.py:89 | 9 | 6f/8r | — |
| policy_scheduler_service | ALIVE | tasks:app/tasks/accountability_tasks.py:31; state_aggregator:app/state_aggregator/service.py:48 | 9 | 6f/6r | — |
| predictive_service | ALIVE | core:app/core/celery_tasks.py:1426; state_aggregator:app/state_aggregator/service.py:49 | 25 | 15f/32r | — |
| preference_consumption_service | ALIVE | services:app/services/push_service.py:252; aurora:app/aurora/runtime_v1/notification_settings.py:306 | 5 | 1f/2r | — |
| preference_event_consumer | ALIVE | main:app/main.py:69 | 2 | 2f/3r | — |
| proactive_suggestion_service | ALIVE | core:app/core/celery_tasks.py:2121; services:app/services/nudge_service.py:8 | 27 | 8f/23r | — |
| profile_context_service | ALIVE | core:app/core/context_manager.py:38; consumers:app/consumers/user_profile_bootstrap_consumer.py:7 | 28 | 12f/25r | — |
| profile_eval_llm_judge | ALIVE | services:app/services/profile_eval_runner.py:11 | 4 | 2f/7r | — |
| profile_eval_runner | ORPHAN | — | 0 | 0f/0r | argparse CLI 工具（__main__ 入口），非运行时模块；判 ORPHAN(工具) 待 devtools 归位 |
| profile_event_consumer | ALIVE | main:app/main.py:70 | 17 | 4f/16r | — |
| profile_front_door_service | PARTIAL | tools:app/tools/growth_strategy_tools.py:11 | 1 | 0f/0r | 零测试 |
| profile_insight_control_service | ALIVE | tools:app/tools/growth_strategy_tools.py:12; api:app/api/v1/profile_transparency.py:48 | 2 | 0f/0r | — |
| profile_truth_compiler | ALIVE | orchestration:app/orchestration/situation_brief.py:365 | 3 | 2f/2r | — |
| profile_write_service | ALIVE | orchestration:app/orchestration/planning_workflow.py:31; services:app/services/achievement_event_consumer.py:755 | 34 | 8f/11r | — |
| progress_narrative_service | ALIVE | core:app/core/celery_tasks.py:2408; orchestration:app/orchestration/session_state_mixin.py:37 | 20 | 5f/11r | — |
| push_delivery_service | ALIVE | services:app/services/notification_center_service.py:34 | 4 | 2f/2r | — |
| push_feedback_service | PARTIAL | api:app/api/v1/push_interaction.py:18 | 1 | 0f/0r | 零测试 |
| push_policy_compiler | ALIVE | services:app/services/push_delivery_service.py:13 | 5 | 4f/4r | — |
| push_scheduler | ALIVE | services:app/services/agent_grpc_service.py:491 | 6 | 5f/6r | — |
| push_sender_service | ALIVE | core:app/core/websocket.py:642; services:app/services/notification_push_service.py:132 | 3 | 0f/0r | — |
| push_service | ALIVE | core:app/core/celery_tasks.py:545; services:app/services/nudge_service.py:9 | 15 | 4f/17r | — |
| quota | PARTIAL | services:app/services/llm_dispatcher.py:25 | 2 | 13f/35r | 仅同层互调、消费/测试单薄 |
| rag_indexing_service | ALIVE | core:app/core/redis_search_client.py:26; services:app/services/context_retrieval_pipeline.py:96 | 10 | 4f/6r | — |
| recommendation_feedback_service | ALIVE | services:app/services/friend_match_service.py:544; api:app/api/v1/community.py:223 | 3 | 0f/0r | — |
| redeem_service | ALIVE | other:app/schemas/redeem.py:15; services:app/services/photon_redeem_service.py:55 | 7 | 1f/17r | — |
| relationship_profile_service | PARTIAL | services:app/services/companion_state_service.py:21 | 1 | 1f/2r | 仅同层互调、消费/测试单薄 |
| release_approval | ALIVE | api:app/api/v1/release_approvals.py:15 | 3 | 1f/2r | — |
| rerank_service | ALIVE | core:app/core/celery_tasks.py:459; orchestration:app/orchestration/graph_rag.py:43 | 4 | 3f/4r | — |
| response_feedback_service | ALIVE | services:app/services/agent_grpc_service.py:51; api:app/api/v1/feedback_admin.py:12 | 6 | 3f/3r | — |
| review_appeal_service | PARTIAL | services:app/services/agent_grpc_service.py:1276 | 3 | 0f/0r | 仅同层互调、消费/测试单薄 |
| review_history_service | ALIVE | services:app/services/agent_grpc_service.py:1084; agents:app/agents/graph/nodes/review_nodes.py:41 | 7 | 0f/0r | — |
| route_history_service | ALIVE | orchestration:app/orchestration/routing_engine.py:49; services:app/services/error_replan_bridge.py:30 | 17 | 8f/16r | — |
| routing_outcome_service | ALIVE | core:app/core/celery_tasks.py:568; orchestration:app/orchestration/routing_engine.py:1801 | 3 | 1f/1r | — |
| routing_parameter_effectiveness_service | PARTIAL | services:app/services/routing_parameter_proposal_service.py:308 | 2 | 1f/1r | 仅同层互调、消费/测试单薄 |
| routing_parameter_experiment_service | PARTIAL | services:app/services/routing_parameter_proposal_service.py:30 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| routing_parameter_proposal_service | ALIVE | core:app/core/celery_tasks.py:3782 | 2 | 1f/1r | — |
| routing_profile_service | ALIVE | orchestration:app/orchestration/routing_engine.py:50; services:app/services/task_feedback_service.py:32 | 6 | 2f/3r | — |
| rule_y_adapter | ALIVE | services:app/services/llm_extractor_service.py:16 | 4 | 1f/1r | — |
| run_projection_consumer | ALIVE | main:app/main.py:71 | 5 | 4f/4r | — |
| scene_consolidation_service | ALIVE | state_aggregator:app/state_aggregator/service.py:50; services:app/services/memory_inferred_write_lane.py:33 | 11 | 10f/11r | — |
| scheduler_service | ALIVE | main:app/main.py:72 | 10 | 4f/9r | — |
| seed_library_service | ALIVE | agents:app/agents/workflow_experience.py:545; orchestration:app/orchestration/context_builder.py:650 | 32 | 11f/22r | — |
| self_evolution_service | ALIVE | core:app/core/celery_tasks.py:1347; orchestration:app/orchestration/context_builder.py:64 | 15 | 3f/8r | — |
| self_revision_service | ALIVE | services:app/services/companion_state_service.py:22 | 4 | 2f/8r | — |
| semantic_cache_service | ALIVE | services:app/services/galaxy/retrieval_service.py:63 | 19 | 8f/23r | — |
| semantic_memory_service | PARTIAL | services:app/services/error_book_service.py:52 | 1 | 0f/0r | 仅 1 服务层消费者、0 测试 |
| shadow_prediction_service | ALIVE | orchestration:app/orchestration/execution_engine.py:173; api:app/api/v1/prediction.py:19 | 13 | 4f/16r | — |
| share_card_service | ALIVE | api:app/api/v1/achievements.py:37 | 2 | 1f/1r | — |
| share_card_templates | ALIVE | services:app/services/share_card_service.py:27; api:app/api/v1/achievements.py:38 | 2 | 0f/0r | — |
| shop_service | ALIVE | api:app/api/v1/shop.py:20 | 16 | 5f/48r | — |
| signal_adaptation | ALIVE | services:app/services/asset_review_signal_processor.py:15 | 10 | 1f/1r | — |
| signal_generation_service | ALIVE | services:app/services/candidate_generation_service.py:16 | 6 | 2f/7r | — |
| simulation_runner | ALIVE | core:app/core/celery_tasks.py:3480 | 3 | 1f/3r | — |
| skill_content_reader | PARTIAL | orchestration:app/orchestration/routing_engine.py:51 | 1 | 0f/0r | 零测试 |
| skill_extract_service | ALIVE | orchestration:app/orchestration/orchestrator.py:3979; api:app/api/v1/skills.py:11 | 6 | 2f/4r | — |
| skill_schema | ALIVE | state_aggregator:app/state_aggregator/service.py:51; orchestration:app/orchestration/orchestrator.py:3993 | 10 | 3f/3r | — |
| skill_selection_service | ALIVE | state_aggregator:app/state_aggregator/service.py:52; orchestration:app/orchestration/routing_engine.py:53 | 3 | 1f/1r | — |
| smart_schedule_service | ALIVE | api:app/api/v1/calendar.py:36 | 5 | 2f/4r | — |
| social_signal_bridge | ALIVE | core:app/core/context_manager.py:39; state_aggregator:app/state_aggregator/service.py:53 | 8 | 4f/5r | — |
| social_signal_event_consumer | PARTIAL | main:app/main.py:73 | 1 | 0f/0r | 零测试 |
| social_signal_types | ALIVE | orchestration:app/orchestration/dual_core_router.py:9; services:app/services/social_signal_bridge.py:23 | 6 | 3f/3r | — |
| soul_drift_evaluator | ALIVE | services:app/services/constitutional_drift_firewall.py:6 | 4 | 1f/1r | — |
| source_lifecycle | ALIVE | main:app/main.py:832; api:app/api/v1/documents.py:30 | 13 | 6f/10r | — |
| source_state_encoder | ALIVE | learning:app/learning/persistent_bayesian_learner.py:56; orchestration:app/orchestration/routing_engine.py:56 | 6 | 3f/3r | — |
| spine_event_bridge | ALIVE | services:app/services/task_event_consumer.py:712 | 4 | 3f/3r | — |
| sprint_task_ledger | ALIVE | services:app/services/community_squad_service.py:43 | 10 | 5f/17r | — |
| srl_phase_tracker_service | ALIVE | main:app/main.py:74; other:scripts/stage29/bench_eventbus_throughput.py:25 | 9 | 10f/10r | — |
| srl_phase_traits | ALIVE | scaffolding:app/scaffolding/scaffolding_fsm.py:19; services:app/services/srl_phase_tracker_service.py:34 | 4 | 1f/1r | — |
| srl_phase_types | ALIVE | scaffolding:app/scaffolding/scaffolding_fsm.py:23; orchestration:app/orchestration/dual_core_router.py:10 | 16 | 10f/10r | — |
| stage33_journey_event_service | ALIVE | services:app/services/plan_service.py:20; api:app/api/v1/auth.py:61 | 8 | 2f/6r | — |
| state_driven_push_service | PARTIAL | services:app/services/achievement_event_consumer.py:160 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| state_estimator_service | ALIVE | services:app/services/analytics/cognitive_stream_worker.py:26; api:app/api/v1/events.py:28 | 6 | 4f/4r | — |
| state_notification_service | ALIVE | api:app/api/v1/plans.py:70 | 2 | 1f/1r | — |
| strategy_belief_service | ALIVE | api:app/api/v1/cognitive.py:24 | 2 | 1f/4r | — |
| streak_quality | ALIVE | services:app/services/achievement_engine.py:2175; api:app/api/v1/experience/streak_router.py:13 | 9 | 5f/12r | — |
| streak_signal_processor | ALIVE | api:app/api/v1/community.py:225 | 1 | 1f/1r | — |
| struggle_signal_aggregator | ALIVE | orchestration:app/orchestration/adaptive_replanner.py:2831; aurora:app/aurora/runtime_v1/wake_policy.py:9 | 13 | 4f/16r | — |
| stt_grpc_service | ALIVE | grpc_server.py:44,82 | 0 | 0f/0r | — |
| stt_service | ALIVE | services:app/services/stt_grpc_service.py:20; api:app/api/v1/stt.py:16 | 17 | 2f/16r | — |
| stuck_journey_service | ALIVE | api:app/api/v1/experience/stuck_journey_router.py:25 | 17 | 5f/16r | — |
| subject_service | ALIVE | main:app/main.py:75; api:app/api/v1/subjects.py:12 | 2 | 0f/0r | — |
| sufficiency_judge_schema | ALIVE | state_aggregator:app/state_aggregator/service.py:54; orchestration:app/orchestration/routing_engine.py:58 | 7 | 4f/4r | — |
| sufficiency_judge_service | ALIVE | state_aggregator:app/state_aggregator/service.py:55; orchestration:app/orchestration/routing_engine.py:59 | 4 | 2f/2r | — |
| suggestion_service | PARTIAL | api:app/api/v1/suggestions.py:8 | 1 | 0f/0r | 零测试 |
| system_update_service | ALIVE | core:app/core/websocket.py:37; consumers:app/consumers/journey_consumer_base.py:15 | 48 | 11f/14r | — |
| task_completion_evidence | ALIVE | services:app/services/task_service.py:1229; api:app/api/v1/tasks.py:74 | 11 | 3f/3r | — |
| task_document_service | ALIVE | services:app/services/focus_context_service.py:15; api:app/api/v1/tasks.py:75 | 4 | 4f/4r | — |
| task_event_consumer | ALIVE | main:app/main.py:76 | 30 | 10f/35r | — |
| task_feedback_service | ALIVE | core:app/core/background_tasks.py:14; api:app/api/v1/tasks.py:1576 | 45 | 5f/39r | — |
| task_guide_service | ALIVE | api:app/api/v1/tasks.py:76 | 2 | 1f/1r | — |
| task_occurrence_service | ALIVE | services:app/services/card_protocol/card_operations_service.py:40 | 8 | 5f/5r | — |
| task_optional_capabilities | PARTIAL | services:app/services/task_service.py:350 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| task_priority_service | ALIVE | api:app/api/v1/tasks.py:77 | 7 | 3f/9r | — |
| task_recommendation_service | PARTIAL | api:app/api/v1/tasks.py:522 | 1 | 0f/0r | 零测试 |
| task_reflection_service | ALIVE | services:app/services/card_protocol/outcome_verifier.py:31; api:app/api/v1/tasks.py:1275 | 30 | 8f/26r | — |
| task_service | ALIVE | tools:app/tools/plan_tools.py:32; core:app/core/context_manager.py:40 | 101 | 48f/124r | — |
| task_state_sync | ALIVE | tools:app/tools/plan_state_tools.py:21; services:app/services/card_protocol/card_operations_service.py:41 | 19 | 4f/4r | — |
| task_stuck_signal_service | ALIVE | orchestration:app/orchestration/adaptive_replanner.py:41; services:app/services/aurora_control_surface_service.py:17 | 7 | 2f/2r | — |
| template_registry | ALIVE | services:app/services/intervention_event_consumer.py:42 | 5 | 2f/2r | — |
| template_service | ALIVE | services:app/services/intervention_event_consumer.py:43 | 4 | 2f/2r | — |
| thumbnail_service | PARTIAL | services:app/services/file_processing_orchestrator.py:33 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| tool_call_ledger_service | ALIVE | services:app/services/agent_run_service.py:1840; api:app/api/v1/runs.py:281 | 3 | 0f/0r | — |
| tool_history_service | ALIVE | orchestration:app/orchestration/context_builder.py:66; routing:app/routing/tool_preference_router.py:18 | 9 | 3f/5r | — |
| traits_bias_calibration | PARTIAL | services:app/services/traits_nlp_observer_service.py:17 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| traits_coldstart_service | ALIVE | api:app/api/v1/profile_transparency.py:51 | 4 | 3f/3r | — |
| traits_merge_service | PARTIAL | services:app/services/traits_nlp_observer_service.py:18 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| traits_metrics | PARTIAL | services:app/services/traits_coldstart_service.py:15 | 3 | 0f/0r | 仅同层互调、消费/测试单薄 |
| traits_nlp_observer_service | PARTIAL | core:app/core/celery_tasks.py:3726 | 1 | 0f/0r | 零测试 |
| translation_service | ALIVE | tools:app/tools/translation_tool.py:12 | 51 | 4f/60r | — |
| tts_service | ALIVE | api:app/api/v1/tts.py:12 | 14 | 1f/13r | — |
| understanding_benchmark_evaluator | DEAD | — | 0 | 0f/0r | rule-bj 豁免头；同族 understanding_benchmark_service 亦零外部消费 |
| understanding_benchmark_service | PARTIAL | services:app/services/understanding_benchmark_evaluator.py:11 | 1 | 0f/0r | 仅同层互调、消费/测试单薄 |
| understanding_calibration_service | ALIVE | core:app/core/celery_tasks.py:3894; api:app/api/v1/insights.py:126 | 3 | 1f/1r | — |
| understanding_depth_metric_service | ALIVE | core:app/core/celery_tasks.py:3853; services:app/services/understanding_dimensions_service.py:61 | 6 | 3f/4r | — |
| understanding_dimensions_service | ALIVE | core:app/core/celery_tasks.py:3895; services:app/services/understanding_calibration_service.py:39 | 7 | 4f/4r | — |
| user_activity_service | ALIVE | aurora:app/aurora/runtime_v1/service.py:343 | 2 | 1f/2r | — |
| user_insight_analysis_service | ALIVE | services:app/services/user_insight_compiler.py:21 | 3 | 1f/3r | — |
| user_insight_calibration_service | PARTIAL | services:app/services/user_insight_compiler.py:22 | 2 | 1f/1r | 仅同层互调、消费/测试单薄 |
| user_insight_compiler | ALIVE | services:app/services/profile_context_service.py:37 | 8 | 3f/7r | — |
| user_insight_transparency_service | ALIVE | profile:app/profile/projection_contract.py:77; services:app/services/profile_front_door_service.py:14 | 3 | 0f/0r | — |
| user_push_opt_in_service | ALIVE | services:app/services/push_delivery_service.py:14; api:app/api/v1/memory_settings.py:12 | 5 | 1f/1r | — |
| user_service | ALIVE | main:app/main.py:77; core:app/core/celery_app.py:923 | 22 | 8f/28r | — |
| user_settings_service | ALIVE | api:app/api/v1/profile_transparency.py:58 | 4 | 1f/1r | — |
| user_strategy_state_service | ALIVE | tools:app/tools/growth_strategy_tools.py:13; orchestration:app/orchestration/experience_actuator.py:12 | 7 | 6f/12r | — |
| visual_element_service | ALIVE | services:app/services/achievement_engine.py:1929; api:app/api/v1/visual_elements.py:26 | 5 | 2f/2r | — |
| vocabulary_service | ALIVE | services:app/services/translation_service.py:26; api:app/api/v1/vocabulary.py:26 | 4 | 4f/14r | — |
| weekly_digest_service | ALIVE | core:app/core/celery_tasks.py:1135 | 4 | 3f/3r | — |
| within_category_preference_service | ALIVE | services:app/services/predictive_service.py:70 | 3 | 1f/2r | — |
| working_memory_consolidation_service | ALIVE | services:app/services/working_memory_pipeline_service.py:12; api:app/api/v1/memory.py:27 | 6 | 3f/4r | — |
| working_memory_orphan_cleanup | PARTIAL | main:app/main.py:132 | 1 | 0f/0r | 零测试 |
| working_memory_pipeline_service | ALIVE | services:app/services/memory_inferred_write_lane.py:326 | 3 | 2f/2r | — |
### 6.2 app/orchestration（92）

| 模块 | 判定 | 入口证据 | 生产消费数 | 测试 | 注记 |
|---|---|---|---|---|---|
| adaptive_replanner | ALIVE | orchestration:app/orchestration/multi_agent_adapter.py:237; services:app/services/behavior_signal_collector.py:32 | 29 | 19f/30r | — |
| agent_activity | ALIVE | orchestration:app/orchestration/execution_engine.py:35; agents:app/agents/graph/nodes/collaboration.py:28 | 10 | 0f/0r | — |
| agent_memory | ALIVE | orchestration:app/orchestration/agent_scoring.py:13; services:app/services/response_feedback_service.py:25 | 3 | 0f/0r | — |
| agent_scoring | ALIVE | orchestration:app/orchestration/response_builder.py:32; services:app/services/response_feedback_service.py:26 | 10 | 0f/0r | — |
| ai_strategy_ontology | ALIVE | orchestration:app/orchestration/ai_strategy_renderer.py:6 | 2 | 1f/1r | — |
| ai_strategy_renderer | ALIVE | orchestration:app/orchestration/lang_graph_planner.py:21; services:app/services/planning_benchmark_service.py:10 | 6 | 1f/1r | — |
| aurora_language_principles | ALIVE | orchestration:app/orchestration/prompts.py:46; aurora:app/aurora/runtime_v1/chat_adapter.py:19 | 4 | 1f/1r | — |
| bert_intent_classifier | DEAD | — | 23 | 1f/23r | rule-bj 豁免头自称已登记 KNOWN_CODE_DEBT_LEDGER，台账实无条目（dangling 指针）；multi_intent 实走 LLM（multi_intent_service.py:20,30 imports 无 bert） |
| bottleneck_analyzer | ALIVE | orchestration:app/orchestration/planning_workflow.py:3259; services:app/services/exam_sprint_intake_service.py:22 | 16 | 8f/23r | — |
| capability_lane | ALIVE | agents:app/agents/standard_workflow.py:60; orchestration:app/orchestration/context_builder.py:46 | 6 | 2f/9r | — |
| capability_requirement_compiler | ALIVE | orchestration:app/orchestration/situation_brief.py:9; services:app/services/capability_selection_evaluator.py:10 | 3 | 1f/1r | — |
| capability_selection_policy | ALIVE | orchestration:app/orchestration/orchestrator.py:60; services:app/services/capability_selection_evaluator.py:11 | 4 | 1f/1r | — |
| chat_modes | ALIVE | agents:app/agents/standard_workflow.py:68; orchestration:app/orchestration/execution_engine.py:37 | 12 | 4f/4r | — |
| circuit_breaker | ALIVE | orchestration:app/orchestration/execution_engine.py:164 | 20 | 14f/41r | — |
| companion_constitution | ALIVE | orchestration:app/orchestration/soul_compiler.py:8 | 3 | 2f/2r | — |
| companion_identity_kernel | ALIVE | orchestration:app/orchestration/soul_compiler.py:9 | 3 | 2f/2r | — |
| composer | ALIVE | orchestration:app/orchestration/orchestrator.py:73; api:app/api/v1/chat.py:31 | 4 | 2f/14r | — |
| context_builder | ALIVE | orchestration:app/orchestration/orchestrator.py:78 | 31 | 21f/61r | — |
| context_focus | ALIVE | core:app/core/context_pack.py:51; agents:app/agents/standard_workflow.py:69 | 7 | 12f/39r | — |
| context_funnel | ALIVE | agents:app/agents/standard_workflow.py:1306; orchestration:app/orchestration/context_builder.py:838 | 13 | 3f/9r | — |
| context_pruner | ALIVE | orchestration:app/orchestration/context_builder.py:71 | 6 | 5f/19r | — |
| context_sources | ALIVE | core:app/core/context_pack.py:57; orchestration:app/orchestration/context_builder.py:1604 | 13 | 4f/17r | — |
| conversation_compaction | ALIVE | core:app/core/knowledge_jit.py:33; orchestration:app/orchestration/context_pruner.py:26 | 4 | 1f/1r | — |
| decision_policy | ALIVE | orchestration:app/orchestration/situation_brief.py:11 | 1 | 1f/2r | — |
| discovery_manager | ALIVE | api:app/api/v1/plans.py:37 | 6 | 3f/6r | — |
| dual_core_router | ALIVE | aurora:app/aurora/migration.py:23; orchestration:app/orchestration/adaptive_replanner.py:30 | 29 | 24f/81r | — |
| dynamic_tool_registry | ALIVE | tools:app/tools/registry.py:35; orchestration:app/orchestration/execution_engine.py:38 | 22 | 11f/38r | — |
| error_handler | ALIVE | api:app/api/v1/chat.py:32 | 3 | 2f/4r | — |
| exam_sprint_policy | ALIVE | orchestration:app/orchestration/planning_workflow.py:26; other:scripts/xiaolin_lifecycle_acceptance.py:61 | 5 | 25f/77r | — |
| execution_engine | ALIVE | orchestration:app/orchestration/orchestrator.py:88 | 28 | 15f/35r | — |
| executor | ALIVE | agents:app/agents/standard_workflow.py:70; orchestration:app/orchestration/error_handler.py:82 | 68 | 43f/266r | — |
| experience_actuator | ALIVE | orchestration:app/orchestration/orchestrator.py:90 | 8 | 3f/8r | — |
| experience_packets | ALIVE | orchestration:app/orchestration/orchestrator.py:91 | 2 | 1f/1r | — |
| expert_strategy | PARTIAL | orchestration:app/orchestration/orchestrator.py:92 | 1 | 0f/0r | 零测试 |
| goal_quality_evaluator | ALIVE | orchestration:app/orchestration/validation_engine.py:16 | 8 | 3f/9r | — |
| graph_rag | ALIVE | tools:app/tools/plan_tools.py:221; core:app/core/citation_markers.py:27 | 24 | 15f/26r | — |
| grounding_validator | ALIVE | orchestration:app/orchestration/execution_engine.py:166 | 11 | 8f/25r | — |
| intent_cache | DEAD | — | 2 | 1f/2r | intent_monitor.py:75-110 以字符串声明 intent_cache_* 指标，两模块同死——指标从未注册 |
| intent_monitor | DEAD | — | 0 | 0f/0r | 声明 intent_cache_hits_total 等 Prometheus 指标但零导入，指标面不存在 |
| lang_graph_planner | ALIVE | orchestration:app/orchestration/execution_engine.py:167 | 13 | 13f/30r | — |
| latency_probe | ALIVE | orchestration:app/orchestration/orchestrator.py:100 | 3 | 2f/2r | — |
| learning_state_fragment | ALIVE | orchestration:app/orchestration/situation_brief.py:12 | 2 | 2f/8r | — |
| memory_helpers | ALIVE | orchestration:app/orchestration/orchestrator.py:101 | 10 | 0f/0r | — |
| mode_workflow_config | ALIVE | orchestration:app/orchestration/execution_engine.py:39 | 6 | 2f/2r | — |
| multi_agent_adapter | ALIVE | orchestration:app/orchestration/execution_engine.py:168 | 19 | 9f/27r | — |
| observability_logger | ALIVE | orchestration:app/orchestration/circuit_breaker.py:258 | 4 | 1f/1r | — |
| observability_mixin | ALIVE | orchestration:app/orchestration/orchestrator.py:135 | 5 | 3f/4r | — |
| orchestration_trace | ALIVE | orchestration:app/orchestration/execution_engine.py:41 | 3 | 5f/14r | — |
| orchestrator | ALIVE | orchestration:app/orchestration/execution_engine.py:61; services:app/services/agent_grpc_service.py:47 | 82 | 97f/1657r | — |
| persistence_layer | ALIVE | orchestration:app/orchestration/context_builder.py:2097 | 11 | 7f/12r | — |
| persona_aware_planner | ALIVE | tools:app/tools/plan_tools.py:25; orchestration:app/orchestration/execution_engine.py:42 | 3 | 0f/0r | — |
| phase_sketch_service | ALIVE | api:app/api/v1/plans.py:42 | 5 | 2f/5r | — |
| plan_quality_contract | ALIVE | orchestration:app/orchestration/ai_strategy_renderer.py:7; services:app/services/planning_benchmark_evaluator.py:11 | 9 | 2f/2r | — |
| plan_quality_gate | ALIVE | orchestration:app/orchestration/plan_review_service.py:40 | 3 | 3f/3r | — |
| plan_review_service | ALIVE | consumers:app/consumers/plan_task_generation_consumer.py:11; orchestration:app/orchestration/adaptive_replanner.py:31 | 29 | 14f/61r | — |
| plan_revision_summary | ALIVE | orchestration:app/orchestration/adaptive_replanner.py:32 | 4 | 2f/3r | — |
| planning_intent | ALIVE | orchestration:app/orchestration/situation_brief.py:14; services:app/services/insight_gap_detector.py:6 | 5 | 3f/6r | — |
| planning_strategy_compiler | ALIVE | orchestration:app/orchestration/situation_brief.py:15; services:app/services/planning_benchmark_service.py:12 | 10 | 7f/13r | — |
| planning_workflow | ALIVE | orchestration:app/orchestration/orchestrator.py:139; services:app/services/error_replan_bridge.py:982 | 27 | 12f/26r | — |
| prompts | ALIVE | agents:app/agents/standard_workflow.py:77; orchestration:app/orchestration/multi_agent_adapter.py:31 | 73 | 67f/123r | — |
| rendered_plan_artifact | ALIVE | orchestration:app/orchestration/lang_graph_planner.py:22 | 2 | 1f/10r | — |
| residual_diagnosis | ALIVE | orchestration:app/orchestration/situation_brief.py:16 | 2 | 1f/1r | — |
| response_builder | ALIVE | orchestration:app/orchestration/orchestrator.py:140 | 9 | 7f/11r | — |
| retrieval_intent | ALIVE | orchestration:app/orchestration/session_state_mixin.py:22; aurora:app/aurora/runtime_v1/l1_light_aurora.py:19 | 9 | 5f/9r | — |
| route_adapter | ALIVE | orchestration:app/orchestration/routing_engine.py:36 | 2 | 1f/1r | — |
| routing_engine | ALIVE | orchestration:app/orchestration/orchestrator.py:143 | 50 | 16f/78r | — |
| routing_parameter_registry | ALIVE | orchestration:app/orchestration/dual_core_router.py:14; services:app/services/routing_parameter_experiment_service.py:21 | 4 | 1f/1r | — |
| run_ledger | ALIVE | orchestration:app/orchestration/orchestrator.py:144; services:app/services/agent_grpc_service.py:49 | 7 | 4f/12r | — |
| schemas | ALIVE | agents:app/agents/standard_workflow.py:2694; orchestration:app/orchestration/circuit_breaker.py:18 | 73 | 168f/204r | — |
| session_feedback | ALIVE | orchestration:app/orchestration/execution_engine.py:45 | 5 | 1f/1r | — |
| session_state_mixin | ALIVE | orchestration:app/orchestration/orchestrator.py:150; api:app/api/v1/profile_transparency.py:35 | 17 | 6f/17r | — |
| situation_brief | ALIVE | tools:app/tools/growth_strategy_tools.py:9; orchestration:app/orchestration/prompts.py:51 | 7 | 18f/72r | — |
| social_context_renderer | ALIVE | orchestration:app/orchestration/prompts.py:52 | 2 | 1f/1r | — |
| soul_compiler | ALIVE | orchestration:app/orchestration/orchestrator.py:151; services:app/services/companion_state_service.py:9 | 5 | 2f/2r | — |
| stage_events | ALIVE | agents:app/agents/standard_workflow.py:78; orchestration:app/orchestration/orchestrator.py:152 | 5 | 1f/4r | — |
| state_manager | ALIVE | orchestration:app/orchestration/context_builder.py:72 | 20 | 26f/325r | — |
| state_snapshot | ALIVE | orchestration:app/orchestration/execution_engine.py:170 | 9 | 2f/6r | — |
| statechart_engine | ALIVE | visualization:app/visualization/execution_tracer.py:6; checkpoint:app/checkpoint/redis_checkpointer.py:9 | 51 | 32f/39r | — |
| step_feedback_collector | ALIVE | orchestration:app/orchestration/adaptive_replanner.py:44 | 6 | 3f/3r | — |
| sufficiency_checker | ALIVE | orchestration:app/orchestration/validation_engine.py:20 | 11 | 7f/13r | — |
| summarization_worker | ALIVE | main:app/main.py:52 | 2 | 1f/1r | — |
| task_card_generator | ALIVE | orchestration:app/orchestration/task_guide_enricher.py:9 | 5 | 3f/4r | — |
| task_guide_enricher | ALIVE | orchestration:app/orchestration/planning_workflow.py:2739; api:app/api/v1/plans.py:43 | 4 | 1f/1r | — |
| token_tracker | ALIVE | core:app/core/celery_tasks.py:296; orchestration:app/orchestration/execution_engine.py:171 | 12 | 8f/12r | — |
| tool_result_extractor | ALIVE | orchestration:app/orchestration/response_builder.py:36 | 4 | 2f/2r | — |
| transparency_data_generator | ALIVE | orchestration:app/orchestration/execution_engine.py:51 | 4 | 2f/2r | — |
| user_intent_profiler | DEAD | — | 0 | 0f/0r | rule-bj 豁免头；无测试 |
| utilization_metrics | ALIVE | orchestration:app/orchestration/response_builder.py:37 | 2 | 2f/5r | — |
| ux_envelope | ALIVE | orchestration:app/orchestration/execution_engine.py:52 | 4 | 2f/2r | — |
| validation_engine | ALIVE | orchestration:app/orchestration/orchestrator.py:164 | 13 | 5f/12r | — |
| validator | ALIVE | orchestration:app/orchestration/orchestrator.py:165 | 5 | 22f/229r | — |
| version_conflict_service | ALIVE | orchestration:app/orchestration/execution_engine.py:172 | 13 | 10f/15r | — |

## 七、Top 风险清单（round-1 审计轴）

1. **V3-FIX-337 /push/interaction 断链（P1）**：移动端推送交互回执 100% 丢失且静默（catch 吞错）。产品若以推送打开率做任何宣称即为无源指标；修法=网关补 /push 组（或端点并入 /notification-center）。
2. **V3-FIX-338 GDPR 清理宣称执行断裂（P2）**：login_attempt_cleanup 有 beat 无 worker 注册面，按仓内 EI-02 学说=静默丢弃；合规宣称（90 天删除）无执行证据。修法=补 include 一行+worker 侧注册测试。
3. **V3-FIX-341 GraphRAG 双闸（P2）**：flag 翻开也不可达，属「假开关」； Either 删面或补网关组，勿让旗宣称能力。
4. **rule-bj 豁免头 dangling 指针（P3，文档债）**：9 个 DEAD 模块头注指向 KNOWN_CODE_DEBT_LEDGER，台账无条目；真实登记在守卫脚本+接力日志。豁免头注应改指真实登记面或补台账行。
5. **services/community_context_boundary 隐私守卫未接线（P2）**：自称单一守卫面却零消费——S-02 隐私红线是否由其他面兑现需 round-2 专查。
6. **测试在测死代码（P3）**：update_similarities（容量故事）、community_context_boundary（隐私故事）、bert_intent_classifier（意图故事）三处测试绿=假信心源。

## 八、方法与局限

- import 索引盲区已校正三项：gRPC bootstrap（仓根 grpc_server.py）、路径加载（lua 脚本）、CLI __main__（profile_eval_runner）；字符串引用（如 celery beat 任务名、gateway 代理路径）不在 import 索引内，均另行 grep 亲证。
- 「生产消费数」含同层服务互调；判定为 PARTIAL 的 55 个多为被 orchestration/consumers 之外的兄弟服务单点调用——属分层常态而非死亡，但测试单薄（0-1 文件）在列，供 round-2 抽样复核。
- StateGraph 节点面以 app/agents/ 对 orchestration/services 的 import 关系作代理证据（agents 类目在机械扫描内），未逐节点展开。
- 本报告零产品代码改动；台账登记（V3-FIX-337～342）以独立 commit 提交于 v3/06_agent_fleet/DYNAMIC_ISSUES.md。
