# Card System Audit: Gateway / Proto / Database

**Date**: 2026-05-09
**Auditor**: Claude Agent (GLM-5.1)
**Scope**: Go Gateway, Protocol Buffers, Database Schema, Python Models, Cross-Layer Consistency

---

## Executive Summary

The card system spans six database tables (`cards`, `card_edges`, `card_snapshots`, `card_share_records`, `card_adoption_records`, `task_occurrences`), seven Python SQLAlchemy models, a full REST API (`/api/v1/cards/*`), a Go gateway proxy layer, and widget/card rendering across the Flutter frontend. The audit found **23 issues** across all layers: 2 P0, 5 P1, 10 P2, and 6 P3.

Key findings:
- **P0**: Card enum types are missing from the SQL schema (stored as unvalidated `varchar`), allowing arbitrary values.
- **P0**: Default value syntax errors in `card_edges.binding_mode` and `cards.schema_version` cause literal triple-quote values instead of intended strings.
- **P1**: Python backend emits 10+ `widget_type` values that have no corresponding handler in the Go gateway's action feedback routing, causing silent drops.
- **P1**: No proto message definition for the Card Protocol -- card CRUD, sharing, and adoption operate entirely through REST proxy, bypassing the typed gRPC contract.

---

## 1. Protocol Buffer Issues

### PB-01: No Proto Definition for Card Protocol Entities

| Field | Value |
|-------|-------|
| **File** | `proto/` (all files) |
| **Severity** | P1 |
| **Category** | Proto |
| **Description** | The card system has 6 database tables, 7 Python models, and a full REST API, but zero proto message definitions. Card CRUD, tree traversal, sharing, adoption, recurrence, and snapshot operations all go through REST proxy (`/api/v1/cards/*`) to the Python backend. This means no typed gRPC contract exists for cards. |
| **Current behavior** | Go gateway proxies all card requests as opaque HTTP to Python backend. No field-level validation at the gateway layer. |
| **Expected behavior** | Card operations should have proto definitions for type safety and backward compatibility tracking, or at minimum the current REST-only design should be documented as intentional in the proto files. |
| **Fix approach** | Either add `card_service.proto` with messages for Card, CardEdge, CardSnapshot, etc., or add a comment in `agent_service.proto` documenting the intentional REST-only card protocol. |

### PB-02: `widget_type` Field is Untyped String in Proto

| Field | Value |
|-------|-------|
| **File** | `proto/agent_service.proto:626` (`ToolResultPayload.widget_type`) |
| **Severity** | P2 |
| **Category** | Proto |
| **Description** | `widget_type` is a free-form `string` with no enum constraint. Python backend emits at least 14 distinct widget types (`task_card`, `task_list`, `plan_card`, `knowledge_card`, `prism_card`, `achievement_card`, `error_card`, `focus_card`, `execution_summary`, `plan_context_summary`, `task_detail`, `translation_result`, `web_search_results`, `profile_front_door`, `graph_diagnostic`, `system_update`, `intervention_card`). |
| **Current behavior** | Any string value is accepted. No compile-time or runtime validation of widget types. |
| **Expected behavior** | Widget types should be an enum (or at least a documented set of string constants) to prevent typos and ensure cross-layer consistency. |
| **Fix approach** | Add a `WidgetType` enum to `agent_service.proto` and use it in `ToolResultPayload`. Maintain an `UNSPECIFIED = 0` sentinel for forward compatibility. |

### PB-03: `InterventionPayload` Duplicates WebSocket `InterventionPushMessage`

| Field | Value |
|-------|-------|
| **File** | `proto/agent_service.proto:682-684` vs `proto/websocket.proto:48-68` |
| **Severity** | P2 |
| **Category** | Proto / Cross-Layer |
| **Description** | `InterventionPayload` in agent_service.proto and `InterventionPushMessage` in websocket.proto define overlapping intervention delivery structures with different schemas. The agent_service version has `request.reason`, `request.content` (Struct), and `request.on_reject`. The websocket version has `content` (with `rendered_message`, `intent_type`, `template_id`, `scaffolding_level`) and `actions`. |
| **Current behavior** | Two separate intervention schemas coexist without a clear mapping between them. |
| **Expected behavior** | Single canonical intervention schema, or a documented transformation between the two. |
| **Fix approach** | Add comments documenting which path uses which schema. The Go gateway `convertResponseToJSON` handles `ChatResponse_Intervention` (agent_service path). The `SignalPushHandler` uses the websocket path. Document this clearly. |

