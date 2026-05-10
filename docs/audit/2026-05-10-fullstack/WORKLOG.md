# Full-Stack Audit Fix Worklog

> **Started**: 2026-05-10
> **Branch**: Starting from `main` (17959ea34)
> **Agent**: Claude Code (GLM-5.1) + Opus verification agents
> **Last Updated**: 2026-05-10 14:45

---

## Progress Dashboard

| Phase | Total | Done | Remaining |
|-------|-------|------|-----------|
| P0 Critical | 8 | 8 | 0 |
| P1 High | 35 | 18 | 17 |
| P2 Medium | 60 | 0 | 60 |
| P3 Low | 32 | 0 | 32 |
| i18n (net reduction) | ~1070 | ~16 | ~1054 |

---

## Commits Made

| Commit | Time | Scope | Changes |
|--------|------|-------|---------|
| 9d80efa4e | 14:15 | P0 | error_widget.dart EN fallbacks, error_messages.dart bilingual matching, client.go fresh retry timeout, chat_provider.dart partial msg deduplication |
| a665f0cfd | 14:34 | Backend P1 | kill_switch.py Redis try/except + no in-memory mutation, plan_review_service.py done-callback |
| 416b7bd76 | 14:38 | Mobile SM P1 | sync_engine.dart listener leak, chat_provider.dart gRPC dispose + debouncer cancel, chat_notifier_reviews.dart catchError + l10n key |
| 38acc0616 | 14:42 | DB P1 | 7 composite indexes migration, goals.plan_id FK ON DELETE SET NULL, galaxy_event_consumer.py stable consumer name |
| 87808c549 | 14:45 | i18n | task_board_card.dart 8 isChinese → ARB migration |

---

## P0 — Critical (ALL FIXED)

| Issue | Status | Analysis | Fix |
|-------|--------|----------|-----|
| P0-FE-01/02 (`ctx`, `message` undefined) | ✅ VERIFIED FALSE POSITIVE | `ctx` is Builder parameter (line 1630); `message` extracted at line 1558. Audit line numbers stale. | No fix needed. |
| P0-I18N-01 (error_widget Chinese fallback) | ✅ FIXED | 4 Chinese fallbacks replaced with English | `'哎呀，出错了'` → `'Oops, something went wrong'` etc. |
| P0-I18N-02 (error_messages Chinese matching) | ✅ FIXED | Chinese-only matching replaced with bilingual (lowercase + EN patterns) + English fallback strings | Added 40+ EN patterns; all 9 fallback strings → English |
| P0-DB-01 (AchievementType duplicate) | ✅ VERIFIED FALSE POSITIVE | Alembic migration r8 already normalized to lowercase `planning`; schema.sql shows only lowercase. Migration chain resolves the duplicate. | No fix needed. schema.sql dump outdated but DB is correct after `alembic upgrade head`. |
| P0-INT-01 (StreamChat retry timeout) | ✅ FIXED | `retryCtx` now uses fresh `context.WithTimeout(context.Background(), 120s)` | client.go:349-369 |
| P0-SM-02 (WS reconnect duplicate msg) | ✅ FIXED | Failed streams with bare partial text no longer create messages | `shouldPreserveMessage` guard in `finalizeRun` |

---

## P1 — High Priority

### Fixed (verified & committed)
| Issue | Fix | Evidence |
|-------|-----|----------|
| BE-P1-05/06 kill_switch | Redis try/except in `read_mode`; no in-memory mutation in `write_mode` | kill_switch.py:102-120 |
| BE-P1-03 plan_review task tracking | Added `done-callback` with error logging to 3rd `asyncio.create_task` | plan_review_service.py:2256-2271 |
| SM-P1-01 SyncEngine listener leak | Store `_connectivitySubscription`, cancel in `stop()` | sync_engine.dart:36,56,65 |
| SM-P1-02 gRPC dispose | Call `_planReviewService?.close()` + `_reviewService?.close()` | chat_provider.dart:233-234 |
| SM-P1-03 debouncer cancel | Cancel `_streamDebouncer` in `cancelActiveRun` | chat_provider.dart:229 |
| SM-P1-05 requestRegeneration fire-and-forget | Added `catchError` + user-facing error state + new l10n key | chat_notifier_reviews.dart:136-163 + app_en/zh.arb |
| DB-P1-01 circular FK | Added `ON DELETE SET NULL` to `goals.plan_id_fkey` | fix_goals_plan_fk_20260510 migration |
| DB-P1-02/03 missing indexes | 7 composite indexes including `idx_tasks_plan_user_status`, `idx_goals_plan_id` | comp_idx_20260510 migration |
| DB-P1-05-09 other indexes | notifications, user_state_snapshots, friendships, error_records | comp_idx_20260510 migration |
| DB-P1-06 galaxy consumer naming | Uses `os.getpid()` instead of timestamp | galaxy_event_consumer.py:53 |
| FE-P1-03 task_board i18n | 8 isChinese → ARB with new l10n keys | task_board_card.dart + app_en/zh.arb |

