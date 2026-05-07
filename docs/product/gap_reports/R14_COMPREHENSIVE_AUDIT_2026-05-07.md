# R14 Comprehensive Audit Report

> Date: 2026-05-07 | 11 independent agents | 3 rounds parallel dispatch
> Total: 3 P0, 28 P1, 32 P2 (63 findings)
> Previous: R13 (141 findings, all fixed)

---

## Executive Summary

R14 dispatched 11 fresh independent auditors across the full Sparkle stack (Flutter/Go/Python). Each agent was instructed to not reference any prior findings. Overall finding count dropped 55% from R13 (141→63), confirming the R13 fix cycle was effective.

**3 P0 items** require immediate attention:
1. Go Apple login `CreateSocialUser` omits `password_login_enabled` → column defaults to `true`, diverging from Python
2. Go/Python JWT signing key divergence risk — Go uses `JWT_SECRET` directly, Python aliases it from `SECRET_KEY`
3. Go Galaxy gRPC client wraps only 3 of 10 proto RPCs — 7 RPCs permanently fall back to slower REST proxy

---

## P0 Findings (3)

### P0-1: Go `CreateSocialUser` omits `password_login_enabled`, defaults to `true`
- **Agent**: R1A1 Onboarding/Auth
- **File**: `backend/gateway/internal/db/query.sql:7-13`
- **Evidence**: `CreateSocialUser` INSERT does not include `password_login_enabled`; column default is `DEFAULT true` (schema.sql:6640). Python `auth.py:520` explicitly sets `password_login_enabled=False` for social-login users.
- **Impact**: Apple users created through Go handler have `password_login_enabled=True` while Google/WeChat/Apple-via-Python users have `False`. Flutter uses this field to decide "Change Password" UI visibility.
- **Fix**: Add `password_login_enabled = false` to `CreateSocialUser` SQL INSERT.

### P0-2: JWK/key divergence — Go and Python use separate config aliases for the same signing secret
- **Agent**: R1A1 Onboarding/Auth
- **File**: `backend/gateway/internal/config/config.go:46` vs `backend/app/config/settings.py:134`
- **Evidence**: Go uses `cfg.JWTSecret` directly; Python maps `JWT_SECRET` → `SECRET_KEY` via `AliasChoices`. Both sign with HS256. If only `SECRET_KEY` is set (not `JWT_SECRET`), Go-signed Apple login tokens are rejected by Python `decode_token`.
- **Impact**: Apple login tokens issued by Go fail validation in Python-authenticated proxy routes.
- **Fix**: Validate at startup that `JWT_SECRET == SECRET_KEY` in `env-check`, or use unified config key.

### P0-3: Go Galaxy gRPC client wraps only 3 of 10 proto RPCs
- **Agent**: R2A5 Galaxy/Knowledge
- **File**: `backend/gateway/internal/galaxy/client.go:65-90`
- **Evidence**: Only `UpdateNodeMastery`, `GetUserGalaxy`, `RecordNodeInteraction` wrapped. Missing: `GetNodeDetail`, `SearchNodes`, `GetLearningPath`, `GetNodeDependencies`, `GetGalaxyStats`, `GetRecommendedNodes`, `SyncCollaborativeGalaxy`.
- **Impact**: The 7 missing RPCs have zero gRPC code path. All traffic falls back to slower REST proxy (Gateway→Python FastAPI), defeating the gRPC channel's purpose.
- **Fix**: Add 7 missing method wrappers to `client.go`, wire into `galaxy_handler.go`.

---

## P1 Findings (28)

### Onboarding + Auth (4)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-01 | `auth.py:817` | Guest ID uses 6-char random suffix (~2B namespace), collision risk under concurrency | Use `uuid.uuid4().hex[:8]` |
| P1-02 | `setup.go:840` | NoRoute proxy doesn't call `SetProxyUserContextHeaders`; `X-User-ID` header not set for NoRoute-proxied requests | Add `SetProxyUserContextHeaders` call |
| P1-03 | `api_interceptor.dart:185-207` | Refresh `Completer` cleared only after 100ms delay; concurrent 401s trigger redundant refresh | Clear immediately after completion |
| P1-04 | `users.py:561-584` | Account deletion relies on SQLAlchemy cascade; no integration test verifying all relations cleaned | Add cascade verification test |

### Chat + AI (2)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-05 | `chat_input.dart:188-198` | Send race: `_isSending` guard bypassed when `onSend` callback set; double-tap fires twice | Set `_isSending=true` before calling `onSend` |
| P1-06 | `websocket_chat_service_v2.dart:2456` | Single `_sendMessage` failure broadcasts error to ALL active request controllers via `_handleConnectionError` | Error only the specific request controller |

