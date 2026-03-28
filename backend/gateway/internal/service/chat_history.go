package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

const (
	DefaultMaxQueueSize = 10000
	ChatHistoryTTL      = 30 * time.Minute

	// P1修复: 断路器恢复机制参数
	// 队列过载时消息进入本地重试缓冲，每隔 retryInterval 尝试重新入队
	breakerRetryInterval = 5 * time.Second
	breakerRetryMaxAge   = 2 * time.Minute // 超过此时间的消息丢弃（防止堆积无限增长）
	breakerRetryBufMax   = 500             // 本地重试缓冲上限
)

// retryEntry 保存一条待重试的消息及其首次入队时间
type retryEntry struct {
	msg        []byte
	enqueuedAt time.Time
}

type ChatHistoryService struct {
	rdb              *redis.Client
	pool             *pgxpool.Pool
	breakerThreshold atomic.Int64
	chatHistoryTTL   time.Duration

	// P1修复: 断路器本地重试缓冲 + 后台重试 goroutine 控制
	retryBuf    []retryEntry
	retryMu     sync.Mutex
	retryStopCh chan struct{}
}

func NewChatHistoryServiceWithPool(rdb *redis.Client, pool *pgxpool.Pool, ttl time.Duration) *ChatHistoryService {
	s := &ChatHistoryService{
		rdb:            rdb,
		pool:           pool,
		chatHistoryTTL: ttl,
		retryStopCh:    make(chan struct{}),
	}
	s.breakerThreshold.Store(DefaultMaxQueueSize)
	go s.retryWorker()
	return s
}

type ChatHistoryMessage struct {
	ID        string `json:"id"` // Unique message ID (UUID)
	SessionID string `json:"session_id"`
	UserID    string `json:"user_id"`
	Role      string `json:"role"`
	Content   string `json:"content"`
	Timestamp string `json:"timestamp"`
}

type ChatSessionSummary struct {
	ID        string `json:"id"`
	Title     string `json:"title"`
	UpdatedAt string `json:"updated_at"`
}

func NewChatHistoryService(rdb *redis.Client) *ChatHistoryService {
	return NewChatHistoryServiceWithTTL(rdb, ChatHistoryTTL)
}

func NewChatHistoryServiceWithTTL(rdb *redis.Client, ttl time.Duration) *ChatHistoryService {
	s := &ChatHistoryService{
		rdb:            rdb,
		chatHistoryTTL: ttl,
		retryStopCh:    make(chan struct{}),
	}
	s.breakerThreshold.Store(DefaultMaxQueueSize)
	go s.retryWorker()
	return s
}

// Stop shuts down the background retry worker gracefully.
func (s *ChatHistoryService) Stop() {
	select {
	case <-s.retryStopCh:
		// already closed
	default:
		close(s.retryStopCh)
	}
}

// retryWorker periodically flushes the local retry buffer back into the persist queue.
// P1修复: 替代原来的"直接丢弃"策略，提供有限次指数退避重试
func (s *ChatHistoryService) retryWorker() {
	ticker := time.NewTicker(breakerRetryInterval)
	defer ticker.Stop()
	for {
		select {
		case <-s.retryStopCh:
			return
		case <-ticker.C:
			s.flushRetryBuf()
		}
	}
}

func (s *ChatHistoryService) flushRetryBuf() {
	s.retryMu.Lock()
	if len(s.retryBuf) == 0 {
		s.retryMu.Unlock()
		return
	}
	// 取出当前所有条目进行尝试，同时清空 buf
	entries := s.retryBuf
	s.retryBuf = nil
	s.retryMu.Unlock()

	ctx := context.Background()
	queueKey := "queue:persist:history"
	var requeue []retryEntry

	for _, e := range entries {
		// 超时丢弃
		if time.Since(e.enqueuedAt) > breakerRetryMaxAge {
			log.Printf("[ChatHistoryService] Retry entry expired after %v, dropping", breakerRetryMaxAge)
			continue
		}
		qLen, err := s.rdb.LLen(ctx, queueKey).Result()
		if err != nil {
			requeue = append(requeue, e)
			continue
		}
		threshold := s.breakerThreshold.Load()
		if qLen < threshold {
			if err := s.rdb.RPush(ctx, queueKey, e.msg).Err(); err != nil {
				requeue = append(requeue, e)
			}
		} else {
			// 队列仍然满，继续等待下次重试
			requeue = append(requeue, e)
		}
	}

	if len(requeue) > 0 {
		s.retryMu.Lock()
		s.retryBuf = append(requeue, s.retryBuf...)
		// 防止缓冲无限增长
		if len(s.retryBuf) > breakerRetryBufMax {
			dropped := len(s.retryBuf) - breakerRetryBufMax
			s.retryBuf = s.retryBuf[dropped:]
			log.Printf("[ChatHistoryService] Retry buffer overflow, dropped %d oldest entries", dropped)
		}
		s.retryMu.Unlock()
	}
}

