# Aurora Stage 29 SRL Event Schema

版本：v1.0  
日期：2026-04-21  
对应实现：`backend/app/core/event_bus.py`、`backend/app/event_publishers/srl_events.py`

## 1. Design Goal

Stage 29 通过 EventBus 完成解耦：

- 发布侧：业务动作只发布 SRL 事件
- 消费侧：`SRLPhaseTrackerService` 独立订阅并更新状态
- 读取侧：Aggregator 只读 `srl_phase_states`
- Scaffolding 只消费 Aggregator summary

永久边界：

- orchestrator 不得 import Tracker
- orchestrator 不得硬编码 SRL 阶段分支
- orchestrator 与 Tracker 之间无 direct call

## 2. Raw Source Events

以下原始事件在 `backend/app/core/event_bus.py` 注册：

| Event | Class | 发布位置 | 说明 |
| --- | --- | --- | --- |
| `task.started` | `TaskStartedEvent` | `backend/app/services/task_service.py` | 任务开始执行 |
| `plan.created` | `PlanCreatedEvent` | `backend/app/orchestration/discovery_manager.py`、`backend/app/orchestration/plan_review_service.py` | 新计划 / 重规划完成 |
| `task.feedback_submitted` | 既有事件 | `backend/app/services/task_feedback_service.py` | 既有反馈发布点，未重写 |
| `task.completed` | 既有事件 | `backend/app/services/task_service.py` | 执行完成 |
| `task.abandoned` | 既有事件 | `backend/app/services/task_service.py` | 执行放弃 |
| `reflection.completed` | `ReflectionCompletedEvent` | `backend/app/services/task_reflection_service.py` | 结构化反思提交完成 |

## 3. Bridge Event

唯一供 Tracker 消费的桥接事件：

### 3.1 Event Type

`srl.phase.transition`

### 3.2 Schema

| Field | Type | Required | 说明 |
| --- | --- | --- | --- |
| `event_type` | `str` | Yes | 固定为 `srl.phase.transition` |
| `user_id` | `str` | Yes | 强制非空，跨用户查询红线 |
| `trigger_event_type` | `str` | Yes | 上游原始事件类型 |
| `evidence_id` | `str` | Yes | 本次转移证据 ID |
| `metadata` | `dict` | No | 可携带 `plan_id` / `task_id` 等上下文 |
| `published_at` | ISO8601 `str` | Yes | lag 计算基准 |
| `timestamp` | ISO8601 `str` | Yes | EventBus 落流时间 |

### 3.3 Publisher Contract

发布入口统一为：

- `backend/app/event_publishers/srl_events.py`
- `publish_srl_event(user_id, trigger_event_type, evidence_id, metadata=None)`

Publisher 会先检查 kill-switch：

- `AURORA_SRL_MODE=off` → 不发布
- `AURORA_SRL_BRIDGE_MODE=off` → 不发布
- `shadow` → 仍发布，但下游按 shadow 读取

## 4. Consumer Contract

Tracker consumer group 固定：

- stream：`sparkle_events`
- group：`srl_phase_tracker`

防循环规则：

```python
if event_type.startswith("srl.") and event_type != "srl.phase.transition":
    return None
```

含义：

- Tracker 永不自消费 `srl.*` 的其他衍生事件
- 只处理桥接事件 `srl.phase.transition`

## 5. Retry / DLQ / Lag

- EventBus 消费失败最多 `3` 次
- 超限进入 DLQ
- 指标：
  - `srl.event.published`
  - `srl.event.consumed`
  - `srl.event.lag.p95`
  - `srl.dlq.size`

自动降级规则：

- `lag p95 > 5s` 连续 3 分钟 → `bridge=shadow` 且 `scaffolding_consume=shadow`
- `misjudgment_rate > 20%` 连续 3 日 → 同上

## 6. Non-Looping Call Chain

冻结调用链如下：

`business action -> srl_events.py -> EventBus -> SRLPhaseTrackerService -> PostgreSQL/Redis -> StateAggregatorService(read) -> ScaffoldingFSM(read-only support calculation)`

链条终止于 `ScaffoldingFSM.resolve_support_level()` 的纯计算，无反向调用 orchestrator。
