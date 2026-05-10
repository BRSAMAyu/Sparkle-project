# Galaxy Gateway / Proto / DB Audit Report

**Date**: 2026-05-10
**Auditor**: Go/gRPC/Database Expert Agent
**Scope**: Go Gateway galaxy handlers, gRPC clients, proto definitions, CQRS implementation, database schema

---

## Executive Summary

**29 verified issues found**: 3 P0 (data integrity/security), 8 P1 (broken features), 11 P2 (performance/reliability), 7 P3 (minor).

The most critical findings are: (1) Go CQRS writes to `study_records` using a `performance_score` column that does not exist in the database schema, causing every study recording to fail; (2) community CQRS `LikePost` fires an event even when `ON CONFLICT DO NOTHING` silently skips the insert, producing phantom like-count increments; (3) galaxy client shares the same gRPC connection as the agent client but has no reconnect/retry logic, so a single network blip permanently disables all galaxy gRPC paths.

---

## Category 1: Proto Contract Violations

### ISSUE P2-01: Proto `mastery` field is `int32` but Python model uses `float64` (0-100)

- **Severity**: P2 (data precision loss)
- **File**: `proto/galaxy_service.proto:63-65`, `backend/app/models/galaxy.py:237`
- **Issue**: The proto field `int32 mastery = 3` truncates fractional mastery values. The Python `UserNodeStatus.mastery_score` is a `Float` in the range 0-100. The Go gRPC client at `galaxy/client.go:68` passes `int32(req.Mastery)`, which drops the decimal portion. The Python gRPC service at `galaxy_grpc_service.py:96` does `int(request.mastery)`, further truncating. When the Python service responds, it also truncates with `int(result.get("old_mastery", 0))` at line 157.
- **Context**:
  ```protobuf
  // proto line 63
  int32 mastery = 3;
  ```
  ```python
  # galaxy_grpc_service.py line 96
  mastery=int(request.mastery)  # truncates float to int
  ```
- **Fix**: Change proto field to `double mastery = 3` and remove `int()` casts in Python, or document that mastery is always an integer percentage (0-100) and ensure the Python side treats it as such consistently. Given the DB model uses `Float`, the proto should use `double`.

### ISSUE P3-01: Proto `tags` field name mismatches DB column `keywords`

- **Severity**: P3 (semantic inconsistency)
- **File**: `proto/galaxy_service.proto:102`, `backend/app/models/galaxy.py:131`
- **Issue**: The proto message `GalaxyNode` has `repeated string tags = 5`, but the database column is called `keywords` (JSONB). The Python gRPC service at `galaxy_grpc_service.py:350` maps it as `tags=r.node.tags or []` but `r.node` is a KnowledgeNode which has no `tags` attribute -- it has `keywords`. This will produce `AttributeError` or empty tags at runtime. Similarly, `GetNodeDetail` at line 320 does `tags=node.tags or []` where `node` is a KnowledgeNode model with no `tags` attribute.
- **Context**:
  ```python
  # galaxy_grpc_service.py line 350
  tags=r.node.tags or [],  # KnowledgeNode has keywords, not tags
  ```
- **Fix**: Change to `tags=(r.node.keywords or [])` in all locations where KnowledgeNode.tags is referenced, or add a `tags` property/alias on the Python model.

---

## Category 2: Gateway Routing Bugs

### ISSUE P1-01: Community CQRS handler routes never registered -- community.go is dead code

- **Severity**: P1 (broken feature)
- **File**: `backend/gateway/internal/api/v1/community.go:24-33`, `backend/gateway/internal/handler/proxy_routes.go:528-535`
- **Issue**: The `CommunityHandler` in `community.go` defines `RegisterRoutes` with routes for `POST /posts`, `POST /posts/:id/like`, and `GET /feed`. However, `setup.go` never constructs a `CommunityHandler` and never calls `RegisterRoutes` on it. Instead, `proxy_routes.go` registers the same paths as proxy routes at lines 528-535. This means the CQRS command service for community posts is never invoked -- all community write operations bypass the Go CQRS pipeline entirely and go straight to Python REST.
- **Context**:
  ```go
  // community.go defines CQRS handlers but is never instantiated in setup.go
  // proxy_routes.go proxies same paths to Python backend instead
  community.GET("/feed", h.proxyWithHeaders)      // line 528
  community.POST("/posts", h.proxyWithHeaders)     // line 529
  community.POST("/posts/:post_id/like", h.proxyWithHeaders)  // line 530
  ```
- **Fix**: Either (a) instantiate `CommunityHandler` in `setup.go` and use it for the 3 write endpoints while keeping proxy routes for reads, or (b) remove `community.go` and `community_command.go` as dead code if the CQRS path was intentionally abandoned.

