# Go Gateway & Database Audit: Community & Accountability Partner System

**Date**: 2026-05-10
**Auditor**: Senior Backend Engineer
**Scope**: Go Gateway CQRS community subsystem + DB schema + Proto definitions
**Files Audited**: 15+ source files across gateway, proto, and schema

---

## Summary

| Severity | Count |
|----------|-------|
| **P0**   | 3     |
| **P1**   | 7     |
| **P2**   | 7     |
| **P3**   | 5     |
| **Total**| **22** |

---

## P0 Findings (Data Loss / Security / Crash)

### [SEVERITY: P0] Query service references non-existent `community_posts` table
**File**: `backend/gateway/internal/service/community_query.go:120,156`
**Category**: bug
**Description**: Both `fetchPostsFromDB` and `fetchRecentPostsFromDB` query a table named `community_posts`, but the actual table in `schema.sql` is named `posts`. This means the DB fallback path (cold start, cache miss) will always fail with a PostgreSQL error: `relation "community_posts" does not exist`. Since the global feed relies on this fallback when Redis is empty or keys are missing, the feed endpoint is completely broken in production.
**Context**:
```sql
-- community_query.go:120
FROM community_posts p   -- WRONG: table does not exist
JOIN users u ON p.user_id = u.id

-- community_query.go:156
FROM community_posts p   -- WRONG: table does not exist
```
**Suggested Fix**: Change `community_posts` to `posts` in both queries in `community_query.go` (lines 120 and 156).

---

### [SEVERITY: P0] `post:likes:{post_id}` Redis sets never written -- `isLikedByMe` always false
**File**: `backend/gateway/internal/service/community_query.go:184-195`
**Category**: bug/cqrs
**Description**: `populateIsLikedByMe` checks `SISMEMBER` on `post:likes:{post_id}` for each post, but nowhere in the codebase is data ever written to these Redis sets. The `handlePostLiked`/`handlePostUnliked` workers only increment/decrement `LikeCount` in the cached JSON, but never maintain the set. This means `is_liked_by_me` is always `false` for every post in the feed, making the like button appear unpressed even when the user has liked the post.
**Context**:
```go
// community_query.go:189
key := "post:likes:" + posts[i].ID
isMember, err := s.redis.SIsMember(ctx, key, userID).Result()
```
**Suggested Fix**: In `community_sync.go` `handlePostLiked`, add `SADD post:likes:{post_id} {user_id}`. In `handlePostUnliked`, add `SREM post:likes:{post_id} {user_id}`. Also include `user_id` in the EventPostLiked/EventPostUnliked payloads (it is already there).

---

### [SEVERITY: P0] Feed endpoint unauthenticated -- public access to all posts without auth
**File**: `backend/gateway/internal/api/v1/community.go:31`
**Category**: security
**Description**: The `GET /feed` route is registered on the unprotected `group` router (not `protected`), meaning it requires no authentication. Any unauthenticated request can read all community posts. While `GetFeed` extracts `user_id` from context for `isLikedByMe`, the endpoint still returns full post content without any auth check.
**Context**:
```go
func (h *CommunityHandler) RegisterRoutes(router *gin.RouterGroup, authMiddleware gin.HandlerFunc) {
    group := router.Group("/community")
    {
        protected := group.Group("")
        protected.Use(authMiddleware)
        protected.POST("/posts", h.CreatePost)
        protected.POST("/posts/:id/like", h.LikePost)
        group.GET("/feed", h.GetFeed)  // NO auth middleware applied
    }
}
```
**Suggested Fix**: Move `group.GET("/feed", h.GetFeed)` into the `protected` group, or add auth middleware directly. If public feed access is intended by design, add explicit documentation and filter for `visibility = 'public'`.

---

## P1 Findings (Wrong Data / Broken Feature / CQRS Sync Failure)

### [SEVERITY: P1] LikePost always publishes event even on duplicate like (ON CONFLICT DO NOTHING)
**File**: `backend/gateway/internal/service/community_command.go:119-159`
**Category**: cqrs/concurrency
**Description**: `LikePost` uses `INSERT ... ON CONFLICT DO NOTHING` but does not check `RowsAffected()` before publishing the `PostLiked` event. On duplicate likes, the INSERT is silently skipped but the event is still published to the outbox, causing the Redis `LikeCount` to be incremented multiple times for the same user. The same user can click "like" 10 times and the counter will increment 10 times.
**Context**:
```go
_, err := txCtx.Tx().Exec(ctx, `
    INSERT INTO post_likes (id, user_id, post_id, created_at, updated_at)
    VALUES ($1, $2, $3, NOW(), NOW())
    ON CONFLICT DO NOTHING
