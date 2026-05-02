# Flutter Mobile Second-Wave Audit Report

**Date**: 2026-05-02
**Auditor**: Claude Agent (Second Wave)
**Scope**: Section 15.1 APP-001 through APP-010, UX-001/003/007/012
**Branch**: codex/final-closeout-integration-2026-05-02

---

## APP-001: Riverpod State Management

**Score: 5/5**

Riverpod is the primary state management solution across the entire Flutter codebase.

**Evidence**:
- `mobile/lib/main.dart` line 5: `import 'package:flutter_riverpod/flutter_riverpod.dart'` and line 111: `ProviderScope(...)` wraps the root app
- `mobile/lib/core/providers/` contains 4 core providers (keep_alive, locale, persistent_state_notifier, theme)
- Every feature module uses Riverpod: chat_provider.dart, community_providers.dart, error_book_provider.dart, notification_center_provider.dart, etc.
- ProviderContainer injection used in WebSocket service (`websocket_chat_service_v2.dart` line 1287)
- UX envelope extraction in chat_provider.dart (lines 421-525) parses `uxEnvelope` fields from backend metadata including: `continuity_banner`, `mode_explanation`, `adaptation_summary`, `ux_sources`, `ux_result`, `ux_followthrough`, `ux_evolution` -- this is consistent with the backend `ux_envelope.py` PresentationProfile

