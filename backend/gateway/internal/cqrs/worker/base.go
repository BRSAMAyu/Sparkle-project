// Package worker provides the base worker implementation for event consumers.
package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	"go.uber.org/zap"
)

// BaseWorker provides common functionality for event workers.
type BaseWorker struct {
	redis           *redis.Client
	processedEvents *outbox.ProcessedEventsRepository
	metrics         *metrics.CQRSMetrics
	logger          *zap.Logger

	streamKey    string
	consumerGroup string
	consumerName string

	retryConfig RetryConfig
	options     WorkerOptions

	// State
	running      atomic.Bool
	processedIDs sync.Map // In-memory cache for recent events
}

// WorkerOptions configures worker behavior.
type WorkerOptions struct {
	// BatchSize is the maximum number of events to fetch per read.
	BatchSize int64

	// BlockTimeout is how long to wait for new events (in milliseconds).
	BlockTimeout time.Duration

	// IdempotencyCheck enables database-based idempotency checking.
	IdempotencyCheck bool

	// EnableDLQ enables sending failed events to the dead letter queue.
	EnableDLQ bool

	// MaxRetries is the maximum number of retries before sending to DLQ.
	MaxRetries int
}

// DefaultWorkerOptions returns sensible defaults.
func DefaultWorkerOptions() WorkerOptions {
	return WorkerOptions{
		BatchSize:        10,
		BlockTimeout:     2 * time.Second,
		IdempotencyCheck: true,
		EnableDLQ:        true,
		MaxRetries:       3,
	}
}

// RetryConfig defines retry behavior with exponential backoff.
type RetryConfig struct {
	MaxRetries     int
	InitialBackoff time.Duration
	MaxBackoff     time.Duration
	Multiplier     float64
}

// DefaultRetryConfig returns sensible defaults.
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{
		MaxRetries:     3,
		InitialBackoff: 100 * time.Millisecond,
		MaxBackoff:     30 * time.Second,
		Multiplier:     2.0,
	}
}

// NewBaseWorker creates a new base worker.
func NewBaseWorker(
	redis *redis.Client,
	processedEvents *outbox.ProcessedEventsRepository,
	metrics *metrics.CQRSMetrics,
	logger *zap.Logger,
	streamKey, consumerGroup, consumerName string,
	opts ...WorkerOptions,
) *BaseWorker {
	options := DefaultWorkerOptions()
	if len(opts) > 0 {
		options = opts[0]
	}

	return &BaseWorker{
		redis:           redis,
		processedEvents: processedEvents,
		metrics:         metrics,
		logger:          logger.Named(consumerGroup),
		streamKey:       streamKey,
		consumerGroup:   consumerGroup,
		consumerName:    consumerName,
		retryConfig:     DefaultRetryConfig(),
		options:         options,
	}
}

// Run starts the worker loop. Blocks until context is cancelled.
func (w *BaseWorker) Run(ctx context.Context, handler event.EventHandler) error {
	if !w.running.CompareAndSwap(false, true) {
		return nil // Already running
	}
	defer w.running.Store(false)

	w.logger.Info("Worker started",
		zap.String("stream", w.streamKey),
		zap.String("group", w.consumerGroup),
		zap.String("consumer", w.consumerName),
	)

	// Create consumer group if it doesn't exist
	err := w.redis.XGroupCreateMkStream(ctx, w.streamKey, w.consumerGroup, "0").Err()
	if err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
		return fmt.Errorf("create consumer group: %w", err)
	}

	for {
		select {
		case <-ctx.Done():
			w.logger.Info("Worker stopping")
			return ctx.Err()
		default:
			if err := w.processMessages(ctx, handler); err != nil {
				w.logger.Error("Error processing messages", zap.Error(err))
				w.metrics.RecordWorkerError(w.consumerGroup, "process_batch")
				time.Sleep(time.Second) // Backoff on error
			}
		}
	}
}

