# V3 Event Name Registry（词表文档）

> 权威代码位置：`backend/app/core/event_registry.py`（本文件是它的文档投影；代码与契约测试 `backend/tests/contract/test_event_registry_contract.py` 才是真源，两边漂移会被测试抓住——词表 sha256 冻结）。
> 契约版本：`event.v1` ｜ 任务卡：D-01（stream DATA，locks: event-contract）

## 1. 事件域物理拓扑（复用，不新建）

| 存储/管线 | 角色 | live 现状（2026-09-19 dev DB 实测） |
|---|---|---|
| `event_outbox` | 外发权威（relay 管线；`event_sequence_counters` 保证 per-aggregate 单调序号） | 106 行（101 galaxy + 5 probe-origin run/task） |
| `event_store` | CQRS 追加存储（gateway SQLC 写入面） | **0 行**（无活跃写入方，见 REPORT 断点 B1） |
| `decision_records` | 决策账（preferences 审计） | 2870 行 |
| `tracking_events` | **client telemetry，非业务真值** | 1 行 |
| `intervention_requests` + `intervention_audit_logs` + `passive_signals` | 干预/路由决策记录 | 552 / 40 / 226 行 |
| `chat_messages` / `chat_sessions` | 交互真源 | 954 / 240 行 |
| `execution_audit_log` / `intervention_outcomes` / `behavioral_outcomes` / `memory_corrections` | 执行审计 / outcome 面 | 全部 0 行（见 REPORT 断点 B2/B3） |

V3 不新增事件表：B-06 裁决"面向 decision 的读侧投影，不是新事件存储"。本契约把 shared fields 放进 `event_outbox.metadata` jsonb（零 schema 变更，无 Alembic 加列）。

## 2. Shared fields（每个 V3 事件必须携带）

由 `build_event_metadata()` 产出，落在 `event_outbox.metadata`（也可用于 payload 内嵌）：

| 字段 | 规则 |
|---|---|
| `event_id` | 幂等键，**语义限于"同一行重投递"**：同输入（name/aggregate/seq/correlation）派生同 id，供未来消费者对 at-least-once 投递去重；**不覆盖"同一因果重执行"**（重执行烧新 sequence → 新 id，属重复因果，本键不检测）。已有全局唯一 id（如 outbox 行 uuid）可直传；否则用 `derive_event_id()` 派生 `evt_<sha256[:32]>`。**当前零消费者（R2 F1）**：唯一活跃消费方 Go publisher 按 Redis messageID 去重，且其 metadata 解码第一跳丢弃 event_id；gateway `processed_events` 表经 `uuid.Parse` 拒收 `evt_` 前缀——消费侧接线属后续卡，接入前需先解决 id 格式/列语义 |
| `user_id` | 隔离键，必填，canonical UUID 字符串 |
| `schema_version` | 固定 `event.v1`（本契约冻结） |
| `source` | 封闭 enum：`server_service` / `gateway` / `worker` / `client_telemetry` / `probe`。后两个**永远不是业务真值**（`is_business_truth_eligible()` 强制）。已知缺口（R2 F2，修复卡）：该门对 None/未知 source 值 fail-open（→True），ingest 侧亦不校验客户端上报的 source |
| `service` | 生产者模块名（保留既有字段，向后兼容 legacy `{"service": ...}` 行） |
| `occurred_at` | naive-UTC ISO（`normalize_occurred_at()` 强制转换 aware→naive UTC） |
| `correlation` | 可选互链（全部 canonical UUID）：`intervention_id` / `action_id` / `run_id` / `outcome_id` + 辅助因果键 `task_id` / `session_id` / `message_id` / `decision_id` / `plan_id` / `node_id`。EXECUTION/OUTCOME/STATE_UPDATE 事件**存在上游因果对象时至少带一条**，GJ trace 才能纯靠 ID 走通。**声明豁免类**（R2 #3，`CORRELATION_EXEMPT_EVENT_NAMES` 冻结）：`asset_created` / `asset_status_changed`——learning-asset 生命周期是聚合根事件，流程内不存在可链的上游 intervention/action/run/outcome/task 对象，asset 自身（aggregate_id）+ user_id 即全部 lineage |

读侧：`read_event_metadata()` 同时解析 v3 envelope 与 legacy `{"service":...}` 行（106 行存量全部兼容，`is_v3_envelope=False` 降级）；**防御契约（R2 #4）**：畸形输入（非 Mapping 对象/超限 64KiB 串/~1MiB mapping/深嵌套 JSON）一律拒绝并记 warning 日志、降级空视图，永不抛异常。

与 C-01 `decision_context.v1` 对齐：correlation ids 就是 `memory://` / `plan://` ref URI 指向的同一批记录 id；版本语义同为 `<contract>.v<n>`。

## 3. 事件名词表（封闭，33 个）

状态语义：**live**=仓内生产者存在；**reserved**=V3 预留（生产者未上线，禁止提前造假数据——同 C-01 document_chunk 原则）；**observed_unregistered**=live DB 里存在但仓内无生产者（probe 残留，已收编入册但不视为有主）。