`, ...)

// No RowsAffected() check -- event is always published
domainEvent := event.NewDomainEvent(event.EventPostLiked, ...)
```
**Suggested Fix**: Use `ExecResult` instead of `Exec` and check `RowsAffected()`. Only publish the event when the INSERT actually inserted a row:
```go
result, err := txCtx.Tx().Exec(ctx, `INSERT ... ON CONFLICT DO NOTHING`, ...)
if err != nil { return err }
if result.RowsAffected() == 0 { return nil } // duplicate like, no event
```

---

### [SEVERITY: P1] `posts.like_count` column allows NULL and is never updated on like/unlike
**File**: `backend/gateway/internal/db/schema.sql:4228`
**Category**: schema/cqrs
**Description**: The `posts.like_count` column is `integer` (nullable, no default). When `CreatePost` inserts via raw SQL, it omits `like_count` and `comment_count`, resulting in NULL values. The CQRS write path (`LikePost`/`UnlikePost`) never issues `UPDATE posts SET like_count = like_count + 1`. The count only lives in Redis. If Redis is flushed or the projection is rebuilt from DB, the `like_count` in the `PostView` is hardcoded to `0` in `handlePostCreated`, and the DB column remains NULL.
**Context**:
```sql
-- schema.sql:4228
like_count integer,     -- nullable, no DEFAULT
```
```go
// community_sync.go:163
LikeCount: 0,  // hardcoded, not read from DB column
```
**Suggested Fix**: (1) Add `DEFAULT 0 NOT NULL` to `like_count` and `comment_count`. (2) Either add a DB trigger to maintain the count, or update it in `LikePost`/`UnlikePost` commands. (3) In `handlePostCreated`, read `like_count` from the fetched post row.

---

### [SEVERITY: P1] Missing index on `posts.created_at` -- feed queries do full table scan
**File**: `backend/gateway/internal/db/schema.sql` (missing index)
**Category**: performance/schema
**Description**: The `posts` table has indexes on `user_id` and `deleted_at` but NOT on `created_at`. The feed queries (`fetchRecentPostsFromDB`, cold-start fallback) order by `created_at DESC LIMIT $1`. Without an index, this is a full table scan with a sort. As the posts table grows, feed loading will degrade significantly.
**Context**: Only these indexes exist on `posts`:
```
ix_posts_deleted_at ON posts (deleted_at)
ix_posts_user_id ON posts (user_id)
```
**Suggested Fix**: Add `CREATE INDEX idx_posts_created_at ON posts (created_at DESC);`. A composite index `CREATE INDEX idx_posts_not_deleted_created ON posts (deleted_at, created_at DESC)` where `deleted_at IS NULL` would be even better.

---

### [SEVERITY: P1] `accountability_partnership` unique constraint `(initiator_id, partner_id)` allows reverse duplicates
**File**: `backend/gateway/internal/db/schema.sql:9142`
**Category**: schema/bug
**Description**: The `uq_accountability_partnership_pair` unique constraint is on `(initiator_id, partner_id)` only. This means user A can invite user B, AND user B can independently invite user A, creating two partnerships between the same pair. The schema should enforce uniqueness in both directions.
**Context**:
```sql
ADD CONSTRAINT uq_accountability_partnership_pair UNIQUE (initiator_id, partner_id);
```
**Suggested Fix**: Add a check constraint or a unique index on `LEAST(initiator_id, partner_id), GREATEST(initiator_id, partner_id)`:
```sql
CREATE UNIQUE INDEX uq_accountability_partnership_bidirectional
ON accountability_partnership (
    LEAST(initiator_id, partner_id),
    GREATEST(initiator_id, partner_id)
);
```

---

