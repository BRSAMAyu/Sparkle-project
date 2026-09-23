package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/i18n"
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

// HISTORY-TAIL (V13-RETEST Major residual): the Redis cache only receives
// messages the gateway appends (SaveMessage), while the engine persists to
// PostgreSQL independently. When an append is missed (app killed mid-run,
// lost run-finalization event) the cache-hit short-circuit served a truncated
// history — and a truncated AI context — until the TTL healed it (~15min).
// The read path therefore re-checks the authoritative DB tail behind a live
// cache, bounded by a per-session probe watermark:
const (
	// How often a cache hit may be re-checked against the DB tail. Within
	// this window a hit is served from Redis only (zero added DB cost).
	chatHistoryTailProbeInterval = 30 * time.Second
	// Per-probe DB timeout: a stale check must never stall the read path.
	chatHistoryTailProbeTimeout = 2 * time.Second
	// Max DB rows fetched per probe (index-backed range scan on
	// idx_chat_user_session_created_at).
	chatHistoryTailProbeRowLimit = 50
	// Lookback before the oldest cached timestamp so rows whose engine-side
	// created_at sits just below the cache window still take part in matching.
	chatHistoryTailLookback = 5 * time.Second
	// Max |Δt| between a cached message and a DB row treated as the same
	// logical message (gateway append time vs engine created_at drift; the
	// two writers use unrelated message IDs).
	chatHistoryTailMatchTolerance = 2 * time.Minute
	// session_meta field holding the last successful tail-probe stamp.
	chatHistoryTailCheckedAtField = "tail_checked_at"
)

var errRetryBufferOverflow = errors.New("chat history retry buffer overflow")
var errChatHistoryForbidden = errors.New("chat history forbidden")

func ErrChatHistoryForbidden() error {
	return errChatHistoryForbidden
}

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

	// P2-D (daily-flow R2): the Redis persist queue only exists to feed
	// ChatHistoryPersister. When the persister is disabled (now the default —
	// the engine is the single authoritative chat writer), the producer must
	// stop enqueueing too, or queue:persist:history grows unbounded with
	// nothing draining it. Defaults to true so standalone constructors keep
	// the historical behaviour; server wiring sets it from config.
	persistQueueEnabled atomic.Bool

	// P1修复: 断路器本地重试缓冲 + 后台重试 goroutine 控制
	retryBuf    []retryEntry
	retryMu     sync.Mutex
	retryStopCh chan struct{}

	// R2-GW-7: cache backfills run fire-and-forget, but bounded — at most
	// chatHistoryBackfillMaxConcurrent run at once and excess backfills are
	// dropped (the cache is self-healing on the next read).
	backfillSem chan struct{}
	backfillWg  sync.WaitGroup

	// HISTORY-TAIL: probes the authoritative DB tail behind a live cache.
	// Production wiring sets it to (*ChatHistoryService).probeTailFromDB when
	// a DB pool is available; nil keeps the historical cache-hit
	// short-circuit (tests and pool-less deployments).
	tailProbeFn func(ctx context.Context, sessionID, userID string, since time.Time) ([]ChatHistoryMessage, error)
}

func NewChatHistoryServiceWithPool(rdb *redis.Client, pool *pgxpool.Pool, ttl time.Duration) *ChatHistoryService {
	s := &ChatHistoryService{
		rdb:            rdb,
		pool:           pool,
		chatHistoryTTL: ttl,
		retryStopCh:    make(chan struct{}),
		backfillSem:    make(chan struct{}, chatHistoryBackfillMaxConcurrent),
	}
	if pool != nil {
		s.tailProbeFn = s.probeTailFromDB
	}
	s.breakerThreshold.Store(DefaultMaxQueueSize)
	s.persistQueueEnabled.Store(true)
	go s.retryWorker()
	return s
}

// SetPersistQueueProducerEnabled toggles enqueueing into
// queue:persist:history. Server wiring turns it off when the persister
// consumer is disabled (P2-D): the cache writes in SaveMessage are unaffected.
func (s *ChatHistoryService) SetPersistQueueProducerEnabled(enabled bool) {
	s.persistQueueEnabled.Store(enabled)
}