### Goals + Plans (3)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-07 | `goal_detail_page.dart:820-915` + `goal_repository.dart:101-113` | Goal deadline not editable post-creation; `updateGoal()` only sends title/description, never `target_date` | Add date picker to edit dialog, pass `target_date` |
| P1-08 | `goal_router.py:30-38` + `goal_detail_provider.dart:208-209` | `GoalSummaryPayload` omits `description` field; description entered at creation lost from detail view | Add `description` to payload and model |
| P1-09 | `goals.py:317-321` | Goal soft-delete only marks goal+plan; tasks linked to deleted plan remain queryable (cascade only for hard delete) | Soft-delete associated tasks or filter them out |

### Tasks + Execution (4)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-10 | `task_command.go:242` | `CompleteTask` WHERE clause: `status = 'IN_PROGRESS'` only; PAUSED/STUCK tasks require Resume→Complete (2-step friction) | Expand to `status IN ('IN_PROGRESS','PAUSED','STUCK')` |
| P1-11 | `task_command.go:290` | `AbandonTask` WHERE clause: `status IN ('PENDING','IN_PROGRESS')` only; PAUSED/STUCK un-abandonable | Expand to include `'PAUSED','STUCK'` |
| P1-12 | `task_provider.dart` + `task_command.go:205` | No `ReopenTask` for completed tasks; `StartTask` WHERE is `status='PENDING'` only; completed tasks stuck permanently | Add ReopenTask command + provider method |
| P1-13 | `task_detail_screen.dart` | `TaskFilterOptions` enum missing `abandoned`; abandoned tasks unfilterable in task list | Add `abandoned` to enum |

### Galaxy + Knowledge (4)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-14 | `galaxy_grpc_service.py:295` vs `galaxy.py:713` | gRPC `SearchNodes` uses keyword (ILIKE text), REST `/galaxy/search` uses semantic (pgvector cosine) — different results for same operation | Align both to semantic search |
| P1-15 | `star_map_painter.dart:2640-2642` | `_masteryTemperatureColor` returns `color` unchanged; mastery-based temperature coloring silently disabled | Implement HSL temperature shift or remove dead call |
| P1-16 | `goal_world_graph_mini_panel.dart:632-699` | GoalWorldGraph shows raw metrics but no synthesized importance explanation (why this node matters) | Add `importance_explanation` field, populate server-side |
| P1-17 | `galaxy_handler.go:188` | SparkNode calls `RecordNodeInteraction` not `UpdateNodeMastery`; dual mastery paths undocumented | Document semantic difference (spark=study-driven vs master=explicit override) |

### Community + Social (2)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-18 | `community_service.py:849-861` | Group join notification calls `create_and_push` with wrong params (schema object instead of individual fields, wrong param names); TypeError caught silently | Use individual params: `create_and_push(user_id=..., title=..., content=..., ...)` |
| P1-19 | `community.py:1220-1229` | Friend request responder not notified on accept/reject; requester must manually check | Add `NotificationPushService` call to notify original requester |

### Achievements + Streaks (1)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-20 | `milestone_celebration_screen.dart:96-118` | Switch statements handle only 3 of 8 milestone IDs; 5 IDs (tasks_1, streak_7, nodes_100, plan_first, community_first_share) show wrong "30-day learner" content | Add switch cases for all 8 milestone IDs |

### Settings + i18n (2)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-21 | `theme_manager.dart:47` | `colorBlindFriendly` aliases to `highContrast` palette with zero CB-specific hue shifting; toggle misleading | Implement `SparkleColors.colorBlind()` with Wong 2011 palette |
| P1-22 | `unified_settings_screen.dart:98` + `accessibility_provider.dart:94` | Haptic toggle duplicated in TWO independent places; they can silently diverge | Both screens read/write through `accessibilitySettingsProvider` exclusively |

### Cross-Layer Integration (1)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-23 | `backend/app/gen/__pycache__/` | Orphaned `.pyc` files without source: `community_service_pb2.cpython-314.pyc`, `community_service_pb2_grpc.cpython-314.pyc` | Delete orphaned `.pyc` files |

### Security + Performance (2)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-24 | `file_handler.go:570` | `validateFileByMagicBytes()` defined and tested but never wired into any production code path; uploads go directly to MinIO via presigned URL | Wire into `PrepareUpload` or upload completion path |
| P1-25 | `config.go:476` | `MINIO_USE_SSL` defaults to `false` with no production guard (unlike `AgentTLSInsecure` which has fatal rejection in prod) | Add production guard: reject `MINIO_USE_SSL=false` when `ENVIRONMENT=production` |

