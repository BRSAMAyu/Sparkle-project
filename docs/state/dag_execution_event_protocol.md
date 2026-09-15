# DAG Execution Event Protocol

This document defines how backend streams DAG execution progress to clients via `ChatResponse.metadata`.

## Transport

- Channel: gRPC `ChatResponse.metadata`
- Key: `dag_execution_event`
- Value type:
  - Preferred: JSON string (backend current behavior)
  - Compatible: JSON object (some gateways or test mocks)

## Event Schema

Base field:

- `event` (string, required)

Common optional fields:

- `layer_index` (int)
- `layer_number` (int, 1-based)
- `total_layers` (int)
- `step_id` (string)
- `tool_name` (string)
- `success` (bool)
- `duration_ms` (int)
- `aborted` (bool)
- `reason` (string)
- `completed_steps` (int)
- `step_ids` (string[])
- `tool_names` (string[])
- `plan_id` (string)
- `layers_completed` (int)
- `steps_total` (int)
- `abort_reason` (string)

## Event Types

- `layer_start`
  - Signals start of one DAG layer.
- `step_completed`
  - Signals completion of one step (success/failure).
- `layer_end`
  - Signals completion of current layer.
- `execution_aborted`
  - Signals required-step failure caused abort.
- `execution_end`
  - Signals terminal state of full DAG execution.

## Client State Machine (recommended)

- Idle -> Running: on `layer_start`
- Running -> Running: on `step_completed` / `layer_end`
- Running -> Aborted: on `execution_aborted`
- Running/Aborted -> Done: on `execution_end`
- Done/Aborted -> Idle: when stream `done` or next user turn starts

## UI Mapping (current mobile)

- Use `AiStatusIndicator`:
  - Status: `EXECUTING_TOOL`
  - Details:
    - `layer_start`: `DAG 第X/Y层，N个步骤并行执行`
    - `step_completed`: `${tool_name} 执行完成 (${duration_ms}ms)` or `${tool_name} 执行失败`
    - `layer_end`: `第X层执行完成` / `第X层已中断`
    - `execution_aborted`: `reason`
    - `execution_end`: `DAG 执行完成` or `DAG 执行结束（中断）`

## Compatibility Notes

- If a message has both `status_update` and `dag_execution_event`:
  - Keep status semantics unchanged.
  - Prefer DAG-derived details text for display.
- If `dag_execution_event` parse fails:
  - Ignore silently and continue normal chat streaming.