type ChatHistoryMessage struct {
	ID                   string                   `json:"id"` // Unique message ID (UUID)
	SessionID            string                   `json:"session_id"`
	UserID               string                   `json:"user_id"`
	TaskID               string                   `json:"task_id,omitempty"`
	Role                 string                   `json:"role"`
	Content              string                   `json:"content"`
	Timestamp            string                   `json:"timestamp"`
	Widgets              []map[string]interface{} `json:"widgets,omitempty"`
	ToolResults          []map[string]interface{} `json:"tool_results,omitempty"`
	HasErrors            bool                     `json:"has_errors,omitempty"`
	Errors               []map[string]interface{} `json:"errors,omitempty"`
	RequiresConfirmation bool                     `json:"requires_confirmation,omitempty"`
	ConfirmationData     map[string]interface{}   `json:"confirmation_data,omitempty"`
	ReasoningSteps       []map[string]interface{} `json:"reasoning_steps,omitempty"`
	ReasoningSummary     string                   `json:"reasoning_summary,omitempty"`
	IsReasoningComplete  bool                     `json:"is_reasoning_complete,omitempty"`
	IsInterrupted        bool                     `json:"is_interrupted,omitempty"`
	Meta                 map[string]interface{}   `json:"meta,omitempty"`
	AgentCollaboration   map[string]interface{}   `json:"agentCollaboration,omitempty"`
}

type ChatSessionSummary struct {
	ID        string `json:"id"`
	Title     string `json:"title"`
	UpdatedAt string `json:"updated_at"`
}

type ConversationSettings struct {
	UseDocumentContext bool     `json:"use_document_context"`
	DocumentFilter     []string `json:"document_filter,omitempty"`
	UpdatedAt          string   `json:"updated_at,omitempty"`
}

func NewChatHistoryService(rdb *redis.Client) *ChatHistoryService {
	return NewChatHistoryServiceWithTTL(rdb, ChatHistoryTTL)
}

func NewChatHistoryServiceWithTTL(rdb *redis.Client, ttl time.Duration) *ChatHistoryService {
	s := &ChatHistoryService{
		rdb:            rdb,
		chatHistoryTTL: ttl,
		retryStopCh:    make(chan struct{}),
		backfillSem:    make(chan struct{}, chatHistoryBackfillMaxConcurrent),
	}
	s.breakerThreshold.Store(DefaultMaxQueueSize)
	s.persistQueueEnabled.Store(true)
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
	s.backfillWg.Wait()
}

// chatHistoryBackfillMaxConcurrent bounds concurrent cache backfill
// goroutines (R2-GW-7).
const chatHistoryBackfillMaxConcurrent = 4

