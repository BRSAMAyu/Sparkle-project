// Package worker provides dead letter queue handling for failed events.
package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

// DLQStreamKey is the Redis stream key for the dead letter queue.
const DLQStreamKey = "cqrs:dlq"

// DLQEntry represents a failed event in the dead letter queue.
type DLQEntry struct {
	OriginalStream    string            `json:"original_stream"`
	OriginalMessageID string            `json:"original_message_id"`
	ConsumerGroup     string            `json:"consumer_group"`
	ErrorMessage      string            `json:"error_message"`
	ErrorType         string            `json:"error_type"`
	FailedAt          time.Time         `json:"failed_at"`
	RetryCount        int               `json:"retry_count"`
	OriginalPayload   map[string]string `json:"original_payload"`
}

// SendToDLQ sends a failed event to the dead letter queue.
func SendToDLQ(ctx context.Context, client *redis.Client, entry DLQEntry) error {
	payload, err := json.Marshal(entry)
	if err != nil {
		return fmt.Errorf("marshal DLQ entry: %w", err)
	}

	_, err = client.XAdd(ctx, &redis.XAddArgs{
		Stream: DLQStreamKey,
		Values: map[string]interface{}{
			"payload":             string(payload),
			"original_stream":     entry.OriginalStream,
			"original_message_id": entry.OriginalMessageID,
			"consumer_group":      entry.ConsumerGroup,
			"error_type":          entry.ErrorType,
			"failed_at":           entry.FailedAt.Format(time.RFC3339Nano),
		},
	}).Result()

	if err != nil {
		return fmt.Errorf("add to DLQ stream: %w", err)
	}

	return nil
}

// DLQHandler provides operations for managing the dead letter queue.
type DLQHandler struct {
	redis   *redis.Client
	logger  *zap.Logger
	maxAge  time.Duration
}

// DLQHandlerConfig configures the DLQ handler.
type DLQHandlerConfig struct {
	// MaxAge is the maximum age of DLQ entries before cleanup.
	MaxAge time.Duration
}

// DefaultDLQHandlerConfig returns sensible defaults.
func DefaultDLQHandlerConfig() DLQHandlerConfig {
	return DLQHandlerConfig{
		MaxAge: 7 * 24 * time.Hour, // 7 days
	}
}

// NewDLQHandler creates a new DLQ handler.
func NewDLQHandler(
	redis *redis.Client,
	logger *zap.Logger,
	config ...DLQHandlerConfig,
) *DLQHandler {
	cfg := DefaultDLQHandlerConfig()
	if len(config) > 0 {
		cfg = config[0]
	}

	return &DLQHandler{
		redis:  redis,
		logger: logger.Named("dlq-handler"),
		maxAge: cfg.MaxAge,
	}
}

// GetEntries retrieves entries from the dead letter queue.
func (h *DLQHandler) GetEntries(ctx context.Context, count int64) ([]DLQEntry, error) {
	messages, err := h.redis.XRange(ctx, DLQStreamKey, "-", "+").Result()
	if err != nil {
		return nil, fmt.Errorf("read DLQ: %w", err)
	}

	entries := make([]DLQEntry, 0, len(messages))
	for _, msg := range messages {
		payloadStr, ok := msg.Values["payload"].(string)
		if !ok {
			continue
		}

		var entry DLQEntry
		if err := json.Unmarshal([]byte(payloadStr), &entry); err != nil {
			h.logger.Warn("Failed to unmarshal DLQ entry",
				zap.String("message_id", msg.ID),
				zap.Error(err),
			)
			continue
		}

		entries = append(entries, entry)
		if int64(len(entries)) >= count {
			break
		}
	}

	return entries, nil
}