### PB-04: `Citation.score` is `float` but `float` Fields Have Precision Issues in Proto

| Field | Value |
|-------|-------|
| **File** | `proto/agent_service.proto:597` |
| **Severity** | P3 |
| **Category** | Proto |
| **Description** | `Citation.score` uses `float` (32-bit IEEE 754). For similarity scores between 0-1, float can lose precision. The `MemoryItem.score` also uses float. |
| **Current behavior** | Scores may have rounding artifacts when serialized/deserialized across proto boundary. |
| **Expected behavior** | Use `double` for scores to maintain precision across languages. |
| **Fix approach** | Change `float score = 6` to `double score = 6` in both `Citation` and `MemoryItem`. This is a backward-compatible change for proto3. |

### PB-05: `reserved` Fields Scattered Without Documentation

| Field | Value |
|-------|-------|
| **File** | `proto/agent_service.proto:252-253`, `proto/galaxy_service.proto:47-48`, `proto/websocket.proto:21-22` |
| **Severity** | P3 |
| **Category** | Proto |
| **Description** | Multiple `reserved` blocks exist (`timestamp` at field 13 in ChatResponse, field 4 in UpdateNodeMasteryRequest, field 6 in WebSocketMessage) without comments explaining what was removed and why. |
| **Current behavior** | Future developers may accidentally reuse reserved field numbers without understanding history. |
| **Expected behavior** | Each reserved block should have a comment like `// Reserved: formerly google.protobuf.Timestamp, migrated to event_time (field 19)`. |
| **Fix approach** | Add comments to all reserved blocks. |

---

## 2. Go Gateway Issues

### GW-01: Action Feedback Handler Missing Widget Types

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/chat_orchestrator_feedback.go:226-303` |
| **Severity** | P1 |
| **Category** | Gateway |
| **Description** | The `handleActionFeedbackWithResponder` switch only handles: `task_list`, `create_task`, `plan_card`, `create_plan`, `focus_card`, and `execution_summary`. But Python tools emit these additional widget types with actions: `task_card`, `knowledge_card`, `prism_card`, `achievement_card`, `error_card`, `plan_context_summary`, `plan_state`, `task_detail`, `translation_result`, `web_search_results`, `profile_front_door`, `graph_diagnostic`, `system_update`, `intervention_card`. Any action feedback for these types hits the `default` branch and is logged as "Unknown widget type" but otherwise silently dropped. |
| **Current behavior** | User taps confirm/dismiss on `task_card`, `knowledge_card`, etc. -- the feedback is logged but not routed to any handler. The `persistActionFeedback` still fires (best-effort HTTP POST to Python), but the client gets no status response for these types. |
| **Expected behavior** | All widget types that produce user-facing action cards should be handled or at minimum return a generic acknowledgment. |
| **Fix approach** | Add cases for `task_card`, `knowledge_card`, `prism_card`, `achievement_card`, `error_card` etc. to the switch statement, or add a `default` branch that sends a generic `SendActionStatus(toolResultID, "received", ...)` response instead of silently ignoring. |

### GW-02: `widget_data` Merge Order Can Overwrite Critical Fields

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/chat_orchestrator_protocol.go:196-204` |
| **Severity** | P1 |
| **Category** | Gateway |
| **Description** | When `widgetType == "execution_summary"`, the code builds a `merged` map from `buildExecutionSummaryWidget` first, then overwrites with `widgetData` entries (`for k, v := range widgetData { merged[k] = v }`). This means Python-provided `widget_data` values take precedence over gateway-generated fields like `title`, `status`, `tool_name`. If Python sends a `title` that differs from the i18n-generated one, the Python version wins. But if Python sends an empty/error string for `title`, it also overwrites the gateway's fallback. |
| **Current behavior** | Python widget_data always wins in merge conflicts, even if it contains empty/error values. |
| **Expected behavior** | Gateway fallbacks should not be overwritten by empty values from upstream. |
| **Fix approach** | Add non-empty checks: `if v != "" && v != nil { merged[k] = v }` or use a priority merge that only overwrites when the incoming value is non-zero. |

