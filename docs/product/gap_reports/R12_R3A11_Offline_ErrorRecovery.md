# R12 / R3A11 — Offline_ErrorRecovery 二次深度审查
**Date**: 2026-05-07
**Scope**: Offline + Error Recovery
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: Sparkle's offline capability is built on a solid Isar-based Sync Engine that correctly handles PENDING/FAILED states, enabling a "growth never stops" experience even in low-connectivity environments.

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 0 |
| P1 (important gap, ship with plan) | 2 |
| P2 (nice to have, post-launch) | 2 |
| Verified working | 5 |

---

## R11 P0 验证
Verified that the `ErrorWidget` override is present in `main.dart`, resolving the previous R11 concern about the default red error screen.

---

## P0 Findings (Must Fix Before Launch)
No P0 issues found in the core offline/error recovery pipeline. The system is robust.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: Missing Global Sync Status Indicator in Main Shell
**File**: `mobile/lib/app/app.dart`, `mobile/lib/core/navigation/main_navigation_shell.dart`
**Problem**: While the `SyncCenterProvider` tracks status, there is no persistent UI indicator (e.g., a "cloud with slash" or "syncing" icon) in the main navigation shell to inform users that they are currently offline or have pending items.
**Expected**: Users should know their data is queued.
**Fix recommendation**: Add a small sync status icon to the App Bar or Bottom Navigation.

### P1-2: Fixed WebSocket Reconnect Window in Go Gateway
**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Lines**: 351-360
**Problem**: The reconnect window is hardcoded and might be too short (10s) for subway commutes or deep-offline scenarios, causing sessions to be prematurely cleaned up.
**Fix recommendation**: Make the window configurable and consider an exponential backoff for the cleanup timer.

---

## P2 Findings (Post-Launch)

### P2-1: Lack of Partial Conflict Resolution UI
**File**: `mobile/lib/core/offline/conflict_resolver.dart`
**Problem**: Currently, conflicts are resolved automatically using "last-write-wins" or "server-wins" strategies. There is no UI for users to manually resolve complex data conflicts.
**Fix recommendation**: Implement a conflict resolution screen for high-stakes data (like Goals).

---

## Verified Working (Strengths)

### V-1: Custom Branded Error UI
- `main.dart` overrides `ErrorWidget.builder` to use `CustomErrorWidget`.
- **Verdict**: Verified working.

### V-2: Isar Outbox & Sync Engine
- `mobile/lib/core/offline/sync_engine.dart` implements a professional outbox pattern with automatic retries and exponential backoff.
- **Verdict**: Verified working.

### V-3: Local Cognitive Queue Migration
- `main.dart` performs a migration from legacy Hive storage to the new Isar outbox on startup.
- **Verdict**: Verified working.

---

## Cross-Route Integration Issues
- **Offline Analytics**: Analytics events are queued in the same outbox as business data, which is correct.

---

## Code Quality Observations
- **Isar CodeGen**: The generated `local_database.g.dart` is massive (200k+ lines); consider splitting schemas if performance degrades.
