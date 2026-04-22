# SPARKLE Aurora Stage 38 Handoff

⚠ 验收门未达标

## 验收结论

- `bash scripts/run_all_rule_guards.sh`：PASS
- `bash scripts/stage38/drill_transitions.sh`：PASS
- `cd backend/gateway && go test ./...`：PASS
- `bash scripts/journey_smoke.sh all`：PASS
- `cd backend && pytest -q`：FAIL

`backend pytest -q` 在 integration 区域提前暴露出非 Stage 38 直因的历史失败面，未能达到全绿。实跑过程中已观察到以下失败簇：

- `backend/tests/integration/test_adaptive_replanning_integration.py`
- `backend/tests/integration/test_auth_flow_integration.py`
- `backend/tests/integration/test_cache_consistency_integration.py`
- `backend/tests/integration/test_ltm_e2e.py`
- `backend/tests/integration/test_p0_fixes_validation.py`
- `backend/tests/integration/test_preference_to_plan_e2e.py`
- `backend/tests/integration/test_shop_acceptance.py`
- `backend/tests/integration/test_shop_end_to_end.py`

补充说明：

- Stage 38 新增链路已单独回归通过：`test_stage38_event_publishers.py`、`test_stage38_journey_subscribers.py`
- Journey 主链和 ErrorReplanBridge smoke 已回绿：`test_stage35_journey_smoke.py`、`test_stage35_error_journey_smoke.py`
- `AQ` 依赖的 Python proto stubs 已在本地生成并通过 guard 校验

## WS Commit Ledger

| WS | Scope | Commit |
| --- | --- | --- |
| WS-38-01 | EventBus reliability foundation | `7e247f3bac1cabe47e0ab55a98fec18898093975` |
| WS-38-02 | Seed / Theater / Shop publishers | `9a006d0626fcdb79be459284c449bec202940d07` |
| WS-38-03 | Journey subscriber expansion | `2a868354281566e613c8d26b38e353a0224ba594` |
| WS-38-04 | Error bridge, push scheduler, persistence | `3f539e61fac42fd4b2227bb968e34a415b195c17` |
| WS-38-05 | Gateway contract, gRPC error, FSM cap | `e593db348916af9a609a956b62715536790e046b` |
| WS-38-06 | HNSW + perf capacity | `fed14fb04ce863266288661da1ef50da3c370d00` |
| WS-38-07 | Rule AZ / BA, drill, handoff | `pending current commit at document authoring time` |

## Rule Lock Summary

- Rule AZ 新增并接入 manifest：所有 Stage 38 路径统一改走 `event_bus_reliable.publish(...)`，可靠消费者必须通过可靠消费包装器进入 XACK / DLQ 路径。
- Rule BA 新增并接入 manifest：Go chat history JSON 字段集必须为 Flutter `ChatMessageModel` 的超集。
- Stage 38 drill 新增：`scripts/stage38/drill_transitions.sh` 覆盖 `err_replan` / `push_scheduler` / `EVENT_BUS_DLQ_ENABLED` 的关键态切换。

## DLQ Schema Record

Migration：`backend/alembic/versions/stage38_01_add_event_bus_dlq.py`

| Column | Type | Notes |
| --- | --- | --- |
| `stream` | `varchar(255)` | 原始 stream 名称 |
| `event_type` | `varchar(255)` | 事件类型 |
| `user_id` | `uuid` | 用户作用域，允许为空 |
| `group_name` | `varchar(255)` | consumer group |
| `consumer_name` | `varchar(255)` | consumer 标识 |
| `message_id` | `varchar(255)` | Redis stream message id |
| `retry_count` | `int` | 最终失败前的重试计数 |
| `failure_stage` | `varchar(64)` | `publish` / `consume` 等失败阶段 |
| `error` | `text` | 错误文本 |
| `payload` | `jsonb` | 原始事件 payload |
| `id` | `uuid` | 主键 |
| `created_at` / `updated_at` / `deleted_at` | `datetime` | 标准审计字段 |

索引：

- `ix_event_bus_dlq_created_at`
- `ix_event_bus_dlq_deleted_at`
- `ix_event_bus_dlq_event_type`
- `ix_event_bus_dlq_failure_stage`
- `ix_event_bus_dlq_group_name`
- `ix_event_bus_dlq_message_id`
- `ix_event_bus_dlq_stream`
- `ix_event_bus_dlq_user_id`