// startBackfill runs cache-backfill work without blocking the request path
// but with bounded concurrency: once chatHistoryBackfillMaxConcurrent
// backfills are in flight, additional ones are dropped. Backfills are pure
// cache warm-up — dropping is safe and the next read repopulates.
func (s *ChatHistoryService) startBackfill(work func()) {
	select {
	case s.backfillSem <- struct{}{}:
	default:
		return // at capacity: drop instead of stacking goroutines
	}
	s.backfillWg.Add(1)
	go func() {
		defer s.backfillWg.Done()
		defer func() { <-s.backfillSem }()
		work()
	}()
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
	if len(s.retryBuf) == 0 || !s.persistQueueEnabled.Load() {
		s.retryBuf = nil
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
			zap.L().Warn("Chat history retry entry expired",
				zap.Duration("max_age", breakerRetryMaxAge),
			)
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
			zap.L().Warn("Chat history retry buffer overflow",
				zap.Int("dropped_count", dropped),
				zap.Int("buffer_limit", breakerRetryBufMax),
			)
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

// TryAcceptRealtimeRequest records a client request_id for a bounded window.
// It returns false when the same user/request_id has already been accepted,
// preventing reconnect/offline replay from creating duplicate side effects.
func (s *ChatHistoryService) TryAcceptRealtimeRequest(ctx context.Context, userID, requestID string, ttl time.Duration) (bool, error) {
	if s.rdb == nil || strings.TrimSpace(userID) == "" || strings.TrimSpace(requestID) == "" {
		return true, nil
	}
	if ttl <= 0 {
		ttl = time.Hour
	}
	key := fmt.Sprintf("ws:chat:request:%s:%s", userID, requestID)
	return s.rdb.SetNX(ctx, key, time.Now().UTC().Format(time.RFC3339Nano), ttl).Result()
}

func (s *ChatHistoryService) SaveMessage(ctx context.Context, sid string, msg []byte) error {
	pipe := s.rdb.Pipeline()
	bufferOverflow := false

	// 1. Write to cache (for AI context, with TTL)
	cacheKey := "chat:history:" + sid
	pipe.RPush(ctx, cacheKey, msg)
	pipe.LTrim(ctx, cacheKey, -20, -1) // Keep last 20 messages
	pipe.Expire(ctx, cacheKey, s.chatHistoryTTL)

	// 2. Write to persistent queue (for DB, with Circuit Breaker).
	// P2-D: skipped entirely when the persister consumer is disabled —
	// without a consumer the queue would only grow.
	queueKey := "queue:persist:history"

	if !s.persistQueueEnabled.Load() {
		if _, err := pipe.Exec(ctx); err != nil {
			return err
		}
		return nil
	}

	// Check queue length (Circuit Breaker)
	// We do this check outside the pipeline for simplicity, acknowledging the small race condition.
	// For strict atomicity, a Lua script could be used, but this is sufficient for OOM protection.
	qLen, err := s.rdb.LLen(ctx, queueKey).Result()
	if err != nil {
		// If Redis is reachable but LLEN fails, it's risky.
		// If Redis is unreachable, pipeline exec will fail anyway.
		zap.L().Error("Failed to check chat history persist queue length",
			zap.String("queue_key", queueKey),
			zap.Error(err),
		)
		return err
	}

	threshold := s.breakerThreshold.Load()
	if qLen < threshold {
		pipe.RPush(ctx, queueKey, msg)
	} else {
		// P1修复: 队列过载时进入本地重试缓冲，由 retryWorker 定期重试入队，不再直接丢弃
		zap.L().Warn("Chat history persist queue overloaded",
			zap.Int64("queue_length", qLen),
			zap.Int64("threshold", threshold),
		)
		s.retryMu.Lock()
		if len(s.retryBuf) < breakerRetryBufMax {
			s.retryBuf = append(s.retryBuf, retryEntry{msg: msg, enqueuedAt: time.Now()})
		} else {
			bufferOverflow = true
			zap.L().Error("Chat history retry buffer full; dropping message",
				zap.Int64("queue_length", qLen),
				zap.Int64("threshold", threshold),
				zap.Int("buffer_limit", breakerRetryBufMax),
			)
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
			fields["title"] = buildSessionTitle(ctx, payload.Role, payload.Content)
		}
		pipe.HSet(ctx, metaKey, fields)
		pipe.Expire(ctx, metaKey, s.chatHistoryTTL)
	}

	_, err = pipe.Exec(ctx)
	if err != nil {
		return err
	}
	if bufferOverflow {
		return errRetryBufferOverflow
	}
	return nil
}

func (s *ChatHistoryService) GetConversationSettings(ctx context.Context, userID, sessionID string) (*ConversationSettings, bool, error) {
	if s.rdb == nil {
		return nil, false, nil
	}
	if err := s.ensureSessionAccess(ctx, userID, sessionID); err != nil {
		return nil, false, err
	}

	metaKey := fmt.Sprintf("chat:session_meta:%s", sessionID)
	values, err := s.rdb.HMGet(ctx, metaKey, "use_document_context", "document_filter", "settings_updated_at").Result()
	if err != nil {
		if err == redis.Nil {
			return nil, false, nil
		}
		return nil, false, err
	}
	rawUse, _ := values[0].(string)
	if strings.TrimSpace(rawUse) == "" {
		return nil, false, nil
	}
	useDocumentContext, err := strconv.ParseBool(rawUse)
	if err != nil {
		return nil, false, err
	}
	settings := &ConversationSettings{
		UseDocumentContext: useDocumentContext,
		DocumentFilter:     []string{},
	}
	if rawFilter, _ := values[1].(string); strings.TrimSpace(rawFilter) != "" {
		_ = json.Unmarshal([]byte(rawFilter), &settings.DocumentFilter)
	}
	if updatedAt, _ := values[2].(string); updatedAt != "" {
		settings.UpdatedAt = updatedAt
	}
	return settings, true, nil
}

func (s *ChatHistoryService) UpdateConversationSettings(ctx context.Context, userID, sessionID string, settings ConversationSettings) (*ConversationSettings, error) {
	if s.rdb == nil {
		return &settings, nil
	}
	if err := s.ensureSessionAccess(ctx, userID, sessionID); err != nil {
		return nil, err
	}

	filter := normalizeDocumentFilter(settings.DocumentFilter)
	filterJSON, err := json.Marshal(filter)
	if err != nil {
		return nil, err
	}
	updatedAt := time.Now().UTC().Format(time.RFC3339)
	metaKey := fmt.Sprintf("chat:session_meta:%s", sessionID)
	fields := map[string]interface{}{
		"user_id":              userID,
		"use_document_context": strconv.FormatBool(settings.UseDocumentContext),
		"document_filter":      string(filterJSON),
		"settings_updated_at":  updatedAt,
	}
	pipe := s.rdb.Pipeline()
	pipe.HSet(ctx, metaKey, fields)
	pipe.Expire(ctx, metaKey, s.chatHistoryTTL)
	if _, err := pipe.Exec(ctx); err != nil {
		return nil, err
	}
	return &ConversationSettings{
		UseDocumentContext: settings.UseDocumentContext,
		DocumentFilter:     filter,
		UpdatedAt:          updatedAt,
	}, nil
}

func (s *ChatHistoryService) ensureSessionAccess(ctx context.Context, userID, sessionID string) error {
	metaKey := fmt.Sprintf("chat:session_meta:%s", sessionID)
	owner, err := s.rdb.HGet(ctx, metaKey, "user_id").Result()
	if err != nil && err != redis.Nil {
		return err
	}
	if owner != "" && owner != userID {
		return errChatHistoryForbidden
	}
	if owner != "" || s.pool == nil {
		return nil
	}

	var sessionUUID, userUUID pgtype.UUID
	if err := sessionUUID.Scan(sessionID); err != nil {
		// P2-E: label sessions resolve to the engine's derived pseudo UUID so
		// the DB ownership check applies to them too (a label owned by
		// another user must 403, not silently pass the DB check).
		derived := resolveSessionUUID(sessionID)
		sessionUUID = pgtype.UUID{Bytes: derived, Valid: true}
	}
	if err := userUUID.Scan(userID); err != nil {
		return nil
	}
	hasAccess, err := s.userOwnsSessionInDB(ctx, userUUID, sessionUUID)
	if err != nil {
		return err
	}
	if hasAccess {
		return nil
	}
	exists, err := s.sessionExistsInDB(ctx, sessionUUID)
	if err != nil {
		return err
	}
	if exists {
		return errChatHistoryForbidden
	}
	return nil
}

func (s *ChatHistoryService) GetMessages(ctx context.Context, userID, sessionID string, limit, offset int) ([]ChatHistoryMessage, error) {
	if limit <= 0 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}

	// 1. Try Redis first
	messages, err := s.getMessagesFromRedis(ctx, userID, sessionID)
	if err != nil {
		// Security errors must not be swallowed — never fallback to DB on access denial
		if errors.Is(err, errChatHistoryForbidden) {
			return nil, err
		}
		zap.L().Warn("Chat history Redis query failed; trying DB fallback",
			zap.String("session_id", sessionID),
			zap.Error(err),
		)
	} else if len(messages) > 0 {
		// Cache hit. HISTORY-TAIL: before trusting the cache, repair a
		// truncated tail against the authoritative DB (bounded by the
		// per-session probe watermark), then page the merged window.
		messages = s.repairTailFromDB(ctx, userID, sessionID, messages)
		return sliceMessagesPage(messages, limit, offset), nil
	}

	// 2. Fallback to PostgreSQL if Redis is empty or failed
	if s.pool != nil {
		messages, err = s.getMessagesFromDB(ctx, userID, sessionID, limit, offset)
		if err != nil {
			zap.L().Error("Chat history DB fallback failed",
				zap.String("session_id", sessionID),
				zap.Error(err),
			)
			return nil, err
		}

		// 3. Backfill Redis cache (async) - only if we got data from DB
		if len(messages) > 0 {
			s.startBackfill(func() { s.backfillRedisMessages(sessionID, messages) })
		}

		return messages, nil
	}

	// 4. Return empty if no DB pool available
	return []ChatHistoryMessage{}, nil
}

// getMessagesFromRedis fetches the full message list from Redis cache (the
// ownership filter applied). Paging is applied by sliceMessagesPage AFTER the
// HISTORY-TAIL tail repair, so offset windows are computed on the merged view.
func (s *ChatHistoryService) getMessagesFromRedis(ctx context.Context, userID, sessionID string) ([]ChatHistoryMessage, error) {
	metaKey := fmt.Sprintf("chat:session_meta:%s", sessionID)
	owner, err := s.rdb.HGet(ctx, metaKey, "user_id").Result()
	if err != nil && err != redis.Nil {
		return nil, err
	}
	// If meta exists and owner doesn't match, reject immediately (even if messages list is empty)
	if owner != "" && owner != userID {
		return nil, errChatHistoryForbidden
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
	return messages, nil
}

// sliceMessagesPage applies the history paging window (limit/offset counted
// from the newest message backwards). Semantics are extracted verbatim from
// the old getMessagesFromRedis slicing.
func sliceMessagesPage(messages []ChatHistoryMessage, limit, offset int) []ChatHistoryMessage {
	if offset >= len(messages) {
		return []ChatHistoryMessage{}
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
		return []ChatHistoryMessage{}
	}
	return messages[start:end]
}

// getMessagesFromDB fetches messages from PostgreSQL as fallback
func (s *ChatHistoryService) getMessagesFromDB(ctx context.Context, userID, sessionID string, limit, offset int) ([]ChatHistoryMessage, error) {
	if s.pool == nil {
		return nil, fmt.Errorf("database pool not initialized")
	}

	// Parse UUIDs
	var sessionUUID, userUUID pgtype.UUID
	if err := sessionUUID.Scan(sessionID); err != nil {
		// P2-E (daily-flow R2): session labels like "df2-d1-s1" are legal
		// client-side ids. The engine persisted those rows under a derived
		// pseudo UUID (see resolveSessionUUID), so a label must resolve to
		// the same UUID here instead of failing the whole read with
		// "invalid session_id" (surfaced as a 500 once the Redis cache
		// expired).
		derived := resolveSessionUUID(sessionID)
		sessionUUID = pgtype.UUID{Bytes: derived, Valid: true}
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
			return nil, errChatHistoryForbidden
		}
		return []ChatHistoryMessage{}, nil
	}

	// N-2（web-round2）：chat_messages.metadata 已由 gfix03 迁移删除
	// （docs/competition/2026-tmall-hackathon/系统审查/round2/schema-route-tail.md；
	// 全仓审计漏掉了本文件这段手写 SQL，导致 DB fallback 必然 42703 → 500）。
	// 富元数据由引擎侧持久化管道负责，不再从该列重建。
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

	messages, err := scanChatMessageRows(rows)
	if err != nil {
		return nil, err
	}

	for left, right := 0, len(messages)-1; left < right; left, right = left+1, right-1 {
		messages[left], messages[right] = messages[right], messages[left]
	}
	return messages, nil
}

// scanChatMessageRows maps chat_messages rows (newest-first or oldest-first
// per the caller's ORDER BY) into history messages. Shared by the DB fallback
// reader and the HISTORY-TAIL tail probe.
func scanChatMessageRows(rows pgx.Rows) ([]ChatHistoryMessage, error) {
	messages := make([]ChatHistoryMessage, 0, 16)
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
		msg := ChatHistoryMessage{
			ID:        id.String(),
			SessionID: dbSession.String(),
			UserID:    dbUser.String(),
			Role:      role,
			Content:   content,
			Timestamp: fmt.Sprintf("%d", createdAt.Time.Unix()),
		}
		messages = append(messages, msg)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return messages, nil
}

// probeTailFromDB fetches the authoritative messages the engine persisted
// after `since` (oldest-first). It is the production tailProbeFn; the query is
// a range scan on idx_chat_user_session_created_at.
func (s *ChatHistoryService) probeTailFromDB(ctx context.Context, sessionID, userID string, since time.Time) ([]ChatHistoryMessage, error) {
	if s.pool == nil {
		return nil, fmt.Errorf("database pool not initialized")
	}

	var sessionUUID, userUUID pgtype.UUID
	if err := sessionUUID.Scan(sessionID); err != nil {
		// Session labels resolve to the engine's derived pseudo UUID, same as
		// getMessagesFromDB (P2-E).
		derived := resolveSessionUUID(sessionID)
		sessionUUID = pgtype.UUID{Bytes: derived, Valid: true}
	}
	if err := userUUID.Scan(userID); err != nil {
		return nil, fmt.Errorf("invalid user_id: %w", err)
	}

	rows, err := s.pool.Query(ctx, `
		SELECT id, session_id, user_id, role, content, created_at
		FROM chat_messages
		WHERE session_id = $1 AND user_id = $2 AND created_at > $3
		ORDER BY created_at ASC
		LIMIT $4
	`, sessionUUID, userUUID, since, chatHistoryTailProbeRowLimit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanChatMessageRows(rows)
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
			zap.L().Error("Failed to marshal chat history message for Redis backfill",
				zap.String("session_id", sessionID),
				zap.Error(err),
			)
			continue
		}
		// P1修复: 捕获 RPush 错误，不再静默失败
		if err := s.rdb.RPush(ctx, cacheKey, msgBytes).Err(); err != nil {
			zap.L().Error("Failed to push chat history Redis backfill message",
				zap.String("session_id", sessionID),
				zap.String("cache_key", cacheKey),
				zap.Error(err),
			)
			return // Redis 不可用时提前终止，避免无效循环
		}
		successCount++
	}

	if err := s.rdb.LTrim(ctx, cacheKey, -20, -1).Err(); err != nil {
		zap.L().Error("Failed to trim chat history Redis backfill cache",
			zap.String("session_id", sessionID),
			zap.String("cache_key", cacheKey),
			zap.Error(err),
		)
	}
	if err := s.rdb.Expire(ctx, cacheKey, s.chatHistoryTTL).Err(); err != nil {
		zap.L().Error("Failed to set chat history Redis backfill expiration",
			zap.String("session_id", sessionID),
			zap.String("cache_key", cacheKey),
			zap.Duration("ttl", s.chatHistoryTTL),
			zap.Error(err),
		)
	}

	zap.L().Info("Backfilled chat history Redis cache",
		zap.String("session_id", sessionID),
		zap.Int("success_count", successCount),
		zap.Int("message_count", len(messages)),
	)
}