**Key files**:
- `mobile/lib/main.dart` -- ProviderScope bootstrap
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart` -- UX envelope extraction
- `mobile/lib/core/providers/` -- core providers
- 40+ feature providers across `mobile/lib/features/*/presentation/providers/`

---

## APP-002: WebSocket Streaming

**Score: 5/5**

A production-grade WebSocket client exists with streaming, reconnection, dedup, and heartbeat.

**Evidence**:
- `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` (2647 lines) -- full implementation
- **Streaming**: `_parseChatEvent()` handles 30+ event types (delta, done, tool_call, tool_result, status_update, aurora_state_band, plan_review_widget, transparency_step, etc.)
- **Reconnection**: Exponential backoff with jitter (800ms, 1200ms, 2200ms, 4200ms, 8200ms, 12200ms), max 6 attempts, `_triggerReconnect()` with `_reconnectSchedule`
- **Dedup**: Per-request stream controllers (`_requestControllers` map) route events by `request_id`; ACK/NACK handling for message delivery confirmation
- **Heartbeat**: 30s ping interval, 60s pong timeout, 3 consecutive failure threshold, RTT metrics exposed via `heartbeatMetrics` stream
- **Auth**: JWT token refresh on 401 with automatic reconnection (`_handle401Error`, `_onTokenRefreshSuccess`)
- **Large frame handling**: Messages >12000 bytes parsed in isolate via `compute()` to avoid UI thread blocking
- **Offline queue**: `OfflineMessageQueueService` persists outgoing messages to Isar, restores on reconnect

**Key files**:
- `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart`
- `mobile/lib/features/chat/data/models/chat_stream_events.dart` -- typed event models
- `mobile/lib/core/services/websocket_service.dart` -- lower-level WS wrapper

---

## APP-003: Isar Local Database

**Score: 5/5**

Isar is used as the local database with comprehensive schema.

**Evidence**:
- `mobile/lib/core/offline/local_database.dart` -- singleton LocalDatabase with Isar.open() initializing 11 collections:
  - LocalKnowledgeNode, PendingUpdate, LocalCRDTSnapshot, OutboxItem
  - UserAnalyticsEvent, TranslationRecord, TranslationWordLink, VocabWord, VocabReview
  - FocusSessionRecord, CachedStatisticsModel, OfflineChatMessage
- Generated code at `local_database.g.dart`
- Isar indices: unique index on `serverId` for knowledge nodes, index on `requestId` for offline messages, index on `dedupeKey` for outbox
- Platform-specific: `local_database_native.dart` and `local_database_web.dart` variants

**Key files**:
- `mobile/lib/core/offline/local_database.dart`
- `mobile/lib/core/offline/local_database.g.dart`

---

## APP-004: Offline Outbox with Idempotent Sync

**Score: 5/5**

A full outbox pattern with idempotent sync exists.

**Evidence**:
- `mobile/lib/core/offline/sync_engine.dart` (523 lines) -- complete outbox processor:
  - `enqueue()` method with topic/opType/dedupeKey/priority/traceId
  - Connectivity-aware processing via `connectivity_plus`
  - Batch processing (20 items), max 5 attempts, exponential backoff (800ms-30s)
  - ACK-backed flow for knowledge mastery and CRDT updates (`_waitForAck` with type matching)
  - Stuck-item requeue for waitingAck items exceeding TTL
- `mobile/lib/core/offline/outbox_dedupe_key.dart` -- structured dedup keys per entity type
- `mobile/lib/core/network/idempotency_interceptor.dart` -- Dio interceptor auto-attaching `X-Idempotency-Key` header to POST/PUT/PATCH requests
- `mobile/lib/core/offline/offline_message_queue_service.dart` (193 lines) -- chat-specific offline queue with pending/sent/acked/failed lifecycle
- WebSocket chat service restores pending from DB on reconnect (`_restorePendingFromDb`)

**Key files**:
- `mobile/lib/core/offline/sync_engine.dart`
- `mobile/lib/core/offline/outbox_dedupe_key.dart`
- `mobile/lib/core/network/idempotency_interceptor.dart`
- `mobile/lib/core/offline/offline_message_queue_service.dart`

---

## APP-005: CRDT Conflict Resolution

**Score: 5/5**

A complete custom CRDT implementation exists for offline/multi-device state.

**Evidence**:
- `mobile/lib/core/offline/offline_crdt_document.dart` (389 lines) -- full CmRDT document:
  - `OfflineCrdtOperation` with opId, actorId, objectType, objectId, opType, lamport timestamp, vectorClock
  - `OfflineCrdtDocument` with `apply()`, `applyAll()`, `merged()` methods
  - Deterministic ordering via Lamport clock then actor ID then opId tiebreaker
  - Domain-specific queries: `knowledgeMastery()`, `taskState()`, `chatMessages()` with tombstone support
  - Protocol version `sparkle-crdt-v1` with SHA-256 content hash
- `mobile/lib/core/offline/conflict_resolver.dart` -- 3-tier resolution strategy for knowledge nodes:
  1. Revision (logical clock) priority
  2. Timestamp (last-writer-wins)
  3. Higher mastery wins (learning-positive bias)
- `mobile/lib/core/offline/crdt_sync_manager.dart` (267 lines) -- coordinates CRDT with SyncEngine
- `mobile/lib/core/offline/crdt_persistence.dart` -- Isar-backed CRDT snapshot persistence

**Key files**:
- `mobile/lib/core/offline/offline_crdt_document.dart`
- `mobile/lib/core/offline/conflict_resolver.dart`
- `mobile/lib/core/offline/crdt_sync_manager.dart`
- `mobile/lib/core/offline/crdt_persistence.dart`

---

## APP-006: UI Regression / Responsive Design

**Score: 4/5**

Responsive design system exists with breakpoints and adaptive layouts.

**Evidence**:
- `mobile/lib/core/design/breakpoints.dart` -- phone breakpoints (360, 390, 428) and layout breakpoints (tablet=768, desktop=1200, wide=1440)
- `mobile/lib/core/design/responsive_widgets.dart` -- full responsive widget library:
  - `ResponsiveScaffold`: mobile (bottom nav) / tablet (NavigationRail) / desktop (NavigationDrawer)
  - `ContentConstraint`: max-width centering for large screens
  - `ResponsiveGrid` / `ResponsiveSliverGrid`: adaptive column counts
  - `ResponsiveTwoColumn`: sidebar collapse on mobile
- `mobile/lib/core/design/tokens_v2/responsive_system.dart` -- DeviceCategory enum (phone, phablet, tablet, desktop, tv, watch) with adaptive spacing/grid systems
- Custom widgets use `LayoutBuilder` / `MediaQuery` patterns
- No automated visual regression test suite found (golden tests may exist but were not verified)

**Deduction**: -1 for lack of automated visual regression/golden test evidence.

**Key files**:
- `mobile/lib/core/design/breakpoints.dart`
- `mobile/lib/core/design/responsive_widgets.dart`
- `mobile/lib/core/design/tokens_v2/responsive_system.dart`

---

## APP-007: Push Notification Navigation

**Score: 5/5**

Push notification tap navigates to correct context with rich payload resolution.

**Evidence**:
- `mobile/lib/core/services/push_navigation_service.dart` (286 lines) -- comprehensive payload routing:
  - `resolveRouteForPayload()` tries 6 strategies in order: destination_route, deep_link, suggested_action, task_id, plan_id, notification_id, recall_type
  - Deep link scheme `sparkle://task/{id}`, `sparkle://chat/{session}`, `sparkle://plan/{id}/review`
  - Action types: open_task, start_task, execute_task, open_plan, review_plan
  - Route resilience via `RouteResilience.openExternalRoute()`
- `mobile/lib/core/services/firebase_messaging_service.dart` -- Firebase messaging integration
- `mobile/lib/core/services/unified_push_service.dart` -- unified push abstraction (FCM + JPush)
- `mobile/lib/core/services/deep_link_service.dart` -- deep link resolution
- `mobile/lib/core/services/app_link_router_service.dart` -- app link routing

**Key files**:
- `mobile/lib/core/services/push_navigation_service.dart`
- `mobile/lib/core/services/firebase_messaging_service.dart`
- `mobile/lib/core/services/unified_push_service.dart`

---

## APP-008: Error Degradation

**Score: 5/5**

Graceful UI for all failure modes.

**Evidence**:
- `mobile/lib/core/design/widgets/error_widget.dart` (503 lines) -- comprehensive error widget system:
  - 3 types: page (full-screen), banner (top bar), inline
  - 3 severities: error (red), warning (orange), info (blue)
  - Factory constructors: `CustomErrorWidget.page()`, `.banner()`, `.inline()`
  - Specialized pages: `NetworkErrorPage`, `NotFoundErrorPage`, `ServerErrorPage`
  - Animated icon, gradient backgrounds, retry buttons, semantic labels
- WebSocket error handling in chat: `ErrorEvent` with retryable flag, graceful degradation to pending queue, user-visible error messages
- Task execution handles offline state: `ExecutionCopy.engineOfflineQueuedMessage()`, OpenClaw offline visual tone
- Galaxy performance monitor catches rendering failures

**Key files**:
- `mobile/lib/core/design/widgets/error_widget.dart`
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart` -- error state handling
- `mobile/lib/features/task/presentation/execution_copy.dart` -- offline task copy

---

## APP-009: Performance Monitoring

**Score: 4/5**

Performance monitoring exists with Sentry integration and service-specific monitors.

**Evidence**:
- `mobile/lib/core/services/performance_monitor.dart` (543 lines) -- Sentry-based monitoring:
  - FPS tracking, memory estimation, page load timing, interaction tracking
  - Slow interaction detection (>1s), offline sync tracking
  - Performance anomaly detection (FPS<30, memory>500MB)
  - Sentry breadcrumbs and transactions
- `mobile/lib/core/services/performance_service.dart` -- performance service abstraction
- `mobile/lib/features/galaxy/data/services/galaxy_performance_monitor.dart` -- knowledge graph rendering perf
- `mobile/lib/core/services/client_observability_service.dart` (215 lines) -- client telemetry with offline queue
- Large message parsing offloaded to isolate (`compute()` in WS service line 1978)
- Memory: FPS tracking uses `devicePixelRatio` as a proxy rather than actual frame timing

**Deduction**: -1 because FPS measurement uses `devicePixelRatio` as a proxy instead of actual frame timing (SchedulerBinding.instance.currentFrameTimeStamp or similar). This is noted in the code comments.

**Key files**:
- `mobile/lib/core/services/performance_monitor.dart`
- `mobile/lib/core/services/client_observability_service.dart`
- `mobile/lib/features/galaxy/data/services/galaxy_performance_monitor.dart`

---

## APP-010: Observability (trace_id / turn_id)

**Score: 5/5**

Frontend events carry trace_id and workflow_id throughout the streaming pipeline.

**Evidence**:
- `mobile/lib/core/tracing/tracing_service.dart` -- `TracingService` singleton with `createTraceId()` and `startSpan()` methods
- `mobile/lib/features/chat/data/models/chat_stream_events.dart` -- every event model has `traceId` and `workflowId` fields (lines 15, 23)
  - Parsed from `json['trace_id']` at line 1038
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart` line 890: `String? traceId` accumulated across streaming events
- `websocket_chat_service_v2.dart` line 2394: trace_id injected into outbound messages via `TracingService.instance.createTraceId()`
- `sync_engine.dart` line 88: `traceId` stored on outbox items for end-to-end tracing
- `client_observability_service.dart`: all recorded events carry metadata, platform, and timestamp
- `performance_monitor.dart`: Sentry transactions and breadcrumbs include context

**Key files**:
- `mobile/lib/core/tracing/tracing_service.dart`
- `mobile/lib/features/chat/data/models/chat_stream_events.dart`
- `mobile/lib/core/services/client_observability_service.dart`

---

## UX-001: Homepage Goal-Centric

**Score: 5/5**

The homepage is organized around goals, not a feature grid.

**Evidence**:
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`:
  - Imports GoalSwitcher (line 37), MultiGoalDashboardCard (line 41)
  - `_DashboardGoalSwitcherBand` at line 912 renders `GoalSwitcher(dense: true)`
  - `MultiGoalDashboardCard` at line 628
  - First-run empty state (line 381) prompts `_buildFirstGoalEmptyState()` with goal chips: ExamSprint, LongTerm, Project, SelfGrowth
  - Imports `goal_detail_snapshot_card.dart` and `growth_quality_card.dart` from experience module
- `mobile/lib/features/home/presentation/widgets/goal_switcher.dart` -- active goal switching widget
- `mobile/lib/features/home/presentation/widgets/multi_goal_dashboard_card.dart` -- multi-goal overview with suggestion engine
- Dashboard widgets: exam_sprint_dashboard_card, long_term_plan_card, next_actions_card, task_board_card -- all goal-oriented

**Key files**:
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`
- `mobile/lib/features/home/presentation/widgets/goal_switcher.dart`
- `mobile/lib/features/home/presentation/widgets/multi_goal_dashboard_card.dart`

---

## UX-003: Aurora State Band Widget

**Score: 5/5**

A dedicated Aurora status band widget exists on the dashboard.

**Evidence**:
- `mobile/lib/features/home/presentation/widgets/aurora_status_band.dart` (492 lines):
  - 9 states: sensing, calibrated, riskDetected, needsConfirmation, calibrationAvailable, coolingDown, sourceAware, noSourcesUsed, strategyActive
  - Each state has distinct icon, title, colors
  - Expandable with correction options (ActionChip-based)
  - Cooldown timer display with override button
  - Correction option model: `CorrectionOption` with label and isDisconfirming flag
  - Freeform correction input dialog accessible from dashboard
  - Full accessibility: semantic labels, keyboard shortcuts, FocusableActionDetector
  - Integrated with `spine_status_band_provider.dart` for state management
- Dashboard imports and renders it: `import aurora_status_band.dart` in dashboard_screen.dart
- WebSocket feeds it: `AuroraStateBandEvent` parsed in chat_service, updates `emotionStateProvider`

**Key files**:
- `mobile/lib/features/home/presentation/widgets/aurora_status_band.dart`
- `mobile/lib/features/home/presentation/providers/spine_status_band_provider.dart`
- `mobile/lib/features/aurora/presentation/providers/emotion_state_provider.dart`

---

## UX-007: Causal Timeline Widget

**Score: 5/5**

A full Causal Timeline panel exists with evidence chains and correction.

**Evidence**:
- `mobile/lib/features/chat/presentation/widgets/causal_timeline_panel.dart` (633 lines):
  - `CausalTimelinePanel` -- bottom sheet widget
  - `TimelineCardModel` with cardId, traceId, mode, headline, summary, evidenceChain, userActions
  - `CausalTimelineNotifier` Riverpod provider loading from `ApiEndpoints.auroraSpineTimeline`
  - Expandable cards showing evidence chain steps (signal, policy, directive, outcome types)
  - User actions via ActionChips (correct, dismiss, etc.)
  - Correction submission: `submitCorrection()` with traceId, cardId, action, userExplanation
  - Error/retry and empty states
  - i18n support: `chatCausalWhyDecisions`, `chatCausalLoadFailed`, etc.
- `aurora_receipt_chip.dart` -- inline receipt widget in chat
- Wire: `causalTimeline` metadata field in chat events triggers the panel

**Key files**:
- `mobile/lib/features/chat/presentation/widgets/causal_timeline_panel.dart`
- `mobile/lib/features/chat/presentation/widgets/aurora_receipt_chip.dart`

---

## UX-012: Tasks Continue Offline

**Score: 4/5**

Tasks can continue offline via the CRDT outbox pattern, but the UX is limited.

**Evidence**:
- `mobile/lib/core/offline/offline_crdt_document.dart` -- `makeTaskStatusOperation()` allows local task state changes offline
- `mobile/lib/core/offline/crdt_sync_manager.dart` -- `setTaskState()` queues CRDT operation for sync
- `mobile/lib/core/offline/sync_engine.dart` -- outbox processes task state changes when connectivity returns
- `mobile/lib/core/offline/network_monitor.dart` -- connectivity listener triggers sync on network restoration
- `mobile/lib/features/task/presentation/execution_copy.dart` -- offline queue messaging for OpenClaw tasks
- Task execution screen shows offline state with appropriate visual tone

**Deduction**: -1 because while the infrastructure is complete, there is no explicit "offline mode" UI indicator on the task screen showing pending operations count or estimated sync time. The offline queue is functional but not prominently surfaced to the user.

**Key files**:
- `mobile/lib/core/offline/offline_crdt_document.dart`
- `mobile/lib/core/offline/crdt_sync_manager.dart`
- `mobile/lib/core/offline/network_monitor.dart`
- `mobile/lib/features/task/presentation/execution_copy.dart`

---

## Summary Table

| Item | Score | Key Finding |
|------|-------|-------------|
| APP-001 Riverpod State Management | 5/5 | Full Riverpod with UX envelope integration |
| APP-002 WebSocket Streaming | 5/5 | 2647-line production WS client with streaming, reconnect, heartbeat, ACK |
| APP-003 Isar Local DB | 5/5 | 11 Isar collections, generated schemas, platform variants |
| APP-004 Offline Outbox | 5/5 | Full outbox with idempotency keys, ACK-backed sync, exponential backoff |
| APP-005 CRDT | 5/5 | Custom CmRDT with Lamport clocks, vector clocks, 3-tier conflict resolution |
| APP-006 UI Regression | 4/5 | Responsive design system exists; no automated golden tests |
| APP-007 Push Navigation | 5/5 | Rich payload routing with 6 strategies, deep links, action resolution |
| APP-008 Error Degradation | 5/5 | 3-type error widget system, network/server/404 specialized pages |
| APP-009 Performance | 4/5 | Sentry + observability; FPS proxy not actual frame timing |
| APP-010 Observability | 5/5 | trace_id/workflow_id on all events, client telemetry with offline queue |
| UX-001 Goal-Centric Home | 5/5 | GoalSwitcher, MultiGoalDashboardCard, first-goal empty state |
| UX-003 Aurora State Band | 5/5 | 9-state band with corrections, cooldown, accessibility |
| UX-007 Causal Timeline | 5/5 | Full panel with evidence chains, user corrections, i18n |
| UX-012 Offline Tasks | 4/5 | CRDT task state works offline; no prominent offline indicator |

**Total: 66/70 (94%)**

---

## Additional Notable Files Discovered

### Divine Moment Widgets (Spine Integration)
- `mobile/lib/features/chat/presentation/widgets/stale_recovery_card.dart` -- StaleRecoveryCard (divine moment #4) with elapsed time display and 4 resume options
- GrowthCardEvent, SpineReceiptEvent, UXWarningEvent, CommunityHintEvent, GoalArbitrationEvent -- all parsed in WS event stream

### Emotion-Adaptive UI (FV-12)
- `mobile/lib/features/aurora/presentation/providers/emotion_state_provider.dart` -- EmotionStateNotifier with fatigue/cognitive_load/stress_signal
- `mobile/lib/core/design/adaptive/emotion_responsive_theme.dart` -- adaptive theme based on emotion state
- `mobile/lib/core/design/tokens_v2/responsive_system.dart` -- 6 device categories

### Test Coverage
- 249 test files in `mobile/test/`
- Specific tests: `offline_sync_test.dart`, `sync_engine_test.dart`, `chat_stream_parsing_test.dart`, `offline_crdt_document_test.dart`, `sync_engine_crdt_ack_test.dart`