func (w *BaseWorker) processMessages(ctx context.Context, handler event.EventHandler) error {
	// Read messages from stream
	entries, err := w.redis.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    w.consumerGroup,
		Consumer: w.consumerName,
		Streams:  []string{w.streamKey, ">"},
		Count:    w.options.BatchSize,
		Block:    w.options.BlockTimeout,
	}).Result()

	if err != nil {
		if err == redis.Nil {
			return nil // No new messages
		}
		return fmt.Errorf("xreadgroup: %w", err)
	}

	for _, stream := range entries {
		for _, msg := range stream.Messages {
			w.processMessage(ctx, msg, handler)
		}
	}

	// Update consumer lag metric
	pending, err := w.redis.XPending(ctx, w.streamKey, w.consumerGroup).Result()
	if err == nil {
		w.metrics.SetConsumerLag(w.streamKey, w.consumerGroup, float64(pending.Count))
	}

	return nil
}

func (w *BaseWorker) processMessage(ctx context.Context, msg redis.XMessage, handler event.EventHandler) {
	messageID := msg.ID
	startTime := time.Now()

	// Check idempotency
	if w.options.IdempotencyCheck {
		if w.isProcessed(ctx, messageID) {
			w.acknowledge(ctx, messageID)
			w.metrics.RecordDuplicateEvent()
			w.logger.Debug("Skipping duplicate event", zap.String("message_id", messageID))
			return
		}
	}

	// Parse event
	domainEvent, err := parseRedisMessage(msg)
	if err != nil {
		w.logger.Error("Failed to parse message",
			zap.String("message_id", messageID),
			zap.Error(err),
		)
		w.sendToDLQ(ctx, msg, err, "parse_error")
		w.acknowledge(ctx, messageID)
		return
	}

	// Process with retry
	err = w.processWithRetry(ctx, domainEvent, messageID, handler)
	processingTime := time.Since(startTime)

	if err != nil {
		w.logger.Error("Failed to process event after retries",
			zap.String("event_id", domainEvent.ID),
			zap.String("event_type", string(domainEvent.Type)),
			zap.Error(err),
		)
		w.sendToDLQ(ctx, msg, err, "processing_error")
		w.metrics.RecordWorkerError(w.consumerGroup, "process_event")
	} else {
		// Mark as processed
		w.markProcessed(ctx, messageID)
		w.metrics.RecordEventProcessed(string(domainEvent.Type), w.consumerGroup, processingTime.Seconds())
		w.logger.Debug("Event processed",
			zap.String("event_id", domainEvent.ID),
			zap.String("event_type", string(domainEvent.Type)),
			zap.Duration("duration", processingTime),
		)
	}

	// Always acknowledge to prevent redelivery
	w.acknowledge(ctx, messageID)
}

func (w *BaseWorker) processWithRetry(
	ctx context.Context,
	evt *event.DomainEvent,
	messageID string,
	handler event.EventHandler,
) error {
	var lastErr error
	backoff := w.retryConfig.InitialBackoff

	for attempt := 0; attempt <= w.retryConfig.MaxRetries; attempt++ {
		if attempt > 0 {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
			}

			backoff = time.Duration(float64(backoff) * w.retryConfig.Multiplier)
			if backoff > w.retryConfig.MaxBackoff {
				backoff = w.retryConfig.MaxBackoff
			}
			w.metrics.RecordRetry(w.consumerGroup)
			w.logger.Debug("Retrying event",
				zap.String("event_id", evt.ID),
				zap.Int("attempt", attempt),
			)
		}

		if err := handler(ctx, *evt, messageID); err != nil {
			lastErr = err
			continue
		}
		return nil
	}

	return fmt.Errorf("max retries exceeded: %w", lastErr)
}

func (w *BaseWorker) isProcessed(ctx context.Context, messageID string) bool {
	// Check in-memory cache first
	if _, ok := w.processedIDs.Load(messageID); ok {
		return true
	}

	// Check database
	if w.processedEvents != nil {
		processed, err := w.processedEvents.IsProcessed(ctx, messageID, w.consumerGroup)
		if err != nil {
			w.logger.Warn("Failed to check processed status", zap.Error(err))
			return false
		}
		return processed
	}

	return false
}

