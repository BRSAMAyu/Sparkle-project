package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

// chatMessageInsertSQL persists one queued message.
//
// DF-2 (daily-flow) fixes, all load-bearing:
//   - no `metadata` column: dropped by migration gfix03, rich metadata is the
//     engine-side pipeline's job (see chat_history.go N-2 note);
//   - `to_timestamp($6::double precision)`: producers enqueue Unix *seconds*
//     (handler.saveMessage, chat_history.go read-back); the previous
//     `/ 1000.0` division wrote 1970 rows;
//   - `ON CONFLICT (id, created_at)`: chat_messages PK is (id, created_at);
//     bare `(id)` fails with 42P10 against no matching unique index;
//   - NOT EXISTS dedup: the engine already persists user+assistant rows for
//     streamed chats (RB-06); without this guard the durable backstop would
//     duplicate every message in DB-fallback history reads.
const chatMessageInsertSQL = `
	INSERT INTO chat_messages (id, session_id, user_id, role, content, created_at, updated_at)
	SELECT $1, $2, $3, $4, $5, ts, ts
	FROM (SELECT to_timestamp($6::double precision) AS ts) AS stamp
	WHERE NOT EXISTS (
		SELECT 1 FROM chat_messages
		WHERE session_id = $2
		  AND role = $4
		  AND content = $5
		  AND created_at BETWEEN to_timestamp($6::double precision) - interval '15 seconds'
		                    AND to_timestamp($6::double precision) + interval '15 seconds'
	)
	ON CONFLICT (id, created_at) DO NOTHING
`

// chatSessionUpsertSQL mirrors the message insert timestamp semantics (epoch
// seconds) for the session list's last_message_at.
const chatSessionUpsertSQL = `
	INSERT INTO chat_sessions (id, user_id, title, last_message_at, is_active, created_at, updated_at)
	VALUES ($1, $2, $3, to_timestamp($4::double precision), true, NOW(), NOW())
	ON CONFLICT (id) DO UPDATE SET
		last_message_at = EXCLUDED.last_message_at,
		updated_at = NOW(),
		title = COALESCE(NULLIF(EXCLUDED.title, ''), chat_sessions.title)
`

// resolveSessionUUID maps a queue session id to a chat_messages.session_uuid.
// Valid UUIDs pass through. Legacy labels ("df-d2-s1") would fail the NOT NULL
// uuid column, so they hash to a deterministic pseudo-session: content stays
// durable and retries/requeues stay idempotent, without colliding with
// server-generated session UUIDs.
func resolveSessionUUID(raw string) uuid.UUID {
	raw = strings.TrimSpace(raw)
	if raw != "" {
		if parsed, err := uuid.Parse(raw); err == nil {
			return parsed
		}
		return uuid.NewMD5(uuid.NameSpaceURL, []byte("sparkle:chat-session:"+raw))
	}
	return uuid.New()
}

// parseMessageTimestampSeconds interprets queued timestamps, which producers
// write as epoch seconds. Tolerates empty values and legacy millisecond or
// RFC3339 payloads so one bad producer cannot shift history by decades.
func parseMessageTimestampSeconds(raw string) time.Time {
	raw = strings.TrimSpace(raw)
	if raw != "" {
		if secs, err := strconv.ParseInt(raw, 10, 64); err == nil {
			if secs > 1_000_000_000_000 { // legacy milliseconds
				return time.Unix(secs/1000, (secs%1000)*int64(time.Millisecond))
			}
			return time.Unix(secs, 0)
		}
		if t, err := time.Parse(time.RFC3339Nano, raw); err == nil {
			return t
		}
	}
	return time.Now()
}

// normalizeChatRole maps producer roles onto the messagerole enum's stored
// values, which are SQLAlchemy member NAMES (USER/ASSISTANT/SYSTEM). Empty
// defaults to USER (legacy behaviour); unknown roles return "" and are skipped.
func normalizeChatRole(raw string) string {
	role := strings.ToUpper(strings.TrimSpace(raw))
	switch role {
	case "":
		return "USER"
	case "USER", "ASSISTANT", "SYSTEM":
		return role
	default:
		return ""
	}
}

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

