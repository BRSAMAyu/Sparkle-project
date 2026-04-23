# 覆盖矩阵 · 21 切片轮转

> Auditor 每个 loop 按 `state.json.cursor` 推进一个切片。切片冷却期 **4 小时**：若 `last_audited` 距今 < 4h 则 cursor+1 再取，直到找到冷却已过的切片。每完成 21 个切片 round+=1。
>
> **关键纪律**：每切片必须本会话亲自 Read / Grep 核心文件，不得仅依赖 Agent 子会话摘要。核心文件列已列出"必须亲自看"的 anchor。

## 7 维审查清单（每切片每维都要给结论）

1. **入口可达**：用户从 Flutter 入口发起，是否真能走通到数据落库/落 Redis？
2. **错误分支**：失败、超时、限流、鉴权失败分支是否收敛？幂等是否保持？
3. **日志与埋点**：request_id 是否贯穿？关键节点有无 log？指标是否上报？
4. **鉴权与限流**：中间件是否生效？内部端点是否受白名单保护？
5. **并发与幂等**：重复请求、断连重连、消息重放是否安全？
6. **契约一致性**：Proto / Schema / 前端模型三端是否同步？
7. **与 Product Consensus 的一致性**：功能行为是否符合 `docs/product/` 共识与 CLAUDE.md 对应章节？

---

## 切片清单

| # | 切片 | 必须亲自看的 anchor（本会话 Read） | 额外参考（可 Grep） |
|---|------|------------------------------------|---------------------|
| 01 | auth_session | `mobile/lib/features/auth/`, `backend/gateway/internal/middleware/auth.go`, `backend/gateway/internal/middleware/ws_auth.go`, `backend/app/services/auth_session_service.py` | JWT blacklist, user_revoked_before |
| 02 | chat_websocket | `backend/gateway/internal/handler/websocket_proxy.go`, `backend/gateway/internal/handler/chat_orchestrator.go`, `backend/app/services/agent_grpc_service.py`, `backend/app/orchestration/orchestrator.py`, `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` | signal hub, quota reservation |
| 03 | plan_review | `backend/app/orchestration/plan_review_service.py`, `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart`, `proto/agent_service.proto` (SubmitPlanReview) | metadata delta, requires_review |
| 04 | dual_core_router | `backend/app/orchestration/dual_core_router.py`, `backend/app/orchestration/ux_envelope.py`, `backend/app/orchestration/prompts.py` | routing_decision_log |
| 05 | execution_openclaw | `backend/app/adapters/openclaw/client.py`, `backend/app/services/execution/`, `backend/app/api/v1/executions.py`, `mobile/lib/features/openclaw/` | intent_translator, result_parser |
| 06 | galaxy | `backend/app/services/galaxy_service.py`, `proto/galaxy_service.proto`, `mobile/lib/features/galaxy/`, AGE schema refs | knowledge_prerequisite_baseline |
| 07 | community_accountability | `backend/app/services/community_service.py`, `backend/app/services/accountability_mvp_service.py`, `backend/app/services/community_signal_bridge.py`, `mobile/lib/features/community/` | group events, signal bridge |
| 08 | error_book | `proto/error_book.proto`, `backend/gateway/internal/error_book/`, `mobile/lib/features/error_book/`, ErrorReplanBridge | TRIGGERING_ERROR_TYPES |
| 09 | focus_breathing | `mobile/lib/features/focus/`, focus acceptance script, wall-clock timer models | Phase1 fixes, offline queue |
| 10 | achievement_photon_visual | `backend/app/services/achievement_engine.py`, `backend/app/services/achievement_event_consumer.py`, `mobile/lib/features/achievement/`, `mobile/lib/features/photon/`, `mobile/lib/features/visual_elements/` | 19 event types, contract |
| 11 | calendar_notification | `mobile/lib/features/calendar/`, `backend/app/services/` (calendar/notification), `mobile/lib/features/notification_center/` | notification scheduling |
| 12 | memory_write_lane | `backend/app/services/memory_service.py`, `backend/app/orchestration/orchestrator.py:1700-` (memory read), Stage16 memory write lane refs, Rule Y governance | inferred extraction, kill-switch |
| 13 | cognitive_capsule | `backend/app/services/cognitive_service.py`, `mobile/lib/features/cognitive/`, capsule favorites, behavior_signal_collector | PatternType enum sync |
| 14 | seed_tools_translation | `mobile/lib/features/seed_library/`, `mobile/lib/features/tools/`, `mobile/lib/features/translation/`, seed_library chat integration | quality score, filtering |
| 15 | insights_report_theater_simulation | `mobile/lib/features/insights/`, `mobile/lib/features/report/`, `mobile/lib/features/theater/`, `mobile/lib/features/simulation/`, `backend/app/services/theater/`, `backend/app/services/simulation/` | confidence intervals, what-if |
| 16 | home_profile_shop_settings_leaderboard | `mobile/lib/features/home/`, `mobile/lib/features/user/`, `mobile/lib/features/shop/`, `mobile/lib/features/settings/`, `mobile/lib/features/leaderboard/` | profile audit |
| 17 | event_bus | `backend/app/core/event_bus.py`, `backend/app/services/community_signal_bridge.py`, `backend/app/services/galaxy_event_consumer.py`, `backend/app/services/achievement_event_consumer.py`, DLQ/retry | Redis Streams lag |
| 18 | proto_contract_sync | `proto/*.proto` (10 files), `backend/gateway/gen/`, `backend/app/gen/`, `mobile/lib/gen/`, buf.yaml | breaking changes vs main |
| 19 | db_schema_migrations | `backend/gateway/internal/db/schema.sql`, `backend/alembic/versions/` (80 files), sqlc queries | Go↔Py schema 同步 |
| 20 | monitoring_slo_security | `monitoring/runbooks/incident_response.md`, prometheus rules, `backend/gateway/internal/middleware/` (security/cors/rate_limit), gitleaks/trivy config | 11 SLO 告警 |
| 21 | aurora_governance | `backend/app/services/aurora_stage*_kill_switch_service.py`, `backend/app/services/bayesian_routing_wire_service.py`, Stage16 Memory Write Lane, Stage20 Skill Store, `routing_decision_log` | Rule Y/Z/AA governance |

