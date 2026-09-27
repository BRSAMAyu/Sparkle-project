# WT649 · 今日修复波 round-3 独立复验裁决（9 张）

- 会话：wt649（node-b），2026-09-27
- 基线：main @ 856ce94d（worktree `agent/node-b/wt649/verify3`，本分支唯一新增文件即本文档，零产品代码改动）
- 方法：不信任 worker 回报，逐张亲证——(1) 声称的红→绿测试在当前 main 真实存在且跑绿，并做「恒真性」检查（断言与被测行为绑定，必要时思想实验/实改回滚验证）；(2) 修复面无 Mock/占位冒充真实行为；(3) 宣称 unavailable/UNKNOWN/退役 的行为面抽查属实。
- 台账 FIXED@ SHA 均为 worktree 原始提交号，main 集成为对应 cherry-pick/重放 commit（如 330=773f2055、331=cb9a1f79、332=ec4a88e3、333=e71a5df4、334=57a3eb0f、335/336=7f6ff52e、337=7e8bc1a7、338=b3481580、339=92e750fb），九张内容均已入 HEAD。

## 结论总表

| 卡 | 结论 | 一句话 |
|---|---|---|
| V3-FIX-330 | **PASS** | 四端点无条件标 unavailable，5/5 绿，写侧零调用亲证 |
| V3-FIX-331 | **PASS** | 残轨三路由+文件全灭，双真轨 8 绿，openapi 契约 3 绿 |
| V3-FIX-332 | **PASS** | wire 键全量换新，旧键仅存 docstring，14 绿 |
| V3-FIX-333 | **PASS** | 15 用例绿，registry 七处 active 去除亲证，真实流量挂点在场 |
| V3-FIX-334 | **PASS** | 引擎/网关三态语义一致，13+7 绿，TTL 3600=去重窗亲证 |
| V3-FIX-335 | **PASS** | 入档/还原/优先三面代码亲证，10/10 绿含运行级钱测 |
| V3-FIX-336 | **PASS（状态诚实）** | 台账维持 OPEN 属实；A 轨闭合通道经 335 钱测+X06 基线印证 |
| V3-FIX-337 | **PASS** | /push 组仅 POST /interaction 在册，网关+引擎测试全绿 |
| V3-FIX-338 | **PASS** | 守卫结构性断 include；实改回滚实验：删一行即红 |
| V3-FIX-339 | **PASS** | 模块已删，仓内仅存退役注释口径，orchestration 208 绿 |

九张全过，无新问题登记，台账未动（符合「仅发现问题时登记新行」规则）。

---

## V3-FIX-330 · agent-stats 如实化 — PASS

**测试真测**：`backend/tests/unit/test_agent_stats_unwired_truth.py` 实跑 5 passed。断言非恒真：`_assert_unavailable` 逐端点断 `degraded is True` + `data_status=="unavailable"` + `unavailable_reason=="write_side_unwired"`——修前行为（结构性零、无标记）必挂第一条。思想实验成立：把 `agent_stats.py:64` 的 `**_unavailable_markers()` 删掉，5 用例中 4 条红。

**无冒充**：`backend/app/api/v1/agent_stats.py` 四数据端点（user/overview、overview 别名、user/top-agents、performance）在空表+非空表下均无条件返回 `_unavailable_markers()`（`:32-37` 集中定义、`:64/:95/:122` 展开），旧的「仅表缺失才置 degraded」分支已不存在（grep `Inspector|has_table` 零命中）。数值字段（total_executions=0 等）仍在但明确挂 degraded 占位语义，非测量值宣称。

**行为面诚实**：写侧 `AgentStatsService.record_agent_execution`（agent_stats_service.py:29）全仓仅定义零调用——unavailable 宣称与事实一致。`/agent-types` 静态目录不降级（测试第 5 用例覆盖）。mobile `api_endpoints.dart:582-584` 注释改真（"server reports degraded/unavailable … StatisticsSourceUnavailableException"）；:587 "real DB aggregation" 属 Capsule Statistics 段，与 agent-stats 无关，非残留。

## V3-FIX-331 · weekly mock 残轨删除 — PASS

**删除面亲证**：`backend/app/services/weekly_synthesis_service.py`、`backend/app/templates/`（整目录）、`backend/scripts/test_report_generation.py` 均不存在；`analytics.py` 仅剩 `GET /north-star/trends` 一条自有路由，POST /reports/generate、GET /report、GET /reports/download 三个 mock 出口全部除名。

**无 dangling 冒充**：仓内 `weekly_synthesis|WeeklySynthesis` 命中仅 4 处，全部是退役说明注释（analytics.py:12、weekly_stats_service.py:21/69、test docstring），无导入无调用。

