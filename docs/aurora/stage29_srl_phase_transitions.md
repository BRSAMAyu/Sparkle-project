# Aurora Stage 29 SRL Phase Transition Matrix

版本：v1.0  
日期：2026-04-21  
对应实现：`backend/app/services/srl_phase_types.py`

## 1. Frozen Enum

`SRLPhase` 固定为四值：

- `FORETHOUGHT`
- `PERFORMANCE`
- `SELF_REFLECTION`
- `UNKNOWN`

## 2. Transition Design Notes

本 Stage 锁定的实现语义如下：

- `task.started` 是进入执行态的唯一强信号，`FORETHOUGHT -> PERFORMANCE`
- `plan.created` 代表规划语义，而不是执行开始
  - `FORETHOUGHT -> FORETHOUGHT`：持续规划 / 重规划 self-loop
  - `PERFORMANCE -> FORETHOUGHT`：执行中断后回到重规划
  - `SELF_REFLECTION -> FORETHOUGHT`：复盘后进入下一轮规划
- `reflection.completed` 在 `PERFORMANCE` 中允许直接落到 `SELF_REFLECTION`
- `SELF_REFLECTION -> PERFORMANCE` 永久非法，必须经 `FORETHOUGHT`
- 长时间无活动 `>24h` 统一退化到 `UNKNOWN`

## 3. Frozen Matrix

### 3.1 Forethought

| Trigger | To | Allowed | 说明 |
| --- | --- | --- | --- |
| `task.started` | `PERFORMANCE` | Yes | 用户开始执行任务 |
| `plan.created` | `FORETHOUGHT` | Yes | 继续规划 / 重规划 self-loop |
| `task.feedback_submitted` | `SELF_REFLECTION` | No | 禁止跳过执行直接反思 |
| `task.completed` | `SELF_REFLECTION` | No | 无执行态完成非法 |
| `task.abandoned` | `SELF_REFLECTION` | No | 无执行态放弃非法 |
| `reflection.completed` | `SELF_REFLECTION` | No | 未执行前不能完成反思 |
| `plan_stall_detected` | `SELF_REFLECTION` | No | stall 需已有执行态 |
| `next_plan_draft` | `FORETHOUGHT` | Yes | 新草案仍属规划 |
| `user_start_new` | `FORETHOUGHT` | Yes | 新尝试从规划开始 |
| `inactive_timeout` | `UNKNOWN` | Yes | 超 24h 失活 |

### 3.2 Performance

| Trigger | To | Allowed | 说明 |
| --- | --- | --- | --- |
| `task.started` | `PERFORMANCE` | Yes | 连续执行多任务 self-loop |
| `plan.created` | `FORETHOUGHT` | Yes | 执行中重规划 |
| `task.feedback_submitted` | `SELF_REFLECTION` | Yes | 收到反馈进入反思 |
| `task.completed` | `SELF_REFLECTION` | Yes | 完成后进入反思 |
| `task.abandoned` | `SELF_REFLECTION` | Yes | 放弃后进入反思 |
| `reflection.completed` | `SELF_REFLECTION` | Yes | 反思产物落地，切入反思态 |
| `plan_stall_detected` | `SELF_REFLECTION` | Yes | 执行停滞触发复盘 |
| `next_plan_draft` | `PERFORMANCE` | No | 必须经 `plan.created` 回规划 |
| `user_start_new` | `PERFORMANCE` | No | 禁止无规划直接重启执行 |
| `inactive_timeout` | `UNKNOWN` | Yes | 超 24h 失活 |

### 3.3 Self-Reflection

| Trigger | To | Allowed | 说明 |
| --- | --- | --- | --- |
| `task.started` | `PERFORMANCE` | No | 必须先回 `FORETHOUGHT` |
| `plan.created` | `FORETHOUGHT` | Yes | 复盘后新规划 |
| `task.feedback_submitted` | `SELF_REFLECTION` | Yes | 继续深化反思 |
| `task.completed` | `SELF_REFLECTION` | Yes | 迟到完成信号仍维持反思 |
| `task.abandoned` | `SELF_REFLECTION` | Yes | 放弃信号维持反思 |
| `reflection.completed` | `SELF_REFLECTION` | Yes | bounded self-loop |
| `plan_stall_detected` | `SELF_REFLECTION` | Yes | stall 证据维持反思 |
| `next_plan_draft` | `FORETHOUGHT` | Yes | 明确下一步草案回规划 |
| `user_start_new` | `FORETHOUGHT` | Yes | 显式重启回规划 |
| `inactive_timeout` | `UNKNOWN` | Yes | 超 24h 失活 |

### 3.4 Unknown

| Trigger | To | Allowed | 说明 |
| --- | --- | --- | --- |
| `task.started` | `PERFORMANCE` | Yes | 可直接推断执行态 |
| `plan.created` | `FORETHOUGHT` | Yes | 可直接推断规划态 |
| `task.feedback_submitted` | `SELF_REFLECTION` | Yes | 无先验时按反思处理 |
| `task.completed` | `SELF_REFLECTION` | Yes | 无先验时按反思处理 |
| `task.abandoned` | `SELF_REFLECTION` | Yes | 无先验时按反思处理 |
| `reflection.completed` | `SELF_REFLECTION` | Yes | 可直接推断反思态 |
| `plan_stall_detected` | `SELF_REFLECTION` | Yes | 无先验时按反思处理 |
| `next_plan_draft` | `FORETHOUGHT` | Yes | 新规划恢复规划态 |
| `user_start_new` | `FORETHOUGHT` | Yes | 新开始恢复规划态 |
| `inactive_timeout` | `UNKNOWN` | Yes | 空转允许但记录 |

## 4. Cold Start Rule

冷启动只读 Stage 28 `traits_prior`，不调用 LLM：

- `conscientiousness.value >= 0.6` 且 `confidence >= 0.1` → 初值 `FORETHOUGHT`
- 其他情况 → 初值 `UNKNOWN`
- traits 影响置信度上限仍受 Rule AM 约束，当前实现冷启动 phase confidence 封顶 `0.3`

## 5. Determinism and Inactivity

- 同一事件序列多次重放，Tracker 结果保持确定性
- `phase_started_at` 只在 phase 真正变化时刷新
- self-loop 仅更新时间与 evidence，不重置 phase 起点
- inactivity 通过读取时检查 `updated_at` 与 `24h` 阈值实现

## 6. Evidence IDs

每次转移最多保留最近 `12` 条 evidence：

- 直接事件 evidence：`evidence_id`
- plan 补充证据：`plan:<plan_id>`
- inactivity 证据：`inactive_timeout`
- force reset 证据：`force_reset:<reason>`