// SetBreakerThreshold updates the circuit breaker limit dynamically
func (s *ChatHistoryService) SetBreakerThreshold(val int64) {
	s.breakerThreshold.Store(val)
}

// GetBreakerThreshold returns the current limit
func (s *ChatHistoryService) GetBreakerThreshold() int64 {
	return s.breakerThreshold.Load()
}

// GetQueueLength returns the current persistent queue size
func (s *ChatHistoryService) GetQueueLength(ctx context.Context) (int64, error) {
	return s.rdb.LLen(ctx, "queue:persist:history").Result()
}

// PublishConnectionEvent publishes a WebSocket connection event to Redis Pub/Sub
func (s *ChatHistoryService) PublishConnectionEvent(ctx context.Context, userID string, event string) error {
	if s.rdb == nil {
		return nil
	}

	eventKey := fmt.Sprintf("ws:connection:events:%s", userID)
	eventValue := fmt.Sprintf("%s:%d", event, time.Now().Unix())

	return s.rdb.Publish(ctx, eventKey, eventValue).Err()
}

func (s *ChatHistoryService) SaveMessage(ctx context.Context, sid string, msg []byte) error {
	pipe := s.rdb.Pipeline()

	// 1. Write to cache (for AI context, with TTL)
	cacheKey := "chat:history:" + sid
	pipe.RPush(ctx, cacheKey, msg)
	pipe.LTrim(ctx, cacheKey, -20, -1) // Keep last 20 messages
	pipe.Expire(ctx, cacheKey, s.chatHistoryTTL)

	// 2. Write to persistent queue (for DB, with Circuit Breaker)
	queueKey := "queue:persist:history"

	// Check queue length (Circuit Breaker)
	// We do this check outside the pipeline for simplicity, acknowledging the small race condition.
	// For strict atomicity, a Lua script could be used, but this is sufficient for OOM protection.
	qLen, err := s.rdb.LLen(ctx, queueKey).Result()
	if err != nil {
		// If Redis is reachable but LLEN fails, it's risky.
		// If Redis is unreachable, pipeline exec will fail anyway.
		log.Printf("Failed to check queue length: %v", err)
		return err
	}

	threshold := s.breakerThreshold.Load()
	if qLen < threshold {
		pipe.RPush(ctx, queueKey, msg)
	} else {
		// P1修复: 队列过载时进入本地重试缓冲，由 retryWorker 定期重试入队，不再直接丢弃
		log.Printf("[ChatHistoryService] Persist queue overloaded (%d/%d), buffering for retry", qLen, threshold)
		s.retryMu.Lock()
		if len(s.retryBuf) < breakerRetryBufMax {
			s.retryBuf = append(s.retryBuf, retryEntry{msg: msg, enqueuedAt: time.Now()})
		} else {
			log.Printf("[ChatHistoryService] Retry buffer full, dropping message (queue: %d/%d)", qLen, threshold)
		}
		s.retryMu.Unlock()
		// 仍继续执行 pipeline（缓存写入不受影响）
	}

	var payload ChatHistoryMessage
	if err := json.Unmarshal(msg, &payload); err == nil && payload.UserID != "" {
		sessionsKey := fmt.Sprintf("chat:sessions:user:%s", payload.UserID)
		metaKey := fmt.Sprintf("chat:session_meta:%s", sid)
		updatedAt := parseUnixString(payload.Timestamp)
		preview := strings.TrimSpace(payload.Content)
		if len(preview) > 120 {
			preview = preview[:120]
		}

		pipe.ZAdd(ctx, sessionsKey, redis.Z{
			Score:  float64(updatedAt.Unix()),
			Member: sid,
		})
		pipe.Expire(ctx, sessionsKey, s.chatHistoryTTL)
		fields := map[string]interface{}{
			"user_id":         payload.UserID,
			"last_preview":    preview,
			"last_message":    preview,
			"last_role":       payload.Role,
			"last_message_at": updatedAt.UTC().Format(time.RFC3339),
		}
		if payload.Role == "user" {
			fields["title"] = buildSessionTitle(payload.Role, payload.Content)
		}
		pipe.HSet(ctx, metaKey, fields)
		pipe.Expire(ctx, metaKey, s.chatHistoryTTL)
	}

	_, err = pipe.Exec(ctx)
	return err
}

