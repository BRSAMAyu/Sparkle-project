# Auditor Session Log

> 每次 loop 追加一段。最老的条目超过 14 日后可由自己归档到 `ARCHIVE_<yyyymm>.md`。

<!--
格式：
## <iso-timestamp> round=<r> slice=<NN-name>
- directives_read: [DIRECTIVE-... | none]
- produced: <n> issues  (P0=a P1=b P2=c P3=d)
- deferred: <m>         (超出单 loop 上限留到下轮)
- anchors_personally_read: [path:line, ...]
- grep_queries: [...]
- deviations: <偏离正常节奏的说明>
- next_cursor: <cursor+1>
- commit: <sha-workflow-only>
-->

## 2026-04-24T19:00+08:00 round=0 slice=01-auth_session
- directives_read: none active (example advisory only)
- produced: 6 issues  (P0=0 P1=3 P2=3 P3=0)
- deferred: 0
- anchors_personally_read: [auth.go:1-423, ws_auth.go:1-172, auth_session_service.py:1-194, handler/auth.go:1-240, auth.py:1-80+127-160+405-476+567-658+798-883, users.py:119-124+395-470, auth_repository.dart:1-750]
- grep_queries: [session_revoked in gateway → 0 matches, GuestLogin in gateway → 0 matches, guest in app/api → auth.py:798, me/sessions in gateway → 0 matches, sessions|revoke in app/api → users.py:400+425+454]
- deviations: none
- next_cursor: 1 (slice 02-chat_websocket)
- commit: pending

