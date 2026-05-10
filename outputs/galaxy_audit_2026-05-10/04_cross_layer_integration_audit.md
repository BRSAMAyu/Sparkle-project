# Cross-Layer Integration Audit: Knowledge Galaxy System

**Date**: 2026-05-10
**Auditor**: Integration Audit Agent
**Scope**: 5 cross-layer flows spanning Flutter -> Go -> Python -> DB -> Event Bus -> Back

---

## Executive Summary

All 5 flows were traced end-to-end across the stack. The system is **well-structured** with consistent mastery scale (0-100), proper event-driven decoupling, and correct proto field types. However, **4 verified issues** and **2 minor observations** were found.

| Flow | Status | Issues |
|------|--------|--------|
| Flow 1: Mastery Update | PASS with observation | 0 critical, 1 observation |
| Flow 2: Get User Galaxy | FAIL | 2 verified issues (1 HIGH, 1 MEDIUM) |
| Flow 3: Error Created -> Mastery Impact | FAIL | 1 verified issue (MEDIUM) |
| Flow 4: Document Upload -> Knowledge Nodes | PASS with issue | 1 verified issue (MEDIUM), 1 observation |
| Flow 5: Community Sharing -> Knowledge Base | PASS | 0 issues |

---

## Flow 1: Mastery Update (Flutter -> Go -> Python -> DB -> Event -> Back)

### Trace

1. **Flutter** (`mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart`, line 221-262):
   - Sends `POST /galaxy/nodes/$id/mastery` with JSON body `{"mastery": int, "reason": string}`
   - Mastery parameter typed as `required int mastery` (0-100 integer scale)
   - Endpoint: `ApiEndpoints.galaxyUpdateMastery(nodeId)` -> `'/galaxy/nodes/$id/mastery'`

2. **Go Gateway** (`backend/gateway/internal/handler/galaxy_handler.go`, line 214-286):
   - Handler: `UpdateMastery` registered on `galaxy.POST("/nodes/:id/mastery")` (line 75)
   - Parses JSON body: `Mastery int` (Go int, line 228)
   - Calls gRPC client: `h.galaxyClient.UpdateNodeMastery(ctx, userID, nodeID, int32(req.Mastery), time.Now(), req.Reason)` (line 253-259)
   - Converts `int` -> `int32` for proto compatibility. No data loss since mastery is 0-100.

3. **Go gRPC Client** (`backend/gateway/internal/galaxy/client.go`, line 65-75):
   - `UpdateNodeMastery` sends `UpdateNodeMasteryRequest{UserId, NodeId, Mastery int32, Revision, Reason}`
   - Mastery field is `int32` matching proto definition.

4. **Proto** (`proto/galaxy_service.proto`, line 62-80):
   - `UpdateNodeMasteryRequest.mastery` is `int32` (line 65)
   - `UpdateNodeMasteryResponse.old_mastery` is `int32` (line 75)
   - `UpdateNodeMasteryResponse.new_mastery` is `int32` (line 76)

5. **Python gRPC Service** (`backend/app/services/galaxy_grpc_service.py`, line 79-167):
   - Receives `request.mastery` as int
   - Passes to `GalaxyService.update_node_mastery(new_mastery=request.mastery)` (line 96)
   - `update_node_mastery` (`backend/app/services/galaxy_service.py`, line 3009-3034) clamps to `0.0-100.0` as float
   - DB column `UserNodeStatus.mastery_score` is `Float` (`backend/app/models/galaxy.py`, line 237)
   - Response converts back: `int(result.get("old_mastery", 0))`, `int(result.get("new_mastery", 0))` (line 157-158)

6. **DB** (`backend/app/models/galaxy.py`, line 237):
   - `mastery_score = Column(Float, default=0)` -- stored as float in DB

7. **Event publication** (`backend/app/services/galaxy/stats_service.py`, line 115-128):
   - After `spark_node` commits, publishes `node_mastery_updated` event
   - Event values: `old_mastery=int(old_mastery)`, `new_mastery=int(status.mastery_score)`

### Findings

**Mastery Scale Consistency: PASS**
- Flutter sends 0-100 int -> Go converts to int32 -> Proto is int32 -> Python clamps to 0-100 float -> DB stores as float -> Response converts back to int32
- No data loss: mastery range (0-100) fits comfortably in int32 (max ~2.1 billion)

