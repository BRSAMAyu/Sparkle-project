# R11-R2A5: Knowledge Galaxy + Learning Experience End-to-End Audit

**Date**: 2026-05-07
**Audit Scope**: Galaxy Screen UI, Node Interaction, GoalWorldGraph Widget, Knowledge Node Backend, Error Book Completeness, Learning Flow, Data Integrity
**Severity Legend**: P0 = Launch-blocker, P1 = Degraded experience before launch, P2 = Post-launch fix

---

## Architecture Summary

```
Flutter GalaxyScreen (StarMapPainter + GoalWorldGraphMiniPanel)
    ↓ REST (Dio + SmartCache)
Go Gateway (GalaxyHandler) 
    ↙                    ↘
ProxyToBackend    gRPC (UpdateNodeMastery only)
    ↓                    ↓
Python REST API   Python gRPC Server
    ↓                    ↓
GalaxyService (Facade → Stats/Structure/Retrieval)
    ↓
PostgreSQL (knowledge_nodes, user_node_status, study_records, node_relations)
                              ↕ (outbox events → Redis Streams)
Event Bus (galaxy.node.updated, galaxy.mastery_updated, galaxy.error.created)
    ↓ SSE
Flutter GalaxyNotifier (live updates)
```

Error Book uses a separate path: Flutter → Dio → Go gRPC bridge → Python gRPC → ErrorBookService.

---

## P0 Findings (Launch Blockers)

### P0-1: Galaxy Graph API Has No gRPC Path -- Entirely REST-Proxied

**File**: `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/handler/galaxy_handler.go`, line 78
**Proto**: `/Users/brsama/code/GitHub/Sparkle-project/proto/galaxy_service.proto`, lines 10-16

**Current Code**:
```go
// galaxy_handler.go:78
galaxy.GET("/graph", h.ProxyToBackend)
```

**Proto (galaxy_service.proto)**: Only defines 2 RPCs:
```proto
service GalaxyService {
  rpc UpdateNodeMastery(UpdateNodeMasteryRequest) returns (UpdateNodeMasteryResponse);
  rpc SyncCollaborativeGalaxy(SyncCollaborativeGalaxyRequest) returns (SyncCollaborativeGalaxyResponse);
}
```

**Issue**: The main galaxy graph endpoint (`GET /galaxy/graph`) has no gRPC path. It proxies to Python REST via `httputil.ReverseProxy`. This means:
- No typed contract for the most critical galaxy endpoint
- No gRPC streaming for large graphs
- Potential performance bottleneck under load (ReverseProxy adds overhead per request)
- Error handling is opaque (no structured gRPC status codes)

**Expected**: `galaxy_service.proto` should define `rpc GetGraph(GetGraphRequest) returns (GalaxyGraphResponse)` and the GalaxyClient should implement a gRPC call path. The REST proxy should be a fallback, not the primary path.

**Fix**: 
1. Add `GetGraph` RPC to `proto/galaxy_service.proto`
2. Implement in Python gRPC service
3. Add `GetGraph` method to `backend/gateway/internal/galaxy/client.go`
4. Wire in `galaxy_handler.go` with proxy fallback

---

### P0-2: Spark Node Regression -- gRPC Path Disabled, No Study Data Persisted

**File**: `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/handler/galaxy_handler.go`, lines 137-175

**Current Code**:
```go
// galaxy_handler.go:170-174
// Keep spark on the REST path until gRPC has a dedicated study_minutes field/RPC.
// UpdateNodeMastery expects an absolute mastery score, so sending study_minutes there
// would overwrite progress with corrupted values.
c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
h.ProxyToBackend(c)
```

**Issue**: The SparkNode handler has a code-level TODO acknowledging that the gRPC path cannot be used because `UpdateNodeMastery` expects an absolute mastery score, not study minutes. The REST proxy path is used as an explicit workaround. However, there is no corresponding issue tracking this in the proto file -- `galaxy_service.proto` has no `SparkNode` RPC at all.

**Expected**: Add `rpc SparkNode(SparkNodeRequest) returns (SparkNodeResponse)` to the proto, with a `study_minutes` field. Implement in Python gRPC service (StatsService.spark_node exists), then wire Go client.

---

### P0-3: Galaxy Proto Is Incomplete -- Only 2 of ~30 Endpoints Have gRPC Coverage