func (s *ChatHistoryService) GetMessages(ctx context.Context, userID, sessionID string, limit, offset int) ([]ChatHistoryMessage, error) {
	if limit <= 0 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}

	// 1. Try Redis first
	messages, err := s.getMessagesFromRedis(ctx, userID, sessionID, limit, offset)
	if err != nil {
		// Security errors must not be swallowed — never fallback to DB on access denial
		if err.Error() == "forbidden" {
			return nil, err
		}
		log.Printf("[ChatHistoryService] Redis query failed: %v, trying DB fallback", err)
	} else if len(messages) > 0 {
		// Cache hit - return immediately
		return messages, nil
	}

	// 2. Fallback to PostgreSQL if Redis is empty or failed
	if s.pool != nil {
		messages, err = s.getMessagesFromDB(ctx, userID, sessionID, limit, offset)
		if err != nil {
			log.Printf("[ChatHistoryService] DB fallback failed: %v", err)
			return nil, err
		}

		// 3. Backfill Redis cache (async) - only if we got data from DB
		if len(messages) > 0 {
			go s.backfillRedisMessages(sessionID, messages)
		}

		return messages, nil
	}

	// 4. Return empty if no DB pool available
	return []ChatHistoryMessage{}, nil
}

// getMessagesFromRedis fetches messages from Redis cache
func (s *ChatHistoryService) getMessagesFromRedis(ctx context.Context, userID, sessionID string, limit, offset int) ([]ChatHistoryMessage, error) {
	metaKey := fmt.Sprintf("chat:session_meta:%s", sessionID)
	owner, err := s.rdb.HGet(ctx, metaKey, "user_id").Result()
	if err != nil && err != redis.Nil {
		return nil, err
	}
	// If meta exists and owner doesn't match, reject immediately (even if messages list is empty)
	if owner != "" && owner != userID {
		return nil, fmt.Errorf("forbidden")
	}

	cacheKey := "chat:history:" + sessionID
	raw, err := s.rdb.LRange(ctx, cacheKey, 0, -1).Result()
	if err != nil {
		if err == redis.Nil {
			return []ChatHistoryMessage{}, nil
		}
		return nil, err
	}

	messages := make([]ChatHistoryMessage, 0, len(raw))
	for _, item := range raw {
		var msg ChatHistoryMessage
		if err := json.Unmarshal([]byte(item), &msg); err != nil {
			continue
		}
		if msg.UserID != "" && msg.UserID != userID {
			continue
		}
		messages = append(messages, msg)
	}

	if offset >= len(messages) {
		return []ChatHistoryMessage{}, nil
	}
	start := len(messages) - offset - limit
	if start < 0 {
		start = 0
	}
	end := len(messages) - offset
	if end < 0 {
		end = 0
	}
	if start >= end {
		return []ChatHistoryMessage{}, nil
	}
	return messages[start:end], nil
}