// repairTailFromDB closes the HISTORY-TAIL gap on a cache hit: the cache only
// receives gateway-appended messages while the engine persists to PostgreSQL
// independently, so a live-but-truncated cache must be re-checked against the
// authoritative DB tail. Probes are bounded by a per-session watermark
// (chatHistoryTailProbeInterval): within the window the hit is served from
// Redis only, past it the DB tail is probed once, missing messages are merged
// into the returned window and the cache is rewritten. Every failure path
// degrades to the plain cache view (the historical behaviour).
func (s *ChatHistoryService) repairTailFromDB(ctx context.Context, userID, sessionID string, cached []ChatHistoryMessage) []ChatHistoryMessage {
	if s.tailProbeFn == nil {
		return cached
	}

	// Per-session probe watermark: fresh hits stay pure-Redis (no added DB
	// cost, no latency regression); stale ones re-check the DB tail once.
	metaKey := fmt.Sprintf("chat:session_meta:%s", sessionID)
	if checkedAt, err := s.rdb.HGet(ctx, metaKey, chatHistoryTailCheckedAtField).Result(); err == nil {
		if t, perr := time.Parse(time.RFC3339, checkedAt); perr == nil && time.Since(t) < chatHistoryTailProbeInterval {
			return cached
		}
	} else if err != redis.Nil {
		zap.L().Warn("Chat history tail watermark read failed; serving cache",
			zap.String("session_id", sessionID),
			zap.Error(err),
		)
		return cached
	}
	// Stamp BEFORE probing so a slow or failing DB cannot turn every read
	// into a probe; worst-case staleness is bounded by the probe interval.
	_ = s.rdb.HSet(ctx, metaKey, chatHistoryTailCheckedAtField, time.Now().UTC().Format(time.RFC3339)).Err()
	_ = s.rdb.Expire(ctx, metaKey, s.chatHistoryTTL).Err()

	oldest := parseUnixString(cached[0].Timestamp)
	for _, msg := range cached[1:] {
		if t := parseUnixString(msg.Timestamp); t.Before(oldest) {
			oldest = t
		}
	}

	probeCtx, cancelProbe := context.WithTimeout(ctx, chatHistoryTailProbeTimeout)
	dbRows, err := s.tailProbeFn(probeCtx, sessionID, userID, oldest.Add(-chatHistoryTailLookback))
	cancelProbe()
	if err != nil {
		zap.L().Warn("Chat history tail probe failed; serving cache",
			zap.String("session_id", sessionID),
			zap.Error(err),
		)
		return cached
	}

	merged, dbOnly, matched := mergeCacheAndDBTail(cached, dbRows)
	if len(dbOnly) == 0 {
		return cached
	}
	if matched == 0 {
		// Not a single cached message matches any probed DB row: the two
		// sources carry incompatible content shapes and a merge would
		// duplicate every turn. The DB is the single-writer authoritative
		// view — serve it and rewrite the cache from it instead.
		authoritative, dbErr := s.getMessagesFromDB(ctx, userID, sessionID, chatHistoryTailProbeRowLimit, 0)
		if dbErr != nil || len(authoritative) == 0 {
			zap.L().Warn("Chat history tail sources diverged; DB fallback failed",
				zap.String("session_id", sessionID),
				zap.Error(dbErr),
			)
			return cached
		}
		zap.L().Info("Chat history cache diverged from DB; serving authoritative view",
			zap.String("session_id", sessionID),
			zap.Int("cached", len(cached)),
			zap.Int("authoritative", len(authoritative)),
		)
		s.startBackfill(func() { s.replaceRedisMessages(sessionID, authoritative) })
		return authoritative
	}

	zap.L().Info("Repaired truncated chat history tail from DB",
		zap.String("session_id", sessionID),
		zap.Int("cached", len(cached)),
		zap.Int("merged", len(merged)),
	)
	s.startBackfill(func() { s.replaceRedisMessages(sessionID, merged) })
	s.refreshSessionMetaTail(ctx, sessionID, merged)
	return merged
}

