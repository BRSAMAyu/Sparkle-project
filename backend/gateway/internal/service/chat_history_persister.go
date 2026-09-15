package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

const (
	// PersisterBatchSize is the maximum number of messages to batch before writing to DB
	PersisterBatchSize = 100
	// PersisterFlushInterval is the maximum time to wait before flushing batch to DB
	PersisterFlushInterval = 5 * time.Second
	// PersisterMaxRetries is the maximum number of retries for failed writes
	PersisterMaxRetries = 5
	// PersisterInitialBackoff is the initial backoff duration for retries
	PersisterInitialBackoff = 100 * time.Millisecond
	// PersisterMaxBackoff is the maximum backoff duration for retries
	PersisterMaxBackoff = 30 * time.Second
)

// ChatHistoryPersister consumes messages from Redis queue and persists them to PostgreSQL
type ChatHistoryPersister struct {
	rdb     *redis.Client
	pool    *pgxpool.Pool
	batch   []ChatHistoryMessage
	batchMu sync.Mutex
	ticker  *time.Ticker
	stopCh  chan struct{}

	// Metrics
	totalPersisted int64
	totalFailed    int64
	lastFlushTime  time.Time
}

// NewChatHistoryPersister creates a new persister instance
func NewChatHistoryPersister(rdb *redis.Client, pool *pgxpool.Pool) *ChatHistoryPersister {
	return &ChatHistoryPersister{
		rdb:    rdb,
		pool:   pool,
		batch:  make([]ChatHistoryMessage, 0, PersisterBatchSize),
		stopCh: make(chan struct{}),
	}
}

// Run starts the persister loop
func (p *ChatHistoryPersister) Run(ctx context.Context) error {
	p.ticker = time.NewTicker(PersisterFlushInterval)
	defer p.ticker.Stop()

	log.Printf("[ChatHistoryPersister] Started with batch_size=%d, flush_interval=%v",
		PersisterBatchSize, PersisterFlushInterval)

	for {
		select {
		case <-ctx.Done():
			log.Printf("[ChatHistoryPersister] Context cancelled, flushing remaining messages")
			p.flushWithRetry(ctx)
			return ctx.Err()
		case <-p.stopCh:
			log.Printf("[ChatHistoryPersister] Stop signal received, flushing remaining messages")
			p.flushWithRetry(ctx)
			return nil
		case <-p.ticker.C:
			// Periodic flush
			if err := p.flushWithRetry(ctx); err != nil {
				log.Printf("[ChatHistoryPersister] Periodic flush failed: %v", err)
			}
		default:
			// Try to consume messages from queue
			if err := p.consumeBatch(ctx); err != nil {
				// Brief sleep on error to avoid tight loop
				time.Sleep(100 * time.Millisecond)
			}
		}
	}
}

// Stop gracefully stops the persister
func (p *ChatHistoryPersister) Stop() {
	close(p.stopCh)
}

// consumeBatch reads up to BatchSize messages from Redis queue
func (p *ChatHistoryPersister) consumeBatch(ctx context.Context) error {
	queueKey := "queue:persist:history"

	// Use LPop to get one message at a time (more reliable than batch pop)
	result, err := p.rdb.LPop(ctx, queueKey).Result()
	if err == redis.Nil {
		// Queue is empty, wait a bit
		time.Sleep(50 * time.Millisecond)
		return nil
	}
	if err != nil {
		return err
	}

	var msg ChatHistoryMessage
	if err := json.Unmarshal([]byte(result), &msg); err != nil {
		log.Printf("[ChatHistoryPersister] Failed to unmarshal message: %v", err)
		return nil // Skip invalid message
	}

	// Ensure message has a stable ID
	if msg.Timestamp == "" {
		msg.Timestamp = fmt.Sprintf("%d", time.Now().UnixNano())
	}

	p.batchMu.Lock()
	p.batch = append(p.batch, msg)
	batchLen := len(p.batch)
	p.batchMu.Unlock()

	// Flush if batch is full
	if batchLen >= PersisterBatchSize {
		return p.flushWithRetry(ctx)
	}

	return nil
}

// flushWithRetry flushes the current batch to DB with exponential backoff retry
func (p *ChatHistoryPersister) flushWithRetry(ctx context.Context) error {
	p.batchMu.Lock()
	if len(p.batch) == 0 {
		p.batchMu.Unlock()
		return nil
	}

	batch := p.batch
	p.batch = make([]ChatHistoryMessage, 0, PersisterBatchSize)
	p.batchMu.Unlock()

	backoff := PersisterInitialBackoff
	var lastErr error

	for attempt := 0; attempt < PersisterMaxRetries; attempt++ {
		if attempt > 0 {
			log.Printf("[ChatHistoryPersister] Retry attempt %d/%d after %v", attempt, PersisterMaxRetries, backoff)
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
			}
			// Exponential backoff with cap
			backoff *= 2
			if backoff > PersisterMaxBackoff {
				backoff = PersisterMaxBackoff
			}
		}

		if err := p.writeBatchToDB(ctx, batch); err != nil {
			lastErr = err
			log.Printf("[ChatHistoryPersister] Write failed (attempt %d): %v", attempt+1, err)
			continue
		}

		p.lastFlushTime = time.Now()
		p.totalPersisted += int64(len(batch))
		log.Printf("[ChatHistoryPersister] Persisted %d messages (total: %d)", len(batch), p.totalPersisted)
		return nil
	}

	// All retries failed - push messages back to queue for later retry
	p.totalFailed += int64(len(batch))
	log.Printf("[ChatHistoryPersister] All retries failed, re-queuing %d messages", len(batch))
	p.requeueMessages(ctx, batch)
	return lastErr
}