**测试真测**：双真轨（weekly_digest/weekly_growth_narrative/weekly_stats_behavior_clock）8 passed；`tests/contract/test_api_router_openapi_contract.py` 3 passed（快照与路由面一致，无已删路由残留）。mobile 唯一周报消费面仍是 `/learning-reports/generate`（api_endpoints.dart:375，真轨①），零引用已删路由。

## V3-FIX-332 · today_focus_minutes 改名 — PASS

**改名面亲证**：backend payload 键+方法 `_get_today_completed_task_minutes`（dashboard_service.py:115/124/226）；mobile wire 键读取 `dashboard_provider.dart:477` 读 `flameMap['today_completed_task_minutes']`，测试 fixture `dashboard_provider_test.dart:48` 同步。旧键 `"today_focus_minutes"` 在 live 代码零命中（dashboard_service.py:234 为改名说明 docstring）。Dart 模型字段 `todayFocusMinutes` 保留符合卡面范围裁决（仅 wire 键改名）。

**语义诚实**：新 docstring 明确「数据源语义（任务 actual_minutes 而非 FocusSession）自始未变」；代码源 `sum(Task.actual_minutes) where status=COMPLETED`（:242-247）与宣称一致，无 FocusSession 引用。

**测试真测**：`test_dashboard_service.py` + `test_dashboard_flame_card_local_day.py` 14 passed，断言含键名 `result["flame"]["today_completed_task_minutes"] == 45`——键回滚即红。

## V3-FIX-333 · wt642 能力宣称真实化 — PASS

**测试真测**：`tests/services/test_capability_claims_realism.py` 实跑 15 passed（与台账宣称的 15 用例数一致），llm_router 既有族（health_tracking/free_tier）25 passed 无回归。断言绑定行为：如 `test_registry_subsystems_do_not_hardcode_active` 断 active_ids ⊆ {chat_orchestrator} 且其余 ∈ 封闭集——若 registry 回滚硬编码 active，第 216-222 行必红。

**无冒充（红线专项）**：真实流量挂点在场且在真实调用成功/失败之后——embedding_service.py:285（`_dashscope_embeddings`/`_siliconflow_embeddings` 真实 API 返回+熔断 record_success 后才 `observe_success`）、:321 失败臂；stt:203/209（文件）与 :295/302（WS 流）；tts:207/212/219；ocr:119/129/174/180（async/sync 双路）；llm 侧 report_model_success/failure 在 llm_service.py:96/98 与 llm/fallback.py:783/842/875。测试注入用的 `observe_*` 与生产同一入口，测试文件头有显式非冒充声明（不伪造探测结果）。

**registry 亲证**：capability_registry_service.py:33 唯一 `"state": "active"` 为 chat_orchestrator 且附 in_process_self_evident 证据串；六个 in-process 子系统降 `configured` 全附 `state_evidence`（:57-118）；openclaw settings 派生（:45-46）；新增 media:embedding/stt/tts/ocr 按 `aggregate_family_state` 聚合。llm `is_healthy` 缺省 True 保留属 E-07 路由熔断语义（与宣称面分离，`ModelHealthState.ever_observed` 新证据位映射五态，测试 §4/§6 覆盖）。selection policy `_HEALTHY_AVAILABILITY` 含 verified、不含 unverified（测试 §5 覆盖，body-map unverified 不进 healthy_organs）。

## V3-FIX-334 · wt640 三态回放+GetRequestResult+TTL — PASS

**契约面**：proto/agent_service.proto:74 `rpc GetRequestResult` + :798 `RequestResultStatus` 三态枚举；`backend/app/gen/agent_service_pb2_grpc.py` 与 `backend/gateway/gen/agent/v1/` 均含生成物（worktree 补拷后亲证），无手改痕迹。

**引擎**：`agent_grpc_service.py:88-136` resolve_request_result——响应缓存 dict 命中→COMPLETED+完整回放体；ledger 会话索引双等值（session_id+request_id）命中且 status=running→RUNNING、status=completed 但回放体缺失→UNKNOWN（:131，诚实不回放）；无匹配→UNKNOWN；缓存/ledger 读故障均按 UNKNOWN 兜底。handler（:620 附近）镜像 StreamChat 鉴权（伪造→PERMISSION_DENIED、缺元数据→UNAUTHENTICATED），payload ParseDict 失败降级 message-only。