// getMessagesFromDB fetches messages from PostgreSQL as fallback
func (s *ChatHistoryService) getMessagesFromDB(ctx context.Context, userID, sessionID string, limit, offset int) ([]ChatHistoryMessage, error) {
	if s.pool == nil {
		return nil, fmt.Errorf("database pool not initialized")
	}

	// Parse UUIDs
	var sessionUUID, userUUID pgtype.UUID
	if err := sessionUUID.Scan(sessionID); err != nil {
		return nil, fmt.Errorf("invalid session_id: %w", err)
	}
	if err := userUUID.Scan(userID); err != nil {
		return nil, fmt.Errorf("invalid user_id: %w", err)
	}

	hasAccess, err := s.userOwnsSessionInDB(ctx, userUUID, sessionUUID)
	if err != nil {
		return nil, err
	}
	if !hasAccess {
		exists, err := s.sessionExistsInDB(ctx, sessionUUID)
		if err != nil {
			return nil, err
		}
		if exists {
			return nil, fmt.Errorf("forbidden")
		}
		return []ChatHistoryMessage{}, nil
	}

	rows, err := s.pool.Query(ctx, `
		SELECT id, session_id, user_id, role, content, created_at
		FROM chat_messages
		WHERE session_id = $1 AND user_id = $2
		ORDER BY created_at DESC
		LIMIT $3 OFFSET $4
	`, sessionUUID, userUUID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	messages := make([]ChatHistoryMessage, 0, limit)
	for rows.Next() {
		var (
			id        pgtype.UUID
			dbSession pgtype.UUID
			dbUser    pgtype.UUID
			role      string
			content   string
			createdAt pgtype.Timestamptz
		)
		if err := rows.Scan(&id, &dbSession, &dbUser, &role, &content, &createdAt); err != nil {
			return nil, err
		}
		messages = append(messages, ChatHistoryMessage{
			ID:        id.String(),
			SessionID: dbSession.String(),
			UserID:    dbUser.String(),
			Role:      role,
			Content:   content,
			Timestamp: fmt.Sprintf("%d", createdAt.Time.Unix()),
		})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	for left, right := 0, len(messages)-1; left < right; left, right = left+1, right-1 {
		messages[left], messages[right] = messages[right], messages[left]
	}
	return messages, nil
}

func (s *ChatHistoryService) userOwnsSessionInDB(ctx context.Context, userUUID, sessionUUID pgtype.UUID) (bool, error) {
	const ownershipQuery = `
		SELECT EXISTS(
			SELECT 1 FROM chat_sessions WHERE id = $1 AND user_id = $2
		) OR EXISTS(
			SELECT 1 FROM chat_messages WHERE session_id = $1 AND user_id = $2
		)
	`

	var owns bool
	if err := s.pool.QueryRow(ctx, ownershipQuery, sessionUUID, userUUID).Scan(&owns); err != nil {
		return false, err
	}
	return owns, nil
}

func (s *ChatHistoryService) sessionExistsInDB(ctx context.Context, sessionUUID pgtype.UUID) (bool, error) {
	const existenceQuery = `
		SELECT EXISTS(
			SELECT 1 FROM chat_sessions WHERE id = $1
		) OR EXISTS(
			SELECT 1 FROM chat_messages WHERE session_id = $1
		)
	`

	var exists bool
	if err := s.pool.QueryRow(ctx, existenceQuery, sessionUUID).Scan(&exists); err != nil {
		return false, err
	}
	return exists, nil
}

// backfillRedisMessages populates Redis cache with messages from DB
func (s *ChatHistoryService) backfillRedisMessages(sessionID string, messages []ChatHistoryMessage) {
	ctx := context.Background()
	cacheKey := "chat:history:" + sessionID

	successCount := 0
	for _, msg := range messages {
		msgBytes, err := json.Marshal(msg)
		if err != nil {
			log.Printf("[ChatHistoryService] backfillRedisMessages: marshal error for session %s: %v", sessionID, err)
			continue
		}
		// P1修复: 捕获 RPush 错误，不再静默失败
		if err := s.rdb.RPush(ctx, cacheKey, msgBytes).Err(); err != nil {
			log.Printf("[ChatHistoryService] backfillRedisMessages: RPush error for session %s: %v", sessionID, err)
			return // Redis 不可用时提前终止，避免无效循环
		}
		successCount++
	}

	if err := s.rdb.LTrim(ctx, cacheKey, -20, -1).Err(); err != nil {
		log.Printf("[ChatHistoryService] backfillRedisMessages: LTrim error for session %s: %v", sessionID, err)
	}
	if err := s.rdb.Expire(ctx, cacheKey, s.chatHistoryTTL).Err(); err != nil {
		log.Printf("[ChatHistoryService] backfillRedisMessages: Expire error for session %s: %v", sessionID, err)
	}

	log.Printf("[ChatHistoryService] Backfilled Redis cache for session %s: %d/%d messages", sessionID, successCount, len(messages))
}

func (s *ChatHistoryService) GetRecentSessions(ctx context.Context, userID string, limit int) ([]ChatSessionSummary, error) {
	if limit <= 0 {
		limit = 20
	}

	// 1. Try Redis first
	sessions, err := s.getRecentSessionsFromRedis(ctx, userID, limit)
	if err != nil {
		log.Printf("[ChatHistoryService] Redis query failed: %v, trying DB fallback", err)
	} else if len(sessions) > 0 {
		// Cache hit - return immediately
		return sessions, nil
	}

	// 2. Fallback to PostgreSQL if Redis is empty or failed
	if s.pool != nil {
		sessions, err = s.getRecentSessionsFromDB(ctx, userID, limit)
		if err != nil {
			log.Printf("[ChatHistoryService] DB fallback failed: %v", err)
			return nil, err
		}

		// 3. Backfill Redis cache (async) - only if we got data from DB
		if len(sessions) > 0 {
			go s.backfillRedisCache(userID, sessions)
		}

		return sessions, nil
	}

	// 3. Return empty if no DB pool available
	return []ChatSessionSummary{}, nil
}

// getRecentSessionsFromRedis fetches sessions from Redis cache
func (s *ChatHistoryService) getRecentSessionsFromRedis(ctx context.Context, userID string, limit int) ([]ChatSessionSummary, error) {
	sessionsKey := fmt.Sprintf("chat:sessions:user:%s", userID)
	ids, err := s.rdb.ZRevRange(ctx, sessionsKey, 0, int64(limit-1)).Result()
	if err != nil {
		if err == redis.Nil {
			return []ChatSessionSummary{}, nil
		}
		return nil, err
	}

	summaries := make([]ChatSessionSummary, 0, len(ids))
	for _, sid := range ids {
		metaKey := fmt.Sprintf("chat:session_meta:%s", sid)
		meta, err := s.rdb.HGetAll(ctx, metaKey).Result()
		if err != nil || len(meta) == 0 {
			continue
		}
		if owner := meta["user_id"]; owner != "" && owner != userID {
			continue
		}
		title := strings.TrimSpace(meta["title"])
		if title == "" {
			title = "新对话"
		}
		updatedAt := meta["last_message_at"]
		summaries = append(summaries, ChatSessionSummary{
			ID:        sid,
			Title:     title,
			UpdatedAt: updatedAt,
		})
	}

	sort.SliceStable(summaries, func(i, j int) bool {
		return summaries[i].UpdatedAt > summaries[j].UpdatedAt
	})
	return summaries, nil
}

// getRecentSessionsFromDB fetches sessions from PostgreSQL as fallback
func (s *ChatHistoryService) getRecentSessionsFromDB(ctx context.Context, userID string, limit int) ([]ChatSessionSummary, error) {
	if s.pool == nil {
		return nil, fmt.Errorf("database pool not initialized")
	}

	query := `
		SELECT cs.id, cs.title, cs.last_message_at, cm.content as preview
		FROM chat_sessions cs
		LEFT JOIN LATERAL (
			SELECT content FROM chat_messages
			WHERE session_id = cs.id AND user_id = $1
			ORDER BY created_at DESC LIMIT 1
		) cm ON true
		WHERE cs.user_id = $1 AND cs.is_active = true
		ORDER BY cs.last_message_at DESC
		LIMIT $2
	`

	rows, err := s.pool.Query(ctx, query, userID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	summaries := make([]ChatSessionSummary, 0, limit)
	for rows.Next() {
		var id, title, lastMessageAt string
		var preview *string
		if err := rows.Scan(&id, &title, &lastMessageAt, &preview); err != nil {
			continue
		}

		// Format title
		formattedTitle := strings.TrimSpace(title)
		if formattedTitle == "" {
			if preview != nil && len(*preview) > 24 {
				formattedTitle = string((*preview)[:24]) + "..."
			} else if preview != nil && *preview != "" {
				formattedTitle = *preview
			} else {
				formattedTitle = "新对话"
			}
		}

		summaries = append(summaries, ChatSessionSummary{
			ID:        id,
			Title:     formattedTitle,
			UpdatedAt: lastMessageAt,
		})
	}

	return summaries, nil
}

// backfillRedisCache populates Redis cache with data from DB
func (s *ChatHistoryService) backfillRedisCache(userID string, sessions []ChatSessionSummary) {
	ctx := context.Background()
	sessionsKey := fmt.Sprintf("chat:sessions:user:%s", userID)

	for _, session := range sessions {
		// Add session ID to sorted set
		score := float64(time.Now().Unix())
		// P1修复: time.Parse(layout, value) 参数顺序修正（原来颠倒了）
		if t, err := time.Parse(time.RFC3339, session.UpdatedAt); err == nil {
			score = float64(t.Unix())
		}

		s.rdb.ZAdd(ctx, sessionsKey, redis.Z{
			Score:  score,
			Member: session.ID,
		})

		// Set session metadata
		metaKey := fmt.Sprintf("chat:session_meta:%s", session.ID)
		fields := map[string]interface{}{
			"user_id":         userID,
			"title":           session.Title,
			"last_message_at": session.UpdatedAt,
		}
		s.rdb.HSet(ctx, metaKey, fields)
		s.rdb.Expire(ctx, metaKey, s.chatHistoryTTL)
	}

	// Set expiry on sessions list
	s.rdb.Expire(ctx, sessionsKey, s.chatHistoryTTL)

	log.Printf("[ChatHistoryService] Backfilled Redis cache for user %s with %d sessions", userID, len(sessions))
}

func parseUnixString(raw string) time.Time {
	if raw == "" {
		return time.Now().UTC()
	}
	seconds, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		return time.Now().UTC()
	}
	return time.Unix(seconds, 0).UTC()
}

func buildSessionTitle(role, content string) string {
	if role != "user" {
		return "新对话"
	}
	title := strings.TrimSpace(content)
	if title == "" {
		return "新对话"
	}
	runes := []rune(title)
	if len(runes) > 24 {
		title = string(runes[:24]) + "..."
	}
	return title
}