### ISSUE P2-02: Duplicate route registrations for node/:id vs nodes/:id

- **Severity**: P2 (maintenance hazard, potential routing ambiguity)
- **File**: `backend/gateway/internal/handler/galaxy_handler.go:72-134`
- **Issue**: Every galaxy route is registered twice -- once with `/node/:id/...` and once with `/nodes/:id/...`. For example, lines 72-73 both map `POST /node/:id/spark` and `POST /nodes/:id/spark` to `SparkNode`. This doubles route registration count and can cause confusion about which is canonical. Gin will match the first registered route, so both work, but it is maintenance debt.
- **Context**:
  ```go
  galaxy.POST("/node/:id/spark", h.SparkNode)   // line 72
  galaxy.POST("/nodes/:id/spark", h.SparkNode)  // line 73
  ```
- **Fix**: Standardize on one path pattern (either singular or plural). If both must be supported for backward compatibility, add a deprecation comment and plan removal.

---

## Category 3: gRPC Client Issues

### ISSUE P0-01: Galaxy gRPC client has no reconnect or retry logic

- **Severity**: P0 (permanent service loss on network blip)
- **File**: `backend/gateway/internal/galaxy/client.go:22-56`
- **Issue**: Unlike the agent client at `agent/client.go` which has reconnect logic (line 184-240), circuit breaker (line 268-282), and retry policy (line 142-154), the galaxy client has none of these. It creates a single connection with `grpc.DialContext` at initialization, and if that connection drops, all galaxy gRPC calls will permanently fail. The setup.go code at line 222-225 logs a warning and sets `galaxyClient = nil` on init failure, but there is no mechanism to recover.
- **Context**:
  ```go
  // galaxy/client.go - no reconnect, no circuit breaker, no retry
  conn, err := grpc.DialContext(ctx, cfg.AgentAddress,
      grpc.WithTransportCredentials(creds),
      grpc.WithBlock(),
      grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
  )
  ```
  ```go
  // agent/client.go - has full resilience
  retryPolicy := `{"methodConfig": [{"name": [...], "retryPolicy": {...}}}]}`
  ```
- **Fix**: Add retry policy, reconnect logic, and circuit breaker matching the agent client pattern. At minimum, add `grpc.WithDefaultServiceConfig(retryPolicy)` to the dial options.

### ISSUE P1-02: Galaxy gRPC client uses `WithBlock()` causing startup hang

- **Severity**: P1 (startup failure propagation)
- **File**: `backend/gateway/internal/galaxy/client.go:48`
- **Issue**: The client uses `grpc.WithBlock()` which means `DialContext` will block until the connection is established or the timeout expires. The timeout is derived from `cfg.GRPCTimeoutSeconds` (default 5s). If the Python gRPC server is slow to start, this will cause the gateway to fail to initialize. The agent client does NOT use `WithBlock()`.
- **Context**:
  ```go
  // galaxy/client.go line 45-49
  conn, err := grpc.DialContext(ctx, cfg.AgentAddress,
      grpc.WithTransportCredentials(creds),
      grpc.WithBlock(),  // blocks until connected
  )
  ```
- **Fix**: Remove `grpc.WithBlock()` and use lazy connection establishment like the agent client. The setup.go code already handles nil galaxyClient gracefully.

### ISSUE P2-03: Galaxy client shares agent address configuration

- **Severity**: P2 (configuration coupling)
- **File**: `backend/gateway/internal/galaxy/client.go:45`
- **Issue**: The galaxy client connects to `cfg.AgentAddress` -- the same address as the agent client. While the galaxy gRPC service runs in the same Python process, this couples the configuration. If galaxy ever needs its own endpoint, this will require a config change.
- **Fix**: Add a dedicated `cfg.GalaxyAddress` config field or document that galaxy shares the agent address intentionally.

### ISSUE P2-04: SparkNode uses `context.Background()` instead of request context

- **Severity**: P2 (lost cancellation/tracing)
- **File**: `backend/gateway/internal/handler/galaxy_handler.go:192`
- **Issue**: The `SparkNode` handler calls `h.galaxyClient.RecordNodeInteraction(context.Background(), ...)` instead of using the request context. This means if the client disconnects, the gRPC call continues running. It also breaks OpenTelemetry trace propagation. Other handlers (UpdateMastery, RecordStudy, etc.) correctly use `c.Request.Context()`.
- **Context**:
  ```go
  // galaxy_handler.go line 191-193
  resp, grpcErr := h.galaxyClient.RecordNodeInteraction(
      context.Background(), userID, nodeID, "study", metadata,  // should use c.Request.Context()
  )
  ```