**File**: `/Users/brsama/code/GitHub/Sparkle-project/proto/galaxy_service.proto`
**Go handler**: `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/handler/galaxy_handler.go`, lines 58-133

**Issue**: The Go galaxy handler registers ~30 routes (graph, search, stats, heatmap, predict, expansion, review, drafts, documents, chunks, events, sync, etc.), all of which proxy to the Python REST backend. The proto file defines only 2 RPCs. This violates the architectural invariant that "Flutter gets to Python through Go gRPC."

The GalaxyClient in Go only implements `UpdateNodeMastery`. Everything else is pure HTTP reverse proxy.

**Expected**: Proto should cover at minimum: GetGraph, SearchNodes, GetNodeDetail, SparkNode, PredictNextNode, GetStats, GetHeatmap, GetExpansionCandidates, ApplyExpansion, GetReviewSuggestions.

---

## P1 Findings (Pre-Launch Fixes)

### P1-1: GoalWorldGraph Overlay Not Linked to Galaxy Node Positions

**File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`, lines 2781-2790
**Provider**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/providers/goal_graph_overlay_provider.dart`

**Current Code**:
```dart
// galaxy_screen.dart:2781-2790
final activeGoalId = ref.watch(activeGoalHeaderProvider);
final goalOverlayData = activeGoalId != null
    ? ref.watch(goalGraphOverlayProvider(activeGoalId)).valueOrNull
    : null;
if (goalOverlayData != null && goalOverlayData.nodes.isNotEmpty) {
  _goalWorldNodeIds = goalOverlayData.nodes.map((n) => n.id).toSet();
} else {
  _goalWorldNodeIds = const <String>{};
  if (_isGoalWorldMode) _isGoalWorldMode = false;
}
```

**Issue**: When `_isGoalWorldMode` is toggled on, `_goalWorldNodeIds` contains goal-linked node IDs, but there is no visual differentiation code in the StarMapPainter to highlight these nodes with a distinct "goal world" visual treatment. The state is computed and stored but never consumed by the rendering layer beyond `_goalWorldNodeIds`. A grep through `star_map_painter.dart` shows no reference to goal world mode or the `_goalWorldNodeIds` set.

The GoalWorldGraphMiniPanel widget (positioned at top-right) shows the data in a sidebar panel, but the galaxy canvas itself does not visually distinguish goal-linked nodes from unlocked nodes. The vision requires "showing mastered vs need to conquer nodes" visually on the star map, not just in a sidebar.

**Expected**: The StarMapPainter should accept a `goalWorldNodeIds` parameter and apply a distinct glow/border treatment (e.g., gold ring for goal-linked nodes, red pulsing for bottlenecks). The `_isGoalWorldMode` flag should be piped through.

---

### P1-2: Node Preview/Detail Sheet Does Not Include Error Link Information

**File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart`
**File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/shared/entities/galaxy_model.dart`, lines 300-302

**Current Code**:
```dart
// galaxy_model.dart:300-302
/// Recent error count (last 14 days) — drives error cluster tint in star map
@JsonKey(name: 'recent_error_count')
final int recentErrorCount;
```

**Issue**: The `GalaxyNodeModel` has `recentErrorCount` and `reviewUrgencyScore` fields, but the `NodeDetailSheet` does not display recent error history or provide a direct link to filter the error book by this node. The `onViewErrors` callback is defined in the widget but is not wired from the galaxy screen (the galaxy screen calls `NodeDetailSheet.show` which does not pass `onViewErrors`).

**Expected**: `NodeDetailSheet.show()` should accept and pass `onViewErrors`. The galaxy screen should wire it to navigate to ErrorListScreen filtered by nodeId. Additionally, the detail sheet should display `recentErrorCount` and `reviewUrgencyScore` prominently.

---

### P1-3: Galaxy Graph Cache TTL Is Too Long for a Learning App

