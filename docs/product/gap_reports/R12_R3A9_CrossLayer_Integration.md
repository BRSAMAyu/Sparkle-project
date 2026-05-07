# R12 / R3A9 — CrossLayer_Integration 二次深度审查
**Date**: 2026-05-07
**Scope**: Cross-Layer Integration
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: The project has a dual-track API strategy (gRPC for core AI, REST for social/supporting) that is inconsistently documented and partially implemented, leading to significant integration "ghosts".

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 2 |
| P1 (important gap, ship with plan) | 3 |
| P2 (nice to have, post-launch) | 2 |
| Verified working | 4 |

---

## R11 P0 验证
Verified that the gRPC/REST duplication mentioned in R11 persists. The community system remains REST-only despite the existence of `CommunityService` in proto.

---

## P0 Findings (Must Fix Before Launch)

### P0-1: 80% of GalaxyService gRPC Methods are Unimplemented "Ghosts"
**File**: `proto/galaxy_service.proto`, `backend/app/services/galaxy_grpc_service.py`, `backend/gateway/internal/galaxy/client.go`
**Problem**: The Protobuf definition defines 9 RPCs, but only 2 (`UpdateNodeMastery`, `SyncCollaborativeGalaxy`) are implemented in Python gRPC, and only 1 (`UpdateNodeMastery`) is implemented in the Go gRPC client.
**Evidence**: `backend/app/services/galaxy_grpc_service.py` lacks `GetUserGalaxy`, `GetNodeDetail`, etc. Go `backend/gateway/internal/galaxy/client.go` only has `UpdateNodeMastery`.
**Expected**: Contract should match implementation. Unimplemented methods should be implemented or removed from proto to avoid frontend confusion.
**Fix recommendation**: Implement the missing gRPC methods in Python and Go, or unify them under the REST proxy if gRPC is not required for these read-heavy ops.

### P0-2: Achievement Unlock Notification Type Mismatch (Broken Push)
**File**: `backend/app/services/notification_service.py`, `mobile/lib/core/navigation/shell_navigation.dart`
**Problem**: Python sends achievement notifications with `type: "notification"` and data nested inside, but Flutter's `MainNavigationShell` expects a top-level `type: "achievement_unlock"`.
**Evidence**: `NotificationService._push_notification_via_websocket` sets `message["type"] = "notification"`. Flutter `shell_navigation.dart:154` checks `if (type != 'achievement_unlock') return;`.
**Expected**: WS message type must match the expected handler type.
**Fix recommendation**: Update `NotificationService` to allow custom top-level types for specific high-priority events, or update Flutter to handle the generic `notification` type and route internally based on `notification_type`.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: CommunityService gRPC is Dead Code
**File**: `proto/community_service.proto`
**Problem**: The entire gRPC service is marked as deprecated in `grpc_server.py` but remains in the proto tree, misleading developers.
**Fix recommendation**: Remove the proto file or add a clear header comment about REST-only status.

### P1-2: WebSocketProxy Sanitization Risks for Binary Payloads
**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Problem**: The proxy attempts to JSON-sanitize any message with `websocket.TextMessage` type. If a developer accidentally sends binary data as text, the sanitizer might corrupt it.
**Fix recommendation**: Add a guard to check if the payload is valid JSON before attempting to decode and sanitize.

### P1-3: Missing DLQ visibility in Gateway
**File**: `backend/gateway/internal/handler/proxy_routes.go`
**Problem**: No endpoint exists in Go Gateway to check the health of Python's EventBus DLQs, making production monitoring harder.
**Fix recommendation**: Proxy the `dlq_health_check` endpoint to the Go Gateway.

---

## Verified Working (Strengths)

### V-1: Robust EventBus DLQ/Retry Logic
- `backend/app/core/event_bus.py` has excellent retry and persistence logic for failed events.
- **Verdict**: Verified working.

### V-2: Go Gateway REST Proxying
- `proxy_routes.go` and `handler/proxy.go` provide a stable and transparent bridge for the majority of the social features.
- **Verdict**: Verified working.

---

## Cross-Layer Integration Issues
- **Proto Sync**: Code generation (`make proto-gen`) is mandatory but not always checked in CI, leading to potential drift.

---

## Code Quality Observations
- **Type Safety**: Python gRPC services use `Any` too frequently in internal mappings.
- **Duplicate Logic**: `NotificationService` and `SystemUpdateService` have overlapping responsibilities for user alerts.