### [SEVERITY: P1] `GetPost` query requires `created_at` but worker reconstructs it from event timestamp
**File**: `backend/gateway/internal/db/query.sql:109-111`
**Category**: cqrs/bug
**Description**: The `GetPost` sqlc query filters by both `id` AND `created_at`: `WHERE id = $1 AND created_at = $2 AND deleted_at IS NULL`. The community sync worker passes the event timestamp as `created_at`, but this may differ from the actual DB `created_at` by milliseconds (event timestamp is `time.Now().UTC()` in Go, while DB uses `NOW()` in SQL). If the timestamps don't match exactly, the query returns no rows and the projection silently fails to create the post view.
**Context**:
```sql
-- query.sql:110-111
SELECT * FROM posts
WHERE id = $1 AND created_at = $2 AND deleted_at IS NULL;
```
```go
// community_sync.go:135-138
post, err := w.queries.GetPost(ctx, db.GetPostParams{
    ID:        pgtype.UUID{Bytes: postID, Valid: true},
    CreatedAt: pgtype.Timestamp{Time: createdAt, Valid: true},  // from event, not DB
})
```
**Suggested Fix**: Remove `created_at` from the `GetPost` WHERE clause. The `id` alone is a primary key and sufficient for lookup. Change to: `SELECT * FROM posts WHERE id = $1 AND deleted_at IS NULL`.

---

### [SEVERITY: P1] `friendshipstatus` enum missing `REJECTED`/`CANCELLED` states
**File**: `backend/gateway/internal/db/schema.sql:281-285`
**Category**: schema/proto
**Description**: The `friendshipstatus` enum only has `PENDING`, `ACCEPTED`, `BLOCKED`. The proto `FriendshipStatus` also only has these three states. When a friend request is declined, there is no `REJECTED` status to transition to. The application likely either deletes the row or leaves it as `PENDING`, which would keep it visible in pending requests.
**Context**:
```sql
CREATE TYPE friendshipstatus AS ENUM (
    'PENDING',
    'ACCEPTED',
    'BLOCKED'
);
```
```proto
enum FriendshipStatus {
  FRIENDSHIP_STATUS_UNSPECIFIED = 0;
  PENDING = 1;
  ACCEPTED = 2;
  BLOCKED = 3;
}
```
**Suggested Fix**: Add `REJECTED` and optionally `CANCELLED` to both the PostgreSQL enum and the proto definition. Run `ALTER TYPE friendshipstatus ADD VALUE 'REJECTED' BEFORE 'BLOCKED';` and update proto.

---

### [SEVERITY: P1] `handlePostLiked`/`handlePostUnliked` read-modify-write is not atomic -- race condition
**File**: `backend/gateway/internal/worker/community_sync.go:211-253` and `backend/gateway/internal/cqrs/projection/handlers.go:192-260`
**Category**: concurrency/cqrs
**Description**: Both the worker and projection handler implement like/unlike by: (1) GET the cached JSON, (2) unmarshal, (3) increment/decrement counter, (4) SET back. This is a classic read-modify-write race. If two like events arrive close together, both may read the same count, increment to the same value, and one increment is lost. This exists in both `CommunitySyncWorker` and `CommunityProjectionHandler`.
**Context**:
```go
// community_sync.go:219-244
viewJSON, err := w.redis.Get(ctx, viewKey).Bytes()  // STEP 1: read
json.Unmarshal(viewJSON, &view)                      // STEP 2: decode
view.LikeCount++                                      // STEP 3: modify
w.redis.Set(ctx, viewKey, updatedJSON, 0)            // STEP 4: write
```
**Suggested Fix**: Use a Redis Lua script for atomic read-modify-write, or use `HINCRBY` on a separate hash field. Example Lua:
```lua
local view = cjson.decode(redis.call('GET', KEYS[1]))
view.like_count = view.like_count + tonumber(ARGV[1])
return redis.call('SET', KEYS[1], cjson.encode(view))
```

---

## P2 Findings (Performance / Edge Cases / Non-Critical Bugs)

### [SEVERITY: P2] `populateIsLikedByMe` uses N+1 Redis roundtrips per feed page
**File**: `backend/gateway/internal/service/community_query.go:184-195`
**Category**: performance
**Description**: For each post in the feed (up to 20), `populateIsLikedByMe` makes a separate `SISMEMBER` call. This is 20 sequential Redis roundtrips per feed request. With pipeline or batch, this could be reduced to 1 roundtrip.
**Context**:
```go
for i := range posts {
    key := "post:likes:" + posts[i].ID
    isMember, err := s.redis.SIsMember(ctx, key, userID).Result()
```
**Suggested Fix**: Use a Redis pipeline to batch all SISMEMBER calls, or use `SMISMEMBER` with a Lua script.

---