**File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart`, lines 31-33

**Current Code**:
```dart
final SmartCache<String, GalaxyGraphResponse> _graphCache = SmartCache(
  maxSize: 5,
  maxAge: const Duration(minutes: 10),
);
```

**Issue**: A 10-minute cache TTL for the galaxy graph means:
- After a user completes a study session (sparks a node), the mastery score in the cached graph is stale for up to 10 minutes
- The `refreshForTaskCompletion` method calls `_repository.clearCache()` but this only clears the Flutter-side cache -- if the SSE event arrives faster than the graph reload, there is a race condition
- The SSE event path (`_handleNodeUpdated`) does optimistic updates but only updates mastery scores, not `studyCount`, `recentErrorCount`, or `daysSinceMasteryUpdate`

**Expected**: Reduce maxAge to 2 minutes. Additionally, after spark/error events, call `clearCache()` before reloading.

---

### P1-4: Error Book Semantic Summary Endpoint Not Consumed by Flutter

**File**: `/Users/brsama/code/GitHub/Sparkle-project/proto/error_book.proto`, lines 19-20 (RPC defined)
**File**: `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/handler/error_book.go`, line 81 (route registered)
**File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/error_book/presentation/screens/error_detail_screen.dart` (does not reference semantic summary)

**Proto RPC**:
```proto
rpc GetErrorSemanticSummary(GetErrorRequest) returns (ErrorSemanticSummary);
```

**Issue**: The error book proto defines `GetErrorSemanticSummary` which returns linked concepts, strategies, and similar errors. The Go handler registers `GET /errors/:id/semantic`. However, the Flutter `ErrorDetailScreen` does not call this endpoint -- it only loads the basic error record. The semantic summary data (which provides the "why this happened" and "what to study next" context crucial for learning) is never displayed.

**Expected**: `ErrorDetailScreen` should call the semantic summary endpoint and display linked concepts, strategy nodes, and similar errors in a dedicated section. This is the core learning value of the error book.

---

### P1-5: Deprecated Mastery Methods Still Exist in GalaxyService (Clean Code Issue)

**File**: `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/galaxy_service.py`, lines 161-190

**Current Code**:
```python
async def handle_error_created(self, event_data: dict):
    """
    [DEPRECATED] Do NOT call — mastery is owned by ErrorBookMasterySyncService.
    Calling this will cause double mastery deductions.
    """
    logger.warning(...)
    return None

async def update_mastery_from_error(self, ...):
    """
    [DEPRECATED] Do NOT call — mastery is owned by ErrorBookMasterySyncService.
    Calling this will cause double mastery deductions.
    """
    logger.warning(...)
    return None
```

**Issue**: Two deprecated methods with logging warnings remain in the GalaxyService. The warnings suggest a recent ownership migration from GalaxyService to ErrorBookMasterySyncService, but the old methods were left as stubs rather than removed. This risks accidental calls from future developers who see the method names and don't read the docstring.

**Expected**: Remove these methods entirely. If backward compatibility is needed (for existing callers), keep for one more release cycle with a hard deprecation warning and scheduled removal date.

---

## P2 Findings (Post-Launch Fixes)

### P2-1: StudyRecords Table Underutilized in Go Write Path

**File**: `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/service/galaxy_command.go`, lines 338-410

**Issue**: The Go GalaxyCommandService has a `RecordStudy` method that writes to `study_records` and updates mastery. However, the Go handler routes call for spark/mastery go through either:
1. The Spark REST proxy (line 174 of galaxy_handler.go), which bypasses Go's command service entirely
2. The UpdateMastery gRPC path (line 218), which calls Python gRPC, not Go's RecordStudy

This means the Go-side `study_records` table may never get populated from the Flutter app's study sessions, because the Go command service is never called by the HTTP handler for spark/study operations.

**Expected**: Either remove the dead Go command service code or wire spark/study through it. Currently, the Python GalaxyService handles all write operations through its own DB session, so the Go-side study_records insert path is dead code in the normal user flow.

---

### P2-2: No End-to-End Error Book ↔ Galaxy Mastery Synchronization Test

**Files checked**:
- `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/test_phase4_galaxy_services.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/unit/test_error_book_mastery_sync_service.py`

**Issue**: The test files for galaxy services and error book mastery sync exist but test these in isolation. There is no integration test that verifies:
1. User creates an error record → error analysis runs → knowledge node mastery decreases → galaxy graph reflects the decrease → Flutter sees the update via SSE

This is the full learning feedback loop -- error impacts knowledge, which impacts the galaxy visualization. Without this test, regressions in the mastery sync pipeline can go undetected.

