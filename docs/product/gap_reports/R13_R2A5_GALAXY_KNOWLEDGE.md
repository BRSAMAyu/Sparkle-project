# R13 Audit Report: Galaxy + Knowledge System

> **Auditor**: Independent R13 Audit (2026-05-07)
> **Scope**: 3D Star Map, Node Interaction, Knowledge Search, Galaxy-Goal, gRPC/REST, Data Model, Edge Cases
> **Files Audited**: 40+ source files across Flutter/Go/Python layers

---

## Summary Table

| Area | Status | P0 | P1 | P2 |
|------|--------|----|----|-----|
| 1. Star Map Rendering | STRONG | 0 | 1 | 1 |
| 2. Node Interaction | GOOD | 0 | 1 | 1 |
| 3. Knowledge Search | GOOD | 1 | 1 | 0 |
| 4. Galaxy-Goal Association | GOOD | 0 | 1 | 0 |
| 5. gRPC vs REST Paths | ADEQUATE | 0 | 2 | 1 |
| 6. Knowledge Node Data | STRONG | 0 | 0 | 1 |
| 7. Edge Cases | ADEQUATE | 1 | 1 | 1 |
| **TOTAL** | | **1** | **7** | **5** |

---

## P0 Findings (Blocking)

### P0-1: GalaxyNode proto message omits critical fields (sector, importance, isUnlocked, position, sectorWeights, reviewUrgency, errorCount)

**Evidence**:
- `proto/galaxy_service.proto:97-103` -- `GalaxyNode` message has only: `node_id`, `label`, `node_type`, `mastery`, `tags`
- `mobile/lib/shared/entities/galaxy_model.dart:160-187` -- Flutter model expects: `importance`, `sector`, `isUnlocked`, `masteryScore`, `studyCount`, `recentErrorCount`, `reviewUrgencyScore`, `isReviewRecommended`, `positionX`, `positionY`, `sectorWeights`, `baseColor`, `glowColor`, `tags`, `description`, `parentId`
- `backend/app/services/galaxy_grpc_service.py:188-196` -- `GetUserGalaxy` only maps `node_id`, `label`, `node_type`, `mastery`, `tags`

**Impact**: When the Flutter client receives galaxy data via gRPC path (via `"via": "grpc"` in the response), it gets a severely truncated dataset. Nodes arrive without sector coloring (all land in `voidSector`), without importance (all default to 1), all appear locked (`isUnlocked=false`), and without position hints. This makes the gRPC fast-path produce a visually broken star map compared to the REST fallback path. The REST path returns full JSON from Python's `get_galaxy_graph()` which includes all fields.

**Severity**: The Flutter client transparently falls back to REST when gRPC fails (line 206 of `galaxy_handler.go`), and when gRPC succeeds the data is returned as JSON anyway (line 391-396). However, the gRPC data is missing ~15 fields that the painter relies on for correct visual rendering (sector colors, locked/unlocked states, importance-based sizing, mastery ring rendering, review pulse, error cluster indicator). This is a data completeness bug in the gRPC path.

---

## P1 Findings (Should Fix Before Launch)

### P1-1: PerformanceMonitor.getPerformanceReport() returns hardcoded stub data

**Evidence**:
- `mobile/lib/features/galaxy/data/services/galaxy_performance_monitor.dart:68-70`:
```dart
PerformanceReport getPerformanceReport() => PerformanceReport(
    frameCount: 100,
  );
```
- `averageFps`, `jankRate`, `averageFrameTimeMs` all default to 0/60 -- not measured
- `addEventListener` at line 63-65 is a no-op: `// Legacy integration: PerformanceService doesn't have events yet`

**Impact**: The `GalaxyPerformanceMonitor` is a facade that reports fake data. The actual frame timing is done inline in `_GalaxyScreenState._handleFrameTimings()` (galaxy_screen.dart:1930-1957) using `FrameTiming` directly, bypassing this monitor entirely. The monitor class exists but is not meaningfully integrated.

**File**: `mobile/lib/features/galaxy/data/services/galaxy_performance_monitor.dart:63-70`

---

### P1-2: Knowledge Search gRPC endpoint (SearchNodes) defined in proto but not implemented in Python gRPC service