**Proto field type (int32 vs float): NO DATA LOSS**
- The proto uses `int32` for mastery, while the DB stores `Float`. The Python gRPC service converts `float -> int` at the response boundary (line 157-158: `int(result.get(...))`). Since mastery is always in 0-100 integer range at the API level, this truncation is intentional and correct. The internal `GalaxyStatsService.spark_node` computes mastery deltas as floats (line 56: `status.mastery_score = min(status.mastery_score + mastery_delta, self.MAX_MASTERY)`) but the `MAX_MASTERY = 100.0` clamp and `int()` conversion at the response boundary prevent fractional values from leaking.

**Observation [OBS-1]: spark_node internal float precision**
- `GalaxyStatsService.spark_node` (`backend/app/services/galaxy/stats_service.py`, line 49) calculates `mastery_delta` as a float (line 438-441: `BASE_MASTERY_POINTS * time_factor * difficulty_factor`). This means `mastery_score` in DB can be a non-integer float (e.g., 47.3). When converted to int32 for gRPC response, this truncates (not rounds). However, `int(47.3)` = 47, not 48. The gRPC service uses `int()` (which truncates toward zero), not `round()`. This is consistent across all conversion points but means the user might see "47%" when the internal state is "47.7%". This is cosmetic, not a data integrity issue.

---

## Flow 2: Get User Galaxy (DB -> Python -> gRPC -> Go -> Flutter)

### Trace

1. **Python gRPC** (`backend/app/services/galaxy_grpc_service.py`, line 221-260):
   - Calls `GalaxyService.get_galaxy_graph(user_id)` (line 226)
   - Returns `GetUserGalaxyResponse` with `repeated GalaxyNode` (line 230-238)

2. **Mastery population** (line 235):
   ```python
   mastery=int(node.mastery * 100) if isinstance(getattr(node, 'mastery', 0), float) else getattr(node, 'mastery', 0),
   ```
   - This tries to convert from 0-1 float to 0-100 int. BUT `NodeWithStatus` from `get_galaxy_graph` stores mastery in `user_status.mastery_score` on the 0-100 scale. The `NodeWithStatus` class (inherits from `NodeBase`) does NOT have a direct `.mastery` attribute.

3. **Tags/Keywords mapping**:
   - The `GalaxyNode.tags` proto field (line 102: `repeated string tags`) is populated from `getattr(node, 'tags', []) or []` (galaxy_grpc_service.py line 236).
   - In `NodeWithStatus` (schema), `tags` comes from `_build_auto_tags(node, sector_code)` which reads `node.keywords` from the `KnowledgeNode` model (`backend/app/schemas/galaxy.py`, line 555-588).
   - The REST path serializes `tags` directly from the schema's `tags` field (built from `keywords`).
   - The gRPC path reads `tags` attribute which exists on `NodeWithStatus` via its parent `NodeBase` (schema line 231: `tags: list[str]`).

4. **Go Gateway** (`backend/gateway/internal/handler/galaxy_handler.go`, line 517-542):
   - `GetGraph` handler calls `GetUserGalaxy` gRPC
   - Returns JSON with `nodes`, `edges`, `total_nodes`
   - Go passes through the gRPC response directly as JSON

5. **Flutter** (`mobile/lib/shared/entities/galaxy_model.dart`, line 189-268):
   - `GalaxyNodeModel.fromJson` reads:
     - `mastery_score`: via `_readMasteryScore` (line 218-220, 366-373) which auto-detects 0-1 vs 0-100 scale and normalizes to 0-100 int
     - `tags`: reads `json['auto_tags'] ?? json['tags'] ?? json['keywords']` (line 249) -- handles all possible field names

### Findings

**VERIFIED ISSUE [ISSUE-F2-1] [HIGH]: GetUserGalaxy gRPC always returns mastery=0 for all nodes**