### GW-03: `convertResponseToJSON` Does Not Handle Nil Maps in Metadata

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/chat_orchestrator_protocol.go:75-97` |
| **Severity** | P2 |
| **Category** | Gateway |
| **Description** | When `resp.Metadata` is nil (proto3 map fields are never nil in Go protobuf, but can be empty), the loop `for key, value := range resp.Metadata` simply produces an empty map, which is fine. However, the `jsonMetadataKeys` lookup attempts JSON unmarshalling of each value. If a value is malformed JSON that starts with `{` but is incomplete (e.g. `{"partial`), the `json.Unmarshal` will fail and the raw string is used. This is handled correctly, but the error is silently consumed with only a `log.Printf`. |
| **Current behavior** | Malformed JSON metadata values are silently passed through as strings. |
| **Expected behavior** | At minimum, increment a metric counter for malformed metadata JSON to catch upstream issues. |
| **Fix approach** | Add a metric increment alongside the existing `log.Printf` for failed JSON decode in metadata keys. |

### GW-04: SignalPush Widget Delivery Has No Ordering Guarantee

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/signal_push.go:107-128` |
| **Severity** | P2 |
| **Category** | Gateway |
| **Description** | The `SignalPushHandler` iterates over candidates and calls `h.hub.Send()` for each. The `SignalHub.Send()` method (in `service/signal_hub.go`) likely uses a per-user channel or connection map. If multiple candidates are sent for the same user in sequence, there is no guarantee they arrive in the same order at the Flutter client, because WebSocket writes may be interleaved with other messages in the connection's write goroutine. |
| **Current behavior** | Signal push candidates may arrive out of order at the client. |
| **Expected behavior** | Candidates from a single push request should maintain their relative order. |
| **Fix approach** | Batch all candidates for a user into a single WebSocket message (JSON array), or add a sequence number to each widget push so the client can reorder. |

### GW-05: No Gateway-Side Validation of Card API Requests

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/proxy_routes.go:195-215` |
| **Severity** | P2 |
| **Category** | Gateway |
| **Description** | All card routes (`/api/v1/cards/*`) are proxied directly to Python with no gateway-side validation. The Go gateway performs authentication but does not validate: card_type enum values, lifecycle_status values, edge_type values, share scope/permission values, or request body schema. Any malformed request passes through to Python. |
| **Current behavior** | Malformed card API requests are forwarded to Python, which may return 422 or 500 errors that could have been caught earlier. |
| **Expected behavior** | Gateway should at minimum validate that enum-like fields contain known values before proxying. |
| **Fix approach** | Add lightweight request body validation middleware for card routes, or add proto-based validation when proto definitions are added (PB-01). |

### GW-06: WebSocket Proxy Does Not Transform Card-Specific Messages

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/websocket_proxy.go:426-459` |
| **Severity** | P3 |
| **Category** | Gateway |
| **Description** | The community WebSocket proxy (`proxyWebSocket`) does bidirectional message forwarding without any transformation. Card share messages (`MessageType.CAPSULE_SHARE`, `PLAN_SHARE`, etc.) pass through as raw JSON. This is correct for a transparent proxy, but means the gateway cannot enforce any card-related invariants (e.g., validating that a shared card exists, checking visibility permissions). |
| **Current behavior** | Card share messages pass through unmodified. All validation happens at Python backend. |
| **Expected behavior** | This is acceptable for the current architecture. Document it as intentional. |
| **Fix approach** | Add comment in proxy code noting that card share validation is delegated to Python backend. |

---

## 3. Database Schema Issues

### DB-01: Card Enum Types Missing from SQL Schema

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql` (card tables at lines 1467-1579) |
| **Severity** | P0 |
| **Category** | Database |
| **Description** | The card tables use `character varying(32)` or `character varying(24)` for enum-like columns (`card_type`, `lifecycle_status`, `visibility`, `source_type`, `created_by`, `updated_by`, `edge_type`, `binding_mode`, `scope`, `permission`, `import_mode`, `occurrence_status`). None of these have corresponding PostgreSQL `CREATE TYPE ... AS ENUM` entries in the schema dump. Python models define `Enum` types with `native_enum=False`, which stores values as plain strings without database-level constraints. |
| **Current behavior** | Any string value can be inserted into `card_type`, `lifecycle_status`, etc. For example, a bug could insert `card_type='PLAAAN'` and the database would accept it. |
| **Expected behavior** | PostgreSQL enum types or CHECK constraints should enforce valid values at the database level. |
| **Fix approach** | Create Alembic migration adding: (1) `card_type_enum`, `card_lifecycle_enum`, `card_visibility_enum`, `card_source_type_enum`, `card_created_by_enum`, `edge_type_enum`, `binding_mode_enum`, `share_scope_enum`, `share_permission_enum`, `import_mode_enum`, `occurrence_status_enum` as PostgreSQL enum types; (2) ALTER columns to use these types. Alternatively, add CHECK constraints. |

### DB-02: Default Value Syntax Error in `card_edges.binding_mode`

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql:1494` |
| **Severity** | P0 |
| **Category** | Database |
| **Description** | The default value is `'''OWNED'''::character varying` which includes literal triple-single-quotes. This is a pg_dump artifact where the value `'''OWNED'''` represents a string that contains single quotes around `OWNED`. The actual stored default is `'OWNED'` (with quotes), not `OWNED`. Compare with other tables that use simple defaults like `'pending'::accountabilitystatus` (line 801) without triple quotes. |
| **Current behavior** | New card edges get binding_mode = `'OWNED'` (literally with single quotes in the string value), not `OWNED`. |
| **Expected behavior** | Default should be the bare string `OWNED`. |
| **Fix approach** | Fix the Alembic migration or manual ALTER: `ALTER TABLE card_edges ALTER COLUMN binding_mode SET DEFAULT 'OWNED';` Also check if existing data contains quoted values and clean up. The same issue affects `cards.schema_version` (default `'''3.0'''`) and `card_snapshots.schema_version` (default `'''1.0'''`). |

### DB-03: `card_snapshots.schema_version` Default Mismatch

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql:1544` vs `backend/app/models/card_protocol.py:448` |
| **Severity** | P1 |
| **Category** | Database / Cross-Layer |
| **Description** | SQL schema default is `'''1.0'''` (triple-quoted, so actual value is `'1.0'`), while the Python model default is `"1.0"` (bare string). The triple-quote issue (DB-02) means the actual DB default differs from the Python default. |
| **Current behavior** | Records created via SQL defaults get a different `schema_version` than records created via Python ORM. |
| **Expected behavior** | Consistent default values across SQL and Python. |
| **Fix approach** | Fix the SQL default to `'1.0'` without extra quoting. |

### DB-04: Missing Index on `cards.updated_at` for Pagination

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql` (cards table, line 1556) |
| **Severity** | P2 |
| **Category** | Database |
| **Description** | The `cards` table has indexes on `owner_id`, `holder_id`, `card_type`, `lifecycle_status`, and composite indexes, but no index on `updated_at`. The card search API (`GET /api/v1/cards/search`) likely needs to sort by `updated_at` for pagination ("recently updated cards"). Without this index, such queries require a full table scan and sort. |
| **Current behavior** | Queries sorting by `updated_at` perform sequential scans. |
| **Expected behavior** | An index on `updated_at` (or a composite index with `owner_id, updated_at`) for efficient pagination. |
| **Fix approach** | Add index: `CREATE INDEX ix_cards_owner_updated ON cards(owner_id, updated_at DESC);` |

### DB-05: Missing Index on `card_share_records` for "shared with me" Queries

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql` (card_share_records table, line 1510) |
| **Severity** | P2 |
| **Category** | Database |
| **Description** | The `card_share_records` table has indexes on `scope + group_id`, `scope + target_user_id`, and `shared_by_user_id + scope`, but no index on `target_user_id` alone or `target_user_id + revoked_at`. The "shared with me" query pattern (`WHERE target_user_id = ? AND revoked_at IS NULL`) would benefit from a composite index. |
| **Current behavior** | "Shared with me" queries may scan many rows. |
| **Expected behavior** | Efficient index for the most common query pattern. |
| **Fix approach** | Add index: `CREATE INDEX ix_card_share_target_active ON card_share_records(target_user_id) WHERE revoked_at IS NULL;` |

### DB-06: `card_edges.active` Column Lacks Partial Index for Active-Only Queries

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql` (card_edges indexes) |
| **Severity** | P2 |
| **Category** | Database |
| **Description** | The `ix_card_edges_active` index covers `(active, edge_type)`, but the most common query pattern is likely `WHERE from_card_id = ? AND active = true` (get active children of a card). The existing `ix_card_edges_from_type` covers `(from_card_id, edge_type)` but doesn't filter by `active`. A partial index would be more efficient. |
| **Current behavior** | Active-edge queries scan inactive edges too. |
| **Expected behavior** | A partial index like `CREATE INDEX ... WHERE active = true` for common queries. |
| **Fix approach** | Add partial index: `CREATE INDEX ix_card_edges_from_active ON card_edges(from_card_id, edge_type) WHERE active = true;` and similar for `to_card_id`. |

### DB-07: No CASCADE DELETE from `cards` to `task_occurrences`

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql` (task_occurrences FK references) |
| **Severity** | P2 |
| **Category** | Database |
| **Description** | `task_occurrences` references `cards.id` via `series_card_id` (CASCADE), `plan_card_id` (SET NULL), and `phase_card_id` (SET NULL). If a PLAN card is deleted, its `task_occurrences.plan_card_id` is set to NULL, which is correct. However, if a TASK card (series) is deleted, the CASCADE on `series_card_id` will delete all occurrences. This is semantically correct but could be surprising if occurrences have feedback_payload or completion data. |
| **Current behavior** | Deleting a task card cascade-deletes all its occurrences, including completed ones with feedback data. |
| **Expected behavior** | Document this as intentional or consider archiving occurrences before cascade delete. |
| **Fix approach** | Add a comment in the schema or model documenting the cascade behavior. Consider a pre-delete hook that archives occurrence data. |

### DB-08: `card_adoption_records.adopted_root_card_id` Nullable Without Documentation

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql:1474`, `backend/app/models/card_protocol.py:516` |
| **Severity** | P3 |
| **Category** | Database |
| **Description** | `adopted_root_card_id` is nullable, but there is no documentation explaining when it would be NULL. This could represent: (a) the card was adopted but later deleted, or (b) the adoption is pending and the card hasn't been created yet. Without documentation, this ambiguity can lead to bugs. |
| **Current behavior** | Unclear semantic meaning of NULL `adopted_root_card_id`. |
| **Expected behavior** | Document when this field can be NULL and what it means. |
| **Fix approach** | Add a comment in the Python model: `# NULL when the adopted card has been subsequently deleted (FK uses SET NULL)`. |

---

## 4. Cross-Layer Consistency Issues

### XL-01: Card Type Enums Inconsistent Between Python and SQL

| Field | Value |
|-------|-------|
| **File** | `backend/app/models/card_protocol.py:49-56` vs `backend/gateway/internal/db/models.go:2345` |
| **Severity** | P1 |
| **Category** | Cross-Layer |
| **Description** | Python defines `CardType` as StrEnum with values: `PLAN`, `PHASE`, `TASK`, `KNOWLEDGE`, `ACHIEVEMENT`, `CUSTOM`. The Go model uses `string` for `CardType`. The Go models use `pgtype.UUID` and `[]byte` for JSONB fields (Tags, Metadata), while Python uses `JSONB`. There is no validation in Go that card_type values match the Python enum. |
| **Current behavior** | Go reads card_type as a free-form string; Python writes validated enum values. Mismatch only detectable at runtime. |
| **Expected behavior** | Go should have constants or an iota enum matching Python's CardType values. |
| **Fix approach** | Define `const ( CardTypePlan = "PLAN" ... )` in Go, or generate Go types from proto when proto definitions are added. |

### XL-02: Widget Type Values Diverge Between Python and Go/Frontend

| Field | Value |
|-------|-------|
| **File** | Python tools vs Go gateway vs Flutter `agent_message_renderer.dart` |
| **Severity** | P2 |
| **Category** | Cross-Layer |
| **Description** | Python backend emits these `widget_type` values across different tools:

| Python tool | widget_type |
|---|---|
| task_tools.py | `task_card`, `task_list`, `focus_card` |
| plan_tools.py | `plan_card`, `task_list` |
| plan_state_tools.py | `plan_context_summary`, `task_list`, `task_detail` |
| prism_tools.py | `prism_card` |
| growth_strategy_tools.py | `profile_front_door`, `graph_diagnostic` |
| web_search_tool.py | `web_search_results` |
| translation_tool.py | `translation_result` |
| execution_engine.py | `execution_summary` |
| session_state_mixin.py | `system_update` |

Flutter `agent_message_renderer.dart` only has `_widgetConfigs` entries for: `task_card`, `knowledge_card`, `task_list`, `plan_card`, `plan_context_summary`, `plan_state`, `prism_card`, `achievement_card`, `error_card`.

Missing from Flutter's widget configs: `task_detail`, `web_search_results`, `translation_result`, `profile_front_door` (handled separately in `action_card.dart`), `graph_diagnostic` (also in `action_card.dart`), `system_update`, `focus_card`. Some of these are handled in `chat_bubble.dart` and `action_card.dart` but through different code paths. |
| **Current behavior** | Some widget types fall through to a generic "Unknown widget type" fallback in Flutter. |
| **Expected behavior** | All widget types emitted by Python should have documented renderers in Flutter, or Python should not emit unhandled types. |
| **Fix approach** | Create a centralized `widget_type` registry (enum or constants) shared across Python/Go/Flutter. Map each type to its handler. Add explicit unknown-type fallback in Flutter that logs the type for debugging. |

### XL-03: `nodeId` vs `node_id` Naming Inconsistency in Go Responses

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/chat_orchestrator_feedback.go:113-120` vs `:124-134` |
| **Severity** | P2 |
| **Category** | Cross-Layer |
| **Description** | The `SendUpdateNodeError` method uses `"nodeId"` (camelCase) in the JSON payload, while `SendUpdateNodeMasteryAck` uses `"node_id"` (snake_case). This inconsistency forces Flutter to handle both key names. |
| **Current behavior** | Error response has `{"payload": {"nodeId": "..."}}`, ack response has `{"payload": {"node_id": "..."}}`. |
| **Expected behavior** | Consistent naming convention. The project standard is snake_case for JSON keys (matching Python/DB convention). |
| **Fix approach** | Change `"nodeId"` to `"node_id"` in `SendUpdateNodeError`. Check Flutter for any code that reads `"nodeId"` and update accordingly. |

### XL-04: `groupfiletrustlevel` Enum Value Case Mismatch

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql:294-298` vs `proto/community_service.proto:33-38` |
| **Severity** | P2 |
| **Category** | Cross-Layer |
| **Description** | The SQL enum `groupfiletrustlevel` has lowercase values: `'official', 'verified', 'member'`. The proto enum `GroupFileTrustLevel` has uppercase values: `GROUP_FILE_MEMBER = 1`, `GROUP_FILE_VERIFIED = 2`, `GROUP_FILE_OFFICIAL = 3`. The proto service is deprecated and documented as "compatibility documentation only", so this may not matter, but it creates confusion. |
| **Current behavior** | DB stores lowercase, proto defines uppercase. Community service is REST-based so proto values are not used directly. |
| **Expected behavior** | Document the mapping clearly or unify casing. |
| **Fix approach** | Add a comment in the proto file and Python model documenting the case mapping. |

### XL-05: `achievementtype` Enum Has Duplicate Value

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql:122-136` |
| **Severity** | P2 |
| **Category** | Database |
| **Description** | The `achievementtype` enum defines both `'planning'` (lowercase, line 134) and `'PLANNING'` (uppercase, line 135). This is a duplicate with different casing. PostgreSQL enum values are case-sensitive, so these are two distinct values. Any code comparing achievement types must handle both cases. |
| **Current behavior** | Two distinct enum values `'planning'` and `'PLANNING'` exist in the database. Code may match one but not the other. |
| **Expected behavior** | Single canonical value. |
| **Fix approach** | Add Alembic migration to merge `'planning'` into `'PLANNING'`: `UPDATE achievements SET type = 'PLANNING' WHERE type = 'planning';` then drop the old enum value. |

### XL-06: Card Visibility Enum Values Differ Between Python and DB Schema

| Field | Value |
|-------|-------|
| **File** | `backend/app/models/card_protocol.py:67-71` vs `backend/gateway/internal/db/schema.sql` (searchvisibility enum, line 513) |
| **Severity** | P3 |
| **Category** | Cross-Layer |
| **Description** | Python `CardVisibility` defines: `PRIVATE`, `FRIENDS`, `COMMUNITY`, `PUBLIC`. The SQL schema has a separate `searchvisibility` enum with: `'everyone'`, `'friends'`, `'nobody'`. These serve different purposes (card visibility vs user search visibility) but the overlapping `FRIENDS`/`friends` with different casing may cause confusion. |
| **Current behavior** | Two separate visibility systems with overlapping but inconsistent values. |
| **Expected behavior** | Either unify or clearly differentiate with documentation. |
| **Fix approach** | Add documentation distinguishing the two visibility systems. The `searchvisibility` enum is for user profile search, not card visibility. |

---

## 5. Community/Share Card Protocol Issues

### SC-01: No Race Condition Protection on `card_share_records.adoption_count`

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql:1523` and `backend/app/api/v1/cards.py:449-478` |
| **Severity** | P1 |
| **Category** | Database / Security |
| **Description** | The `adoption_count` column on `card_share_records` is an `integer DEFAULT 0`. The adopt endpoint (`POST /shares/{id}/adopt`) likely does a read-modify-write on this counter. Without `SELECT ... FOR UPDATE` or an atomic `UPDATE ... SET adoption_count = adoption_count + 1`, concurrent adoptions could lose counts (lost update anomaly). |
| **Current behavior** | Under concurrent adoptions, the adoption_count may be lower than the actual number of adoption records. |
| **Expected behavior** | Counter should be atomically incremented, or derived from counting `card_adoption_records`. |
| **Fix approach** | Use `UPDATE card_share_records SET adoption_count = adoption_count + 1 WHERE id = :share_id` instead of read-modify-write. Or better, derive adoption_count from a COUNT query on `card_adoption_records` and remove the denormalized column. |

### SC-02: Share Permission Check Missing for Group-Scoped Shares

| Field | Value |
|-------|-------|
| **File** | `backend/app/api/v1/cards.py:403-445` |
| **Severity** | P2 |
| **Category** | Security |
| **Description** | The `get_card_share` endpoint checks `if share.target_user_id and share.target_user_id != current_user.id and share.shared_by_user_id != current_user.id` but does not check whether the current user is a member of the group when `scope == GROUP` and `group_id` is set. A user who is not in the group could access group-scoped share details if they know the share_record_id. |
| **Current behavior** | Any authenticated user can view share details if they know the share_record_id, regardless of group membership. |
| **Expected behavior** | Group-scoped shares should only be visible to group members. |
| **Fix approach** | Add group membership check: `if share.group_id and not await is_group_member(db, current_user.id, share.group_id): raise 403`. |

### SC-03: No Expiration Enforcement on Share Records

| Field | Value |
|-------|-------|
| **File** | `backend/app/api/v1/cards.py:417-425` |
| **Severity** | P2 |
| **Category** | Database |
| **Description** | Share expiration is stored in `metadata.expires_at` (a JSONB string), not as a proper database column with a timestamp type. This means: (1) no index on expiration for efficient cleanup queries, (2) no database-level enforcement, (3) string comparison issues if date format varies. The `get_card_share` endpoint does check expiration at read time, but the `adopt_card_share` endpoint does not check expiration. |
| **Current behavior** | Expired shares can still be adopted through the adopt endpoint. |
| **Expected behavior** | Expired shares should reject adoption attempts. |
| **Fix approach** | Add expiration check in `adopt_card_share`. Long-term: add `expires_at timestamp` column to `card_share_records` with an index. |

### SC-04: No Cascade from `card_share_records` to `card_adoption_records` on Revocation

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/db/schema.sql:17566` |
| **Severity** | P2 |
| **Category** | Database |
| **Description** | When a share record is deleted, adoption records are cascade-deleted (`ON DELETE CASCADE`). However, share revocation only sets `revoked_at` (soft delete) rather than deleting the record. This means revoked shares still have their adoption records intact, which is correct. But there is no mechanism to "undo" adoptions when a share is revoked. Adopted cards remain in the adopter's card tree. |
| **Current behavior** | Revoked shares do not affect already-adopted cards. |
| **Expected behavior** | Document whether this is intentional (adopted cards persist after revocation) or should trigger a notification/reversal. |
| **Fix approach** | Add documentation to the ShareService clarifying the lifecycle: "Revocation prevents new adoptions but does not affect previously adopted cards." |

---

## 6. Security Issues

### SEC-01: Cards REST API Allows Arbitrary Path Traversal

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/proxy_routes.go:205-213` |
| **Severity** | P2 |
| **Category** | Security |
| **Description** | The wildcard route `cards.GET("/*path", h.proxyWithHeaders)` forwards any sub-path to the Python backend. While `proxyWithHeaders` should sanitize the URL, there is no explicit validation that `*path` contains only valid UUIDs or known sub-paths. A malicious user could craft paths like `/api/v1/cards/../../users/` if the proxy does not normalize paths. |
| **Current behavior** | All sub-paths under `/api/v1/cards/` are proxied to Python. |
| **Expected behavior** | Validate that card paths contain only valid segments (UUIDs + known action names like `move`, `link`, `tree`, `share`, `snapshot`, `recurrence`). |
| **Fix approach** | Add path validation middleware for card routes, or switch to explicit route definitions instead of wildcard. |

### SEC-02: `internal_api_key` Comparison Uses Constant-Time (Good) but Missing Rate Limit on Signal Push

| Field | Value |
|-------|-------|
| **File** | `backend/gateway/internal/handler/signal_push.go:133-140` |
| **Severity** | P3 |
| **Category** | Security |
| **Description** | The `isAuthorized` method correctly uses `subtle.ConstantTimeCompare` for the internal API key (good). However, the `HandlePush` endpoint has no rate limiting. An attacker with the internal API key could flood the signal push endpoint, causing excessive WebSocket messages to users. |
| **Current behavior** | No rate limit on signal push endpoint. |
| **Expected behavior** | Rate limit signal push requests per source IP or per API key. |
| **Fix approach** | Add rate limiting middleware to the signal push route, similar to other internal endpoints. |

---

## Summary Table

| ID | Severity | Category | File | Description |
|----|----------|----------|------|-------------|
| PB-01 | P1 | Proto | `proto/` | No proto definition for Card Protocol |
| PB-02 | P2 | Proto | `agent_service.proto:626` | `widget_type` untyped string |
| PB-03 | P2 | Proto | `agent_service.proto` vs `websocket.proto` | Duplicate intervention schemas |
| PB-04 | P3 | Proto | `agent_service.proto:597` | `float` precision for scores |
| PB-05 | P3 | Proto | Multiple | Undocumented reserved fields |
| GW-01 | P1 | Gateway | `chat_orchestrator_feedback.go:226` | Missing widget types in action feedback |
| GW-02 | P1 | Gateway | `chat_orchestrator_protocol.go:196` | widget_data merge overwrites fallbacks |
| GW-03 | P2 | Gateway | `chat_orchestrator_protocol.go:75` | No metrics for malformed metadata JSON |
| GW-04 | P2 | Gateway | `signal_push.go:107` | No ordering guarantee for signal push |
| GW-05 | P2 | Gateway | `proxy_routes.go:195` | No gateway-side card validation |
| GW-06 | P3 | Gateway | `websocket_proxy.go` | No card invariant enforcement |
| DB-01 | P0 | Database | `schema.sql` card tables | Card enum types missing from schema |
| DB-02 | P0 | Database | `schema.sql:1494` | Default value triple-quote syntax error |
| DB-03 | P1 | Database | `schema.sql:1544` | schema_version default mismatch |
| DB-04 | P2 | Database | cards table | Missing index on updated_at |
| DB-05 | P2 | Database | card_share_records | Missing index for "shared with me" |
| DB-06 | P2 | Database | card_edges | No partial index for active edges |
| DB-07 | P2 | Database | task_occurrences | Cascade deletes occurrence data |
| DB-08 | P3 | Database | card_adoption_records | Undocumented nullable FK |
| XL-01 | P1 | Cross-Layer | Python/Go models | Card type enums inconsistent |
| XL-02 | P2 | Cross-Layer | Python/Go/Flutter | Widget type values diverge |
| XL-03 | P2 | Cross-Layer | Go gateway | `nodeId` vs `node_id` inconsistency |
| XL-04 | P2 | Cross-Layer | SQL/Proto | Enum case mismatch |
| XL-05 | P2 | Database | schema.sql:134-135 | Duplicate achievementtype value |
| XL-06 | P3 | Cross-Layer | Python/SQL | Visibility enum overlap |
| SC-01 | P1 | Database | card_share_records | Race condition on adoption_count |
| SC-02 | P2 | Security | cards.py:403 | Missing group membership check |
| SC-03 | P2 | Database | card_share_records | No expiration enforcement on adopt |
| SC-04 | P2 | Database | card_share_records | Revocation doesn't affect adoptions |
| SEC-01 | P2 | Security | proxy_routes.go:205 | Wildcard path forwarding |
| SEC-02 | P3 | Security | signal_push.go | Missing rate limit |

**Severity Distribution**: P0: 2, P1: 5, P2: 14, P3: 6 (total: 27 findings)

**Priority Recommendations**:
1. **Fix DB-02 immediately** (triple-quote defaults) -- this is silently corrupting data.
2. **Fix DB-01** (add enum types or CHECK constraints) -- prevents garbage data at the source.
3. **Fix GW-01** (add widget type handlers or default acknowledgment) -- users see no feedback for many card types.
4. **Fix SC-01** (atomic counter update) -- concurrent adoptions can lose counts.
5. **Fix GW-02** (non-empty merge) -- prevents upstream from overwriting gateway fallbacks.