// mergeCacheAndDBTail folds DB rows probed behind the cache into the cached
// view. A DB row counts as already-covered when an unconsumed cache message
// carries the same (role, content) within chatHistoryTailMatchTolerance —
// gateway appends and engine persists are the same logical message under
// unrelated IDs, matched by content. Legitimate identical retries (V13 B-02)
// are paired in timestamp order, nearest first. Returns the merged view
// (cached ∪ dbOnly, stable-sorted by timestamp), the DB-only tail messages
// and how many cache messages a DB row was matched to.
func mergeCacheAndDBTail(cached, dbRows []ChatHistoryMessage) (merged, dbOnly []ChatHistoryMessage, matched int) {
	consumed := make([]bool, len(cached))
	dbOnly = make([]ChatHistoryMessage, 0, len(dbRows))
	tolerance := int64(chatHistoryTailMatchTolerance / time.Second)

	for _, row := range dbRows {
		rowTs := chatMessageTs(row)
		best := -1
		var bestDelta int64
		for i, cm := range cached {
			if consumed[i] || cm.Role != row.Role || cm.Content != row.Content {
				continue
			}
			delta := chatMessageTs(cm) - rowTs
			if delta < 0 {
				delta = -delta
			}
			if best != -1 && delta >= bestDelta {
				continue
			}
			best, bestDelta = i, delta
		}
		if best != -1 && bestDelta <= tolerance {
			consumed[best] = true
			matched++
			continue
		}
		dbOnly = append(dbOnly, row)
	}

	if len(dbOnly) == 0 {
		return cached, dbOnly, matched
	}
	merged = make([]ChatHistoryMessage, 0, len(cached)+len(dbOnly))
	merged = append(merged, cached...)
	merged = append(merged, dbOnly...)
	sort.SliceStable(merged, func(i, j int) bool {
		return chatMessageTs(merged[i]) < chatMessageTs(merged[j])
	})
	return merged, dbOnly, matched
}