---

## 轮转状态（Auditor 写入，Verifier 只读）

<!-- 格式：| # | slice | last_audited | round | last_issues_count | notes | -->

| # | slice | last_audited | round | last_issues_count | notes |
|---|-------|--------------|-------|-------------------|-------|
| 01 | auth_session | 2026-04-24T19:10+08:00 | 0 | 6 | Go不查session_revoked; AppleLogin静默丢错误; guest限流100/15min |
| 02 | chat_websocket | 2026-04-24T19:40+08:00 | 0 | 8 | Protobuf绕过长度限制; GetWriter非确定性; saveMessage丢错误; goroutine无超时 |
| 03 | plan_review | 2026-04-24T20:15+08:00 | 0 | 6 | asyncio.create_task无错误处理; get-delete竞态; plan_id来源不一致; redis=null降级; feasibility硬编码; get_stored_plan stub |
| 04 | dual_core_router | 2026-04-24T20:35+08:00 | 0 | 6 | chat+direct shortcut绕过信号处理; intent_confidence=0静默覆盖为0.7; 截断不一致; local fallback无淘汰; 子串匹配误报; gentle消息缺4种变体 |
| 05 | execution_openclaw | null | 0 | - | - |
| 06 | galaxy | null | 0 | - | - |
| 07 | community_accountability | null | 0 | - | - |
| 08 | error_book | null | 0 | - | - |
| 09 | focus_breathing | null | 0 | - | - |
| 10 | achievement_photon_visual | null | 0 | - | - |
| 11 | calendar_notification | null | 0 | - | - |
| 12 | memory_write_lane | null | 0 | - | - |
| 13 | cognitive_capsule | null | 0 | - | - |
| 14 | seed_tools_translation | null | 0 | - | - |
| 15 | insights_report_theater_simulation | null | 0 | - | - |
| 16 | home_profile_shop_settings_leaderboard | null | 0 | - | - |
| 17 | event_bus | null | 0 | - | - |
| 18 | proto_contract_sync | null | 0 | - | - |
| 19 | db_schema_migrations | null | 0 | - | - |
| 20 | monitoring_slo_security | null | 0 | - | - |
| 21 | aurora_governance | null | 0 | - | - |