- **Fix**: Replace `context.Background()` with `c.Request.Context()` wrapped in a timeout.

---

## Category 4: CQRS Issues

### ISSUE P0-02: `RecordStudy` writes `performance_score` to column that does not exist

- **Severity**: P0 (every CQRS study recording fails with SQL error)
- **File**: `backend/gateway/internal/service/galaxy_command.go:343-355`
- **Issue**: The `RecordStudy` method inserts into `study_records` with columns `(id, user_id, node_id, duration_minutes, performance_score, created_at)`. However, the database schema at `schema.sql:5382-5394` defines `study_records` with columns `(user_id, node_id, task_id, study_minutes, mastery_delta, initial_mastery, record_type, id, ...)`. There is no `performance_score` column, and the column `study_minutes` is not `duration_minutes`. This SQL will always fail with a column-not-found error.
- **Context**:
  ```go
  // galaxy_command.go lines 343-348
  _, err := txCtx.Tx().Exec(ctx, `
      INSERT INTO study_records (
          id, user_id, node_id, duration_minutes, performance_score,
          created_at
      )
      VALUES ($1, $2, $3, $4, $5, NOW())
  ```
  ```sql
  -- schema.sql lines 5382-5394
  CREATE TABLE study_records (
      user_id uuid NOT NULL,
      node_id uuid NOT NULL,
      task_id uuid,
      study_minutes integer NOT NULL,
      mastery_delta double precision NOT NULL,
      initial_mastery double precision,
      record_type character varying(20),
      id uuid NOT NULL,
      ...
  );
  ```
- **Fix**: Rewrite the INSERT statement to match the actual schema:
  ```sql
  INSERT INTO study_records (id, user_id, node_id, study_minutes, mastery_delta, record_type, created_at, updated_at)
  VALUES ($1, $2, $3, $4, $5, 'study', NOW(), NOW())
  ```
  Calculate `mastery_delta` before insert and pass it as the parameter.

### ISSUE P1-03: Community `LikePost` fires event on `ON CONFLICT DO NOTHING` -- phantom like counts

- **Severity**: P1 (inflated like counts in Redis projections)
- **File**: `backend/gateway/internal/service/community_command.go:119-158`
- **Issue**: The `LikePost` method inserts into `post_likes` with `ON CONFLICT DO NOTHING`. However, the method always creates and saves a `PostLiked` domain event to the outbox regardless of whether the INSERT actually inserted a row. The `result.RowsAffected()` is not checked (unlike `UnlikePost` which does check at line 175). This means duplicate likes from the same user will generate phantom events, and the community_sync worker will increment the Redis like count for each phantom event.
- **Context**:
  ```go
  // community_command.go lines 123-131
  _, err := txCtx.Tx().Exec(ctx, `
      INSERT INTO post_likes (id, user_id, post_id, created_at, updated_at)
      VALUES ($1, $2, $3, NOW(), NOW())
      ON CONFLICT DO NOTHING
  `,
      ...
  )
  // No RowsAffected() check -- event is always published
  ```
- **Fix**: Use `result.RowsAffected()` to check if the insert actually happened before publishing the event, matching the pattern in `UnlikePost`:
  ```go
  result, err := txCtx.Tx().Exec(ctx, ...)
  if result.RowsAffected() == 0 {
      return nil  // Already liked, no event
  }
  ```

### ISSUE P1-04: `ON CONFLICT DO NOTHING` on node_relations has no constraint to conflict with

- **Severity**: P1 (duplicate relations silently inserted)
- **File**: `backend/gateway/internal/service/galaxy_command.go:291-298`
- **Issue**: The `CreateRelation` method uses `ON CONFLICT DO NOTHING` but there is no unique constraint on `(source_node_id, target_node_id, relation_type)` in the `node_relations` table. The only constraint is the primary key on `id`. Since `id` is always a new UUID, `ON CONFLICT DO NOTHING` will never trigger, and duplicate relations will be silently inserted.
- **Context**:
  ```go
  // galaxy_command.go lines 291-298
  _, err := txCtx.Tx().Exec(ctx, `
      INSERT INTO node_relations (...)
      VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
      ON CONFLICT DO NOTHING
  ```
  ```sql
  -- schema.sql: only PK on id, no unique on (source, target, type)
  ALTER TABLE ONLY node_relations
      ADD CONSTRAINT node_relations_pkey PRIMARY KEY (id);
  ```
- **Fix**: Add a unique constraint: `ALTER TABLE node_relations ADD CONSTRAINT uq_node_relations_source_target_type UNIQUE (source_node_id, target_node_id, relation_type);` and ensure `deleted_at IS NULL` is handled (use partial unique index if soft-delete is involved).

### ISSUE P2-05: Galaxy sync worker Redis projections have no TTL -- unbounded memory growth

- **Severity**: P2 (Redis memory exhaustion over time)
- **File**: `backend/gateway/internal/worker/galaxy_sync.go:192, 266, 323`
- **Issue**: All Redis SET operations in the galaxy sync worker use TTL of 0 (no expiry): `pipe.Set(ctx, "galaxy:node:"+nodeIDStr, viewJSON, 0)`. This means node views, user node views, relation data, and study records accumulate in Redis forever. For a system with thousands of knowledge nodes and growing users, this will gradually consume all Redis memory.
- **Context**:
  ```go
  // galaxy_sync.go line 192
  pipe.Set(ctx, "galaxy:node:"+nodeIDStr, viewJSON, 0)  // TTL=0 = no expiry
  ```
- **Fix**: Set reasonable TTLs (e.g., 24h for node views, 1h for user-specific data) and rely on cache-aside pattern to rebuild from DB on cache miss.

### ISSUE P2-06: `handleMasteryUpdated` applies delta to cached value instead of re-reading from DB

- **Severity**: P2 (projection drift from source of truth)
- **File**: `backend/gateway/internal/worker/galaxy_sync.go:336-413`
- **Issue**: The mastery update handler reads the current Redis view, applies the delta locally, and writes back. This is an eventually consistent read-modify-write on a cache, not the source of truth. If the Redis view is stale (e.g., due to missed events, Redis restart, or manual cache clear), the new value will be based on incorrect data. The `handleNodeCreated` and `handleNodeUnlocked` handlers correctly re-read from DB, but mastery updates do not.
- **Context**:
  ```go
  // galaxy_sync.go lines 374-375
  view.MasteryScore = clamp(view.MasteryScore+masteryDelta, 0, 1)  // applies to cached value
  ```
- **Fix**: Re-read `user_node_status` from DB after the event and rebuild the view, consistent with the other handlers. Alternatively, include the new absolute mastery value in the event payload instead of a delta.

### ISSUE P2-07: Community sync worker uses non-atomic read-modify-write for like counts

- **Severity**: P2 (race condition on concurrent likes)
- **File**: `backend/gateway/internal/worker/community_sync.go:211-253`
- **Issue**: The `handlePostLiked` handler GETs the post view JSON, unmarshals, increments `LikeCount`, marshals, and SETs it back. If two like events are processed concurrently (or even in quick succession), the second read will see the old value, and one increment will be lost. This is a classic TOCTOU race.
- **Context**:
  ```go
  // community_sync.go lines 219-243
  viewJSON, err := w.redis.Get(ctx, viewKey).Bytes()  // read
  var view service.PostView
  json.Unmarshal(viewJSON, &view)
  view.LikeCount++  // modify
  w.redis.Set(ctx, viewKey, updatedJSON, 0)  // write
  ```
- **Fix**: Use Redis HINCRBY for the like count field instead of full read-modify-write, or use a Lua script for atomicity.

### ISSUE P3-02: `handleNodeExpanded` silently swallows missing view errors

- **Severity**: P3 (stale data, no alert)
- **File**: `backend/gateway/internal/worker/galaxy_sync.go:288-333`
- **Issue**: When a `NodeExpanded` event arrives but the user node view doesn't exist in Redis, the handler logs a warning and returns nil (success). This silently drops the expansion state. If the view is later created by a different event, it will have `is_collapsed=true` (the default), which is incorrect.
- **Fix**: When the view is not found, fall back to DB to fetch the user node status and create the Redis view, then set `is_collapsed=false`. Alternatively, include a `CreateIfMissing` flag.

---

## Category 5: Database Schema Issues

### ISSUE P1-05: Missing unique constraint on `node_relations(source_node_id, target_node_id, relation_type)`

- **Severity**: P1 (data duplication, see P1-04)
- **File**: `backend/gateway/internal/db/schema.sql:3785-3798`
- **Issue**: The `node_relations` table only has a primary key on `id`. There is no unique constraint on the logical business key `(source_node_id, target_node_id, relation_type)`. This allows duplicate relations to be inserted, which will cause duplicate edges in the galaxy graph and incorrect BFS results in `GetLearningPath`.
- **Fix**: Add a partial unique index:
  ```sql
  CREATE UNIQUE INDEX uq_node_relations_unique_active
  ON node_relations (source_node_id, target_node_id, relation_type)
  WHERE deleted_at IS NULL;
  ```

### ISSUE P2-08: Missing composite index on `study_records(user_id, node_id)`

- **Severity**: P2 (slow queries for user-node study history)
- **File**: `backend/gateway/internal/db/schema.sql:16108-16118`
- **Issue**: The `study_records` table has individual indexes on `user_id` and `node_id` (lines 16115-16118) but no composite index on `(user_id, node_id)`. Queries like "get all study records for this user and node" (common in mastery calculation) will use a single-column index scan plus filter, which is suboptimal.
- **Fix**: Add:
  ```sql
  CREATE INDEX ix_study_records_user_node ON study_records (user_id, node_id);
  ```

### ISSUE P2-09: Missing composite index on `study_records(user_id, created_at)`

- **Severity**: P2 (slow queries for user study timeline)
- **File**: `backend/gateway/internal/db/schema.sql:16108-16118`
- **Issue**: Common queries like "get recent study records for a user" need `(user_id, created_at DESC)`. Without this composite index, the planner must do an index scan on `user_id` then sort by `created_at`.
- **Fix**: Add:
  ```sql
  CREATE INDEX ix_study_records_user_created ON study_records (user_id, created_at DESC);
  ```

### ISSUE P3-03: `knowledge_nodes.community_signal` uses `json` instead of `jsonb`

- **Severity**: P3 (performance)
- **File**: `backend/gateway/internal/db/schema.sql:3292`
- **Issue**: The `community_signal` column is `json` (not `jsonb`), while `keywords`, `sector_weights`, `chunk_refs` all use `jsonb`. The `json` type stores text and cannot be indexed or efficiently queried. This is inconsistent with the rest of the schema and the Python model which declares it as `JSONBCompat`.
- **Context**:
  ```sql
  -- schema.sql line 3292
  community_signal json,  -- should be jsonb
  ```
- **Fix**: Change to `jsonb`:
  ```sql
  ALTER TABLE knowledge_nodes ALTER COLUMN community_signal TYPE jsonb USING community_signal::jsonb;
  ```

---

## Category 6: Security Issues

### ISSUE P1-06: Community `GetFeed` endpoint has no authentication

- **Severity**: P1 (unauthorized data access)
- **File**: `backend/gateway/internal/api/v1/community.go:31`
- **Issue**: In `RegisterRoutes`, the `GET /feed` route is registered on the `group` (unprotected) group instead of the `protected` group that uses `authMiddleware`. This means anyone can access the feed without authentication. The handler at line 85 tries to extract `user_id` via `c.GetString("user_id")` but this will be empty for unauthenticated requests.
- **Context**:
  ```go
  // community.go lines 27-33
  protected := group.Group("")
  protected.Use(authMiddleware)
  protected.POST("/posts", h.CreatePost)
  protected.POST("/posts/:id/like", h.LikePost)
  group.GET("/feed", h.GetFeed)  // NOT in protected group!
  ```
- **Fix**: Move `group.GET("/feed", h.GetFeed)` into the `protected` group:
  ```go
  protected.GET("/feed", h.GetFeed)
  ```

### ISSUE P2-10: Redis SCAN with count=0 in cache invalidation

- **Severity**: P2 (potential Redis blocking)
- **File**: `backend/gateway/internal/handler/galaxy_handler.go:363`
- **Issue**: The `invalidateGalaxyGraphCache` method calls `h.cache.Scan(ctx, 0, pattern, 0)` with count=0. In Redis, SCAN with COUNT 0 uses the server default (typically 10), which is fine. However, the pattern `*:view:get_galaxy_graph:*` is a broad pattern that could match many keys. If the Redis instance has millions of keys, this SCAN could be slow. The function also collects all matching keys into a slice before deleting, which could use significant memory.
- **Context**:
  ```go
  // galaxy_handler.go lines 362-377
  pattern := "*:view:get_galaxy_graph:" + userID + ":*"
  iter := h.cache.Scan(ctx, 0, pattern, 0).Iterator()
  var keys []string
  for iter.Next(ctx) {
      keys = append(keys, iter.Val())
  }
  ```
- **Fix**: Use a more targeted cache key pattern, or use `DEL` with the specific key pattern. Consider using Redis KEYS command in development only and a hash-based cache index in production.

---

## Category 7: Data Consistency Issues

### ISSUE P1-07: Mastery scale mismatch between Go CQRS (0-100) and galaxy_sync worker (0-1)

- **Severity**: P1 (mastery values out of range in Redis projections)
- **File**: `backend/gateway/internal/service/galaxy_command.go:64`, `backend/gateway/internal/worker/galaxy_sync.go:375`
- **Issue**: The Go `GalaxyCommandService` clamps mastery to `LEAST(GREATEST(mastery_score + delta, 0), 100)` (range 0-100, matching the DB schema). However, the galaxy sync worker's `handleMasteryUpdated` at line 375 clamps to `clamp(view.MasteryScore+masteryDelta, 0, 1)` (range 0-1). Since the Redis projection stores the same `mastery_score` that the DB has (0-100 scale), clamping to 0-1 will always result in 1.0 for any non-zero mastery, completely breaking the mastery display.
- **Context**:
  ```go
  // galaxy_command.go line 64
  const maxMasteryScore = 100.0

  // galaxy_sync.go line 375
  view.MasteryScore = clamp(view.MasteryScore+masteryDelta, 0, 1)  // should be 0, 100
  ```
- **Fix**: Change the clamp range to match the DB scale:
  ```go
  view.MasteryScore = clamp(view.MasteryScore+masteryDelta, 0, 100)
  ```

### ISSUE P2-11: Go `RecordStudy` updates mastery without checking node is unlocked

- **Severity**: P2 (data integrity)
- **File**: `backend/gateway/internal/service/galaxy_command.go:365-374`
- **Issue**: The `RecordStudy` method updates `user_node_status` with `WHERE user_id = $1 AND node_id = $2` but does NOT check `is_unlocked = true`. In contrast, `UpdateMastery` at line 244 and `ExpandNode` at line 421 both check `AND is_unlocked = true`. This means `RecordStudy` will silently update mastery for locked nodes, bypassing the unlock gate.
- **Context**:
  ```go
  // galaxy_command.go line 373
  WHERE user_id = $1 AND node_id = $2  // missing: AND is_unlocked = true
  ```
- **Fix**: Add `AND is_unlocked = true` to the WHERE clause, or auto-unlock the node if a study is recorded.

---

## Category 8: Error Propagation Issues

### ISSUE P1-08: `NewGalaxyHandler` returns nil on URL parse failure -- nil pointer panic

- **Severity**: P1 (gateway crash)
- **File**: `backend/gateway/internal/handler/galaxy_handler.go:41-45`
- **Issue**: `NewGalaxyHandler` logs an error and returns `nil` if the backend URL fails to parse. The caller in `setup.go:284` does not check for nil:
  ```go
  galaxyHandler := handler.NewGalaxyHandler(galaxyClient, galaxyCommandService, rdb, cfg.BackendURL)
  ```
  This will cause a nil pointer dereference when any route is called.
- **Context**:
  ```go
  // galaxy_handler.go lines 41-45
  targetURL, err := url.Parse(backendURL)
  if err != nil {
      log.Printf("Failed to parse backend URL: %v", err)
      return nil  // caller does not check
  }
  ```
- **Fix**: Return an error from `NewGalaxyHandler` and handle it in `setup.go`, or panic early with a clear message since a missing backend URL is a startup config error.

### ISSUE P3-04: Python gRPC service returns empty response objects on error instead of proper gRPC status

- **Severity**: P3 (client cannot distinguish success from failure)
- **File**: `backend/app/services/galaxy_grpc_service.py:260, 329, 362, 427, 463, 498, 534`
- **Issue**: When catching exceptions, multiple gRPC methods return empty proto objects like `galaxy_service_pb2.GetUserGalaxyResponse()` after setting the gRPC status code. However, the Go client checks `err == nil && resp != nil` before using the response. If the Python side sets the error code but also returns a response object, the Go client may interpret the nil error as success. The gRPC framework should handle this, but the pattern is inconsistent -- some methods return empty protos while `UpdateNodeMastery` correctly returns `success=False`.
- **Context**:
  ```python
  # galaxy_grpc_service.py lines 256-260
  except Exception as e:
      logger.error(f"gRPC GetUserGalaxy failed: {e}")
      context.set_code(grpc.StatusCode.INTERNAL)
      context.set_details(str(e))
      return galaxy_service_pb2.GetUserGalaxyResponse()  # empty response
  ```
- **Fix**: After setting the error code, return `None` or raise an exception. The gRPC framework will serialize the error to the client. Or consistently use the `success=False` pattern across all responses.

### ISSUE P3-05: SearchNodes in handler silently ignores JSON unmarshal error

- **Severity**: P3 (silent error swallowing)
- **File**: `backend/gateway/internal/handler/galaxy_handler.go:439`
- **Issue**: In `SearchNodesGPRC`, when trying to parse the JSON body as fallback, the error from `json.Unmarshal` is silently ignored. If the body contains malformed JSON, `query` will remain empty, and the handler will return a 400 error saying "query required", which is misleading.
- **Context**:
  ```go
  // galaxy_handler.go line 439
  json.Unmarshal(rawBody, &body)  // error ignored
  ```
- **Fix**: Check and handle the unmarshal error, or at least log it for debugging.

---

## Category 9: Performance Issues

### ISSUE P2-12: Python `GetLearningPath` BFS loads all edges per node in separate queries

- **Severity**: P2 (O(N) DB queries for N nodes in path)
- **File**: `backend/app/services/galaxy_grpc_service.py:364-427`
- **Issue**: The BFS implementation queries `NodeRelation` for each node visited individually (line 393-397). For a graph with thousands of nodes, this creates one DB query per BFS step. This is a classic N+1 query problem.
- **Context**:
  ```python
  # galaxy_grpc_service.py lines 393-397
  stmt = select(NodeRelation).where(
      NodeRelation.source_node_id == _UUID(current)
  ).limit(100)
  result = await db.execute(stmt)
  ```
- **Fix**: Pre-load all edges into memory with a single query (or a batched query), then run BFS in-memory. For a galaxy with thousands of nodes, the full edge set is likely small enough to fit in memory.

### ISSUE P2-13: Galaxy handler cache invalidation uses SCAN on every write

- **Severity**: P2 (write amplification)
- **File**: `backend/gateway/internal/handler/galaxy_handler.go:353-378`
- **Issue**: After every mastery update and study recording, `invalidateGalaxyGraphCache` runs a Redis SCAN to find and delete matching cache keys. SCAN is O(N) over the total key space. For high-frequency operations like spark/study, this creates significant Redis load.
- **Fix**: Use a deterministic cache key (e.g., `galaxy:graph:{user_id}`) and delete it directly, or maintain a cache key index in a Redis hash.

---

## Category 10: Concurrency Issues

### ISSUE P0-03: Python collaborative sessions use module-level dict without thread safety

- **Severity**: P0 (data corruption in concurrent CRDT sessions)
- **File**: `backend/app/services/galaxy_grpc_service.py:36-73`
- **Issue**: The `_active_collaborative_sessions` dictionary is a module-level `OrderedDict` accessed from multiple async coroutines. While Python's GIL prevents true data races, the `_prune_inactive_collaborative_sessions` function iterates and deletes from the dict simultaneously, which can raise `RuntimeError: dictionary changed size during iteration` if concurrent requests trigger pruning. Additionally, `datetime.utcnow()` is deprecated since Python 3.12.
- **Context**:
  ```python
  # galaxy_grpc_service.py lines 43-51
  def _prune_inactive_collaborative_sessions() -> None:
      now = _utcnow()
      expired_ids = [
          galaxy_id
          for galaxy_id, entry in _active_collaborative_sessions.items()
          if now - entry.last_accessed_at > _COLLABORATIVE_SESSION_TTL
      ]
      for galaxy_id in expired_ids:
          _active_collaborative_sessions.pop(galaxy_id, None)
  ```
- **Fix**: Use `asyncio.Lock` around all accesses, or switch to an LRU cache implementation. Replace `datetime.utcnow()` with `datetime.now(datetime.UTC)`.

### ISSUE P3-06: Community `PostView.LikeCount` in Redis is not atomic with DB

- **Severity**: P3 (eventual inconsistency)
- **File**: `backend/gateway/internal/worker/community_sync.go:211-253`
- **Issue**: The Redis `PostView.LikeCount` is maintained by incrementing on events, but is never reconciled with the DB `post_likes` count. If the worker misses events, the Redis count will diverge permanently.
- **Fix**: Add a periodic reconciliation job that counts likes from DB and updates Redis, or include the authoritative count in the response.

### ISSUE P3-07: `community_command.go` `ON CONFLICT DO NOTHING` for post_likes has no unique constraint

- **Severity**: P3 (duplicate likes possible)
- **File**: `backend/gateway/internal/service/community_command.go:123-131`, `backend/gateway/internal/db/schema.sql`
- **Issue**: Similar to P1-04 for node_relations, the `post_likes` INSERT uses `ON CONFLICT DO NOTHING` but there is no documented unique constraint on `(user_id, post_id)` in the schema. If only a primary key on `id` exists, the `ON CONFLICT` clause is a no-op. This is less severe than P1-04 because the `post_likes` table may have a unique constraint in a migration not reflected in the schema dump.
- **Fix**: Verify the unique constraint exists. If not, add one:
  ```sql
  CREATE UNIQUE INDEX uq_post_likes_user_post ON post_likes (user_id, post_id);
  ```

---

## Summary Table

| ID | Severity | Category | File | Line(s) | Issue |
|----|----------|----------|------|---------|-------|
| P0-01 | P0 | gRPC | galaxy/client.go | 22-56 | No reconnect/retry on galaxy gRPC client |
| P0-02 | P0 | CQRS | galaxy_command.go | 343-355 | `performance_score` column does not exist in study_records |
| P0-03 | P0 | Concurrency | galaxy_grpc_service.py | 36-73 | Module-level dict without thread safety |
| P1-01 | P1 | Routing | community.go + proxy_routes.go | 24-33, 528-535 | Community CQRS handler never registered |
| P1-02 | P1 | gRPC | galaxy/client.go | 48 | WithBlock causes startup hang |
| P1-03 | P1 | CQRS | community_command.go | 119-158 | LikePost fires event on duplicate |
| P1-04 | P1 | CQRS | galaxy_command.go | 291-298 | ON CONFLICT with no constraint |
| P1-05 | P1 | Schema | schema.sql | 3785-3798 | Missing unique on node_relations |
| P1-06 | P1 | Security | community.go | 31 | GetFeed has no auth |
| P1-07 | P1 | Data | galaxy_command.go:64, galaxy_sync.go:375 | 64, 375 | Mastery scale 0-100 vs 0-1 mismatch |
| P1-08 | P1 | Error | galaxy_handler.go + setup.go | 41-45, 284 | nil handler on bad URL |
| P2-01 | P2 | Proto | galaxy_service.proto:63 | 63 | int32 mastery truncates float |
| P2-02 | P2 | Routing | galaxy_handler.go | 72-134 | Duplicate node/nodes routes |
| P2-03 | P2 | Config | galaxy/client.go | 45 | Shares agent address config |
| P2-04 | P2 | gRPC | galaxy_handler.go | 192 | context.Background() breaks tracing |
| P2-05 | P2 | CQRS | galaxy_sync.go | 192,266,323 | Redis keys have no TTL |
| P2-06 | P2 | CQRS | galaxy_sync.go | 336-413 | Delta on cached value, not DB |
| P2-07 | P2 | CQRS | community_sync.go | 211-253 | Non-atomic like count update |
| P2-08 | P2 | Schema | schema.sql | 16108-16118 | Missing composite idx study_records |
| P2-09 | P2 | Schema | schema.sql | 16108-16118 | Missing composite idx study_records |
| P2-10 | P2 | Security | galaxy_handler.go | 363 | Unbounded SCAN in cache invalidation |
| P2-11 | P2 | Data | galaxy_command.go | 365-374 | RecordStudy bypasses unlock check |
| P2-12 | P2 | Perf | galaxy_grpc_service.py | 364-427 | N+1 BFS queries |
| P2-13 | P2 | Perf | galaxy_handler.go | 353-378 | SCAN on every write |
| P3-01 | P3 | Proto | galaxy_service.proto:102 | 102 | tags vs keywords naming mismatch |
| P3-02 | P3 | CQRS | galaxy_sync.go | 288-333 | Missing view silently dropped |
| P3-03 | P3 | Schema | schema.sql | 3292 | json instead of jsonb |
| P3-04 | P3 | Error | galaxy_grpc_service.py | 260,329,362 | Empty response on error |
| P3-05 | P3 | Error | galaxy_handler.go | 439 | Silent JSON unmarshal error |
| P3-06 | P3 | Concurrency | community_sync.go | 211-253 | Redis count never reconciled with DB |
| P3-07 | P3 | Concurrency | community_command.go | 123-131 | ON CONFLICT may need unique constraint |

---

## Recommended Fix Priority

**Immediate (P0)**:
1. Fix `galaxy_command.go` RecordStudy SQL to match actual `study_records` schema (P0-02)
2. Add reconnect/retry to galaxy gRPC client (P0-01)
3. Add `asyncio.Lock` around collaborative sessions dict (P0-03)

**High Priority (P1)**:
1. Fix mastery scale mismatch in galaxy_sync.go clamp (P1-07)
2. Fix LikePost to check RowsAffected before event (P1-03)
3. Add unique constraint on node_relations (P1-04/P1-05)
4. Fix community.go GetFeed auth (P1-06)
5. Decide whether community CQRS handler routes should be registered or removed (P1-01)
6. Remove `WithBlock()` from galaxy client (P1-02)
7. Handle nil GalaxyHandler in setup.go (P1-08)

**Medium Priority (P2)**:
1. Add TTL to galaxy Redis keys (P2-05)
2. Fix mastery delta application to re-read from DB (P2-06)
3. Fix context.Background() in SparkNode (P2-04)
4. Add composite indexes on study_records (P2-08, P2-09)
5. Optimize BFS to batch-load edges (P2-12)
6. Optimize cache invalidation (P2-13)
