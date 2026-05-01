# Reviewer B — E02: EventBus可靠性——Redis Streams消费组/DLQ/重试
Timestamp: 2026-04-26T03:30:00+08:00
Chain Index: 22 (Round 4 — E-chain audit)

## Chain Flow Summary
EventBus 使用 Redis Streams 实现，`publish()` 写入 `sparkle_events` stream（maxlen 50000），支持指数退避重试（max 3 次）。`subscribe()` 通过 `xgroup_create` + `xreadgroup` 创建消费组。消费者失败时有 DLQ 机制（Redis stream + DB 双写）。`_consume_loop` 还通过 `xautoclaim` 回收 stale messages。幂等性通过 `idempotency_store` 防重复消费。系统有 18 个 consumer service 订阅 `sparkle_events` stream。

## Critical Issues 🔴
**`backend/app/core/event_bus.py:1161-1173`**: `_process_stream_message` 在 callback 抛异常时直接调用 `_move_to_dlq`，绕过了 `_handle_failed_message` 的 retry 逻辑。`_requeue_for_retry` 方法（line 871-909）实现了完整的重试机制（递增 `_retry_count`、xack+re-publish、max_retries 判断），`_handle_failed_message`（line 911-951）正确路由 retry vs DLQ。但 `_process_stream_message` 完全不调用 `_handle_failed_message`——消费者任何一次失败都直接进 DLQ，不重试。Expected: 消费者失败后按 max_retries=3 重试，超过才进 DLQ。Actual: 消费者失败后直接进 DLQ，零重试。影响：瞬时错误（DB 连接抖动、超时）导致事件永久进入 DLQ，需要人工干预恢复。Evidence: `_process_stream_message:1165` 调用 `_move_to_dlq`，对比 `_handle_failed_message:923` 的 retry/DLQ 分支路由。

## Major Issues 🟡
**事件覆盖缺口——多个已定义事件类型无消费者**: 以下 event_bus.py 中定义的事件类型在 18 个 consumer 中 grep 不到订阅者（仅搜索 `*_consumer.py`，其他 service 中的订阅可能遗漏）：
- `task.started` — 无 consumer 处理
- `plan.created` — 无 consumer 处理
- `user.registered` — 无 consumer 处理（stage33_journey_event_service 可能处理，但不在 consumer 文件中）
- `reflection.completed` — 无 consumer 处理
- `trait_observed` — 无 consumer 处理
- `coldstart_completed` — 无 consumer 处理
- `user_settings.updated` — 无 consumer 处理
- `calendar.event.created/updated/deleted` — 无 consumer 处理
- Card Protocol 事件（`card.created`、`card.updated`、`card.lifecycle_changed`、`card_edge.created`、`card_edge.deactivated`、`occurrence.status_changed`、`occurrence.completed`）— 无 consumer 处理
- `mastery_updated_from_error` — 无 consumer 处理
这些事件被发布到 stream 但可能永远不被消费，占用 Redis 内存（maxlen 50000 自动淘汰旧消息，但仍然浪费）。Card Protocol 事件（7 种）全部无消费者尤为显著——Phase 0 声明的 taxonomy 事件已被发布但无人监听。

## Minor Issues 🟢
None found.

## Working Well ✅
- **`event_bus.py:1024-1044`**: `publish` 有指数退避重试（base 200ms × 2^attempt, max 2000ms），最多 3 次。发布失败也写入 DLQ（line 1047-1061），双重保障。
- **`event_bus.py:1101-1122`**: `_claim_stale_messages` 使用 `xautoclaim` 回收消费者崩溃后遗留的 pending messages，idle 超时 5000ms。
- **`event_bus.py:1142-1160`**: 幂等性机制完善——idempotency store 的 get/lock/set/unlock 保护，防止重复消费。TTL 86400 秒自动清理。
- **`event_bus.py:781-869`**: DLQ 双写机制——Redis stream（实时查看）+ PostgreSQL DB（持久化），`EventBusDLQEntry` 模型记录完整上下文（stream、group、consumer、retry_count、error、payload）。
- **`event_bus.py:1255-1323`**: `get_consumer_lag` 和 `get_dlq_stats` 提供可观测性，可监控消费延迟和 DLQ 积压。
- **18 个 consumer services**: 覆盖 achievement、galaxy、task、plan health、profile、cognitive、execution、intervention、capsule、nudge、social signal、SRL、idiographic 等领域。

## Files Examined
- `backend/app/core/event_bus.py` (full file — 1399 lines)
- `backend/app/services/achievement_event_consumer.py` (lines 55-78)
- `backend/app/services/galaxy_event_consumer.py` (lines 51-75)
- `backend/app/services/task_event_consumer.py` (lines 46-71)
- `backend/app/services/main_chain_artifact_consumer.py` (lines 47-73)
- `backend/app/services/profile_event_consumer.py` (lines 63-84)
- `backend/app/services/plan_health_event_consumer.py` (lines 52-71)
- `backend/app/services/cognitive_event_consumer.py` (line 30-40)
- `backend/app/services/nudge_event_consumer.py` (line 29-39)
- `backend/app/services/execution_event_consumer.py` (lines 39-54)
- 18 consumer services (grep for `event_bus.subscribe`)

## Confidence: High — retry 绕过 bug 已通过 `_process_stream_message` vs `_handle_failed_message` 代码路径对比确认；孤儿事件通过 event_bus.py 定义列表 vs consumer grep 交叉验证。
