-- name: GetUserByEmail :one
SELECT * FROM users WHERE email = $1 LIMIT 1;

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
