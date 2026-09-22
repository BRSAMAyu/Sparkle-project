# EVENT-ACK · 事件消费 blanket-except 恒 ack 静默丢失修复 — 收工报告

- Worker：V3 舰队 Worker（EVENT-ACK 卡，GHOST-OUTCOME 裁决项②派生）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt137`（基线 a1572cfa）
- 日期：2026-09-22
- 交付物：`backend/app/` 6 文件修改 + `backend/tests/unit/test_event_ack_reliability.py`（新增，17 测试）+ 本报告 + `changes.patch`
- 未 commit / 未 push（纪律遵守）；主仓只读；未动活栈/活 Redis（消费行为验证全走 fakeredis 2.38.0 与既有测试夹具）

---

## 0. 病灶机制一句话

所有 `event_bus.subscribe()` 的消费者的失败语义由**回调是否抛出**决定：回调吞掉异常正常返回 → `EventBus._process_stream_message` 视为成功 → **恒 ack**（总线侧的失败 metric、有界重试、DLQ、pending 留存全部被绕过）。总线基础设施本身是好的——缺的是回调层"失败必须上抛"。

## ① 同族点清单（修前行为 → 修后行为）

### A. XACK 直接调用点（3 处）

| # | 位置 | 修前失败行为 | 修后 |
|---|---|---|---|
| A1 | `app/core/event_bus.py`（`_process_stream_message`/`_requeue_for_retry`/`_move_to_dlq`） | **已合规**：回调抛出 → metric+重排队（requeue 先于 ack）/DLQ（先落档再 ack）；重排队自身失败 → 不 ack 留 PEL；`_claim_stale_messages` 每轮 XAUTOCLAIM 回收 pending | **零改动**（本卡的参照实现，仅加回归护栏测试） |
| A2 | `app/workers/graph_sync_worker.py:131` | 失败不 ack（留 PEL）**但无任何回收面**——pending 永久卡死；日志级 TODO 注释"可以选择重试或移到死信队列" | 补最小回收：`_recover_pending()`（XAUTOCLAIM，min_idle 60s，每轮先于 xreadgroup），失败日志升为结构化 warning 带 msg_id；未知消息类型显式良性 ack 注释化 |
| A3 | `app/services/preference_event_consumer.py:75,104,123` | 成功→ack；失败→requeue/DLQ→ack（**已合规**）；但**无 pending 回收**——崩溃（xreadgroup 与 ack 之间）条目永久卡死；非偏好事件静默 ack | 补 `_recover_pending()`（XAUTOCLAIM，min_idle 5s，复用既有 requeue/DLQ 路由）+ `_extract_retry_count` 稳健解析；非偏好事件 → 显式注释 + debug 留痕 |

### B. 吞异常回调 → 恒 ack（4 处修复 + 2 处核查合规）

| # | 位置 | 修前失败行为 | 修后 |
|---|---|---|---|
| B1 | `app/services/galaxy/event_listener.py` — `_on_event` + `on_task_completed`/`on_task_abandoned`/`on_error_created` 整事件 except | **本卡原始病灶**：DB 会话/提交/UUID 级任何失败 → error 日志 → 正常返回 → 恒 ack。星图掌握度/负反馈静默丢失 | 整事件级失败：结构化 warning（带 task_id/error_id）+ **上抛**（总线不 ack → 有界重试 → DLQ）；单节点循环保留 best-effort（显式白名单注释 + error 日志）；未知事件类型保留良性路由 ack（docstring 声明） |
| B2 | `app/services/galaxy/outcome_absorption_service.py` — `OutcomeAbsorptionConsumer._on_event` | 同上：吸收失败（DB 抖动等）→ 恒 ack。原注释"单事件失败不拖垮消费循环"**前提错误**——总线的 per-message 异常隔离本就保证这一点，吞掉反而让幂等门救不回从未到达的吸收 | 移除 blanket-except，失败上抛；docstring 说明：吸收幂等（mastery_audit_log 行 + absorbed_outcomes 标记）保证重投递安全 |
| B3 | `app/services/galaxy/streaming_service.py` — `_on_event` + `_on_mastery_updated` | 推送面失败（含 malformed payload 的 UUID 解析）→ 恒 ack，用户实时星图更新静默丢失 | 整事件失败上抛；`_send_to_user` 单连接推送保留 best-effort（显式注释） |
| B4 | `app/services/galaxy_execution_consumer.py` — `handle_event` | `execution.result_ingested` 星图同步失败 → 恒 ack，委派成果永不入图 | 失败：结构化 warning（带 intent_id）+ 上抛 |
| B5 | `app/core/galaxy_event_bridge.py`（SSE 桥） | **核查合规，零改动**：`_handle_event` 无吞——失败已自然进入总线管线 | — |
| B6 | `app/services/galaxy_event_consumer.py` | **核查合规，零改动**：`handle_event` 派发层已在前卡（R2 F3/F9/K6）修为上抛（`test_galaxy_handle_event_surfaces_callback_failures` 锁定）；内层 catch 均为带日志的单项 best-effort | — |

### C. 同族但本卡不动（清单义务，建议后续立卡）

均与 B1-B4 同一"整事件吞 → 恒 ack"模式，一行 `raise` 可修，但各自的回归面不在本卡红线域（`-k "event_bus or outcome_absorption or galaxy_sse or event_listener"` 不覆盖），修了无法按对比法验证：

| 位置 | 修前行为 |
|---|---|
| `app/services/task_event_consumer.py`（:265/:375/:391 整事件 except） | task.completed/abandoned/stuck 投影失败 → error 日志 → 恒 ack |
| `app/services/achievement_event_consumer.py`（:390） | 成就记录链失败 → warning → 恒 ack |
| `app/services/profile_event_consumer.py`（6 个 per-event handler 全吞） | 偏好/行为画像事件失败 → 恒 ack |
| `app/services/plan_health_event_consumer.py`（:169）、`app/services/nudge_event_consumer.py`（:47） | 计划健康/nudge 事件失败 → 恒 ack |
| `app/consumers/journey_consumer_base.py`（:82） | journey 事件失败 → metric+用户失败通知 → 恒 ack（有 UX 语义，需产品裁决） |
| `app/services/cognitive_event_consumer.py`、`app/services/capsule_event_consumer.py`（:102 per-user 循环） | 分析/胶囊再生失败 → 日志 → 恒 ack（单项 best-effort 与整事件吞混合，需逐处分类） |
| `app/aurora/proactive/pipeline.py`（:347） | 吞异常，注释"失败走 DLQ 语义"**事实错误**（吞掉恰使 DLQ 永不触发）——至少该注释需修正 |

**已核查合规、无需动的其余消费者**（前卡 R2 F3/F9 已修）：`run_projection_consumer`（docstring 明载"不吞投影失败"契约）、`social_signal_event_consumer`、`main_chain_artifact_consumer`、`document_feedback_event_consumer`、`execution_event_consumer`、`idiographic_association_service`、`srl_phase_tracker_service`、`intervention_event_consumer`（log+raise）、`cognitive_stream_worker`（自带 `_send_to_dlq`）。

## ② 红线面（回归验证）

方法：对比法，基线（a1572cfa 原样）→ 修后，同命令同集，**失败集零新增**。pytest 绝对路径 `/opt/homebrew/bin/pytest`，`SECRET_KEY=test`，单进程定向，`--ignore=tests/northstar_eval`。

| 命令面 | 基线 | 修后 | 判定 |
|---|---|---|---|
| `tests -k "event_bus or outcome_absorption or galaxy_sse or event_listener"` | 31 passed, 22 skipped, **0 failed** | 39 passed, 22 skipped, **0 failed**（+8 = 新测试文件中命中 -k 的 8 个） | ✅ 失败集零新增 |
| 显式文件：`test_phase4_galaxy_services.py` + `test_k6_silent_exception_fix.py` + `test_preference_consumer_safety.py` + `test_galaxy_learning_graph_operational.py` + `test_openclaw_phase5_10_followup.py` + `test_event_bus_reliability.py` + `test_event_bus_shutdown.py`（+ 新测试文件） | 41 passed, **0 failed** | 58 passed, **0 failed**（41 + 17 新） | ✅ 零回红 |
| 追加邻接：`test_error_book_mastery_sync_service.py` + `test_f16_galaxy_weak_node_injection.py` | — | 50 passed, **0 failed** | ✅ |

- **`tests/test_event_bus_shutdown.py` 与 phase4 文件不回红**：显式跑，全绿 ✅（注意：卡片 -k 过滤因下划线不匹配只选中 phase4 的 2 个用例，故 phase4 全文件必须显式跑——已做）
- 22 skipped = `test_event_bus_real_redis.py`/`test_event_bus_e2e.py` 等**需活 Redis 的集成测试**，按纪律（不动活栈/活 Redis）保持跳过，前后一致
- 新测试 17/17 全绿（`tests/unit/test_event_ack_reliability.py`）

### pending 回收证明（fakeredis 真实 PEL 语义，非 mock 断言）

| 测试 | 证明 |
|---|---|
| `test_graph_sync_worker_failure_stays_pending_then_recover_acks` | 处理失败后 `XPENDING=1`（未 ack 不丢）→ 恢复后 `_recover_pending` 重试成功 → `XPENDING=0`（ack） |
| `test_preference_consumer_recovers_crash_left_pending` | 模拟崩溃（xreadgroup 后未 ack）→ `_recover_pending` 处理并 ack → PEL 清空、缓存失效被调用 |
| `test_preference_consumer_recover_failure_routes_to_requeue` | 回收重处理失败 → 走既有 requeue：原条目 ack、`_retry_count=1` 副本重进 stream |
| `test_event_bus_requeue_failure_leaves_message_pending` | 红线：requeue 自身失败 → `xack` 从未被调用（留 PEL 天然重试面） |
| `test_event_listener_failure_requeues_then_recovery_acks` | 总线级端到端：galaxy 监听器失败 → 重排队（事件不丢）→ 重试成功 → ack、不进 DLQ |
| `test_graph_sync_worker_recover_pending_is_noop_when_no_pending`、`test_event_bus_claim_stale_messages_*` | 空 PEL 无副作用；EventBus 既有 XAUTOCLAIM 面回归护栏（防后续回退） |

异常→pending、恢复→重试成功、良性路径零变化三类断言齐备（后者：`test_event_listener_unknown_event_type_is_benign_ack`、`test_outcome_absorption_consumer_ignores_non_outcome_events`、`test_preference_consumer_benign_routing_unchanged`、`test_galaxy_execution_consumer_filter_unchanged`、`test_streaming_service_happy_path_unchanged`）。

## ③ 冲突面（在途卡交集声明）

- **wt136（phase5 测试域）**：未动其域内任何文件（`galaxy_event_consumer.py` 未改，K6 测试与 openclaw phase5 测试显式跑全绿）。`galaxy_execution_consumer.py` 的 `handle_event` 失败语义变化若 wt136 有新测试断言"吞掉"行为则冲突——已核对其域内现有测试无此断言。
- **wt138（错题幂等迁移 ERR-IDEM）**：文件零交集（其改 `error_book_mastery_sync_service.py`；我改 galaxy 消费回调与两个独立消费者）。行为面间接交集：`event_listener.on_error_created` 失败上抛后重试，错题负反馈路径进入 at-least-once——ERR-IDEM 的幂等门在 mastery sync 吸收侧，重投递安全方向一致、不相互破坏。
- **wt139（mobile）**：零交集（本卡纯 backend）。

## ④ 诚实申报

1. **语义变化 = 恰好一次假象 → at-least-once**：此前"失败恒 ack"给下游的其实是 exactly-once 假象。修后真实失败会重投递，**各消费者从此必须容忍重放**（项目总线本就是此契约，run_projection docstring 明载；B1/B2 的幂等面——outcome audit 门、spark_node 的 audit 行——已满足）。
2. **graph_sync_worker 边写重放**：AGE `add_edge` 为追加写，重放窗口（min_idle 60s，仅真实故障/崩溃面）内可能产生重复边；vertex 按 id 幂等。未引入 DLQ（遵守卡片"不引入新重试设施"），毒性消息会以每 60s 一条的节奏 warning 可见重试——不静默、不限次，若不可接受需后续立卡补 DLQ。
3. **C 组未修**：8 个同族点留待后续卡（理由：无法在本卡红线域内验证），清单见 ①C。
4. **保留的显式吞**（均有注释+error/debug 日志，非静默）：event_listener 单节点循环、streaming `_send_to_user`、galaxy_event_consumer 内层单项、preference `_report_stream_length`（纯 metric，与 ack 无关，未动）。
5. **`app/gen/`** 从主仓拷贝至 worktree（git 忽略，不入 patch，随 worktree 生命周期回收）。
6. 测试运行的 22 个 skip 为活 Redis 集成测试，本卡未触碰活 Redis，行为面靠 fakeredis 真实 PEL/XAUTOCLAIM 语义验证（fakeredis 2.38.0 对 xreadgroup/xautoclaim/xpending/xack 的语义已实测核对）。

## ⑤ 收工核查

- [x] 改动全部在 worktree 内（`git status` 仅 6 修改 + 2 新增，主仓零触碰）
- [x] 无 commit / 无 push
- [x] 交付物零凭据（patch 与报告仅含代码与路径）
- [x] 未起任何长驻进程/模拟器/浏览器；无 /tmp 残留（探针均为内联脚本）
- [x] 无构建产物入库（mobile/build、.dart_tool 均未产生）
- [x] 内存纪律：pytest 定向单进程，最大峰值为全量定向集 26s 内完成，无 HEAVY 操作
- [x] `df` 收工检查通过（15Gi 可用，>6G 门槛）
- 交付物路径：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt137/v3-output/EVENT-ACK/REPORT.md` + `changes.patch`（845 行，7 文件，新文件带 `--- /dev/null` 头）