**Evidence**:
- `proto/galaxy_service.proto:24` -- `rpc SearchNodes(SearchNodesRequest) returns (SearchNodesResponse);`
- `backend/app/services/galaxy_grpc_service.py` -- Only implements: `UpdateNodeMastery`, `SyncCollaborativeGalaxy`, `GetUserGalaxy`, `RecordNodeInteraction`
- Missing gRPC implementations: `SearchNodes`, `GetNodeDetail`, `GetLearningPath`, `GetNodeDependencies`, `GetGalaxyStats`, `GetRecommendedNodes`

**Impact**: 6 of 9 proto-defined RPCs are not implemented in the Python gRPC service. Search always goes through REST proxy to Python's `GET /galaxy/search`. This is not a runtime bug (REST fallback works), but represents a significant proto contract gap. The Go client (`galaxy/client.go`) only exposes 3 of the 9 RPCs (UpdateNodeMastery, GetUserGalaxy, RecordNodeInteraction), so the unimplemented ones can never be reached via gRPC.

**Files**: `proto/galaxy_service.proto:10-39`, `backend/app/services/galaxy_grpc_service.py:75-243`, `backend/gateway/internal/galaxy/client.go:65-90`

---

### P1-3: Search results from REST bypass Go-level validation -- query parameter not sanitized

**Evidence**:
- `backend/gateway/internal/handler/galaxy_handler.go:95-96`:
```go
galaxy.GET("/search", h.ProxyToBackend)
galaxy.POST("/search", h.ProxyToBackend)
```
- Both search endpoints use `ProxyToBackend` which only sets `X-User-ID` header and forwards raw
- No input validation or length limit on the `query` parameter before proxying to Python
- Python's `retrieval_service.py` uses the raw query string for both keyword and vector search

**Impact**: The search query reaches the Python backend unsanitized. While SQLAlchemy parameterizes SQL, the Redis search path and embedding service receive the raw string. A very long query could cause excessive embedding computation. A 2KB+ search query would still trigger embedding generation.

**File**: `backend/gateway/internal/handler/galaxy_handler.go:95-96`

---

### P1-4: GoalWorldGraph overlay provider has no error message displayed for non-empty failure states

**Evidence**:
- `mobile/lib/features/galaxy/presentation/widgets/goal_world_graph_mini_panel.dart:225-230` -- error state shows only a retry button:
```dart
error: (_, __) => Padding(
  ...
  child: OutlinedButton.icon(
    onPressed: () => ref.invalidate(goalGraphOverlayProvider(goalId)),
    icon: const Icon(Icons.refresh_rounded),
    label: Text(context.l10n.goalGraphRetry),
  ),
),
```
- The error object `_` is silently discarded -- no error message is shown to the user

**Impact**: If the goal graph endpoint fails, the user sees a bare retry button with no indication of what went wrong. The panel collapses to minimal size, making the retry button hard to discover.

**File**: `mobile/lib/features/galaxy/presentation/widgets/goal_world_graph_mini_panel.dart:248-256`

---

### P1-5: Collaborative session cleanup uses OrderedDict with size limit but no periodic sweep

**Evidence**:
- `backend/app/services/galaxy_grpc_service.py:25-26`:
```python
_MAX_ACTIVE_COLLABORATIVE_SESSIONS = 128
_COLLABORATIVE_SESSION_TTL = timedelta(minutes=30)
```
- `_prune_inactive_collaborative_sessions()` at line 43-54 is called only on `_get_active_collaborative_session()` (read access)
- No background task or timer sweeps stale sessions if the server is idle
- Sessions accumulate in `_active_collaborative_sessions` until the next read

**Impact**: Under heavy collaborative editing load followed by idle period, up to 128 sessions with their full Yjs document state remain in memory indefinitely until a new read triggers pruning. This is a slow memory leak in long-running gRPC server processes.

**File**: `backend/app/services/galaxy_grpc_service.py:43-73`

---

### P1-6: Tapped unlocked node navigation race condition -- pendingNavigationNodeId cleared on animation complete but not on widget dispose