### Offline + Error Recovery (3)
| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| P1-26 | `websocket_service.dart:1-167` | V1 WebSocketService has no heartbeat/ping-pong; silent dead connections never detected | Add heartbeat or migrate all consumers to V2 service |
| P1-27 | `offline_message_queue_service.dart:15-39` | No queue size limit on Isar-backed offline messages; failed messages never age out | Add max-pending limit + failed message TTL |
| P1-28 | `main.dart:41-48` | `ErrorWidget.builder` passes raw `exceptionAsString()` to UI; users see Dart exceptions | Route through `ErrorMessages.getUserFriendlyMessage()` |

---

## P2 Findings (32)

### Onboarding + Auth (2)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-01 | Token blacklist checked redundantly in Python `decode_token` when Go middleware already validated (adds ~1-3ms per request) | `security.py:115-118` |
| P2-02 | Guest seed failure silently allows login without demo data; no UI feedback of degraded mode | `auth.py:869-870` |

### Chat + AI (5)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-03 | Hardcoded English Semantics label: `'Open attachment options'` | `chat_input.dart:384` |
| P2-04 | Full payload logged in debug via `_log('Full payload: ${json.encode(payload)}')` — PII risk even in production if log level misconfigured | `websocket_chat_service_v2.dart:2444` |
| P2-05 | ContextReceiptBar dedup key uses pipe-concatenation (`a|b|c`), collision risk with pipe-containing content | `context_receipt_bar.dart:174` |
| P2-06 | Chat history batch insert silently drops individual messages on failure | `chat_history_persister.go:229-232` |
| P2-07 | DualCoreRouter module singleton misses `parameter_snapshot` overrides on re-entry | `dual_core_router.py:1089` |

### Goals + Plans (3)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-08 | No PATCH route for goals in Go proxy (Plans have both PUT and PATCH) | `proxy_routes.go:349-358` |
| P2-09 | Flutter "habit" maps to backend "fitness"; 习惯 ≠ 健身; wrong scenario pack for non-fitness habits | `goal_repository.dart:44` |
| P2-10 | Duplicate goal title check has TOCTOU race (check + insert not atomic) | `goals.py` |

### Tasks + Execution (3)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-11 | `TaskFilterOptions` enum missing `abandoned` | `task_list_screen.dart` |
| P2-12 | Move-to-plan dialog has 7 inline bilingual strings (by design per project convention) | `task_detail_screen.dart:518-564` |
| P2-13 | Complete/Abandon buttons visible for STUCK tasks but fail silently due to WHERE clause mismatch | `task_detail_screen.dart` |

### Galaxy + Knowledge (3)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-14 | Galaxy gRPC client uses `cfg.AgentAddress` instead of dedicated `GalaxyAddress`; blocks horizontal scaling | `galaxy/client.go:45` |
| P2-15 | `GetNodeDetail` gRPC response `child_ids` always empty (hardcoded `[]`); REST equivalent populates correctly | `galaxy_grpc_service.py:280` |
| P2-16 | No Prometheus/OTel metrics for galaxy rendering performance; frame drops invisible to production monitoring | `star_map_painter.dart:326-397` |

### Community + Social (2)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-17 | Comment list lacks pagination; fetches ALL comments with no `limit`/`offset` | `community.py:489-511` |
| P2-18 | Comment delete icon rendered unconditionally; users see delete button they cannot use (backend enforces ownership) | `comment_bottom_sheet.dart:209-218` |

### Achievements + Streaks (2)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-19 | Combo photons granted inline before DB commit; if commit fails, photons persist but achievements roll back | `achievement_engine.py:431+2634` |
| P2-20 | Instance-level `_fatigue_cache` / `_crisis_cache` dicts have no TTL; stale if service instance is long-lived | `streak_quality.py:60-61` |

### Settings + i18n (4)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-21 | No user-facing indicator when EmotionAdaptiveTheme is active; users don't know why UI changed | `emotion_responsive_theme.dart` |
| P2-22 | `EmotionAdaptiveMode` enum + `setMode()` exist but no settings screen exposes auto/low/normal toggle | `emotion_state_provider.dart:218` |
| P2-23 | `lowLoadMode` boolean never read by any rendering widget; toggle works by side-effect only (cascaded flags) | `accessibility_provider.dart:156-167` |
| P2-24 | `SensoryFeedbackService.init()` never called at startup; first sound has ~100-300ms cold-start latency | `sensory_feedback_service.dart:684` |

### Cross-Layer Integration (3)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-25 | Stale `agent_service_pb2.py` at root `gen/` level (May 1 vs proto May 3); not imported (v1 path current), but hygiene issue | `backend/app/gen/agent_service_pb2.py` |
| P2-26 | Go `gen/userstate/v1/` directory empty; `user_state.proto` not excluded from buf.yaml but generates no output | `backend/gateway/gen/userstate/v1/` |
| P2-27 | Go `/community` proxy lacks catch-all for sub-routers (`/community/aggregates`, `/community/strategy-outcomes`); 404 through gateway | `proxy_routes.go:440-565` |

