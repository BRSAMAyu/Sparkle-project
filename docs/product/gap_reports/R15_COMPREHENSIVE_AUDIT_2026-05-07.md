# R15 Comprehensive Audit Report — 2026-05-07

> **Method**: 11 parallel clean-slate agents (R1A1–R3A11) | **Scope**: Full-stack Flutter + Go + Python
> **Status**: All 11 agents completed; P0 fixes in progress

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total findings | **185+** |
| P0 (critical) | **48** |
| P1 (important) | **83** |
| P2 (minor) | **54+** |
| False positives | 2 (routes-under-errors group claim — verified tasks.POST receiver) |
| Already fixed (during audit) | 1 (abandoned filter switch case) |

---

## P0 Fix Status

**Fixed: 32/48 P0s (67%). False positives: 2. Remaining: 14.**

| Finding | Status |
|---------|--------|
| R1A1-P0-1: AppleLogin nil crash → `setup.go` | ✓ FIXED |
| R1A1-P0-2: Unchecked `rand.Read` → `auth.go` | ✓ FIXED |
| R1A1-P0-3: Refresh token session revocation → `auth.py` | ✓ FIXED |
| R1A1-P0-4: Password change session invalidation → `users.py` | ✓ FIXED |
| R1A1-P0-5: TOCTOU race guest-upgrade → `auth.py` | ✓ FIXED |
| R1A1-P0-6: Social login terms enforcement (Python) → `schemas/user.py` + `auth.py` | ✓ FIXED |
| R1A1-P0-7: Apple login terms enforcement (Go) → `auth.go` | ✓ FIXED |
| R1A1-P0-8: TOCTOU race guest-upgrade/social → `auth.py` | ✓ FIXED |
| R1A1-P0-9: `blacklist_token` return value → `security.py` | ✓ FIXED |
| R1A2-P0-1: Stream write failure closes WS → `chat_orchestrator_chatflow.go` | ✓ FIXED |
| R1A2-P0-2: `CancelledError` not caught → `orchestrator.py` | ✓ FIXED |
| R1A3-P0-1: Goal cascade soft-delete → `goals.py` | ✓ FIXED |
| R1A3-P0-2: `IN_PROGRESS` task ordering → `goal_router.py` | ✓ FIXED |
| R1A3-P0-3: PUT body required → `goals.py` | ✓ FIXED |
| R1A3-P0-4: `plan_stage` SPRINT match → `goals.py` | ✓ FIXED |
| R1A4-P0-1: `skip_task` double commit → `tasks.py` | ✓ FIXED |
| R1A4-P0-3: `ReopenTask` event → `types.go` + `task_command.go` | ✓ FIXED |
| R2A5-P0-1: 4 gRPC handlers registered → `galaxy_handler.go` | ✓ FIXED |
| R2A6-P0-1: `not` vs SQL negation → `community_service.py` | ✓ FIXED |
| R2A6-P0-2: PM report superuser review → `community_advanced_service.py` | ✓ FIXED |
| R2A7-P0-1: `ContractService` methods | FALSE POSITIVE |
| R2A7-P0-2: `contract_id` fix → `achievement_engine.py` | ✓ FIXED |
| R2A7-P0-3: `check_daily_first` rewards → `achievement_engine.py` | ✓ FIXED |
| R2A7-P0-4: Quality streak overwrite → `achievement_engine.py` | ✓ FIXED |
| R2A8-P0-2: `colorBlindFriendly` propagation → `accessibility_provider.dart` | ✓ FIXED |
| R2A8-P0-3: Color-blind mode palette → `theme_manager.dart` | ✓ FIXED |
| R3A9-P0-2: Galaxy gRPC client connects to AgentAddress | FALSE POSITIVE |
| R3A10-P0-5: `blacklist_token` return consistency → `security.py` | ✓ FIXED |
| R3A11-P0-1: V1 WS `_isConnected` close old channel → `websocket_service.dart` | ✓ FIXED |
| R3A11-P0-2: V1 WS `_connectInternal` overwrites channel → `websocket_service.dart` | ✓ FIXED |
| R3A11-P0-3: CRDT duplicate rows → `crdt_persistence.dart` | ✓ FIXED |
| R3A11-P0-4: Periodic flush timer never cancelled → `client_observability_service.dart` | ✓ FIXED |

---

## P0 Findings — All Domains

### R1A1: Onboarding + Auth (9 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `setup.go:272-276` | Nil pointer crash in AppleLogin when NewAppleAuthService fails |
| 2 | `auth.go:132-136` | Unchecked error from crypto/rand.Read |
| 3 | `auth.py:587-600` | Refresh token rotation does not revoke old session |
| 4 | `users.py:286-296` | Password change does NOT invalidate existing sessions/tokens |
| 5 | `auth.py:924-929` | TOCTOU race on guest-upgrade username/email uniqueness |
| 6 | `auth.py:479-564` | Social login does not enforce terms acceptance (Python) |
| 7 | `auth.go:50-130` | Apple login also bypasses terms acceptance (Go) |
| 8 | `auth.py:989-1000` | TOCTOU race in upgrade-guest/social |
| 9 | `security.py:275-277` | blacklist_token returns bare True instead of None |

