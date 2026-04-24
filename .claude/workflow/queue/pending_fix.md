# Pending Fix Queue

<!-- Format: - [ISSUE-ID] Slice-N: <brief title> (P0/P1/P2/P3) — <timestamp> -->

<!-- Auditor appends here. Fixer picks from top. -->

- ISSUE-20260424-009 | 2-Chat-WebSocket: saveMessage context.Background() trace 断链 (P2) — 2026-04-24T17:43
- ISSUE-20260424-010 | 2-Chat-WebSocket: ConnectionRegistry Get/GetWriter 多连接不一致 (P2) — 2026-04-24T17:43
- ISSUE-20260424-012 | 2-Chat-WebSocket: ConnectionRegistry goroutine 无超时保护 (P2) — 2026-04-24T17:43
- ISSUE-20260424-005 | 1-Auth: blacklist_token 返回类型注解 -> None 与实际 bool 不一致 (P2) — 2026-04-24T13:39
- ISSUE-20260424-006 | 1-Auth: Go fail-closed vs Python fail-open，Redis 故障时安全策略不一致 (P2) — 2026-04-24T13:39
- ISSUE-20260424-090 | 15-Theater-Sim: Simulation SSE streaming 泄露内部异常详情到客户端 (P1) — 2026-04-24T13:30
- ISSUE-20260424-091 | 15-Theater-Sim: SimulationEngine._local_checkpoints 类级 dict 无限增长 (P1) — 2026-04-24T13:30
- ISSUE-20260424-092 | 15-Theater-Sim: prediction_theater_service.py import logging 绕过 loguru (P2) — 2026-04-24T13:30
- ISSUE-20260424-093 | 15-Theater-Sim: adopt_prediction bare except:pass 静默吞错误 (P2) — 2026-04-24T13:30
- ISSUE-20260424-094 | 15-Theater-Sim: _find_related_concept_anchors ilike 通配符未转义 (P2) — 2026-04-24T13:30
- ISSUE-20260424-095 | 15-Theater-Sim: PredictionAccuracyTracker 过期 prediction ID 积累 (P2) — 2026-04-24T13:30
- ISSUE-20260424-096 | 16-Profile: link_social/unlink_social db.add无commit绑定不持久化 (P1) — 2026-04-25T03:15
- ISSUE-20260424-097 | 16-Leaderboard: 全量加载用户Python排序OOM风险 (P1) — 2026-04-25T03:15
- ISSUE-20260424-098 | 16-Leaderboard: refresh-cache无admin校验空操作stub (P2) — 2026-04-25T03:15
- ISSUE-20260424-099 | 16-Leaderboard: get_top_three泄露str(e)内部异常 (P2) — 2026-04-25T03:15
- ISSUE-20260424-100 | 16-Shop: get_available_items N+1 ownership check (P2) — 2026-04-25T03:15
- ISSUE-20260424-101 | 16-Profile: update_schedule_preferences无类型校验 (P2) — 2026-04-25T03:15