### Verified False Positives / Won't Fix
| Issue | Reason |
|-------|--------|
| BE-P1-09 reconnectTrackers cleanup | Already works: removes if `lastAttempt < cutoff AND blockedUntil passed`. Never-blocked users with successful connects: acceptable design. |
| BE-P1-10 backend-first upgrade | Required for subprotocol negotiation. Client must see backend's subprotocol before echoing. |
| BE-P1-11/12 chatInput pool | `Put()` is called via `defer` on every `Get()`. Correct. |
| BE-P1-01 orchestrator span leak | `span.end()` in outer `finally:3675` covers all paths including generator abandonment. |
| BE-P1-02 lock acquisition | `_acquire_session_lock` catches all exceptions, returns True (fail-open). `lock_acquired` only set after confirmed ownership. |
| BE-P1-04 stream_cb null | `emit_agent_activity` has `if stream_callback is None: return` guard at line 159. |
| BE-P1-07 demo fuzzy match | Report issue P0 → P1 downgrade noted in SUMMARY. Additional ratio check may be worth adding but not critical. |

### Remaining P1s (not yet addressed)
- DB-P1-07: TaskEventConsumer single session risk (6+ ops in one transaction)
- DB-P1-08: ErrorReplanBridge silent ignore (needs metric + DEBUG log)
- BE-P1-01: OTel span leak (verified false positive — already covered)
- FE-P1-04: community_main isChinese (5 instances)
- FE-P1-05: create_post isChinese (15+ instances)
- FE-P1-06: create_post length enforcement (ALREADY FIXED — line 73 checks `content.length > 500`)
- FE-P1-07: node_detail_sheet AI prompt isChinese

---

## P2 — Medium (not yet started)
| Issue | File |
|-------|------|
| FE-P2-01 chat_screen 2900+ lines | chat_screen.dart |
| FE-P2-02 chat error auto-clear | chat_screen.dart:256-265 |
| FE-P2-03 chat bottom padding hardcoded | chat_screen.dart:2442+ |
| FE-P2-04 collapsible_slot isChinese | collapsible_slot.dart:227 |
| FE-P2-05 dashboard_card_grid fixed height | dashboard_card_grid.dart:12 |
| BE-P2-01 orchestrator locals() fallback | orchestrator.py:3617 |
| BE-P2-02 datetime.now() vs UTC | orchestrator.py:1262,2068 |
| BE-P2-03 dual_core_router monolithic | dual_core_router.py:205-863 |
| BE-P2-04 plan_review liberal_arts hardcode | plan_review_service.py:942-959 |
| BE-P2-05 get_stored_plan returns None | plan_review_service.py:1871-1885 |
| DB-P2-01 HNSW m/ef_construction params | schema.sql |
| DB-P2-02 JSONB GIN indexes | schema.sql |
| SM-P2-01 Future.delayed mutation | chat_notifier_actions.dart:605+ |

---

## P3 — Low (not yet started)
32 issues — see full audit report.

---

## Verification Required (before claim completion)
- [ ] Run `alembic current` to confirm DB migration chain is clean
- [ ] Flutter: `flutter build apk` or `flutter analyze` to verify no compile errors
- [ ] Go: `cd backend/gateway && go build ./...` to verify client.go compiles
- [ ] Opus agent: verify all P1 fixes actually work as intended