### Security + Performance (1)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-28 | HS256 symmetric algorithm used everywhere; code comment acknowledges RS256 migration plan but not started; JWKS endpoint absent | `auth.go:446-460`, `security.py:93-104` |

### Offline + Error Recovery (4)
| # | Issue | File:Line |
|---|-------|-----------|
| P2-29 | `CRDTSyncManager.sync()` body is empty (comment only); real sync happens through `SyncEngine` Isar watch | `crdt_sync_manager.dart:166-168` |
| P2-30 | V2 reconnect jitter is flat 0-250ms regardless of backoff tier (2% jitter at 12s); should be proportional | `websocket_chat_service_v2.dart:2305` |
| P2-31 | V1 `_scheduleReconnect()` uses fixed list with zero randomization; synchronized reconnect storms post-outage | `websocket_service.dart:116` |
| P2-32 | `isOnlineProvider` defaults to `true` during loading/error states (`orElse: () => true`); transient false-online at startup | `connectivity_provider.dart:20` |

---

## Verified Working (Highlights)

Each agent verified 7-22 specific capabilities. Key confirmations:

| Domain | Verified |
|--------|----------|
| **Auth** | bcrypt hashing, account lockout, token rotation, anti-enumeration, constant-time admin auth, device identity headers |
| **Chat** | WebSocket V2 heartbeat (30s ping/60s timeout), exponential backoff with 50-msg queue limit, ACK tracking, stream-aware suppression |
| **Goals/Plans** | Auto-create Plan in create_goal, bidirectional FK (goal_id↔plan_id), goal progress updates on task complete/abandon, overdue detection with amber chip |
| **Tasks** | Full state machine (PENDING→IN_PROGRESS→PAUSED/STUCK→COMPLETED/ABANDONED), RESTORE status, all 6 quick actions proxied, confirm-batch route |
| **Galaxy** | All 10 Python gRPC implementations, gRPC server registration, REST proxy chain, 3D LOD pipeline, SSE event stream, GoalWorldGraph data flow |
| **Community** | Comment CRUD, feed pagination, isLiked rendering, friend request push notifications, post rate limiting, share/delete buttons |
| **Achievements** | Combo bonus photons granted, 24h streak quality cache, all 8 milestone IDs in seeds, chronicle entries persisted to PostgreSQL, learning dashboard with real data |
| **Settings** | fontScale/reduceMotion/screenReaderOptimized/highContrast all wired to MediaQuery, ttsEnabled via Riverpod, AmbientScene bilingual labels |
| **Security** | CSP/HSTS/X-Frame-Options/CORS all active, parameterized SQL, bluemonday XSS sanitization, certificate pinning, production guard for AgentTLSInsecure |
| **Offline** | Offline outbox with retry, DB restore on reconnect, reconnect rate limiting, drain handling, message dedup, task idempotency |

---

## Trend Analysis

| Metric | R11 | R13 | R14 | Δ R13→R14 |
|--------|-----|-----|-----|-----------|
| P0 | 14 | 12 | 3 | -75% |
| P1 | 52 | 68 | 28 | -59% |
| P2 | 38 | 61 | 32 | -48% |
| **Total** | **104** | **141** | **63** | **-55%** |

R13's higher count was partly due to more exhaustive scope (vision widget verification + i18n completeness scan). R14's 55% decline confirms the R13 fix cycle was effective. The P0 count dropped from 12 to 3.

---

## Priority Fix Order

1. **P0-3**: Galaxy gRPC client — add 7 missing RPC wrappers (highest user impact: slow galaxy operations)
2. **P0-1**: CreateSocialUser password_login_enabled (incorrect UI for Apple users)
3. **P0-2**: JWT secret key divergence (cross-layer auth break)
4. **P1-18**: Group join notification TypeError (silent failure)
5. **P1-05/06**: Chat send race + broadcast error (user-facing bugs)
6. **P1-07/08**: Goal editing gaps (deadline + description)
7. **P1-10/11/12**: Task state machine friction (complete/abandon/reopen)
8. **P1-14**: Galaxy search inconsistency (keyword vs semantic)
9. **P1-21**: colorBlindFriendly misleading toggle
10. Remaining P1 items → P2 items

---

*Audit methodology: 11 agents dispatched in 3 rounds, each with clean-slate instructions to not reference any prior findings. Each agent verified 7-22 specific capabilities in addition to finding issues. Cross-referenced against actual file contents, not prior reports.*