**Evidence**:
- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart:1140-1145`:
```dart
if (nodeId != null) {
  unawaited(_openNodeDetailSheet(nodeId));
}
```
- `_pendingNavigationNodeId` is set on tap (line 1167) and consumed on animation complete
- If the widget is disposed during the tap feedback animation (e.g., route change), `_handleTapFeedbackStatus` fires on a disposed widget
- `mounted` check exists at line 1138 but `_openNodeDetailSheet` uses `context` which could be invalid in edge cases

**Impact**: Potential null context usage if screen is navigated away during tap feedback animation. Low probability but crashes on race.

**File**: `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart:1134-1145`

---

### P1-7: gRPC GalaxyNode message mastery field is int32 (0-100 range) but Python sends float (0.0-1.0) values from DB

**Evidence**:
- `proto/galaxy_service.proto:99` -- `int32 mastery = 4;`
- `backend/app/services/galaxy_grpc_service.py:193`:
```python
mastery=int(node.mastery * 100) if isinstance(getattr(node, 'mastery', 0), float) else getattr(node, 'mastery', 0),
```
- The conditional `isinstance(..., float)` check is fragile: if `mastery` is stored as `int` in the DB model, the multiplication by 100 is skipped, resulting in a value of 0-1 instead of 0-100
- `UserNodeStatus.mastery_score` is `Column(Float, default=0)` -- but Python may return it as int when value is 0

**Impact**: If mastery_score is 0 (common for new nodes), `isinstance(0, float)` returns `False`, so `int(0)` is returned correctly. But for values like `0.75`, `isinstance(0.75, float)` returns `True` and `int(0.75 * 100) = 75` is correct. However, if SQLAlchemy returns `Decimal` or `int` for round float values (e.g., `1.0`), the check fails and mastery=1 is sent instead of mastery=100.

**File**: `backend/app/services/galaxy_grpc_service.py:193`

---

## P2 Findings (Non-Blocking Improvements)

### P2-1: No offline caching of galaxy graph data for browsing without network

**Evidence**:
- `mobile/lib/core/offline/local_database.dart` -- Isar collections only include: `LocalCRDTSnapshot`, `OfflineChatMessage`, `FocusSessionRecord`, `TranslationRecord`, `VocabWord`
- No collection for `GalaxyGraphResponse` or `KnowledgeNode` data
- `mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart:30-33` -- SmartCache is in-memory only (LRU with 10-minute TTL)
- When network is unavailable, the in-memory cache may have stale data but is lost on app restart

**Impact**: User cannot browse their knowledge galaxy offline. The star map is entirely network-dependent. This is a known limitation but worth tracking for future offline mode.

---

### P2-2: StarMapPainter shouldRepaint comparison uses Map identity for large maps (positions, blendedColors)

**Evidence**:
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart:400-431`:
```dart
oldDelegate.positions != positions ||
...
oldDelegate.blendedColors != blendedColors ||
```
- These use `!=` on `Map<String, Offset>` and `Map<String, Color>` which is O(n) deep equality on every frame
- With 500 nodes, this is 500+ equality comparisons per frame for positions alone
- The `sceneVersion` counter could short-circuit most of these checks if reordered

**Impact**: Minor per-frame overhead. The `sceneVersion` check at line 405 already short-circuits most repaints, so this is only costly when scene changes. Could optimize by checking `sceneVersion` first and returning early.

**File**: `mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart:400-431`

---

### P2-3: Galaxy search is client-side filtered from loaded graph, not server-side vector search

