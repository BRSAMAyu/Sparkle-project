# Sparkle Aurora Stage 33 Handoff

## 已完成

- Social / SRL / Working Memory 三源都不再是“有数据无消费”
- 新 Journey Event 已补齐：
  - `user.registered`
  - `plan.created`
- Rule AS / Rule Z social guard 已入 manifest

## Stage 34 接手项

1. 事件已落地，但 subscriber 仍未接线。
2. `error_replan_bridge.py` 六道门未调整。
3. orphan / dormant 服务治理未开始。
4. normalize fallback bug (`achievement_summary` / `calendar_context`) 仍待 Stage 34 修复。

## Stage 35 / 36 仍保留

- Metacognition -> Router：Stage 35
- Mobile UserState parity：Stage 35
- Calendar 裸管道 kill switch：Stage 36
- 全量 guard 入 manifest / kill switch 三态统一 / drill 文档：Stage 36

## 新增开关默认值

| 开关 | 默认值 |
| --- | --- |
| `AURORA_STAGE33_MODE` | `shadow` |
| `AURORA_STAGE33_SOCIAL_MODE` | `shadow` |
| `AURORA_STAGE33_SRL_MODE` | `shadow` |
| `AURORA_STAGE33_WM_PROMPT_MODE` | `shadow` |
| `AURORA_STAGE33_EVENTS_MODE` | `shadow` |