**Expected**: Add an integration test in `tests/test_phase4_galaxy_services.py` or a new file that exercises the full create-error → analyze → mastery-sync → galaxy-graph-refresh chain.

---

### P2-3: Galaxy Model JSON Deserialization Has Fragile Field Name Matching

**File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/shared/entities/galaxy_model.dart`, lines 189-268

**Current Code**:
```dart
// galaxy_model.dart:189-267 (GalaxyNodeModel.fromJson)
final userStatus = json['user_status'] as Map<String, dynamic>?;
// ...
masteryScore: GalaxyNodeModel._readMasteryScore(
  json['mastery_score'] ?? userStatus?['mastery_score'],
),
studyCount: (GalaxyNodeModel._readStudyCount(json, 'study_count') as num?)?.toInt() ?? 0,
recentErrorCount: ((userStatus?['recent_error_count'] ?? json['recent_error_count']) as num?)?.toInt() ?? 0,
```

**Issue**: The fromJson method tries both root-level and `user_status`-nested fields with fallback chains using `??`. This is fragile because:
1. If the backend changes the response structure (flattened vs nested), the deserialization silently falls back to defaults (0 mastery, false unlocked)
2. There's no warning or error when fields are missing or incorrectly shaped
3. The `_readMasteryScore` method silently returns 0 for NaN or null values

**Expected**: Add `assert()` or logging when fields are missing from both locations. Or better, standardize on one response format and enforce it via backend schema.

---

### P2-4: Error Book AddErrorScreen Not Connected to OCR Pipeline for Image Questions

**File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/error_book/presentation/screens/add_error_screen.dart`
**Backend**: `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/ocr_service.py`

**Issue**: The add_error_screen allows uploading question images, but there's no explicit trigger for OCR in the mobile flow. The backend `ErrorBookService.create_error` does not call `ocr_service` either. OCR is only referenced in the error analysis path (`analyze_and_link`). This means image-only error entries may lack extracted text for search and analysis until the background analysis task runs.

**Expected**: The create_error flow should either trigger OCR synchronously or make it clear in the UI that OCR processing will happen in the background.

---

### P2-5: Galaxy Screen Hardcoded Dark Theme (Always Dark Mode)

**File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`, line 110, 2761

```dart
static const bool _useDarkGalaxyTheme = true;  // line 110
const backgroundColor = isDarkMode ? Color(0xFF060A12) : Color(0xFFF5F6F8);  // line 2761
```

**Issue**: The `_useDarkGalaxyTheme` is a compile-time constant set to `true`, meaning the galaxy always renders in dark mode regardless of the system theme setting. The light mode branch (`Color(0xFFF5F6F8)`) exists but is unreachable. This violates the system-level theme preference.

**Expected**: Either make this a user setting (persisted in GalaxyDisplaySettings) or respect the system theme. The StarMapPainter may need light-mode variants for all its colors.

---

### P2-6: Error ErrorRecord.affectedNodeId Exists in Proto But Not in Flutter Model

**File**: `/Users/brsama/code/GitHub/Sparkle-project/proto/error_book.proto`, lines 68-69
**Flutter model**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/error_book/data/models/error_record.dart`

**Proto**:
```proto
optional string affected_node_id = 19;
optional double mastery_delta = 20;
```

**Issue**: The proto defines `affected_node_id` and `mastery_delta` as optional fields for the ErrorRecord response. These fields are critical for the error→galaxy feedback loop (showing which knowledge node was affected and by how much). If the Flutter ErrorRecord model doesn't parse these (need to verify), the error card cannot display the affected knowledge node link, which is essential for the "tap error → see affected galaxy node" user flow.

**Expected**: Verify Flutter ErrorRecord.fromJson parses `affected_node_id` and `mastery_delta`. Wire the error card's `onKnowledgeNodeTap` to navigate to galaxy with that node highlighted.

---

## Data Flow Traces

### Tap → Widget → Provider → API → Backend → Database → Response

