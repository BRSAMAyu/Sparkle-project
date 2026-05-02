# CXP-09 Report — Knowledge Galaxy And Learning Graph

## Summary

Made Knowledge Galaxy nodes operationally explainable instead of only visually rendered. Galaxy graph responses now include a learning state, a recommended action, a human-readable reason, prerequisite blockers, and graph event provenance so the app can explain why a concept appears and what the user should do next.

## What Changed

- Added `LearningGraphState` to Galaxy node responses: `unknown`, `learning`, `weak`, `ready_for_review`, `mastered`, `connected_to_goal`, and `blocked_by_prerequisite`.
- Added top-level node fields for `learning_state`, `learning_state_reason`, `recommended_action`, `recommendation_reason`, `blocked_by_prerequisite_node_ids`, and `graph_event_sources`.
- Connected graph state to real signals:
  - prerequisite relations and weak prerequisite mastery block downstream nodes;
  - active task/knowledge links mark goal-connected nodes;
  - review urgency marks nodes as ready for review;
  - weak/error tags and recent errors mark nodes as weak;
  - high mastery marks nodes as mastered.
- Added graph event provenance stored in `UserNodeStatus.learning_path_snapshot.graph_event_sources`.
- Stamped provenance for:
  - translation/vocabulary saves via `KnowledgeIntegrationService`;
  - document ontology node creation via `GalaxyService.create_nodes_from_document`;
  - error events via `GalaxyEventConsumer`, including fallback error-gap node creation when an error arrives without linked nodes.
- Allowed user-owned draft nodes to appear in the user's Galaxy graph, so document/translation-created nodes are visible before publication instead of hidden from the learning loop.

## User Journey Evidence

1. Document -> graph node:
   - `create_nodes_from_document()` creates draft nodes.
   - Each user-owned node receives `graph_event_sources[0].event_type = document.ontology_created`.
   - Draft nodes are now included in that user's graph response.

2. Translation -> graph node:
   - `create_vocabulary_node()` creates or links a vocabulary node.
   - The node receives `graph_event_sources[0].event_type = translation.saved`.
   - The graph response exposes the node as `learning` with a concrete next action.

3. Error -> graph node:
   - `GalaxyEventConsumer` now creates an `Error gap: ...` node when an error event lacks linked nodes.
   - The node is tagged weak and receives `graph_event_sources[0].event_type = error.created`.
   - The graph response exposes it as `weak` with `recommended_action = repair`.

4. Mastery/review/prerequisite:
   - A weak prerequisite relation marks the dependent node as `blocked_by_prerequisite`.
   - A stale/due node is returned as `ready_for_review`.
   - A high-mastery node is returned as `mastered`.

## Verification

- `cd backend && ruff check app/schemas/galaxy.py app/services/galaxy_service.py app/services/galaxy_event_consumer.py app/services/knowledge_integration_service.py app/services/galaxy/provenance.py app/services/galaxy/structure_service.py tests/services/test_galaxy_learning_graph_operational.py`
  - Passed.
- `cd backend && pytest tests/services/test_galaxy_learning_graph_operational.py tests/services/test_galaxy_node_sources.py -q --timeout=60`
  - Passed: `5 passed`.

## Residual Risk

- Broader run `pytest tests/services/test_galaxy_node_sources.py tests/unit/test_sprint_galaxy_mastery.py -q --timeout=90` reached `6 passed` then timed out in `test_four_sprint_pack_tasks_reach_mastery_100` while touching event-bus/Postgres side effects. This appears outside the CXP-09 graph response changes, but final integration should isolate that test from live event-bus/achievement side effects.

## Files Changed

- `backend/app/schemas/galaxy.py`
- `backend/app/services/galaxy_service.py`
- `backend/app/services/galaxy/structure_service.py`
- `backend/app/services/galaxy/provenance.py`
- `backend/app/services/galaxy_event_consumer.py`
- `backend/app/services/knowledge_integration_service.py`
- `backend/tests/services/test_galaxy_learning_graph_operational.py`