// writeBatchToDB writes a batch of messages to PostgreSQL
func (p *ChatHistoryPersister) writeBatchToDB(ctx context.Context, batch []ChatHistoryMessage) error {
	conn, err := p.pool.Acquire(ctx)
	if err != nil {
		return fmt.Errorf("failed to acquire connection: %w", err)
	}
	defer conn.Release()

	// Start transaction
	tx, err := conn.Begin(ctx)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback(ctx)

	for _, msg := range batch {
		// Generate stable UUID for message ID
		messageID := uuid.New().String()

		// Parse session ID or generate if empty
		sessionID := msg.SessionID
		if sessionID == "" {
			sessionID = uuid.New().String()
		}

		// Parse user ID
		var userID uuid.UUID
		if msg.UserID != "" {
			if parsed, err := uuid.Parse(msg.UserID); err == nil {
				userID = parsed
			}
		}

		// Parse role
		role := msg.Role
		if role == "" {
			role = "user"
		}

		// Serialize rich metadata (widgets, tool results, reasoning, UX envelope, agent collaboration)
		metadataJSON := buildMessageMetadata(msg)

		// Insert message with UPSERT (ON CONFLICT DO NOTHING for idempotency)
		_, err := tx.Exec(ctx, `
			INSERT INTO chat_messages (id, session_id, user_id, role, content, metadata, created_at)
			VALUES ($1, $2, $3, $4, $5, $6, to_timestamp($7::bigint / 1000.0))
			ON CONFLICT (id) DO NOTHING
		`, messageID, sessionID, userID, role, msg.Content, metadataJSON, msg.Timestamp)

		if err != nil {
			log.Printf("[ChatHistoryPersister] Failed to insert message: %v", err)
			// Continue with other messages - partial success is acceptable
			continue
		}

		// Upsert session metadata
		if userID != uuid.Nil {
			_, err := tx.Exec(ctx, `
				INSERT INTO chat_sessions (id, user_id, title, last_message_at, is_active, created_at, updated_at)
				VALUES ($1, $2, $3, to_timestamp($4::bigint / 1000.0), true, NOW(), NOW())
				ON CONFLICT (id) DO UPDATE SET
					last_message_at = EXCLUDED.last_message_at,
					updated_at = NOW(),
					title = COALESCE(NULLIF(EXCLUDED.title, ''), chat_sessions.title)
			`, sessionID, userID, buildSessionTitle(ctx, role, msg.Content), msg.Timestamp)

			if err != nil {
				log.Printf("[ChatHistoryPersister] Failed to upsert session: %v", err)
			}
		}
	}

	return tx.Commit(ctx)
}

// buildMessageMetadata serializes rich chat message fields into a JSONB value for DB storage.
// Preserves widgets, tool results, reasoning steps, UX envelope data, agent collaboration,
// and other extended attributes that would otherwise be lost on reload.
func buildMessageMetadata(msg ChatHistoryMessage) []byte {
	meta := make(map[string]interface{})

	if len(msg.Widgets) > 0 {
		meta["widgets"] = msg.Widgets
	}
	if len(msg.ToolResults) > 0 {
		meta["tool_results"] = msg.ToolResults
	}
	if len(msg.ReasoningSteps) > 0 {
		meta["reasoning_steps"] = msg.ReasoningSteps
	}
	if msg.ReasoningSummary != "" {
		meta["reasoning_summary"] = msg.ReasoningSummary
	}
	if msg.IsReasoningComplete {
		meta["is_reasoning_complete"] = true
	}
	if msg.HasErrors {
		meta["has_errors"] = true
	}
	if len(msg.Errors) > 0 {
		meta["errors"] = msg.Errors
	}
	if msg.RequiresConfirmation {
		meta["requires_confirmation"] = true
	}
	if len(msg.ConfirmationData) > 0 {
		meta["confirmation_data"] = msg.ConfirmationData
	}
	if len(msg.Meta) > 0 {
		for k, v := range msg.Meta {
			meta[k] = v
		}
	}
	if len(msg.AgentCollaboration) > 0 {
		meta["agent_collaboration"] = msg.AgentCollaboration
	}

	if len(meta) == 0 {
		return nil
	}
	data, err := json.Marshal(meta)
	if err != nil {
		log.Printf("[ChatHistoryPersister] Failed to marshal message metadata: %v", err)
		return nil
	}
	return data
}

// requeueMessages pushes failed messages back to Redis queue
func (p *ChatHistoryPersister) requeueMessages(ctx context.Context, batch []ChatHistoryMessage) {
	queueKey := "queue:persist:history"

	for _, msg := range batch {
		data, err := json.Marshal(msg)
		if err != nil {
			continue
		}
		// Use LPush to add to front of queue (will be processed next)
		p.rdb.LPush(ctx, queueKey, data)
	}
}

// GetStats returns persister statistics
func (p *ChatHistoryPersister) GetStats() map[string]interface{} {
	p.batchMu.Lock()
	batchLen := len(p.batch)
	p.batchMu.Unlock()

	return map[string]interface{}{
		"total_persisted":  p.totalPersisted,
		"total_failed":     p.totalFailed,
		"pending_batch":    batchLen,
		"last_flush_time":  p.lastFlushTime,
		"batch_size":       PersisterBatchSize,
		"flush_interval":   PersisterFlushInterval.String(),
	}
}
