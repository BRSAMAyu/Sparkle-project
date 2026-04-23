# 覆盖矩阵 — 19 切片轮转表

| # | 切片名称 | 关键路径 | last_audited | round | issues_found |
|---|---------|---------|-------------|-------|-------------|
| 1 | Auth 链路 | mobile auth → gateway middleware → api | 2026-04-24T13:39 | 0 | 6 |
| 2 | Chat WebSocket 链路 | ws_proxy → orchestrator → llm_service | 2026-04-24T17:43 | 0 | 6 |
| 3 | Plan Review 链路 | plan_review_service → Flutter plan_review_card | null | 0 | 0 |
| 4 | Dual-Core Router | dual_core_router → ux_envelope → prompt 注入 | null | 0 | 0 |
| 5 | Execution / OpenClaw | execution_service → adapters/openclaw → Flutter openclaw | null | 0 | 0 |
| 6 | Galaxy 知识图谱 | galaxy_service → AGE schema → Flutter galaxy | null | 0 | 0 |
| 7 | Community 链路 | community_service → community_signal_bridge → Flutter community | null | 0 | 0 |
| 8 | Error Book | error_book.proto → Flutter error_book → knowledge penalty | null | 0 | 0 |
| 9 | Focus / Breathing / 计时 | focus_service → breathing → Flutter focus | null | 0 | 0 |
| 10 | Achievement / Photon | achievement_engine → event_consumer → Flutter achievement | null | 0 | 0 |
| 11 | Calendar | calendar_weather → notification scheduling → Flutter calendar | null | 0 | 0 |
| 12 | Memory Service | memory_service 读写路径 + Stage16 Memory Write Lane | null | 0 | 0 |
| 13 | Cognitive Service | cognitive_service → cognitive_patterns → capsule | null | 0 | 0 |
| 14 | Seed Library / Tools / Translation | seed_library → tools → translation → Flutter | null | 0 | 0 |
| 15 | Event Bus | event_bus → Redis Streams → 3 bridges + DLQ | null | 0 | 0 |
| 16 | Proto 契约 | 6 proto 与 Go/Python/Dart 生成代码一致性 | null | 0 | 0 |
| 17 | DB 迁移一致性 | Alembic migrations × sqlc schema.sql | null | 0 | 0 |
| 18 | 监控 & SLO | 11 条告警规则 × runbook × Grafana | null | 0 | 0 |
| 19 | 安全基线 | JWT / rate-limit / CORS / 密钥扫描 / 时序攻击 | null | 0 | 0 |