func (w *BaseWorker) markProcessed(ctx context.Context, messageID string) {
	// Add to in-memory cache
	w.processedIDs.Store(messageID, true)

	// Persist to database
	if w.processedEvents != nil {
		if err := w.processedEvents.MarkProcessed(ctx, messageID, w.consumerGroup); err != nil {
			w.logger.Warn("Failed to mark as processed", zap.Error(err))
		}
	}
}

func (w *BaseWorker) acknowledge(ctx context.Context, messageID string) {
	if err := w.redis.XAck(ctx, w.streamKey, w.consumerGroup, messageID).Err(); err != nil {
		w.logger.Warn("Failed to acknowledge message",
			zap.String("message_id", messageID),
			zap.Error(err),
		)
	}
}

func (w *BaseWorker) sendToDLQ(ctx context.Context, msg redis.XMessage, err error, errorType string) {
	if !w.options.EnableDLQ {
		return
	}

	dlqEntry := DLQEntry{
		OriginalStream:    w.streamKey,
		OriginalMessageID: msg.ID,
		ConsumerGroup:     w.consumerGroup,
		ErrorMessage:      err.Error(),
		ErrorType:         errorType,
		FailedAt:          time.Now().UTC(),
		RetryCount:        0,
		OriginalPayload:   make(map[string]string),
	}

	for k, v := range msg.Values {
		if str, ok := v.(string); ok {
			dlqEntry.OriginalPayload[k] = str
		}
	}

	if err := SendToDLQ(ctx, w.redis, dlqEntry); err != nil {
		w.logger.Error("Failed to send to DLQ",
			zap.String("message_id", msg.ID),
			zap.Error(err),
		)
	}

	w.metrics.RecordDLQMessage(errorType, w.consumerGroup)
}

// IsRunning returns true if the worker is currently running.
func (w *BaseWorker) IsRunning() bool {
	return w.running.Load()
}

// parseRedisMessage converts a Redis Stream message to a DomainEvent.
func parseRedisMessage(msg redis.XMessage) (*event.DomainEvent, error) {
	var evt event.DomainEvent

	// Extract required fields
	id, ok := msg.Values["id"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid event id")
	}
	evt.ID = id

	eventType, ok := msg.Values["type"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid event type")
	}
	evt.Type = event.EventType(eventType)

	aggregateType, ok := msg.Values["aggregate_type"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid aggregate type")
	}
	evt.AggregateType = event.AggregateType(aggregateType)

	aggregateID, ok := msg.Values["aggregate_id"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid aggregate id")
	}
	parsedUUID, err := parseUUID(aggregateID)
	if err != nil {
		return nil, fmt.Errorf("invalid aggregate id: %w", err)
	}
	evt.AggregateID = parsedUUID

	timestamp, ok := msg.Values["timestamp"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid timestamp")
	}
	parsedTime, err := time.Parse(time.RFC3339Nano, timestamp)
	if err != nil {
		return nil, fmt.Errorf("invalid timestamp: %w", err)
	}
	evt.Timestamp = parsedTime

	// Parse version (optional, default to 1)
	if version, ok := msg.Values["version"].(string); ok {
		var v int
		fmt.Sscanf(version, "%d", &v)
		evt.Version = v
	} else {
		evt.Version = 1
	}

	// Parse payload
	if payload, ok := msg.Values["payload"].(string); ok {
		if err := json.Unmarshal([]byte(payload), &evt.Payload); err != nil {
			return nil, fmt.Errorf("invalid payload json: %w", err)
		}
	}

	// Parse metadata (optional)
	if metadata, ok := msg.Values["metadata"].(string); ok && metadata != "" {
		if err := json.Unmarshal([]byte(metadata), &evt.Metadata); err != nil {
			// Non-fatal: metadata is optional
			evt.Metadata = event.EventMetadata{}
		}
	}

	return &evt, nil
}

func parseUUID(s string) (uuid.UUID, error) {
	return uuid.Parse(s)
}