// DrainOnce pops up to PersisterBatchSize queued messages and flushes them to
// the DB. Exported so ops harnesses can drain the queue without running the
// full Run loop.
func (p *ChatHistoryPersister) DrainOnce(ctx context.Context) error {
	queueKey := "queue:persist:history"
	for i := 0; i < PersisterBatchSize; i++ {
		result, err := p.rdb.LPop(ctx, queueKey).Result()
		if err == redis.Nil {
			break
		}
		if err != nil {
			return err
		}
		var msg ChatHistoryMessage
		if err := json.Unmarshal([]byte(result), &msg); err != nil {
			log.Printf("[ChatHistoryPersister] Failed to unmarshal message: %v", err)
			continue // Skip invalid message
		}
		if msg.Timestamp == "" {
			msg.Timestamp = fmt.Sprintf("%d", time.Now().UnixNano())
		}
		p.batchMu.Lock()
		p.batch = append(p.batch, msg)
		p.batchMu.Unlock()
	}
	return p.flushWithRetry(ctx)
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
		// Stable row id: reuse the producer's UUID so requeued duplicates hit
		// ON CONFLICT instead of inserting twice.
		messageID := msg.ID
		if _, err := uuid.Parse(messageID); err != nil {
			messageID = uuid.New().String()
		}

		// Parse user ID; without an attributable owner the row cannot pass the
		// users FK, so skip instead of failing the whole batch.
		var userID uuid.UUID
		if msg.UserID != "" {
			if parsed, err := uuid.Parse(msg.UserID); err == nil {
				userID = parsed
			} else {
				log.Printf("[ChatHistoryPersister] Skipping message with unparseable user_id %q", msg.UserID)
				continue
			}
		} else {
			log.Printf("[ChatHistoryPersister] Skipping message with empty user_id")
			continue
		}

		// Normalize role to the messagerole enum's stored (uppercase) names;
		// unknown roles are skipped, not fatal to the batch.
		role := normalizeChatRole(msg.Role)
		if role == "" {
			log.Printf("[ChatHistoryPersister] Skipping message with unknown role %q", msg.Role)
			continue
		}

		// Per-message savepoint: one bad row must not poison the rest of the
		// batch (a failed statement aborts the surrounding transaction).
		sp, err := tx.Begin(ctx)
		if err != nil {
			return fmt.Errorf("failed to begin savepoint: %w", err)
		}

		// Insert message with UPSERT (idempotent across requeues) and a
		// dedup guard against rows the engine already persisted.
		// Rich metadata (widgets, tool results, reasoning, UX envelope) is
		// the engine-side pipeline's job: chat_messages.metadata was dropped
		// by migration gfix03.
		sessionUUID := resolveSessionUUID(msg.SessionID)
		epochSeconds := float64(parseMessageTimestampSeconds(msg.Timestamp).Unix())

		if _, err := sp.Exec(ctx, chatMessageInsertSQL,
			messageID, sessionUUID, userID, role, msg.Content, epochSeconds); err != nil {
			log.Printf("[ChatHistoryPersister] Failed to insert message: %v", err)
			sp.Rollback(ctx)
			// Continue with other messages - partial success is acceptable
			continue
		}

		// Upsert session metadata (drives the cross-device session list).
		if _, err := sp.Exec(ctx, chatSessionUpsertSQL,
			sessionUUID, userID, buildSessionTitle(ctx, role, msg.Content), epochSeconds); err != nil {
			log.Printf("[ChatHistoryPersister] Failed to upsert session: %v", err)
		}

		if err := sp.Commit(ctx); err != nil {
			log.Printf("[ChatHistoryPersister] Failed to commit message savepoint: %v", err)
		}
	}

	return tx.Commit(ctx)
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
		"total_persisted": p.totalPersisted,
		"total_failed":    p.totalFailed,
		"pending_batch":   batchLen,
		"last_flush_time": p.lastFlushTime,
		"batch_size":      PersisterBatchSize,
		"flush_interval":  PersisterFlushInterval.String(),
	}
}