// GetEntriesByErrorType retrieves entries filtered by error type.
func (h *DLQHandler) GetEntriesByErrorType(ctx context.Context, errorType string, count int64) ([]DLQEntry, error) {
	messages, err := h.redis.XRange(ctx, DLQStreamKey, "-", "+").Result()
	if err != nil {
		return nil, fmt.Errorf("read DLQ: %w", err)
	}

	entries := make([]DLQEntry, 0)
	for _, msg := range messages {
		msgErrorType, ok := msg.Values["error_type"].(string)
		if !ok || msgErrorType != errorType {
			continue
		}

		payloadStr, ok := msg.Values["payload"].(string)
		if !ok {
			continue
		}

		var entry DLQEntry
		if err := json.Unmarshal([]byte(payloadStr), &entry); err != nil {
			continue
		}

		entries = append(entries, entry)
		if int64(len(entries)) >= count {
			break
		}
	}

	return entries, nil
}

// GetEntriesByConsumerGroup retrieves entries filtered by consumer group.
func (h *DLQHandler) GetEntriesByConsumerGroup(ctx context.Context, consumerGroup string, count int64) ([]DLQEntry, error) {
	messages, err := h.redis.XRange(ctx, DLQStreamKey, "-", "+").Result()
	if err != nil {
		return nil, fmt.Errorf("read DLQ: %w", err)
	}

	entries := make([]DLQEntry, 0)
	for _, msg := range messages {
		msgGroup, ok := msg.Values["consumer_group"].(string)
		if !ok || msgGroup != consumerGroup {
			continue
		}

		payloadStr, ok := msg.Values["payload"].(string)
		if !ok {
			continue
		}

		var entry DLQEntry
		if err := json.Unmarshal([]byte(payloadStr), &entry); err != nil {
			continue
		}

		entries = append(entries, entry)
		if int64(len(entries)) >= count {
			break
		}
	}

	return entries, nil
}

// RetryEntry attempts to republish a DLQ entry to its original stream.
func (h *DLQHandler) RetryEntry(ctx context.Context, messageID string) error {
	// Read the specific message
	messages, err := h.redis.XRange(ctx, DLQStreamKey, messageID, messageID).Result()
	if err != nil {
		return fmt.Errorf("read DLQ message: %w", err)
	}

	if len(messages) == 0 {
		return fmt.Errorf("message not found: %s", messageID)
	}

	msg := messages[0]
	payloadStr, ok := msg.Values["payload"].(string)
	if !ok {
		return fmt.Errorf("invalid payload in DLQ message")
	}

	var entry DLQEntry
	if err := json.Unmarshal([]byte(payloadStr), &entry); err != nil {
		return fmt.Errorf("unmarshal DLQ entry: %w", err)
	}

	// Republish to original stream with updated retry count
	entry.RetryCount++
	values := make(map[string]interface{})
	for k, v := range entry.OriginalPayload {
		values[k] = v
	}
	values["_retry_count"] = entry.RetryCount

	_, err = h.redis.XAdd(ctx, &redis.XAddArgs{
		Stream: entry.OriginalStream,
		Values: values,
	}).Result()

	if err != nil {
		return fmt.Errorf("republish to stream: %w", err)
	}

	// Remove from DLQ
	_, err = h.redis.XDel(ctx, DLQStreamKey, messageID).Result()
	if err != nil {
		h.logger.Warn("Failed to delete retried message from DLQ",
			zap.String("message_id", messageID),
			zap.Error(err),
		)
	}

	h.logger.Info("Retried DLQ entry",
		zap.String("message_id", messageID),
		zap.String("original_stream", entry.OriginalStream),
		zap.Int("retry_count", entry.RetryCount),
	)

	return nil
}

// DeleteEntry removes an entry from the dead letter queue.
func (h *DLQHandler) DeleteEntry(ctx context.Context, messageID string) error {
	deleted, err := h.redis.XDel(ctx, DLQStreamKey, messageID).Result()
	if err != nil {
		return fmt.Errorf("delete DLQ entry: %w", err)
	}

	if deleted == 0 {
		return fmt.Errorf("message not found: %s", messageID)
	}

	h.logger.Info("Deleted DLQ entry", zap.String("message_id", messageID))
	return nil
}