**Flow 1: Galaxy Graph Load**
```
User opens Galaxy tab
  → GalaxyScreen.build() / initState() → _loadGraph()
  → GalaxyNotifier.loadGalaxy(forceRefresh: false)
  → EnhancedGalaxyRepository.getGraph(zoomLevel: 1.0)
  → SmartCache check (10-min TTL) → if miss:
      ApiClient.get(ApiEndpoints.galaxyGraph, queryParameters: {'zoom_level': 1.0})
  → HTTP GET /api/v1/galaxy/graph → Go Gin Router → GalaxyHandler.ProxyToBackend()
  → httputil.ReverseProxy → Python FastAPI galaxy.py → GalaxyService.get_graph()
  → SQL: SELECT * FROM knowledge_nodes + JOIN user_node_status + JOIN node_relations
  → GalaxyGraphResponse(nodes: [...], edges: [...], userFlameIntensity: 0.0)
  → JSON response → Go proxy → Flutter Dio → GalaxyGraphResponse.fromJson()
  → GalaxyNotifier state update → setState() → StarMapPainter re-render
```
**Status**: WORKING. Cache TTL is long (P1-3). No gRPC path (P0-1).

**Flow 2: Node Tap → Detail Sheet**
```
User taps node on galaxy canvas
  → GestureHandler → _handleTapCommand(GalaxyCommand.toggleSelect)
  → _handleNodeTap(nodeId) → GalaxyNotifier.selectNode(nodeId)
  → state.copiedWith(selectedNodeId: nodeId, expandedEdgeNodeIds: ...)
  → _recalculateVisibility() → StarMapPainter re-render (node highlighted)
  → NodeDetailSheet.show(context, nodeId, nodeLabel)
  → _loadHistory() → EnhancedGalaxyRepository.getNodeHistory(nodeId)
  → HTTP GET /api/v1/galaxy/node/:id/history → Go proxy → Python
```
**Status**: WORKING. Error link callback not wired (P1-2).

**Flow 3: Spark Node (Study)**
```
User taps "spark" on node detail or completes a task linked to this node
  → GalaxyNotifier.sparkNode(id)
  → EnhancedGalaxyRepository.sparkNode(id)
  → HTTP POST /api/v1/galaxy/node/:id/spark {study_minutes: N}
  → Go GalaxyHandler.SparkNode() → ProxyToBackend() [REST fallback, NOT gRPC]
  → Python spark_node() → StatsService.spark_node()
  → INSERT/UPDATE user_node_status (mastery_score += delta)
  → Publish event to outbox → Redis Streams → SSE to Flutter
  → GalaxyNotifier._handleNodeUpdated() → optimistic update
```
**Status**: WORKING but fragile. REST proxy only, no gRPC (P0-2).

**Flow 4: Error Book Create → Analyze → Mastery Update**
```
User creates error entry (AddErrorScreen)
  → ErrorBookRepository.createError(...)
  → HTTP POST /errors → Go ErrorBookHandler.CreateError()
  → gRPC Python ErrorBookGrpcService.CreateError()
  → ErrorBookService.create_error() → INSERT error_records
  → Background task: analyze_and_link(error_id, user_id)
    → LLM analysis (error_type, root_cause, correct_approach)
    → Knowledge RAG search → link to knowledge nodes
    → ErrorBookMasterySyncService.update_mastery() [NOT GalaxyService]
    → UPDATE user_node_status (mastery_score delta)
    → Publish galaxy.error.created event
  → SSE to Flutter → GalaxyNotifier._handleErrorCreated()
    → setEvidenceHighlight(linkedNodeIds)
    → loadGalaxy(forceRefresh: true) [reloads entire graph]
```
**Status**: WORKING. Mastery sync correctly routed through ErrorBookMasterySyncService. Full graph reload on every error creation is expensive (should be incremental).

**Flow 5: Goal World Graph (Learning Gap Analysis)**
```
GoalGraphMiniPanel loads on Galaxy screen
  → GoalGraphOverlayProvider(goalId) fetches gap analysis
  → HTTP GET /api/v1/goals/:id/knowledge-gap → Go proxy → Python
  → Returns GoalGraphOverlayData { bottleneckNodes, learningNodes, masteredNodes }
  → Displays in panel: gaps, bottlenecks, mastery coverage
  → _isGoalWorldMode toggle sets _goalWorldNodeIds (but not used by painter)
```
**Status**: WORKING for sidebar display. Visual integration missing (P1-1).