- **File**: `backend/app/services/galaxy_grpc_service.py`, line 235
- **Root cause**: `getattr(node, 'mastery', 0)` looks for attribute `mastery` on `NodeWithStatus`, which does not exist. It falls back to `0`. The actual mastery is at `node.user_status.mastery_score` (if status exists).
- **Trace of the code path**:
  1. `get_galaxy_graph()` returns `GalaxyGraphResponse` with `nodes: list[NodeWithStatus]`
  2. Each `NodeWithStatus` has `user_status: UserStatusInfo | None` containing `mastery_score: float` (0-100)
  3. The gRPC code does `getattr(node, 'mastery', 0)` -- `NodeWithStatus` has no `.mastery` attribute -> returns 0
  4. `isinstance(0, float)` is `False` -> takes else branch -> `getattr(node, 'mastery', 0)` -> returns 0
- **Impact**: When the Go gateway uses the gRPC path for `GET /galaxy/graph`, all nodes appear with mastery=0 in the Flutter client. The REST fallback path works correctly because it serializes the full `GalaxyGraphResponse` JSON directly.
- **Fix**: Change line 235 to read mastery from the correct path:
  ```python
  mastery = int(node.user_status.mastery_score) if node.user_status else 0
  ```

**VERIFIED ISSUE [ISSUE-F2-2] [MEDIUM]: GetNodeDetail returns wrong mastery scale**

- **File**: `backend/app/services/galaxy_grpc_service.py`, line 318
- **Code**: `mastery=int(stats.mastery_score * 100) if stats and hasattr(stats, 'mastery_score') else 0`
- **Root cause**: `stats.mastery_score` from `get_node_knowledge_stats` is already on the 0-100 scale (same as `UserNodeStatus.mastery_score`). Multiplying by 100 produces values 0-10000 instead of 0-100.
- **Impact**: Via gRPC `GetNodeDetail`, mastery values are 100x too large (e.g., 75% mastery appears as 7500). The Go gateway passes this through to Flutter, where `_readMasteryScore` would interpret 7500 as 7500% and clamp to 100, so the user sees 100% for any node with mastery > 1.0.
- **Fix**: Remove the `* 100` multiplication:
  ```python
  mastery=int(stats.mastery_score) if stats and hasattr(stats, 'mastery_score') else 0
  ```

**Tags/Keywords mapping: PASS**
- REST path: `KnowledgeNode.keywords` -> `_build_auto_tags()` -> schema `tags` field -> JSON `tags` -- works correctly
- gRPC path: `getattr(node, 'tags', []) or []` -- `NodeWithStatus.tags` is populated by `_build_auto_tags` which reads from `node.keywords` -- works correctly
- Flutter fallback: reads `auto_tags`, `tags`, or `keywords` (line 249) -- defensive and correct

---

## Flow 3: Error Created -> Mastery Impact (Event Chain)

### Trace

1. **ErrorCreated Event** (`backend/app/core/event_bus.py`, line 82-96):
   - Published with `event_type: "error_created"`, `user_id`, `error_id`, `linked_node_ids`

2. **ErrorBookMasterySyncService** (`backend/app/services/error_book_mastery_sync_service.py`):
   - `apply_error_diagnosis` (line 95-160): Called synchronously after `analyze_and_link()`
   - For each linked node (max 3), calculates delta based on `ERROR_TYPE_IMPACT` (line 41-48):
     - `concept_confusion: -8`, `knowledge_gap: -10`, `method_wrong: -6`, etc.
   - Calls `_update_node_mastery` (line 242-341) which:
     - Writes mastery via `GalaxyService.update_node_mastery` (line 355)
     - Creates `StudyRecord` with `record_type='error_diagnosis'`
     - Returns `_pending_event` (line 321-340) -- event is NOT published immediately

3. **Pending event pattern** (line 321-340):
   ```python
   pending_event = {
       "topic": "node_mastery_updated",
       "payload": NodeMasteryUpdatedEvent(...).to_dict(),
   }
   return {..., "_pending_event": pending_event}
   ```
   The comment at line 321 says: "Defer event publish -- caller commits then flushes pending events (fix #1)"

4. **GalaxyEventConsumer** (`backend/app/services/galaxy_event_consumer.py`, line 77-221):
   - `_handle_error_created` (line 77-221): Processes `error_created` events from Redis Streams
   - Explicit guard comment (line 79-86): "MASTERY GUARD: The node mastery update has been migrated to ErrorBookMasterySyncService... This async handler **absolutely does not** modify mastery_score"
   - Does NOT modify mastery_score -- only does graph evolution, seed prewarming, plan-health checks

