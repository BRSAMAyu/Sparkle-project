# R12 / R2A5 — Galaxy_Knowledge 二次深度审查
**Date**: 2026-05-18
**Scope**: Galaxy + Knowledge
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: The implementation aligns with the vision but suffers from architectural technical debt (REST over gRPC) and some missing visual integrations on the Flutter side.

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 3 |
| P1 (important gap, ship with plan) | 5 |
| P2 (nice to have, post-launch) | 3 |
| Verified working | 6 |

---

## R11 P0 验证
1. **Galaxy Graph gRPC Path**: Not fixed. Still entirely REST-proxied in `galaxy_handler.go`.
2. **Spark Node gRPC Path**: Not fixed. Still uses a REST workaround because `UpdateNodeMastery` expects absolute score, not delta.
3. **Incomplete Proto**: Not fixed. `galaxy_service.proto` still only contains `UpdateNodeMastery` and `SyncCollaborativeGalaxy`.

---

## P0 Findings (Must Fix Before Launch)

### P0-1: Galaxy Graph API Has No gRPC Path
**File**: `backend/gateway/internal/handler/galaxy_handler.go`
**Lines**: 78
**Problem**: The main galaxy graph endpoint (`GET /galaxy/graph`) has no gRPC path. It proxies to Python REST.
**Evidence**: `galaxy.GET("/graph", h.ProxyToBackend)`
**Expected**: `galaxy_service.proto` should define `rpc GetGraph`.
**Fix recommendation**: Add `GetGraph` RPC, implement in Python, wire Go client.

### P0-2: Spark Node Regression -- gRPC Path Disabled
**File**: `backend/gateway/internal/handler/galaxy_handler.go`
**Lines**: 170-174
**Problem**: SparkNode handler explicitly uses REST proxy as a workaround because gRPC path lacks `study_minutes`.
**Evidence**: `// Keep spark on the REST path until gRPC has a dedicated study_minutes field/RPC.`
**Expected**: Add `rpc SparkNode` to proto with `study_minutes`.
**Fix recommendation**: Add proto field and wire to Python `StatsService.spark_node`.

### P0-3: Galaxy Proto Is Incomplete
**File**: `proto/galaxy_service.proto`
**Lines**: 10-16
**Problem**: Proto defines only 2 RPCs while Go handler proxies ~30 endpoints to REST.
**Evidence**: See `galaxy_handler.go` routing block vs `galaxy_service.proto`.
**Expected**: Proto should cover core galaxy endpoints.
**Fix recommendation**: Expand proto definition.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: GoalWorldGraph Overlay Not Visually Linked
**File**: `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`
**Lines**: 2926
**Problem**: `_goalWorldNodeIds` are passed to `spotlightNodeIds` when `_isGoalWorldMode` is active, but visual differentiation (e.g. gold ring) is missing from `StarMapPainter`.
**Evidence**: `spotlightNodeIds` only change opacity/brightness, lacks specific "goal world" treatment.
**Expected**: Goal nodes should have clear visual indicators.
**Fix recommendation**: Enhance `StarMapPainter` to distinguish goal nodes visually.

### P1-2: Node Preview/Detail Sheet Missing Error Link
**File**: `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`
**Lines**: 1442-1448
**Problem**: `NodeDetailSheet.show` is called without providing the `onViewErrors` callback.
**Evidence**: `onViewErrors` is omitted in the arguments to `NodeDetailSheet.show`.
**Expected**: `onViewErrors` should be wired to navigate to ErrorListScreen.
**Fix recommendation**: Wire the callback to route to the error list.

### P1-3: Galaxy Graph Cache TTL Too Long
**File**: `mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart`
**Lines**: 30-33
**Problem**: 10-minute TTL for `SmartCache` causes stale mastery and study counts.
**Evidence**: `maxAge: const Duration(minutes: 10)`
**Expected**: Reduce TTL.
**Fix recommendation**: Change to 2 minutes and clear cache on SSE events.

### P1-4: Error Book Semantic Summary Not Consumed
**File**: `mobile/lib/features/error_book/presentation/screens/error_detail_screen.dart`
**Lines**: 145-147
**Problem**: `SemanticSummary` section is commented or missing data integration. 
**Evidence**: `errorSemanticSummaryProvider` is watched, but UI display is partial.
**Expected**: Display linked concepts and similar errors.
**Fix recommendation**: Properly render the fetched semantic summary.

### P1-5: Deprecated Mastery Methods in GalaxyService
**File**: `backend/app/services/galaxy_service.py`
**Lines**: 161-190
**Problem**: `handle_error_created` and `update_mastery_from_error` are deprecated but still present.
**Evidence**: `[DEPRECATED] Do NOT call` in docstrings.
**Expected**: Removed to avoid accidental double deductions.
**Fix recommendation**: Delete methods.

---

## P2 Findings (Post-Launch)

### P2-1: StudyRecords Table Underutilized
**File**: `backend/gateway/internal/service/galaxy_command.go`
**Lines**: 338
**Problem**: `RecordStudy` writes to `study_records` but is never called because Spark uses REST.
**Evidence**: REST handler uses `ProxyToBackend`.
**Expected**: HTTP handlers should use Go command service or remove it.
**Fix recommendation**: Wire Spark through Go `RecordStudy`.

### P2-2: Fragile JSON Deserialization
**File**: `mobile/lib/shared/entities/galaxy_model.dart`
**Lines**: 189-267
**Problem**: `??` fallbacks hide missing fields and schema changes.
**Evidence**: `json['mastery_score'] ?? userStatus?['mastery_score']`
**Expected**: Strict parsing.
**Fix recommendation**: Add assertions.

### P2-3: Missing E2E Integration Test for Error -> Galaxy Mastery
**File**: `backend/tests/`
**Problem**: No integration test covers the full loop from error creation to mastery update in galaxy.
**Evidence**: `test_error_loop.py` tests logic in isolation with mocks.
**Expected**: A true E2E DB-backed test.
**Fix recommendation**: Implement the test.

---

## Verified Working (Strengths)
### V-1: Error to Galaxy Loop Event Publishing
- Checked `test_error_loop.py` showing `error_created` events properly published to EventBus.
- **Verdict**: PASS

### V-2: SM-2 Spaced Repetition Algorithm
- Logic is correctly implemented in `ReviewSchedulerService`.
- **Verdict**: PASS

### V-3: Knowledge Search Vector Retrieval
- HNSW index exists on `knowledge_nodes_embedding_hnsw` and is utilized.
- **Verdict**: PASS

### V-4: Goal World Graph Panel Data
- Panel successfully fetches and models gap analysis data (`GoalGraphOverlayData`).
- **Verdict**: PASS

### V-5: SSE Event Stream for Live Updates
- Flutter `GalaxyNotifier` correctly registers and listens for live updates via SSE.
- **Verdict**: PASS

### V-6: DB Schema Integrity
- PostgreSQL schema has correct constraints for `user_node_status` and composite keys.
- **Verdict**: PASS

---

## Cross-Route Integration Issues
The primary issue remains the disjointed API paths: some critical high-volume updates bypass the planned gRPC/Go command patterns and rely on legacy Python REST proxies, splitting the source of truth and potentially breaking caching and event sourcing in the Go layer.

---

## Code Quality Observations
The codebase contains several instances of "TODOs" and commented out workarounds (e.g. in `galaxy_handler.go`) to bypass architectural rules due to mismatched data shapes between frontend and backend. These need to be resolved.