## EventBus Event Inventory

### Seed Library

- `seed.created`
- `seed.consumed`

说明：`seed.favorited` 未重复接线；Stage 38 按 dispatch 要求沿用 Stage 34 既有收藏语义路径，避免新增重复 publisher / consumer。

### Theater

- `theater.resource_created`
- `theater.access_denied`

### Shop

- `shop.purchase_initiated`
- `shop.purchase_completed`
- `shop.purchase_failed`

## Chat History Contract Parity

Guard 结果：`[Rule BA] PASS - go_fields=19 dart_fields=18 missing=0`

### Stage 38 前后

| 状态 | 字段集 |
| --- | --- |
| Stage 38 前 | `id`、`conversation_id`、`role`、`content`、`created_at`、`user_id` |
| Stage 38 后 | `id`、`user_id`、`conversation_id`、`session_id`、`task_id`、`role`、`content`、`created_at`、`widgets`、`tool_results`、`has_errors`、`errors`、`requires_confirmation`、`confirmation_data`、`reasoning_steps`、`reasoning_summary`、`is_reasoning_complete`、`meta`、`agentCollaboration` |

### 对齐差异表

| Field | Mobile Expectation | Gateway Status |
| --- | --- | --- |
| `user_id` | required in payload path | aligned |
| `conversation_id` | required | aligned |
| `session_id` | factory fallback accepted | added for parity and back-compat |
| `task_id` | optional | added |
| `widgets` | optional | added |
| `tool_results` | optional | added |
| `has_errors` / `errors` | optional | added |
| `requires_confirmation` / `confirmation_data` | optional | added |
| `reasoning_summary` / `is_reasoning_complete` | optional | added |
| `meta` | optional | added |
| `agentCollaboration` | optional | added with current camelCase contract |
| `reasoning_steps` | gateway extra field | retained as backend superset |

## HNSW Index Creation Record

Migration：`backend/alembic/versions/stage38_06_add_vector_hnsw_indexes.py`

所有索引均采用 `CREATE INDEX CONCURRENTLY IF NOT EXISTS ... USING hnsw (...)`，且 migration 在 `autocommit_block()` 中执行，避免事务包裹并减少锁表风险。

| Index | Table | Column |
| --- | --- | --- |
| `idx_document_chunks_embedding_hnsw` | `document_chunks` | `embedding` |
| `idx_knowledge_nodes_embedding_hnsw` | `knowledge_nodes` | `embedding` |
| `idx_episodic_memories_embedding_hnsw` | `episodic_memories` | `embedding` |
| `idx_scenes_centroid_embedding_hnsw` | `scenes` | `centroid_embedding` |

## Stage 38 Persistence Record

Migration：`backend/alembic/versions/stage38_04_add_simulation_and_report_snapshots.py`

- `simulation_runs`：为 Simulation 结果提供 Redis miss 回查的 SQL 落盘
- `report_snapshots`：为 Report cache/snapshot 提供持久化审计面
- 两类 reader 均维持“Redis 优先，DB 回查”的读取顺序，并加 `user_id` 过滤

## Residual Risk Notes

- `backend pytest -q` 未全绿，当前不能写入 “Stage 38 ready for signoff” 顶部结论。
- Python proto stubs 当前依赖本地生成产物；当前 worktree 已生成并通过 `AQ`，但该产物仍是本地环境依赖，不在 Git 跟踪内。
- ErrorReplanBridge shadow 决策类型已更新为 `stage38_error_replan_bridge_shadow`；Journey smoke 与兼容 patch 点已同步回收。

## Stage 39 TODO

- 观察 Memory write lane 的 shadow 数据，决定是否切 live
- 汇总 ErrorReplanBridge shadow divergence 数据与新旧阈值触发率差
- 评估 Push scheduler 在 shadow 下的期望命中率与发送收益
- 继续处理 Idempotency（Workflow C 5 子项）
- 继续处理 AI loop 项：
  - `ScaffoldingFSM -> prompt` 直注
  - `cognitive_load -> Router`
  - `Galaxy -> 对话注入`
  - `Memory live` 就绪评估