5. **`_handle_mastery_updated`** (line 414-421):
   - Delegates to `GraphEvolutionService.handle_mastery_updated(event)` -- graph structure only
   - Does NOT modify mastery_score

### Findings

**Mastery deducted once or multiple times: ONCE (by design)**
- The mastery deduction happens ONLY in `ErrorBookMasterySyncService.apply_error_diagnosis` which is called synchronously during error analysis.
- The `GalaxyEventConsumer._handle_error_created` explicitly does NOT modify mastery (line 79-86 comment + verified by code -- no calls to `update_node_mastery` or any mastery mutation).
- The `GalaxyService.handle_error_created` and `update_mastery_from_error` methods were REMOVED (`backend/app/services/galaxy_service.py`, line 161-170 comment block confirms removal to prevent double-deduction).

**VERIFIED ISSUE [ISSUE-F3-1] [MEDIUM]: Pending events from ErrorBookMasterySyncService may never be published**

- **File**: `backend/app/services/error_book_mastery_sync_service.py`, line 321-340
- **Root cause**: The `_update_node_mastery` method returns a dict with `_pending_event` containing the `node_mastery_updated` event. The comment says "caller commits then flushes pending events" but there is no code in `apply_error_diagnosis` (lines 95-160) that iterates over results and publishes the pending events. The method collects results into a list but never accesses `_pending_event` from them.
- **Impact**: The `node_mastery_updated` event from error diagnosis never reaches the event bus. This means:
  - `GalaxyEventConsumer._handle_mastery_updated` is never triggered for error-related mastery changes
  - `GraphEvolutionService.handle_mastery_updated` never runs for these events
  - Knowledge readiness scores in plans may not update when errors lower mastery
- **Note**: The `spark_node` path in `GalaxyStatsService` DOES publish this event directly (line 115-128), so the event chain works for task-completion mastery updates but NOT for error-diagnosis mastery updates.
- **Fix**: After the DB transaction commits, iterate `results` and publish each `_pending_event`:
  ```python
  for result in results:
      pending = result.get("_pending_event")
      if pending:
          await event_bus.publish(pending["topic"], pending["payload"])
  ```

---

## Flow 4: Document Upload -> Knowledge Nodes

### Trace

1. **DocumentService** (`backend/app/services/document_service.py`, line 935-1030):
   - `draft_knowledge_nodes` method called after document processing
   - Primary path: Calls `GalaxyService.create_nodes_from_document()` (line 954)
   - Fallback: Uses `ExpansionService` with section heuristic (line 963-1029)

2. **GalaxyService.create_nodes_from_document** (`backend/app/services/galaxy_service.py`, line 461-593):
   - Calls `OntologyGenerator.generate()` to extract nodes and relations from text
   - Creates root node from file name (line 473-492)
   - Creates child nodes from ontology candidates (line 498-534)
   - Creates inter-node relations from ontology relations (line 536-549)
   - Creates `KnowledgeNodeDocument` links for all nodes (line 568-584)

3. **OntologyGenerator** (`backend/app/services/galaxy/ontology_generator.py`, line 119-161):
   - Uses LLM to extract knowledge graph from document text
   - Returns `OntologyExtractionResult` with `nodes` and `relations`
   - Truncates text to 50KB max (line 120)

4. **chunk_refs population**:
   - In the primary path (`create_nodes_from_document`), `chunk_refs` is NOT set on any nodes. The `node_updates` dict (line 488-491, 520-523) only sets `source_file_id` and `status: "draft"`, but never `chunk_refs`.
   - In the fallback heuristic path (`draft_knowledge_nodes`, line 997-1026), `chunk_refs` IS set to chunk indices.

5. **Embedding generation**:
   - `generate_embedding=False` is passed in all `upsert_node_from_candidate` calls (lines 483, 515)
   - No embedding is generated at document-import time
   - Background embedding is handled separately via `create_node` -> `_process_node_background` (`backend/app/services/galaxy_service.py`, line 331-332), but `create_nodes_from_document` uses `ExpansionService.upsert_node_from_candidate` directly, which does NOT spawn background embedding tasks.

### Findings

**VERIFIED ISSUE [ISSUE-F4-1] [MEDIUM]: Document-imported nodes have no embeddings and no background embedding is scheduled**