// Cleanup removes old entries from the dead letter queue.
func (h *DLQHandler) Cleanup(ctx context.Context) (int64, error) {
	cutoff := time.Now().Add(-h.maxAge)
	cutoffStr := cutoff.Format(time.RFC3339Nano)

	messages, err := h.redis.XRange(ctx, DLQStreamKey, "-", "+").Result()
	if err != nil {
		return 0, fmt.Errorf("read DLQ: %w", err)
	}

	var deleted int64
	for _, msg := range messages {
		failedAtStr, ok := msg.Values["failed_at"].(string)
		if !ok {
			continue
		}

		failedAt, err := time.Parse(time.RFC3339Nano, failedAtStr)
		if err != nil {
			continue
		}

		if failedAt.Before(cutoff) {
			_, err := h.redis.XDel(ctx, DLQStreamKey, msg.ID).Result()
			if err == nil {
				deleted++
			}
		}
	}

	if deleted > 0 {
		h.logger.Info("Cleaned up old DLQ entries",
			zap.Int64("deleted_count", deleted),
			zap.String("cutoff", cutoffStr),
		)
	}

	return deleted, nil
}

// GetCount returns the total number of entries in the DLQ.
func (h *DLQHandler) GetCount(ctx context.Context) (int64, error) {
	return h.redis.XLen(ctx, DLQStreamKey).Result()
}

// GetStats returns statistics about the DLQ.
type DLQStats struct {
	TotalCount       int64            `json:"total_count"`
	ByErrorType      map[string]int64 `json:"by_error_type"`
	ByConsumerGroup  map[string]int64 `json:"by_consumer_group"`
	OldestEntryTime  *time.Time       `json:"oldest_entry_time"`
	NewestEntryTime  *time.Time       `json:"newest_entry_time"`
}

// GetStats retrieves statistics about the dead letter queue.
func (h *DLQHandler) GetStats(ctx context.Context) (*DLQStats, error) {
	messages, err := h.redis.XRange(ctx, DLQStreamKey, "-", "+").Result()
	if err != nil {
		return nil, fmt.Errorf("read DLQ: %w", err)
	}

	stats := &DLQStats{
		TotalCount:      int64(len(messages)),
		ByErrorType:     make(map[string]int64),
		ByConsumerGroup: make(map[string]int64),
	}

	for i, msg := range messages {
		// Count by error type
		if errorType, ok := msg.Values["error_type"].(string); ok {
			stats.ByErrorType[errorType]++
		}

		// Count by consumer group
		if group, ok := msg.Values["consumer_group"].(string); ok {
			stats.ByConsumerGroup[group]++
		}

		// Track oldest and newest
		if failedAtStr, ok := msg.Values["failed_at"].(string); ok {
			failedAt, err := time.Parse(time.RFC3339Nano, failedAtStr)
			if err == nil {
				if i == 0 {
					stats.OldestEntryTime = &failedAt
				}
				stats.NewestEntryTime = &failedAt
			}
		}
	}

	return stats, nil
}

// DLQCleaner runs periodic cleanup of the dead letter queue.
type DLQCleaner struct {
	handler       *DLQHandler
	cleanInterval time.Duration
	logger        *zap.Logger
}

// NewDLQCleaner creates a new DLQ cleaner.
func NewDLQCleaner(handler *DLQHandler, cleanInterval time.Duration, logger *zap.Logger) *DLQCleaner {
	if cleanInterval == 0 {
		cleanInterval = 24 * time.Hour
	}

	return &DLQCleaner{
		handler:       handler,
		cleanInterval: cleanInterval,
		logger:        logger.Named("dlq-cleaner"),
	}
}

// Run starts the cleaner loop. Blocks until context is cancelled.
func (c *DLQCleaner) Run(ctx context.Context) error {
	c.logger.Info("DLQ cleaner started",
		zap.Duration("clean_interval", c.cleanInterval),
	)

	ticker := time.NewTicker(c.cleanInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			c.logger.Info("DLQ cleaner stopping")
			return ctx.Err()
		case <-ticker.C:
			deleted, err := c.handler.Cleanup(ctx)
			if err != nil {
				c.logger.Error("DLQ cleanup failed", zap.Error(err))
			} else if deleted > 0 {
				c.logger.Info("DLQ cleanup completed",
					zap.Int64("deleted_count", deleted),
				)
			}
		}
	}
}