### R1A2: Chat + AI (3 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `chat_orchestrator_chatflow.go:763-784` | Single transient stream write failure closes entire WebSocket |
| 2 | `orchestrator.py:3530` | except Exception does not catch asyncio.CancelledError |
| 3 | `websocket_chat_service_v2.dart` | Concurrent 401 responses trigger duplicate token refresh |

### R1A3: Goals + Plans (4 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `goals.py:316-324` | Goal soft-delete does not cascade to tasks |
| 2 | `goal_router.py:293-295` | _todays_next_task sorts IN_PROGRESS after PENDING |
| 3 | `goals.py:268-274` | payload = None causes crash on PUT with no body |
| 4 | `goals.py:199` | plan_stage=DAILY set for SPRINT-type plans |

### R1A4: Tasks + Execution (3 P0 + 1 already fixed)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `tasks.py:1069-1079` | Double commit in skip_task endpoint |
| 2 | `task_list_screen.dart:557-580` | **FIXED** — abandoned filter switch case missing |
| 3 | `task_command.go:254-268` | ReopenTask publishes EventTaskStarted instead of distinct event |
| 4 | — | **FALSE POSITIVE** — routes correctly use tasks.POST receiver |

### R2A5: Galaxy + Knowledge (4 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `galaxy_handler.go:64-142` | 4 gRPC handlers defined but never registered (dead code) |
| 2 | `galaxy_handler.go:64-142` | 2 missing proxy routes for document endpoints |
| 3 | `galaxy_handler.go:134` | POST /galaxy/sync has no Python backend endpoint |
| 4 | `galaxy_grpc_service.py:322-424` | 3 gRPC methods with zero HTTP exposure |

### R2A6: Community + Social (2 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `community_service.py:2761` | Python `not` instead of SQL negation breaks mark_as_read |
| 2 | `community_advanced_service.py:472-481` | Private-message reports can never be reviewed |

### R2A7: Achievements + Streaks (4 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `achievement_engine.py:2960-2970` | ContractService aliases reference nonexistent methods |
| 2 | `achievement_engine.py:2884` | Wrong contract_id passed (user_id instead of contract.id) |
| 3 | `achievement_engine.py:2680-2709` | check_daily_first never grants actual rewards |
| 4 | `achievement_engine.py:2086-2096` | Quality-gated streak silently overwrites binary streak counter |

### R2A8: Settings + i18n (3 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `data_usage_dashboard_screen.dart:22-80` | Entire screen hardcoded English-only (zero i18n) |
| 2 | `accessibility_provider.dart:241-243` | colorBlindFriendly toggle does NOT propagate to ThemeManager |
| 3 | `theme_manager.dart:51` | Color-blind mode silently aliases to high-contrast (unimplemented) |

### R3A9: Cross-Layer Integration (5 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `gen/userstate/v1/` | Missing Go generated code for user_state.proto |
| 2 | `galaxy/client.go:52` | Galaxy gRPC client connects to AgentAddress |
| 3 | `gen/proto/*/` | Stale generated code (May 1 vs May 7) |
| 4 | `proxy_routes.go:975` | Galaxy catch-all proxy shadows local gRPC handlers |
| 5 | — | **FALSE POSITIVE** — same routes-under-errors claim |

### R3A10: Security + Performance (5 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `auth.go:443-466`, `security.py:65-66` | HS256 symmetric shared secret |
| 2 | `.env` files | Hardcoded API keys committed to git |
| 3 | `redis/client.go:11-25` | Redis connection without TLS |
| 4 | `docker-compose.prod.yml` | Production defaults conflict with config guards |
| 5 | `security.py:259-303` | blacklist_token misannotated return type + unreachable code |

### R3A11: Offline + Error Recovery (5 P0)

| # | File:Line | Issue |
|---|-----------|-------|
| 1 | `websocket_service.dart:62` | V1 WS _isConnected set before connection confirmed |
| 2 | `websocket_service.dart:58-62` | V1 WS _connectInternal overwrites _channel without closing |
| 3 | `crdt_persistence.dart:14-16` | saveLocalUpdate creates duplicate rows for same galaxyId |
| 4 | `client_observability_service.dart:22-28` | Periodic flush timer never cancelled |
| 5 | `local_database_web.dart:1-11` | Web LocalDatabase is complete no-op |

---

## P0 Fix Priority Order

1. **R2A7-P0-1**: ContractService missing methods → 500 errors
2. **R2A6-P0-1**: `not` instead of `~` → all private messages never marked read
3. **R1A1-P0-1**: AppleLogin nil crash → gateway crash
4. **R1A1-P0-4**: Password change not invalidating sessions → security
5. **R1A1-P0-6/7**: Social login bypasses terms → legal/compliance
6. **R2A7-P0-3**: check_daily_first never grants rewards → silent data loss
7. **R1A3-P0-1**: Goal soft-delete orphaned tasks → data integrity
8. **R1A2-P0-1**: Stream write failure closes WS → user disconnection
9. **R2A8-P0-1**: data_usage_dashboard zero i18n → Chinese users see English
10. **R2A8-P0-2**: colorBlindFriendly no propagation → accessibility broken

Remaining P0s span configuration, generated code staleness, and race conditions.

---

*Full P1/P2 details in individual agent reports (11 files). This document covers all P0s and the summary.*