**Flow 6: Error Review (SM-2 Spaced Repetition)**
```
User enters Review screen
  → ReviewScreen loads today's reviews or selected mode
  → ErrorBookRepository.getErrors(needReview: true)
  → HTTP GET /errors?need_review=true → Go → gRPC → Python
  → ErrorBookService uses ReviewSchedulerService (SM-2 algorithm)
  → User answers (remembered/fuzzy/forgotten)
  → SubmitReview POST /errors/:id/review
  → SM-2: new_ef, new_interval, next_review_at calculated
  → UPDATE error_records SET mastery_level, easiness_factor, next_review_at
```
**Status**: WORKING. SM-2 algorithm correctly implemented with EF bounds and interval calculation.

---

## Data Integrity Checks

| Table | Check | Status |
|-------|-------|--------|
| `knowledge_nodes` | Has position_x, position_y, exam_weight, difficulty, trainability, mistakes, sector_weights | PASS |
| `user_node_status` | Composite PK (user_id, node_id), revision for conflict resolution | PASS |
| `study_records` | Separate table for study session logging | PASS |
| `node_relations` | Tracks edges with relation_type and strength | PASS |
| `error_records` | Has mastery_level, easiness_factor, next_review_at for SM-2 | PASS |
| `event_outbox` | Used for CQRS event sourcing (mastery events) | PASS |
| HNSW index | `idx_knowledge_nodes_embedding_hnsw` on vector(1024) | PASS |
| Indexes | position_x, position_y, parent_id, dominant_sector_code, status | PASS |

---

## Learning Flow Completeness Assessment

| Vision Requirement | Implementation Status | Gap |
|-------------------|-----------------------|-----|
| Galaxy ties to user goals | GoalGraphOverlayProvider exists + panel displayed | P1-1: No visual integration on canvas |
| "Mastered" vs "need to conquer" nodes | masteryScore on GalaxyNodeModel, bottleneck classification | P1-1: Goal world mode doesn't affect rendering |
| Node interaction (tap→detail) | NodeDetailSheet with history, sources | P1-2: Error link not wired |
| Error book (错题本) | Full CRUD, SM-2 review, analysis, knowledge linking | P1-4: Semantic summary not consumed by Flutter |
| Error → Galaxy feedback | SSSE events update galaxy on error creation | PASS (but full graph reload is heavy) |
| Knowledge search | GalaxySearchPanel + RetrievalService | PASS |
| Node expansion | ExpansionService + LLM ontology generation | PASS |
| Predictive next node | GalaxyStatsService.predict_next_node | PASS |
| Collaborative galaxy | CRDT-based Yjs sync via gRPC | NOT VERIFIED (out of scope) |

---

## Severity Summary

| Finding | Severity | Effort |
|---------|----------|--------|
| P0-1: Galaxy graph has no gRPC path | P0 | M (proto + impl) |
| P0-2: Spark node gRPC path disabled | P0 | S (proto field + wire) |
| P0-3: Galaxy proto covers only 2/30 endpoints | P0 | L (systematic proto expansion) |
| P1-1: Goal world mode not visually rendered | P1 | S (pass set to painter) |
| P1-2: NodeDetailSheet missing error link | P1 | S (wire callback) |
| P1-3: Galaxy cache TTL too long (10 min) | P1 | S (change constant) |
| P1-4: Error semantic summary not consumed | P1 | S (add API call + UI) |
| P1-5: Deprecated mastery methods remain | P1 | S (remove methods) |
| P2-1: Dead Go study_records write path | P2 | S (remove or wire) |
| P2-2: No E2E error→galaxy mastery test | P2 | M (integration test) |
| P2-3: Fragile JSON deserialization | P2 | S (add assertions) |
| P2-4: OCR not triggered on error creation | P2 | S (add OCR call) |
| P2-5: Galaxy always dark mode | P2 | M (theme support) |
| P2-6: Error affected_node_id not in Flutter model | P2 | S (add fields) |

**Total**: 3 P0, 5 P1, 6 P2 | Estimated total effort: ~5-7 developer-days

---

## Recommendation

The galaxy experienced system is functionally complete but has two structural gaps: (1) the galaxy proto file has not kept pace with the REST API, making the gRPC path impossible for most operations, and (2) the GoalWorldGraph (goal-linked knowledge visualization) exists as a data pipeline and sidebar panel but does not visually render on the star map canvas. Fixing P0-1 through P0-3 before launch is strongly recommended.