- **File**: `backend/app/services/galaxy_service.py`, line 461-593
- **Root cause**: `create_nodes_from_document` calls `upsert_node_from_candidate` with `generate_embedding=False` for all nodes (lines 483, 515) and does not schedule any background embedding task after creation.
- **Impact**: Document-imported knowledge nodes have `embedding=NULL` in the database, which means:
  - Semantic search (`SearchNodes` gRPC and REST) will never return these nodes
  - Similarity-based recommendations skip these nodes
  - The `predict_next_node` fallback query (`backend/app/services/galaxy/stats_service.py`, line 336-348) uses `importance_level >= 4` which may still surface them, but the primary recommendation path relies on relation traversal which does work.
- **Mitigation**: The separate `create_node` method (for user-created nodes) DOES schedule background embedding via `task_manager.spawn`. Document-imported nodes skip this.
- **Fix**: After `self.db.commit()` (line 586), schedule background embedding for all created nodes:
  ```python
  from app.core.task_manager import task_manager
  for node in [root_node, *created_nodes]:
      await task_manager.spawn(
          self._process_node_background(node.id, node.name, node.description or ""),
          task_name="doc_node_embedding",
          user_id=str(user_id),
      )
  ```

**Observation [OBS-2]: chunk_refs not populated in ontology path**
- The primary `create_nodes_from_document` path does not set `chunk_refs` on any nodes. Only the fallback heuristic path sets `chunk_refs = chunk_indices` (line 1000, 1024).
- Since the primary path is the one actually used (the fallback only triggers on exception, line 963), document-imported nodes will have `chunk_refs = NULL`.
- This is a minor data completeness issue -- `chunk_refs` is used for source-chunk linking in the knowledge detail view. Without it, the "view source chunks" feature may not show which chunks contributed to which node.

---

## Flow 5: Community Sharing -> Knowledge Base

### Trace

1. **CommunitySignalBridge** (`backend/app/services/community_signal_bridge.py`, line 176-259):
   - `handle_resource_shared` method (line 176-259) handles knowledge node sharing
   - Only activates for `resource_type == "knowledge_node"` and `target_group_id is not None` (line 201)
   - Awards `KNOWLEDGE_SHARE_BONUS = 5.0` mastery points (line 45, 216)
   - Uses 0-100 scale correctly: `min(100.0, old_mastery + 5.0)` (line 216)
   - Calls `GalaxyService.update_node_mastery` with `int(round(new_mastery))` (line 222)
   - Publishes `galaxy.node.updated` event (line 226-239)

2. **Flutter GroupKnowledgeBaseView** (`mobile/lib/features/community/presentation/widgets/group_knowledge_base_view.dart`):
   - File upload uses `fileRepositoryProvider` -> `file_picker_with_presigned` widget
   - Does NOT directly call knowledge base upload APIs. The file upload flow goes through the file service.
   - Group files are listed via `repo.listGroupFiles(widget.groupId)` (line 63)
   - File sharing to group uses `repo.copyGroupFileToMyLibrary` (line 138) for saving, and `fileRepositoryProvider` for uploads

3. **API endpoint matching**:
   - Flutter: `ApiEndpoints.groupFiles(groupId)` -> `'/community/groups/$groupId/files'` (`api_endpoints.dart`, line 402)
   - Go: Routes are registered in the community handler under `/community/groups/:id/files`
   - Flutter: `ApiEndpoints.groupFileShare(groupId, fileId)` -> `'/community/groups/$groupId/files/$fileId/share'` (`api_endpoints.dart`, line 404)
   - The community signal bridge is called server-side when a file share event occurs, not directly from Flutter.

### Findings

**Mastery scale: PASS** -- `KNOWLEDGE_SHARE_BONUS = 5.0` is on the 0-100 scale, correctly clamped with `min(100.0, ...)`.

**API endpoint matching: PASS** -- Flutter endpoints match Go route registrations for group files.

**Knowledge share mastery flow: PASS** -- The bridge correctly reads current mastery, adds bonus, calls `update_node_mastery`, and publishes an event.

---

## Summary of Verified Issues

