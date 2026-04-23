# Pending Fix Queue

<!-- Format: - [ISSUE-ID] Slice-N: <brief title> (P0/P1/P2/P3) — <timestamp> -->

<!-- Auditor appends here. Fixer picks from top. -->

- ISSUE-20260424-011 | 2-Chat-WebSocket: Flutter 重连耗尽 pendingMessages 静默丢弃 (P1) — 2026-04-24T17:43
- ISSUE-20260424-009 | 2-Chat-WebSocket: saveMessage context.Background() trace 断链 (P2) — 2026-04-24T17:43
- ISSUE-20260424-010 | 2-Chat-WebSocket: ConnectionRegistry Get/GetWriter 多连接不一致 (P2) — 2026-04-24T17:43
- ISSUE-20260424-012 | 2-Chat-WebSocket: ConnectionRegistry goroutine 无超时保护 (P2) — 2026-04-24T17:43
- ISSUE-20260424-002 | 1-Auth: guest_login SELECT-INSERT 竞态条件，IntegrityError 未捕获 (P1) — 2026-04-24T13:39
- ISSUE-20260424-003 | 1-Auth: guest_login 限流 100/15min 无生产区分，可被滥用 (P1) — 2026-04-24T13:39
- ISSUE-20260424-004 | 1-Auth: Go AppleLogin UpdateUserLastLogin 错误静默丢弃 (P1) — 2026-04-24T13:39
- ISSUE-20260424-005 | 1-Auth: blacklist_token 返回类型注解 -> None 与实际 bool 不一致 (P2) — 2026-04-24T13:39
- ISSUE-20260424-006 | 1-Auth: Go fail-closed vs Python fail-open，Redis 故障时安全策略不一致 (P2) — 2026-04-24T13:39