func chatMessageTs(msg ChatHistoryMessage) int64 {
	return parseUnixString(msg.Timestamp).Unix()
}

// replaceRedisMessages rewrites the cached history with the given view in one
// transaction (DEL+RPUSH+LTRIM+EXPIRE), so a tail repair can never append on
// top of a stale list the way a plain RPush backfill would.
func (s *ChatHistoryService) replaceRedisMessages(sessionID string, messages []ChatHistoryMessage) {
	ctx := context.Background()
	cacheKey := "chat:history:" + sessionID
	pipe := s.rdb.TxPipeline()
	pipe.Del(ctx, cacheKey)
	for _, msg := range messages {
		msgBytes, err := json.Marshal(msg)
		if err != nil {
			zap.L().Error("Failed to marshal chat history message for cache repair",
				zap.String("session_id", sessionID),
				zap.Error(err),
			)
			continue
		}
		pipe.RPush(ctx, cacheKey, msgBytes)
	}
	pipe.LTrim(ctx, cacheKey, -20, -1)
	pipe.Expire(ctx, cacheKey, s.chatHistoryTTL)
	if _, err := pipe.Exec(ctx); err != nil {
		zap.L().Error("Failed to rewrite chat history cache after tail repair",
			zap.String("session_id", sessionID),
			zap.Error(err),
		)
	}
}