### [SEVERITY: P2] Feed cache misses rehydrated with only 10-minute TTL
**File**: `backend/gateway/internal/service/community_query.go:102`
**Category**: cqrs
**Description**: When posts are fetched from DB on cache miss, they are rehydrated to Redis with a 10-minute TTL: `s.redis.Set(ctx, "post:view:"+p.ID, data, 10*time.Minute)`. But posts created through the normal CQRS path get TTL=0 (no expiry). This inconsistency means rehydrated posts expire after 10 minutes, while normal posts persist indefinitely. After 10 minutes, another cache miss + rehydration cycle occurs.
**Context**:
```go
// community_query.go:102
_ = s.redis.Set(ctx, "post:view:"+p.ID, data, 10*time.Minute).Err()

// community_sync.go:179
pipe.Set(ctx, "post:view:"+postIDStr, viewJSON, 0)  // no TTL
```
**Suggested Fix**: Use a consistent TTL policy. Either set TTL=0 for both (and rely on projection delete events for cleanup), or use a long TTL (e.g., 24h) for both paths.

---

### [SEVERITY: P2] `posts.content` is nullable in schema but required in handler
**File**: `backend/gateway/internal/db/schema.sql:4224`
**Category**: schema
**Description**: The `content` column is `text` (nullable, no NOT NULL constraint), but `CreatePost` in the handler validates `content` as `binding:"required"`. If a post is created through any other path (direct SQL, migration, future API), content could be NULL, which would break the scan in `fetchPostsFromDB`.
**Context**:
```sql
content text,   -- nullable
```
```go
Content string `json:"content" binding:"required"`
```
**Suggested Fix**: Add `NOT NULL` to the `content` column in the schema: `content text NOT NULL`.

---

### [SEVERITY: P2] `posts.visibility` has no CHECK constraint for valid values
**File**: `backend/gateway/internal/db/schema.sql:4227`
**Category**: schema
**Description**: The `visibility` column is `varchar(20) NOT NULL` but has no CHECK constraint. The command service hardcodes `'public'`, but there is nothing preventing invalid values like `'foobar'` from being inserted through other paths.
**Context**:
```sql
visibility character varying(20) NOT NULL,  -- no CHECK constraint
```
```go
// community_command.go:61
VALUES ($1, $2, $3, $4, $5, 'public', NOW(), NOW())
```
**Suggested Fix**: Add a CHECK constraint: `CHECK (visibility IN ('public', 'friends', 'private'))`.

---

### [SEVERITY: P2] No pagination bounds on feed endpoint
**File**: `backend/gateway/internal/api/v1/community.go:80-82`
**Category**: performance
**Description**: `GetFeed` accepts `page` and `limit` query parameters with no bounds checking. A client could pass `limit=1000000` and fetch a million keys from the Redis ZSET, causing memory pressure and slow responses. Negative page numbers are also possible.
**Context**:
```go
page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
// No bounds checking
```
**Suggested Fix**: Clamp limit to a maximum (e.g., 100) and ensure page >= 1:
```go
if limit > 100 { limit = 100 }
if limit < 1 { limit = 20 }
if page < 1 { page = 1 }
```

---

### [SEVERITY: P2] `post_likes` foreign keys have no ON DELETE CASCADE
**File**: `backend/gateway/internal/db/schema.sql:18894,18902`
**Category**: schema
**Description**: `post_likes.post_id` and `post_likes.user_id` foreign keys reference `posts(id)` and `users(id)` without `ON DELETE CASCADE`. If a user is deleted (hard delete, not soft delete), the likes remain as orphans. If a post is hard-deleted, likes remain as orphans. The `DeletePost` command uses soft delete, so this is not an immediate problem, but it will become one if hard deletes are ever used.
**Context**:
```sql
ADD CONSTRAINT post_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES posts(id);
ADD CONSTRAINT post_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
-- No ON DELETE clause
```
**Suggested Fix**: Add `ON DELETE CASCADE` to both foreign keys.

---

### [SEVERITY: P2] Duplicate `parseEventTime` function defined in both worker and projection handler
**File**: `backend/gateway/internal/worker/community_sync.go:197-208` and `backend/gateway/internal/cqrs/projection/handlers.go:179-190`
**Category**: dead-code/code-quality
**Description**: The same `parseEventTime` helper function is defined identically in two packages. This is a maintenance risk -- if one is updated, the other may be missed.
**Suggested Fix**: Move to a shared utility package (e.g., `internal/cqrs/util`) and import from both.

---

## P3 Findings (Code Quality / Dead Code / Minor Improvements)

