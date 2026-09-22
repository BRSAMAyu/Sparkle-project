# EVENT-ACK-2 · 事件消费吞异常同族 8 点清偿 — 收工报告

- Worker：V3 舰队 Worker（EVENT-ACK-2 卡，EVENT-ACK 报告 ①C 清单派生）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt144`（基线 be10d59e，含 EVENT-AXT galaxy 域修复 37cac6e8）
- 日期：2026-09-22
- 交付物：`backend/app/` 7 文件修改（4 文件行为修复 + 3 文件注释化）+ `backend/tests/unit/test_event_ack2_reliability.py`（新增，12 测试）+ 本报告 + `changes.patch`（533 行，8 文件）
- 未 commit / 未 push（纪律遵守）；主仓只读；未动活栈/活 Redis（fakeredis 2.38.0 与既有测试夹具验证）
- 基线对照：`git clone` 克隆至 `/tmp/ack2-baseline`（纯 HEAD，收工已删），同命令同集对比

---

## 0. 结论一句话

EVENT-ACK ①C 清单所列 8 点中，**核实后 5 点已在基线达到目标形态或属显式设计**（清单相对 a1572cfa 已过期——多卡并行使部分点被更早修复），**真吞异常恒 ack 实为 4 处**（plan_health 整事件、achievement 两 handler、capsule 再生守护、aurora `_on_bus_event`+事实错误注释），本卡全部修复并上抛进入总线失败管线；pending 回收面**确认由 EventBus `_consume_loop` 每轮 XAUTOCLAIM 统一覆盖**（`event_bus.py:1302-1313`，对所有 subscribe 组生效），无需逐消费者补建。

## ① 8 点逐点表（修前行为 → 处置 → 依据）

| # | 域（文件） | 核实·修前行为 | 处置 | 依据 |
|---|---|---|---|---|
| 1 | task_event_consumer（`app/services/task_event_consumer.py`） | **核查合规，非清单所述吞异常**：三整事件 handler（:265/:375/:391）均 `logger.error + raise` 兜底；并行 fan-out 经 `_safe_run` 单项隔离（warning 留痕）。`tests/services/test_consumer_exception_propagation.py` 文档串明确此为刻意契约（"EventBus retry/DLQ deliberately never sees their exceptions" 指单项面） | `_safe_run` docstring 显式白名单化（注释，行为零变化） | 该文件自 clean-slate 初始提交即含 raise；F5 契约测试锁定 |
| 2 | profile（`app/services/profile_event_consumer.py`） | **核查合规，非清单所述"6 handler 全吞"**：全部 per-event handler `logger.error + raise`。仅 3 处良性单项 best-effort：`_invalidate_context_cache`/`_invalidate_profile_context_cache`（TTL 窗口内陈旧可接受）、`_load_seed_library`（降级 None） | 3 处显式注释化（行为零变化）；F5 传播契约测试锁定 | 同上测试文件 `test_profile_preference_updated_propagates_exceptions` |
| 3 | plan_health（`app/services/plan_health_event_consumer.py:169`） | **真吞异常恒 ack**：`_handle_plan_health_alerted` 整事件 `logger.error` 无 raise——计划健康提醒/干预记录静默丢失。内层 card_protocol 桥 catch 为单项 best-effort（rollback+warning） | **整事件失败：结构化 error（带 user_id）+ 上抛**；桥失败保留 best-effort 并注释化（冷却提醒可能已 enqueue，重投递会重复打扰用户） | 新测试 `test_plan_health_consumer_surfaces_whole_event_failure` / `..._bridge_failure_stays_contained` |
| 4 | nudge（`app/services/nudge_event_consumer.py:47`） | **核查合规，非清单所述吞异常**：`logger.exception + raise` 已在位 | 零改动；新增回归护栏测试锁定（防未来回退） | 新测试 `test_nudge_consumer_surfaces_failure` |
| 5 | journey（`app/consumers/journey_consumer_base.py:82`） | **可见失败设计，非静默丢失**：失败 → metric + error 日志 + 用户失败通知（`_emit_failure_update`）。恒 ack 但非"吞"；EVENT-ACK 已标"需产品裁决" | 注释化显式声明设计意图与裁决 flag（行为零变化）——上抛会使每次总线重试重复发送失败通知；3 个 stage34 错误路径测试锁定该契约 | `tests/unit/consumers/test_stage34_journey_consumers.py` 3 个 `*_error_path_emits_system_update` |
| 6 | achievement（`app/services/achievement_event_consumer.py:278/:390`） | **两处真吞异常恒 ack**：`_handle_execution_result`（执行结果驱动成就进度失败 → warning → 丢）与 `_handle_achievement_unlocked`（认知碎片/社区广播/里程碑通知/画像信号失败 → warning → 全丢）。内层单项（广播 :349、Spine :375、chronicle :388）为 best-effort | **两处整事件失败：结构化 warning/error（带 intent_id / user_id+achievement_id）+ 上抛**；3 处内层单项注释化（chronicle 保留 Redis-only fallback 语义） | 新测试 `test_achievement_unlocked_surfaces_whole_event_failure` / `test_execution_result_achievement_surfaces_failure` |
| 7 | capsule（`app/services/capsule_event_consumer.py:102`） | **真吞（守护面）**：`_handle_regenerate_request` 的 catch 仅捕获偏好读取/批处理基础设施级失败——`generate_capsules_batch` 自身已把生成失败落档（`job.status=failed`+commit）正常返回。但落网之鱼（如偏好读失败）静默 ack = 用户显式再生请求被丢 | **上抛**（带 user_id 结构化 error）。重试安全：批次在单事务内，失败未提交即回滚 | 新测试 `test_capsule_regenerate_surfaces_batch_failure` |
| 8 | aurora（`app/aurora/proactive/pipeline.py:347`） | **真吞 + 注释事实错误**：`_on_bus_event` blanket-except，注释"失败走 DLQ 语义"——吞掉恰使 DLQ/重试/metric 永不触发。管线内部已按 fail-closed 哲学逐处 contain（快照/相关性/状态写/投递，均有 R2 P1-1 级注释） | **`_on_bus_event` 改为结构化 error（event_type+user_id）+ 上抛**；`handle_event` docstring 同步改写（"永不抛出"→"正常路径不抛出，意外错误交总线"）；内部 fail-closed catch 全部保留 | 新测试 `test_aurora_on_bus_event_surfaces_failure` / `..._benign_path_unchanged` |

**pending 回收确认**：EventBus `_consume_loop` 每轮先 `_claim_stale_messages`（XAUTOCLAIM，`min_idle_time=pending_retry_idle_ms`）回收崩溃/慢消费者遗留 pending，再 xreadgroup 新消息——对所有 `subscribe()` 组（含本卡 8 域）统一生效，无需逐消费者补建（卡片"若总线已有统一回收则确认覆盖"条款命中）。

## ② 红线面（回归验证，对比法）

方法：基线（be10d59e 克隆 `/tmp/ack2-baseline`，零本卡改动）→ 修后 worktree，同命令同集，**失败集零新增**。pytest 绝对路径 `/opt/homebrew/bin/pytest`，`SECRET_KEY=test`，单进程定向，`--ignore=tests/northstar_eval`。

### 每修一点定向测试

| 命令面 | 基线 | 修后 | 判定 |
|---|---|---|---|
| `tests/unit/test_event_ack2_reliability.py`（新增 12 测试） | —（不存在） | **12 passed, 0 failed** | ✅ 全绿 |
| `tests/aurora/test_proactive_event_pipeline.py` + `test_proactive_relevance.py`（aurora 域，875 行套件） | 204 passed | 204 passed | ✅ 零回红 |
| `tests/unit/test_phase2_intervention_pipeline.py` + `test_plan_health_signal_service.py`（plan_health 域） | 37 passed, 1 failed（预存，见下） | 37 passed, 1 failed（同一预存） | ✅ 零新增 |
| `tests/unit/test_achievement_event_consumer.py`（achievement 域） | 4 passed | 4 passed | ✅ |
| `tests/unit/test_dailyflow_p2_capsule_today_window.py`（capsule 域） | 4 passed, 1 error（活 PG 集成） | 4 passed, 1 error（同一） | ✅ |
| `tests/unit/consumers/test_stage34_journey_consumers.py`（journey 域） | 8 passed | 8 passed | ✅ |
| `tests/unit/services/test_profile_event_consumer.py` | 3 passed | 3 passed | ✅ |
| `tests/unit/test_checkpoint_nudge_p3b.py` + `test_nudge_channel_delivery.py` + `test_comeback_nudge_task.py`（nudge 域） | 17 passed, 2 failed（预存） | 17 passed, 2 failed（同一对用例） | ✅ 零新增 |
| `tests/services/test_consumer_exception_propagation.py`（task_event/profile F5 契约，单文件跑） | 3 passed | 3 passed | ✅ |

### 预存失败/错误核实（均与本卡无关，基线逐一复现同一集合）

1. **`app.gen.sparkle.rag` 命名空间包导入序伪象**：`test_consumer_exception_propagation.py::test_task_completed_contains_sub_handler_failures`（及 journey 测试文件收集）在**特定多文件同进程收集序**下报 `ModuleNotFoundError: No module named 'app.gen.sparkle.rag'`；单文件跑全绿。基线克隆复现**完全相同**失败（37 passed/1 failed 同一对用例）——测试间导入态污染，非本卡引入。本卡未触碰任何 import 面。
2. **`test_nudge_channel_delivery.py::TestResolveChannel` 2 用例**（in_app/silent_channel_from_directive）：基线与修后失败集逐字一致（本卡对 nudge 零改动）。
3. **`test_capsule_ai_personalization.py` 1 error**：`asyncpg InvalidPasswordError` 活 PG 集成测试（纪律：不动活栈），基线同错。

### 显式红线文件（phase4 / event_bus_shutdown 不回红）

| 文件 | 结果 |
|---|---|
| `tests/test_event_bus_shutdown.py` + `tests/test_phase4_galaxy_services.py` | **25 passed, 0 failed** ✅ |
| `tests/unit/test_event_bus_reliability.py` | 4 passed ✅ |
| `tests/unit/test_event_ack_reliability.py`（EVENT-ACK 前卡 17 测试，防回退） | **17 passed** ✅ |

### 全域收尾对比（卡片指定 -k 表达式）

命令：`pytest tests -k "event or consumer or task_event or profile or plan_health or nudge or journey or achievement or capsule or aurora" --ignore=tests/northstar_eval`

执行方式说明：整机内存熔断（主会话两次击杀 >1.5G 的宽扫描进程）迫使改为**逐文件定向循环**（196 个命中文件，每文件独立 pytest 进程 + `--timeout=60`，单进程小内存），同等覆盖、可断点续跑。基线对照分两层：**(a) 决定性对比**——worktree 侧 8 个失败文件合并跑与基线克隆同命令，失败集逐字对比（11=11，零差集）；**(b) 确认性抽查**——基线同法逐文件循环跑至 82/196，失败剖面与 worktree 一致（如 `spine/test_advanced_features.py` 2 failed 两侧同现），因内存熔断纪律提前收手：worktree 侧其余 ~158 文件全绿，不构成"新增失败"面，无需基线对照即可判定。

- **worktree 侧**：196 命中文件全部跑毕（169 平铺 + 24 嵌套路径 + 3 环境特例）。~166 文件全绿（含 `test_event_ack2_reliability.py` 12/12、event_bus_reliability 4、eventbus_subscribe_raise 单测绿）；失败集中于 8 文件 11 用例。
- **失败集逐一对比**（8 文件合并跑，同命令两侧）：**基线失败集 = 修后失败集 = 11 用例，逐字一致，零新增零残留**：

  | 失败用例（两侧一致） | 域 | 与本卡关系 |
  |---|---|---|
  | `test_user_insight_compiler.py::test_profile_context_service_compiles_canonical_user_insight_state_with_expanded_signal_families` | profile 画像编译 | 预存（本卡对 profile 仅注释） |
  | `spine/test_advanced_features.py::test_v210_spine_start/close_aurora_session`（2 例） | Spine | 预存 |
  | `test_idiographic_kill_switch.py::test_idiographic_shadow_computes_without_db_writes_or_events` | idiographic | 预存 |
  | `test_intervention_outcome_tracker.py::test_record_intervention_writes_db_and_publishes_event` | intervention tracker | 预存（tracker 非本卡改动面） |
  | `test_memory_admin_api.py::test_memory_admin_expanded_aurora_kill_switches` | memory admin | 预存 |
  | `test_outcome_promotion_governor.py::test_outcome_promotion_governor_synthesizes_profile_ledger_into_profile_learning` | profile learning | 预存 |
  | `test_srl_event_publish.py::test_publish_srl_event_publishes_transition_payload / keeps_shadow_mode_active`（2 例） | SRL | 预存 |
  | `test_nudge_channel_delivery.py::TestResolveChannel::test_in_app/silent_channel_from_directive`（2 例） | nudge 渠道 | 预存（本卡 nudge 零改动） |

- **环境性排除（双侧一致）**：`tests/unit/test_run_projection_consumer.py` 依赖活 PG 的 `db_session` 夹具，在本机当前状态下阻塞于 socket 连接（两次全量跑均同一位置、基线复现；该文件属 EVENT-ACK 已核查合规面，非本卡改动面），双侧同排除；`tests/unit/test_eventbus_subscribe_raise.py` 单测通过但进程在解释器关闭期挂起（EventBus 消费循环任务未退出，预存环境特性，双侧同状，按进度点证据记绿）。

**判定：✅ 失败集零新增、零残留，本卡目标域全绿；phase4/event_bus_shutdown/event_bus_reliability/EVENT-ACK 前卡 17 测试显式跑全绿。**

## ③ 行为面声明（at-least-once 下游幂等性逐点评估）

总线侧本就有两层：`evt:{stream}:{message_id}` 幂等锁（同消息重投递去重，`_original_message_id` 保 requeue 链路 id 不变）+ 失败有界重试 → DLQ。本卡修复使 4 域真实进入 at-least-once，下游逐点现状：

| 域 | 下游幂等现状 | 评估 |
|---|---|---|
| plan_health | InterventionRecord 桥有**近期 PENDING 去重门**（"user 无该 plan 的近期 PENDING 干预"才建）→ 重投递大体安全；冷却 `SystemUpdateService.enqueue` **无去重键** → 整事件重试窗口内可能重复一条"观察中"低优先级提醒 | 部分满足；enqueue 侧重复为低危（low priority + 有界重试次数上限），如需强一致登记独立卡 |
| achievement | `AchievementEngine` 进度为 read-then-overwrite（重放安全）；解锁有已解锁检查（顺序重放不重复发奖；并发竞态无 unique 约束兜底——预存现状）；`create_fragment` **自带 `source_event_id` 幂等门，但本调用点未传该键** → 重试窗口内可重复一条认知碎片 | 部分满足；碎片重复为低危（positive_milestone 内容重复），补 `source_event_id=achievement_id` 一行即可，留独立卡 |
| capsule | `generate_capsules_batch` 单事务：失败未提交即回滚 → 重试净重做；仅 commit 后失败窗口可重复整批（窄） | 基本满足 |
| aurora | 意外错误才逃逸（内部 fail-closed 全 contain）；重试重复面 = 投递/状态写在"已成功但后续抛异常"的极窄窗口；novelty/dedup 记忆本身 best-effort | 满足（逃逸面本身就是故障态） |
| task_event（前在 at-least-once，本卡零行为变化） | BehaviorSignalCollector 各 `_maybe_emit_*` 自带条件门；AutoFragment `collect_from_task_completion` 支持 `source_event_id`（调用点是否传键未深查——非本卡语义变更面） | 不变 |
| profile | DELETE 幂等；`update_inferred_preference` 同值覆写幂等；enqueue 重复风险仅在整 handler 失败重试时出现 | 满足（重放为同值覆写） |
| nudge（前已 raise，at-least-once 为预存现状） | `_create_in_app_notification` + push **无业务去重键** → 重试可重复一条通知 | 预存登记（本卡未改变其语义） |
| journey（本卡零行为变化） | 失败即 contain 恒 ack，从不重试 → 无重放面；若产品裁决改上抛需先补通知去重 | 不变，裁决 flag 已注释化 |

**结论**：无一点因本卡修复进入"高风险重复"象限；两处显式登记（plan_health enqueue、achievement fragment 未传幂等键）均为低危用户可见重复，按卡片纪律不强行加幂等（独立卡素材已在上表）。

## ④ 冲突面（在途卡交集声明）

- **wt140（galaxy API 缓存）**：预期零交集——其动 API 层 `galaxy.py` 缓存，本卡 8 文件全部在 event 消费域（`services/`、`consumers/`、`aurora/proactive/`），无 galaxy_execution/galaxy 服务类文件。逐 hunk 级：本卡对 `pipeline.py` 的改动仅在 `_on_bus_event`/`handle_event` docstring，wt140 若有不预期交集应在合入窗口以 `git diff` 三方核对。
- **wt141（galaxy 域在途）**：零文件交集（本卡 8 文件无一属 galaxy 域；EVENT-ACK 已修的 galaxy 6 文件本卡未触碰）。
- **wt143（安全词库）**：零交集（其域为 safety lexicon；本卡无 chat/safety 面）。基线 be10d59e 已含其 SAFETY-FP 提交。

## ⑤ 诚实申报

1. **EVENT-ACK ①C 清单相对基线已过期**：8 点中 task_event（:265/:375/:391）、profile（6 handler）、nudge（:47）三点的"吞异常恒 ack"描述与 be10d59e 实况不符（该三点已是 raise 形态；task_event/profile 有 F5 契约测试在位）。本卡以"逐点核实"为准，不基于过期清单盲改——已合规点只加注释/护栏测试，未引入行为变化。
2. **语义变化面收窄为 4 处真吞点**：plan_health、achievement×2、capsule、aurora 进入 at-least-once。重放安全性评估见 ③；两处低危重复面如实登记未修（独立卡）。
3. **journey 未上抛**（EVENT-ACK 标注"需产品裁决"）：本卡维持可见失败设计（metric+用户通知），仅注释化 + 护栏。若产品裁决改上抛，需连带补 `_emit_failure_update` 去重，避免每次重试重复打扰。
4. **预存测试失败 3 组**（gen 导入序伪象、nudge channel 2 例、capsule 活 PG 1 例）基线逐字复现，非本卡引入，未越权修（超出本卡红线域）。
5. **`app/gen/`** 从主仓拷贝至 worktree（git 忽略，不入 patch，随 worktree 生命周期回收）。
6. 测试 skip 面与基线一致：活 Redis/活 PG 集成测试按纪律保持跳过/报错，行为面靠 fakeredis 与 mock 夹具验证。

## ⑥ 收工核查

- [x] 改动全部在 worktree 内（`git status`：7 修改 + 1 新测试 + `v3-output/EVENT-ACK-2/`，主仓零触碰）
- [x] 无 commit / 无 push
- [x] 交付物零凭据（patch 与报告经 `password|secret|api_key|token|PRIVATE` 扫描，仅 `SECRET_KEY=test` 测试惯例值）
- [x] /tmp 自清：`/tmp/ack2_changes.patch`（已移入交付目录）、`/tmp/ack2-baseline` 基线克隆（对比完成后删除）
- [x] 无构建产物入库；无长驻进程/模拟器/浏览器
- [x] 内存纪律：pytest 单进程定向，无 HEAVY 操作；运行前查 `swapusage` 空闲 1.26G、load <8
- [x] `df` 收工检查通过（>6G 门槛）
- 交付物路径：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt144/v3-output/EVENT-ACK-2/REPORT.md` + `changes.patch`