// refreshSessionMetaTail aligns the cached session metadata with the repaired
// tail so the session list no longer advertises a stale last message (part of
// the V13-RETEST dual-metadata contradiction). The title is intentionally left
// to the SaveMessage writer (title = first user prompt there).
func (s *ChatHistoryService) refreshSessionMetaTail(ctx context.Context, sessionID string, merged []ChatHistoryMessage) {
	if len(merged) == 0 {
		return
	}
	last := merged[len(merged)-1]
	preview := strings.TrimSpace(last.Content)
	if preview == "" {
		return
	}
	if len(preview) > 120 {
		preview = preview[:120]
	}
	metaKey := fmt.Sprintf("chat:session_meta:%s", sessionID)
	fields := map[string]interface{}{
		"last_preview":    preview,
		"last_message":    preview,
		"last_message_at": parseUnixString(last.Timestamp).UTC().Format(time.RFC3339),
	}
	if err := s.rdb.HSet(ctx, metaKey, fields).Err(); err != nil {
		zap.L().Warn("Failed to refresh chat session meta after tail repair",
			zap.String("session_id", sessionID),
			zap.Error(err),
		)
	}
	_ = s.rdb.Expire(ctx, metaKey, s.chatHistoryTTL).Err()
}

func (s *ChatHistoryService) GetRecentSessions(ctx context.Context, userID string, limit int) ([]ChatSessionSummary, error) {
	if limit <= 0 {
		limit = 20
	}

	// 1. Try Redis first
	sessions, err := s.getRecentSessionsFromRedis(ctx, userID, limit)
	if err != nil {
		zap.L().Warn("Chat session Redis query failed; trying DB fallback",
			zap.String("user_id", userID),
			zap.Error(err),
		)
	} else if len(sessions) > 0 {
		// Cache hit - return immediately
		return sessions, nil
	}

	// 2. Fallback to PostgreSQL if Redis is empty or failed
	if s.pool != nil {
		sessions, err = s.getRecentSessionsFromDB(ctx, userID, limit)
		if err != nil {
			zap.L().Error("Chat session DB fallback failed",
				zap.String("user_id", userID),
				zap.Error(err),
			)
			return nil, err
		}

		// 3. Backfill Redis cache (async) - only if we got data from DB
		if len(sessions) > 0 {
			s.startBackfill(func() { s.backfillRedisCache(userID, sessions) })
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
			title = i18n.T(ctx, "chat_history.new_conversation")
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
		WITH session_rollups AS (
			SELECT
				cm.session_id::text AS session_id,
				COALESCE(MAX(cs.title), '') AS title,
				MAX(cm.created_at) AS last_message_at,
				(
					SELECT cm2.content
					FROM chat_messages cm2
					WHERE cm2.session_id = cm.session_id AND cm2.user_id = $1
					ORDER BY cm2.created_at DESC
					LIMIT 1
				) AS preview
			FROM chat_messages cm
			LEFT JOIN chat_sessions cs ON cs.id = cm.session_id
			WHERE cm.user_id = $1
				AND cm.session_id <> '00000000-0000-0000-0000-000000000000'::uuid
			GROUP BY cm.session_id
		)
		SELECT session_id, title, last_message_at, preview
		FROM session_rollups
		ORDER BY last_message_at DESC
		LIMIT $2
	`

	rows, err := s.pool.Query(ctx, query, userID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	summaries := make([]ChatSessionSummary, 0, limit)
	for rows.Next() {
		var id, title string
		var lastMessageAt time.Time
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
				formattedTitle = i18n.T(ctx, "chat_history.new_conversation")
			}
		}

		summaries = append(summaries, ChatSessionSummary{
			ID:        id,
			Title:     formattedTitle,
			UpdatedAt: lastMessageAt.UTC().Format(time.RFC3339),
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

	zap.L().Info("Backfilled chat session Redis cache",
		zap.String("user_id", userID),
		zap.Int("session_count", len(sessions)),
	)
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

func normalizeDocumentFilter(values []string) []string {
	if len(values) == 0 {
		return []string{}
	}
	seen := make(map[string]struct{}, len(values))
	filter := make([]string, 0, len(values))
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" {
			continue
		}
		if _, ok := seen[trimmed]; ok {
			continue
		}
		seen[trimmed] = struct{}{}
		filter = append(filter, trimmed)
	}
	return filter
}

func buildSessionTitle(ctx context.Context, role, content string) string {
	if role != "user" {
		return i18n.T(ctx, "chat_history.new_conversation")
	}
	title := strings.TrimSpace(content)
	if title == "" {
		return i18n.T(ctx, "chat_history.new_conversation")
	}
	runes := []rune(title)
	if len(runes) > 24 {
		title = string(runes[:24]) + "..."
	}
	return title
}