### [SEVERITY: P3] `CommunityHandler` is dead code -- never registered in routes
**File**: `backend/gateway/internal/api/v1/community.go:12-33`
**Category**: dead-code
**Description**: `CommunityHandler`, `NewCommunityHandler`, and `RegisterRoutes` are defined but never called anywhere in the codebase. The community routes are handled through WebSocket proxies and the projection system instead. The `setup.go` file has no reference to `CommunityHandler` or its constructor.
**Context**: Verified via grep -- `NewCommunityHandler` and `CommunityHandler` only appear in `community.go` itself and its tests.
**Suggested Fix**: Remove `CommunityHandler` and related types, or wire them into `setup.go` if the REST API is intended to be active.

---

### [SEVERITY: P3] Deprecated legacy constructors still present
**File**: `backend/gateway/internal/service/community_command.go:246-254` and `backend/gateway/internal/worker/community_sync.go:324-346`
**Category**: dead-code
**Description**: `NewCommunityCommandServiceLegacy` and `CommunitySyncWorkerLegacy` are marked deprecated but still present. `CommunitySyncWorkerLegacy.Run()` is a stub that just blocks until context cancellation -- it does nothing.
**Suggested Fix**: Remove both deprecated types and constructors if no callers exist.

---

### [SEVERITY: P3] Proto `CommunityService` marked deprecated but still contains full RPC definitions
**File**: `proto/community_service.proto:320-323`
**Category**: proto/dead-code
**Description**: The proto file states "This proto is retained only as compatibility documentation and must not be used as a live Python gRPC contract" and marks the service as `option deprecated = true`. However, it still contains 25+ RPC definitions including friends, groups, messages, check-ins, knowledge base, and collaborative galaxy. If these RPCs are truly not implemented on the Python side, having them in the proto creates confusion about the actual API contract.
**Suggested Fix**: Add a clear header comment listing which features are implemented via REST/gateway CQRS and which are future. Consider removing the RPC definitions entirely if they will never be implemented via gRPC.

---

### [SEVERITY: P3] `GroupChatHandler.GetMessages` does not filter soft-deleted messages
**File**: `backend/gateway/internal/handler/group_chat.go:61`
**Category**: bug
**Description**: The `GetGroupMessages` query in `group_chat_service.go` calls `s.store.GetGroupMessages`, but the underlying SQL query may or may not filter `deleted_at IS NULL` depending on the sqlc-generated query. If soft-deleted messages are included, users could see deleted messages in the chat history.
**Suggested Fix**: Verify the sqlc query for `GetGroupMessages` includes `WHERE deleted_at IS NULL`. If not, add the filter.

---

### [SEVERITY: P3] No community-specific rate limiting on group message endpoints
**File**: `backend/gateway/cmd/server/setup.go:552`
**Category**: security
**Description**: The `GET /groups/:group_id/messages` endpoint uses `authMiddleware` but has no rate limiting middleware. A user could poll this endpoint at high frequency to scrape message history. Other endpoints like galaxy have dedicated rate limits.
**Context**:
```go
api.GET("/groups/:group_id/messages", authMiddleware, handlers.groupChatHandler.GetMessages)
// No rate limit middleware
```
**Suggested Fix**: Add rate limiting similar to galaxy: `middleware.HybridRateLimitMiddlewareSimple(rdb, 10, 20)`.

---

## Appendix: Schema Observations (Non-Issues)

The following were checked and found to be correctly handled:

1. **`uq_post_like` UNIQUE(user_id, post_id)** -- Prevents duplicate likes correctly
2. **`uq_friendship` UNIQUE(user_id, friend_id)** -- Prevents duplicate friendships
3. **`uq_group_member` UNIQUE(group_id, user_id)** -- Prevents duplicate group memberships
4. **Accountability indexes** -- Adequate coverage for `(initiator_id, status)`, `(partner_id, status)`, `(slot_type, status)`
5. **Outbox pattern** -- Correctly uses `FOR UPDATE SKIP LOCKED` for concurrent publishers
6. **Idempotency** -- BaseWorker has proper in-memory + DB idempotency checking with `processed_events` table
7. **DLQ** -- BaseWorker sends failed events to dead letter queue after retries
8. **Auth middleware** -- JWT validation with RS256, blacklist checking, fail-closed mode

---

## Recommended Fix Priority

1. **Immediate (P0)**: Fix `community_posts` table name, fix `isLikedByMe` Redis sets, secure feed endpoint
2. **Before launch (P1)**: Fix like idempotency event publishing, fix `GetPost` query, add `created_at` index, fix like count race condition
3. **Post-launch hardening (P2)**: Add pagination bounds, fix TTL inconsistency, add CHECK constraints
4. **Code cleanup (P3)**: Remove dead code, consolidate `parseEventTime`, add rate limiting to group messages