### interaction
| event name | aggregate_type | producers | status |
|---|---|---|---|
| `chat.message.sent` | `ChatSession` | gateway/internal/cqrs/event/types.go (EventMessageSent) | live |
| `chat.message.received` | `ChatSession` | gateway/internal/cqrs/event/types.go (EventMessageReceived) | live |
| `chat.session.created` | `ChatSession` | gateway/internal/cqrs/event/types.go (EventSessionCreated) | live |
| `chat.session.ended` | `ChatSession` | gateway/internal/cqrs/event/types.go (EventSessionEnded) | live |
| `galaxy.study.recorded` | `KnowledgeNode` | gateway/internal/cqrs/event/types.go (EventStudyRecordAdded) | live |
| `user.preferences.updated` | `User` | gateway/internal/cqrs/event/types.go (EventPreferencesUpdated) | live |
| `task.created` | `Task` | gateway/internal/cqrs/event/types.go (EventTaskCreated) | live |

### decision
| event name | aggregate_type | producers | status |
|---|---|---|---|
| `decision.recorded` | `decision_record` | v3: decision_records read projection | reserved |
| `routing.decision_recorded` | `intervention_request` | app/services/routing_outcome_service.py (passive_signals, schema routing_outcome.v1) | reserved |

### execution
| event name | aggregate_type | producers | status |
|---|---|---|---|
| `intervention.requested` | `intervention_request` | v3: intervention pipeline | reserved |
| `intervention.delivered` | `intervention_request` | v3: intervention pipeline | reserved |
| `action.proposed` | `action` | v3: hybrid action engine | reserved |
| `action.accepted` | `action` | v3: hybrid action engine | reserved |
| `run.created` | `agent_run` | *(none in repo)* | observed_unregistered |
| `run.step_completed` | `agent_run` | *(none in repo)* | observed_unregistered |
| `run.awaiting_user` | `agent_run` | *(none in repo)* | observed_unregistered |
| `run.user_resumed` | `agent_run` | *(none in repo)* | observed_unregistered |
| `task.status_changed` | `task_command` | *(none in repo)* | observed_unregistered |
| `task.started` | `Task` | gateway/internal/cqrs/event/types.go (EventTaskStarted) | live |
| `asset_created` | `learning_asset` | app/services/learning_asset_service.py | live（correlation 豁免类） |
| `asset_status_changed` | `learning_asset` | app/services/learning_asset_service.py | live（correlation 豁免类） |

### outcome
| event name | aggregate_type | producers | status |
|---|---|---|---|
| `intervention.feedback_recorded` | `intervention_request` | v3: intervention feedback | reserved |
| `action.rejected` | `action` | v3: hybrid action engine | reserved |
| `task.completed` | `Task` | gateway/internal/cqrs/event/types.go (EventTaskCompleted) | live |
| `task.abandoned` | `Task` | gateway/internal/cqrs/event/types.go (EventTaskAbandoned) | live |
| `outcome.recorded` | `outcome` | v3: outcome evidence adapter | reserved |

### state_update
| event name | aggregate_type | producers | status |
|---|---|---|---|
| `galaxy.node.mastery_updated` | `galaxy_node_mastery` | app/services/galaxy_service.py::_write_mastery_outbox_event<br>app/services/galaxy/stats_service.py::_write_spark_outbox_event | live |
| `galaxy.node.created` | `KnowledgeNode` | gateway/internal/cqrs/event/types.go (EventNodeCreated) | live |
| `galaxy.node.unlocked` | `KnowledgeNode` | gateway/internal/cqrs/event/types.go (EventNodeUnlocked) | live |
| `galaxy.mastery.updated` | `KnowledgeNode` | gateway/internal/cqrs/event/types.go (EventMasteryUpdated) | live |
| `user_state.updated` | `user_state` | v3: state_aggregator projection | reserved |
| `user.created` | `User` | gateway/internal/cqrs/event/types.go (EventUserCreated) | live |
| `user.updated` | `User` | gateway/internal/cqrs/event/types.go (EventUserUpdated) | live |

注：gateway Go 侧还有 `community.post.*` / `plan.*` / `push.*` / `user.preferences.inferred` 等常量（types.go 封闭集）——它们属于 gateway 自有 CQRS 域且 Python 侧无写入方，本 Python 权威词表暂不重复收编；跨层单一真源仍是 Go 常量 + 本模块各自的封闭集，重合名（如 `task.*`、`galaxy.*`、`chat.*`、`user.*`）已两边一致。

## 4. 变更流程

1. 在 `event_registry.py::EVENT_REGISTRY` 加/改/删条目（附 producers 与 status 证据）；
2. `test_event_name_vocabulary_is_frozen` 会因 sha256 不匹配而红——**故意更新** `_FROZEN_VOCABULARY_SHA256` 字面量（契约变更必须显式）；新增/移除 correlation 豁免同理（`test_correlation_exempt_names_are_frozen` 精确集断言，须附理由注释）；
3. 新写入方一律走 `require_registered_event()` / `build_event_metadata()`，禁止自由字符串事件名；
4. 事件名只增不改义；改名=新名+旧名 deprecated（下游 cursor 兼容）。