**Evidence**:
- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart:1694`:
```dart
if (query.isEmpty) {
```
- Search filters `_nodesById` locally by name matching
- The server-side `/galaxy/search` endpoint (which uses pgvector + Redis hybrid search via `retrieval_service.py`) is only called through the REST proxy, not from the in-screen search panel
- `GalaxySearchPanel` receives pre-filtered `results` list from the screen state

**Impact**: Search only finds nodes already loaded in the current graph. If the user has 500+ nodes and the graph is aggregated at lower zoom, some nodes may not be in the loaded set. Server-side vector search (semantic similarity) is available but not wired to the in-galaxy search bar.

**File**: `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart:1694`

---

### P2-4: GalacticEventHandler `_handleFrameTimings` registered but never unregistered

**Evidence**:
- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart:189` -- `_consecutiveSlowFrames` tracking via `FrameTiming`
- Registration happens in `initState` but the `dispose` method would need to call `SchedulerBinding.instance.removeTimingsCallback`
- The callback captures `this` reference preventing GC if not removed

**Impact**: Minor memory concern. The screen uses `AutomaticKeepAliveClientMixin` so it stays alive in the navigation stack. If the screen IS properly disposed (on logout), the callback would leak until the next frame timing event.

---

### P2-5: No "why is this node important for my goal?" explanation in the GoalWorldGraph mini panel

**Evidence**:
- `mobile/lib/features/galaxy/presentation/widgets/goal_world_graph_mini_panel.dart:632-698` -- `_showNodeDetails` shows: nodeType, mastery, relationship, examWeight, difficulty, trainability, mistakes
- The `relationship` field from `focus_suggestions` is displayed but labeled generically
- No explicit "This node is important because it is a prerequisite for [goal-related-node]" or "Your goal requires understanding this concept for [reason]"
- The backend `aurora/spine/goal-graph/` endpoint provides `focus_suggestions` with `reason`/`relationship` fields, but the UI does not prominently surface the "why"

**Impact**: The GoalWorldGraph shows what nodes are bottlenecks/learned/mastered, but the "why" explanation is buried in the detail sheet's "Relationship" row. A user looking at a bottleneck node has to tap it, open the bottom sheet, and look for the relationship row to understand why it matters for their goal.

---

## Verified Working

### 1. Star Map Rendering Engine

**CustomPainter-based rendering** (not Unity/three_dart):
- `StarMapPainter` (`mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart`) -- Full CustomPainter implementation
- 5-level LOD system (`GalaxyLod.l0..l4`) with progressive detail reveal
- Node budget: 500 nodes / 800 edges max per frame (line 318-319)
- Spatial index (`GalaxySpatialIndex`) for viewport culling -- grid-based spatial hashing
- Label caching (`GalaxyLabelCache`) with 600-entry LRU
- Backdrop picture caching for static background elements
- Parallax star layers (3 layers) with twinkling animation
- Sector atmosphere rendering with nebula clouds and wedge boundaries
- 6 sectors: COSMOS, TECH, ART, CIVILIZATION, LIFE, WISDOM + VOID

### 2. Performance Management

**Adaptive degradation**:
- Real-time frame timing via `FrameTiming` callback (galaxy_screen.dart:1930)
- 5 consecutive slow frames triggers `_performanceDegraded = true`
- 30 consecutive fast frames recovers to normal
- Degraded mode reduces: star counts (65%), node budget (20-30%), disables glow/pulse effects
- Force-directed layout engine (`GalaxyForceEngine`) with physics simulation
- Build replay animation system with incremental playback plans

### 3. User Interactions

**Complete gesture handling** (`GalaxyGestureHandler`):
- Pan: camera movement with momentum/fling
- Zoom: pinch-to-zoom with focal point
- Tap: node selection + tap feedback animation -> detail sheet
- Double-tap: focus on node or zoom to region
- Long-press: node preview card OR empty-space upload menu
- Drag: reposition nodes with force engine anchoring

**Node states rendered**:
- Locked: dashed circle + "?" symbol, reduced opacity (line 1622-1648)
- Unlocked: filled circle with mastery-based coloring
- Mastery levels: <30 (dim), 30-60 (blue), 60-85 (green), 85+ (bright green with glow)
- Review pulse: yellow halo animation for review-recommended nodes
- Error cluster: red pulsing ring for nodes with recent errors (line 1663-1680)
- Importance >= 4: orbit ring; importance 5: rotating rays

### 4. Knowledge Search

**Dual-path search architecture**:
- Client-side: name/keyword filtering on loaded graph nodes
- Server-side: `KnowledgeRetrievalService` with Redis hybrid search + pgvector fallback + keyword fallback
- Search panel: `GalaxySearchPanel` with backdrop-filtered glassmorphism UI
- Results highlight matching nodes, dim non-matching (alpha: 0.14)

### 5. Galaxy-Goal Association

**GoalWorldGraph mini panel** (`GoalWorldGraphMiniPanel`):
- Fetches from `aurora/spine/goal-graph/{goalId}` endpoint
- Categorizes nodes: bottleneck (red), learning (teal), mastered (primary)
- Gap analysis summary: coverage %, bottleneck count, mastery average
- Toggle between full star map and goal-world mode (spotlights goal-related nodes)
- Empty state handled for no-goal and no-nodes scenarios

### 6. gRPC vs REST Architecture

**Go Gateway routing** (galaxy_handler.go):
- gRPC direct: `SparkNode` (RecordNodeInteraction), `UpdateMastery` (UpdateNodeMastery), `GetGraph` (GetUserGalaxy), `RecordStudy` (Go CQRS)
- REST proxy: All other endpoints (search, nodes, expansion, documents, sync, events SSE)
- gRPC fallback: All gRPC endpoints fall back to REST proxy on failure
- Cache invalidation: `invalidateGalaxyGraphCache` clears Redis on mastery updates

**Route count**: 40+ registered routes in `RegisterRoutes` (lines 68-141)

### 7. Knowledge Node Data Model

**Complete persistence** (backend/app/models/galaxy.py):
- `KnowledgeNode`: name, name_en, description, keywords, importance_level, exam_weight, difficulty, trainability, mistakes, sector_weights, position_x/y, embedding, source tracking, global_spark_count
- `UserNodeStatus`: mastery_score, bkt_mastery_prob, is_unlocked, study_count, total_minutes, is_favorite, decay_paused, next_review_at, revision (logical clock)
- `NodeRelation`: source_node_id, target_node_id, relation_type (12 types), strength
- `StudyRecord`: user_id, node_id, task_id, study_minutes, mastery_delta

**Relationship types**: prerequisite, derived, related, similar, contrast, application, example, explains, supports, contradicts, weakAt, parentChild -- all with distinct visual rendering (solid/dashed/tapered edges)

### 8. Empty State

**Handled** (galaxy_screen.dart:2860-2875):
- Loading state: animated panel with spinner and feature highlights
- Error state: retry button with error message
- Empty galaxy: action button to create first task, descriptive message with highlights
- Guard against premature empty display during initial load (line 415-420)

### 9. Build Replay System

**GalaxyBuildPlaybackPlan** with incremental animation:
- Node and edge reveal timing with staggered entrance
- Edge reveal trails with particle effects
- Position settling animation with blend interpolation
- Speed multiplier support for playback control

---

## Architecture Diagram

```
Flutter (galaxy_screen.dart)
  |-- CustomPaint(StarMapPainter) -- renders 2D canvas star map
  |-- GalaxyGestureHandler -- pan/zoom/tap/drag
  |-- GalaxySpatialIndex -- grid-based viewport culling
  |-- GalaxyForceEngine -- physics simulation
  |-- GalaxyLayoutEngine -- sector-based initial layout
  |-- GalaxySearchPanel -- local search filtering
  |-- GoalWorldGraphMiniPanel -- goal overlay
  |-- NodeDetailSheet -- bottom sheet on tap
  |
  v  REST (api_client)
Go Gateway (galaxy_handler.go)
  |-- gRPC path:  SparkNode -> RecordNodeInteraction
  |              UpdateMastery -> UpdateNodeMastery
  |              GetGraph -> GetUserGalaxy
  |              RecordStudy -> GalaxyCommandService (CQRS)
  |-- REST proxy: /galaxy/search, /galaxy/nodes, etc.
  |-- Redis cache: galaxy:graph:{userID}
  |
  v  gRPC (port 50051) / REST proxy (port 8000)
Python Engine
  |-- GalaxyGrpcServiceImpl -- 4 RPCs implemented
  |-- GalaxyService (facade) -- delegates to:
  |   |-- GraphStructureService (CRUD, relations)
  |   |-- KnowledgeRetrievalService (search, embedding)
  |   |-- GalaxyStatsService (spark, stats, prediction)
  |   |-- ReviewUrgencyService
  |   |-- ExpansionService
  |-- PostgreSQL: knowledge_nodes, user_node_status, node_relations, study_records
  |-- pgvector: semantic search on embeddings
  |-- Redis: hybrid search (FT.SEARCH) + cache
```
