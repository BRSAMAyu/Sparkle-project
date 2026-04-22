# SRL SQAM

## ID1

- 事件入口通过 `trigger_event_type` + `evidence_id` 明确过渡来源。

## ST1

- `force_reset()` 置信度硬封顶到 `0.8`，避免手动重置伪装成高确定性状态。

## DP1

- `handle_transition_event()` 仅接受 `^[a-zA-Z_]+:[A-Za-z0-9\\-:.]+$` 或 UUID 证据 ID。

## SM1

- `force_reset()` 需要 `justification`，并写入 `routing_decision_log` 审计。