**网关**：`chat_orchestrator_chatflow.go:347-391` 去重命中分支三态化；纯函数 `dedupHitDecision`（:1197）——引擎错误/nil/UNKNOWN→duplicate_request 兜底、RUNNING→ack 等待、COMPLETED 仅非空 message 才回放（blank 显式 guard，:1209-1211）；`buildReplayChatResponse` 镜像 full_text 终帧+`is_replay` 标记。TTL：网关去重 `time.Hour`（:348）= 引擎 `RESPONSE_CACHE_TTL_SECONDS = 3600`（state_manager.py:55，全仓无覆写点）。

**测试真测**：引擎 `tests/unit/services/test_agent_grpc_service_request_result.py` 13 passed（缓存权威优先/ledger running/completed 无回放体诚实 unknown/等值失配/鉴权拒绝/三态映射）；网关 `chat_dedup_replay_test.go` TestDedupHitDecisionTriState 6 子例+TestDedupHitDecisionNeverReplaysBlankMessage 全绿（-count=1）。恒真性：blank-guard 若删，COMPLETED+空 message 会走 dedupReplayResult，`NeverReplaysBlankMessage` 必红。

**交叉核对（语义一致性）**：引擎缓存路径对「message 为空串」的缓存体仍返回 COMPLETED+空 message，此时由网关 blank-guard 降为 duplicate_request——两路径的**可观测行为收敛**：任何 completed-无回放体形态（ledger 路径出 UNKNOWN / 缓存路径空 message）都不会产生空帧回放，最终都落 duplicate_request 兜底。语义一致，无双事实源（回放体仅响应缓存持有，与引擎自身幂等检查同源）。桥梁零业务裁决（dedupHitDecision 仅映射引擎答案）符合分层边界。

## V3-FIX-335 · executable_plan 入 checkpoint — PASS

**实现面亲证**：redis_checkpointer.py:95-104 save 特例置于 KNOWN 跳过**之前**（顺序正确），to_dict 产物 json.dumps 自检，失败仅跳计划不炸 save；`_restore_executable_plan`（:51-67）损坏 payload 丢弃回退重规划；statechart_engine.py:35 `_CHECKPOINT_RESUME_PRIORITY_KEYS = {"executable_plan"}`，:403-408 合并时 checkpoint 计划（非 None）覆盖 fresh，None 清理位不回填。

**测试真测**：`tests/unit/test_v3_fix335_plan_checkpoint_resume.py` 10/10 passed。恒真性思想实验：若回滚（计划回 KNOWN 清单+无优先键），roundtrip 两测红（restored 非 ExecutablePlan）、merge 两测红（fresh plan-replan 胜出）、钱测红（execute_count==3 而非 2）。断言全部绑定被测行为。

**钱测无冒充**：`TestInterruptedResumeNoDuplicateSideEffect` 用真实 ToolExecutor+真实 sqlite AgentToolCall 账本（StaticPool in-memory）+唯一索引撞键面，桩仅替换外部工具本体（X-06 同形态）——`execute_count == 2`（spec-a 同键 replay 不重执行 + spec-b 首次执行）与账本行 `idempotency_key ∈ {spec-a, spec-b}` 均 succeeded，正是「每写意图恰一次」的运行级证据，非 Mock 冒充。

**基线不破**：test_x06_tool_call_safety 33 passed；test_v3_fix223_ledger_gate_attribution + test_x06_run_budget 39 passed——X-06 闸门零放松亲证。

## V3-FIX-336 · 幂等键（状态诚实性核验）— PASS

本卡裁决=不直接修（轨道 B 不采），通道由 335 轨道 A 单轨闭合，**台账状态维持 OPEN**。核验：

- 台账行确为 `OPEN`（第 7 列），round-2 结论、wt641 轨道裁决、不采 B 的理由（A 严格更强：同时保计划内容与 args_hash 一致性；B 在重规划参数漂移下仍撞 IdempotencyArgsMismatch）、跨 run 显式重试=新键设计语义（X-06）均成文——宣称与仓内状态一致，无「口头 FIXED」。
- 闭合有效性经 335 钱测+X06/FIX-223 基线（72 测全绿）印证：同 request_id 恢复路径上键稳定、同键 replay 恰一次。
- executor 尝试唯一键本体（无键即拒/异参拒/并发 fail-closed）未被本批放松。

## V3-FIX-337 · 网关 /push 代理组 — PASS

**接线亲证**：proxy_routes.go:894-899 `/push` authed 组，仅注册 `POST /interaction`（引擎无其余方法面，与 R2-08 同判），纯代理 `h.proxyWithHeaders` 零业务。

**测试真测**：`proxy_routes_push_test.go` 实跑（-count=1）TestPushInteractionProxiesToEngine（真实路由 POST 到 200+上游路径不变断言，非注册表自查）+TestPushInteractionRouteRegistration（POST 在册且 GET/PUT/PATCH/DELETE 不在册）全绿。恒真性：404 回滚即红（第 37 行 want 200）。