### ISSUE-F2-1 [HIGH]: GetUserGalaxy gRPC returns mastery=0 for all nodes
- **File**: `backend/app/services/galaxy_grpc_service.py`, line 235
- **Root cause**: `getattr(node, 'mastery', 0)` on `NodeWithStatus` returns 0 because there is no `.mastery` attribute. The actual value is at `.user_status.mastery_score`.
- **Impact**: Go gateway gRPC path for `GET /galaxy/graph` always shows 0% mastery for all nodes. REST fallback path works correctly.
- **Fix**: `mastery = int(node.user_status.mastery_score) if node.user_status else 0`

### ISSUE-F2-2 [MEDIUM]: GetNodeDetail returns mastery scaled 100x too large
- **File**: `backend/app/services/galaxy_grpc_service.py`, line 318
- **Root cause**: `int(stats.mastery_score * 100)` but `mastery_score` is already on 0-100 scale. Multiplication produces 0-10000 range.
- **Impact**: Node detail via gRPC shows mastery as 100x too large (e.g., 75% appears as 7500, clamped to 100 by Flutter). Any node with mastery > 1.0 appears as 100%.
- **Fix**: `mastery = int(stats.mastery_score) if stats and hasattr(stats, 'mastery_score') else 0`

### ISSUE-F3-1 [MEDIUM]: ErrorBookMasterySyncService pending events never published
- **File**: `backend/app/services/error_book_mastery_sync_service.py`, line 321-340
- **Root cause**: `_update_node_mastery` returns `_pending_event` in the result dict, but `apply_error_diagnosis` never iterates results to publish these events to the event bus.
- **Impact**: `node_mastery_updated` events from error diagnosis never fire, so graph evolution and plan readiness checks do not trigger on error-related mastery changes.
- **Fix**: Add event flush after DB commit in `apply_error_diagnosis`.

### ISSUE-F4-1 [MEDIUM]: Document-imported nodes have no embeddings
- **File**: `backend/app/services/galaxy_service.py`, line 461-593
- **Root cause**: `create_nodes_from_document` passes `generate_embedding=False` and does not schedule background embedding.
- **Impact**: Document-imported nodes are invisible to semantic search.
- **Fix**: Schedule background embedding task for all created nodes.

---

## Summary of Observations (Non-blocking)

### OBS-1: Float-to-int truncation in mastery responses
- Internal mastery_score is Float in DB, but all API boundaries convert with `int()` (truncation) not `round()`. A node with internal 47.7 appears as 47 to the user. Consistent behavior, not a bug.

### OBS-2: chunk_refs not populated in document ontology path
- The primary `create_nodes_from_document` path does not set `chunk_refs` on created nodes, unlike the fallback heuristic path. The "view source chunks" feature may not work for ontology-generated nodes.

---

## Layer-by-Layer Type Consistency Matrix

| Boundary | Mastery Type | Tags Field | Direction |
|----------|-------------|------------|-----------|
| Flutter -> Go (JSON) | `int` (0-100) | N/A (no tags in update) | Request |
| Go -> gRPC (Proto) | `int32` (0-100) | N/A | Request |
| gRPC -> Python (Proto) | `int32` (0-100) | N/A | Request |
| Python -> DB (SQLAlchemy) | `Float` (0-100) | `keywords` (JSONB) | Write |
| DB -> Python REST (Schema) | `Float` -> `mastery_score` | `keywords` -> `_build_auto_tags` -> `tags` | Read |
| DB -> Python gRPC (Proto) | **BUG: always 0** (F2-1) | `tags` from NodeWithStatus | Read |
| GetNodeDetail gRPC | **BUG: 100x too large** (F2-2) | `node.keywords` (correct) | Read |
| Python gRPC -> Go (Proto) | `int32` (0-100) | `repeated string` | Read |
| Go -> Flutter (JSON) | `int` (0-100) | `tags: string[]` | Read |
| Flutter model (Dart) | `int` (0-100, auto-scaled) | `tags: List<String>?` | Read |

---

## Priority Remediation Order

1. **ISSUE-F2-1** (HIGH): Fix `GetUserGalaxy` mastery to use `node.user_status.mastery_score`
2. **ISSUE-F2-2** (MEDIUM): Fix `GetNodeDetail` mastery to remove `* 100` multiplication
3. **ISSUE-F3-1** (MEDIUM): Add event publishing loop after DB commit in `ErrorBookMasterySyncService.apply_error_diagnosis`
4. **ISSUE-F4-1** (MEDIUM): Schedule background embedding for document-imported nodes
