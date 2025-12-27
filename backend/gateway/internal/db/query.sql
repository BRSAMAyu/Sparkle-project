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
ORDER BY created_at ASC;

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

-- name: CreatePost :one
INSERT INTO posts (user_id, content, image_urls, topic, created_at, updated_at)
VALUES ($1, $2, $3, $4, NOW(), NOW())
RETURNING *;

-- name: GetPost :one
SELECT * FROM posts
WHERE id = $1 AND deleted_at IS NULL;

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