**引擎侧**：`tests/api/test_push_interaction_api.py` 3 passed（路由形状恰为 /push/interaction、action 归一化、非法 400）。mobile `notification_service.dart:374-380` catch 升 `_logger.e` 带 push_id/action 上下文+堆栈，仍吞异常不打断 UX（与宣称一致）。真机回执到达断言无设备，台账已如实留阻塞证据，本轮不重复扣分。

## V3-FIX-338 · celery include+守卫 — PASS

**include 亲证**：celery_app.py:77 `"app.tasks.login_attempt_cleanup"` 在 include 列表，注释如实记录「此前靠 setup_periodic_tasks import 副作用遮蔽成假绿」的诚实修正。

**守卫真断 include（回滚实改实验，非思想实验）**：`tests/core/test_celery_beat_registration_guard.py:83` 双断言——(1) 结构性断 `"app.tasks.login_attempt_cleanup" in celery_app.conf.include`（不依赖进程内注册表状态，测试顺序免疫）；(2) beat 条目名==模块注册 `name=`（tasks.cleanup_old_login_attempts）且 `setup_periodic_tasks` 后可解析进注册表。本会话在 worktree 实改：注释掉 include 一行 → 守卫立即红（`1 failed`）；还原后 3 passed。守卫非恒真、非被副作用遮蔽。

## V3-FIX-339 · guest_cleanup 退役 — PASS

**删除亲证**：`backend/app/tasks/guest_cleanup.py` 不存在。

**无 dangling 引用（专项 grep）**：全仓 live 代码（backend/mobile/gateway/tests_e2e/scripts，py/go/dart/ts）`guest_cleanup` 命中仅 context_sources.py:56/60 两行——为模块 docstring 中的退役案注释（明确「不得以本注释旧口径宣称 guest_cleanup 为活机制」），正是台账宣称的替换口径；配置面（docker/deploy/k8s/Makefile）零命中。零 include/零 beat/零入队残留。

**行为面诚实**：退役后游客过期行确实无清理执行方（guest_seed_service 设置 expires_at 无消费方）——台账如实留为「存储卫生缺口待产品决策」，未冒充已解决；真实生命周期执行面（upgrade-guest 原位翻转 + purge_deleted_account 30 天硬删，均在 include）不受影响。`tests/orchestration` 全目录 208 passed。

---

## 抽测证据摘要

- pytest 实跑：330(5)/331 契约(3)+双真轨(8)/332(14)/333(15)+llm_router 既有(25)/334 引擎(13)/335(10)/337 引擎(3)/338(3)/339 orchestration(208)，全绿零 fail。
- go test 实跑（-count=1）：handler 包 TestDedupHitDecisionTriState(6)+NeverReplaysBlank+Push 两组 337 用例全绿。
- 回滚实验：338 include 注释一行 → 守卫红，还原后绿（已还原，工作树净）。
- 恒真性思想实验：330 删 markers 即红、334 删 blank-guard 即红、335 回滚计划特例即钱测红、337 404 即红。

## 发现的问题清单

无新增问题，无新台账行（V3-FIX-345 未启用）。两条非扣分观察，供后续参考：

1. 【334 语义细微处】引擎缓存路径对空 message 缓存体返回 COMPLETED+空 message（而非 UNKNOWN），由网关 blank-guard 兜底降级 duplicate_request——可观测行为收敛一致（绝不回放空帧），但「completed 空体→UNKNOWN」的严格字面语义仅 ledger fallback 路径成立；当前双层结构下无实害，不建议改动。
2. 【339 遗留】游客过期行存储卫生缺口（expires_at 无执行方）按台账留待产品决策，非本卡范围。

---

## 复验期 main 推进核验（postscript）

复验进行期间 main 自基线 856ce94d 推进 2 个 commit（1f8af568 台账180轮 docs + 2e81a696 wt647 Go lint 批四 revive/staticcheck/unparam/ctx 40 处机械烧减）。后者触及本批复验文件（chat_orchestrator_chatflow.go / proxy_routes.go / agent/client.go），已追加核验：

- diff 逐行核对：334 去重三分支（dedupHitDecision/buildReplayChatResponse/duplicate_request 兜底）与 337 /push 组注册面零语义改动（lint 仅签名简化如 resolveUserIdentity 去 error 返回、FileIds→FileIDs 拼写）；
- 新 main HEAD 上重跑受影响测试（-count=1）：TestDedupHitDecisionTriState + NeverReplaysBlankMessage + TestPushInteraction* 全绿。

九张 PASS 结论在 main@1f8af568 上继续成立。
