-- name: GetUserByEmail :one
SELECT * FROM users WHERE email = $1 LIMIT 1;

-- name: GetUserByAppleID :one
SELECT * FROM users WHERE apple_id = $1 LIMIT 1;

-- name: CreateSocialUser :one
INSERT INTO users (
    id, username, email, hashed_password, nickname,
    registration_source, is_active, apple_id, updated_at, created_at
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
RETURNING *;

-- name: UpdateUserLastLogin :exec
UPDATE users SET last_login_at = NOW(), updated_at = NOW() WHERE id = $1;

-- name: LinkAppleUser :one
UPDATE users
SET apple_id = COALESCE(apple_id, $2),
    updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: CreateUser :one
INSERT INTO users (id, email, hashed_password, full_name, is_active, is_superuser, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
RETURNING *;

-- name: CreateChatMessage :one
INSERT INTO chat_messages (id, session_id, user_id, role, content, created_at)
VALUES ($1, $2, $3, $4, $5, NOW())
RETURNING id, created_at;

-- name: GetChatHistory :many
SELECT * FROM chat_messages
WHERE session_id = $1
AND created_at > $2
ORDER BY created_at ASC
LIMIT 500;

-- name: GetMessageByID :one
SELECT * FROM chat_messages
WHERE id = $1 AND session_id = $2
LIMIT 1;

-- name: GetGroupMessages :many
SELECT
    gm.id, gm.group_id, gm.sender_id, gm.message_type, gm.content, gm.content_data, gm.reply_to_id, gm.created_at, gm.updated_at,
    u.username as sender_username, u.nickname as sender_nickname, u.avatar_url as sender_avatar_url,
    rm.id as reply_id, rm.content as reply_content, rm.message_type as reply_type,
    ru.username as reply_sender_username, ru.nickname as reply_sender_nickname
FROM group_messages gm
LEFT JOIN users u ON gm.sender_id = u.id
LEFT JOIN group_messages rm ON gm.reply_to_id = rm.id
LEFT JOIN users ru ON rm.sender_id = ru.id
WHERE gm.group_id = $1
AND gm.deleted_at IS NULL
ORDER BY gm.created_at DESC
LIMIT $2 OFFSET $3;

-- name: IsGroupMember :one
SELECT EXISTS(SELECT 1 FROM group_members WHERE group_id = $1 AND user_id = $2);

-- =====================
-- Chat History Persistence Queries (Phase 1.3)
-- =====================

-- name: GetRecentSessionsFromDB :many
SELECT cs.id, cs.title, cs.last_message_at, cm.content as preview
FROM chat_sessions cs
LEFT JOIN LATERAL (
  SELECT content FROM chat_messages
  WHERE session_id = cs.id
  ORDER BY created_at DESC
  LIMIT 1
) cm ON true
WHERE cs.user_id = $1 AND cs.is_active = true
ORDER BY cs.last_message_at DESC
LIMIT $2;

-- name: GetSessionMessagesFromDB :many
SELECT * FROM chat_messages
WHERE session_id = $1 AND user_id = $2
ORDER BY created_at ASC
LIMIT $3 OFFSET $4;

-- name: UpsertChatSession :one
INSERT INTO chat_sessions (id, user_id, title, last_message_at, is_active, created_at, updated_at)
VALUES ($1, $2, $3, $4, true, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
  last_message_at = EXCLUDED.last_message_at,
  title = COALESCE(EXCLUDED.title, chat_sessions.title),
  updated_at = NOW()
RETURNING *;

-- name: GetChatSessionMeta :one
SELECT id, user_id, title, last_message_at, is_active, created_at, updated_at
FROM chat_sessions
WHERE id = $1 AND user_id = $2
LIMIT 1;

-- name: CreatePost :one
INSERT INTO posts (user_id, content, image_urls, topic, created_at, updated_at)
VALUES ($1, $2, $3, $4, NOW(), NOW())
RETURNING *;

-- name: GetPost :one
SELECT * FROM posts
WHERE id = $1 AND created_at = $2 AND deleted_at IS NULL;

-- name: CreatePostLike :exec
INSERT INTO post_likes (user_id, post_id, created_at)
VALUES ($1, $2, NOW())
ON CONFLICT DO NOTHING;

-- name: DeletePostLike :exec
DELETE FROM post_likes
WHERE user_id = $1 AND post_id = $2;

-- name: CountPostLikes :one
SELECT COUNT(*) FROM post_likes
WHERE post_id = $1;

-- name: GetUser :one
SELECT * FROM users WHERE id = $1;

-- =====================
-- CQRS: Outbox Queries
-- =====================

-- name: InsertOutboxEntry :exec
INSERT INTO event_outbox (
    id, aggregate_type, aggregate_id, event_type,
    event_version, sequence_number, payload, metadata, created_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);

-- name: GetUnpublishedOutboxEntries :many
SELECT id, aggregate_type, aggregate_id, event_type,
       event_version, payload, metadata, sequence_number,
       created_at, published_at
FROM event_outbox
WHERE published_at IS NULL
ORDER BY created_at ASC
LIMIT $1
FOR UPDATE SKIP LOCKED;

-- name: MarkOutboxEntriesPublished :exec
UPDATE event_outbox
SET published_at = NOW()
WHERE id = ANY($1::uuid[]);

-- name: DeleteOldOutboxEntries :execrows
DELETE FROM event_outbox
WHERE published_at IS NOT NULL
  AND published_at < NOW() - INTERVAL '1 day' * $1;

-- name: GetOutboxPendingCount :one
SELECT COUNT(*) FROM event_outbox WHERE published_at IS NULL;

-- =====================
-- CQRS: Event Store Queries
-- =====================

-- name: InsertEventStoreEntry :exec
INSERT INTO event_store (
    aggregate_type, aggregate_id, event_type,
    event_version, sequence_number, payload, metadata, created_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8);

-- name: GetEventsByAggregate :many
SELECT id, aggregate_type, aggregate_id, event_type,
       event_version, sequence_number, payload, metadata, created_at
FROM event_store
WHERE aggregate_type = $1 AND aggregate_id = $2
ORDER BY sequence_number ASC;

-- name: GetEventsAfterSequence :many
SELECT id, aggregate_type, aggregate_id, event_type,
       event_version, sequence_number, payload, metadata, created_at
FROM event_store
WHERE aggregate_type = $1
  AND aggregate_id = $2
  AND sequence_number > $3
ORDER BY sequence_number ASC;

-- name: GetNextSequenceNumber :one
SELECT COALESCE(MAX(sequence_number), 0) + 1
FROM event_store
WHERE aggregate_type = $1 AND aggregate_id = $2;

-- name: GetEventStoreCount :one
SELECT COUNT(*) FROM event_store WHERE aggregate_type = $1;

-- =====================
-- CQRS: Idempotency Queries
-- =====================

-- name: IsEventProcessed :one
SELECT EXISTS(
    SELECT 1 FROM processed_events
    WHERE event_id = $1 AND consumer_group = $2
);

-- name: MarkEventProcessed :exec
INSERT INTO processed_events (event_id, consumer_group, processed_at)
VALUES ($1, $2, NOW())
ON CONFLICT (event_id, consumer_group) DO NOTHING;

-- name: CleanupOldProcessedEvents :execrows
DELETE FROM processed_events
WHERE processed_at < NOW() - INTERVAL '1 day' * $1;

-- =====================
-- CQRS: Projection Metadata Queries
-- =====================

-- name: GetProjectionMetadata :one
SELECT projection_name, last_processed_position, last_processed_at,
       version, status, error_message, created_at, updated_at
FROM projection_metadata
WHERE projection_name = $1;

-- name: UpsertProjectionMetadata :exec
INSERT INTO projection_metadata (projection_name, status, version, created_at, updated_at)
VALUES ($1, 'active', 1, NOW(), NOW())
ON CONFLICT (projection_name) DO UPDATE SET updated_at = NOW();

-- name: UpdateProjectionPosition :exec
UPDATE projection_metadata
SET last_processed_position = $2,
    last_processed_at = NOW(),
    updated_at = NOW()
WHERE projection_name = $1;

-- name: SetProjectionStatus :exec
UPDATE projection_metadata
SET status = $2,
    error_message = $3,
    updated_at = NOW()
WHERE projection_name = $1;

-- name: GetAllProjectionMetadata :many
SELECT projection_name, last_processed_position, last_processed_at,
       version, status, error_message, created_at, updated_at
FROM projection_metadata
ORDER BY projection_name;

-- =====================
-- CQRS: Snapshot Queries
-- =====================

-- name: GetLatestSnapshot :one
SELECT id, projection_name, aggregate_id, snapshot_data, stream_position, created_at
FROM projection_snapshots
WHERE projection_name = $1
  AND (aggregate_id = $2 OR ($2 IS NULL AND aggregate_id IS NULL))
ORDER BY created_at DESC
LIMIT 1;

-- name: SaveSnapshot :exec
INSERT INTO projection_snapshots (
    id, projection_name, aggregate_id, snapshot_data, stream_position, created_at
) VALUES ($1, $2, $3, $4, $5, NOW())
ON CONFLICT (projection_name, aggregate_id)
DO UPDATE SET
    snapshot_data = $4,
    stream_position = $5,
    created_at = NOW();

-- name: DeleteSnapshotsByProjection :execrows
DELETE FROM projection_snapshots
WHERE projection_name = $1;

-- name: GetSnapshotCount :one
SELECT COUNT(*) FROM projection_snapshots WHERE projection_name = $1;

-- =====================
-- Task Queries
-- =====================

-- name: GetTaskByID :one
SELECT * FROM tasks WHERE id = $1 AND deleted_at IS NULL;

-- =====================
-- Knowledge Galaxy Queries
-- =====================

-- name: UpsertUserSession :one
INSERT INTO user_sessions (
    id, user_id, session_id, device_id, device_name, device_type,
    ip_address, user_agent, refresh_token_jti, is_active,
    last_active_at, created_at, updated_at
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, true, NOW(), NOW(), NOW())
ON CONFLICT (session_id) DO UPDATE SET
    user_id = EXCLUDED.user_id,
    device_id = EXCLUDED.device_id,
    device_name = EXCLUDED.device_name,
    device_type = EXCLUDED.device_type,
    ip_address = EXCLUDED.ip_address,
    user_agent = EXCLUDED.user_agent,
    refresh_token_jti = EXCLUDED.refresh_token_jti,
    is_active = true,
    revoked_at = NULL,
    last_active_at = NOW(),
    updated_at = NOW()
RETURNING *;

-- name: GetKnowledgeNodeByID :one
SELECT * FROM knowledge_nodes WHERE id = $1 AND deleted_at IS NULL;

-- name: GetUserNodeStatus :one
SELECT * FROM user_node_status WHERE user_id = $1 AND node_id = $2;
