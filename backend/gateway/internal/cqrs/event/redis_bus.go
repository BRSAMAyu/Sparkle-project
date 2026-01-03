// Package event provides the Redis Stream implementation of the event bus.
package event

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

// RedisEventBus implements EventBus using Redis Streams.
type RedisEventBus struct {
	client  *redis.Client
	maxLen  int64 // Maximum stream length (0 = unlimited)
	options RedisEventBusOptions
}

// RedisEventBusOptions configures the Redis event bus.
type RedisEventBusOptions struct {
	// MaxStreamLength limits the stream size using MAXLEN ~.
	// Set to 0 for unlimited (not recommended in production).
	MaxStreamLength int64

	// DefaultTTL is the default TTL for stream entries (not natively supported by Redis Streams).
	// This is used for cleanup scheduling.
	DefaultTTL time.Duration
}

// DefaultRedisEventBusOptions returns sensible defaults.
func DefaultRedisEventBusOptions() RedisEventBusOptions {
	return RedisEventBusOptions{
		MaxStreamLength: 100000, // Keep last 100k events per stream
		DefaultTTL:      7 * 24 * time.Hour,
	}
}

// NewRedisEventBus creates a new Redis-backed event bus.
func NewRedisEventBus(client *redis.Client, opts ...RedisEventBusOptions) *RedisEventBus {
	options := DefaultRedisEventBusOptions()
	if len(opts) > 0 {
		options = opts[0]
	}

	return &RedisEventBus{
		client:  client,
		maxLen:  options.MaxStreamLength,
		options: options,
	}
}

// Publish publishes a single event to the appropriate Redis Stream.
func (b *RedisEventBus) Publish(ctx context.Context, event DomainEvent) error {
	streamKey := event.Type.StreamKey()

	payload, err := json.Marshal(event.Payload)
	if err != nil {
		return fmt.Errorf("marshal payload: %w", err)
	}

	metadata, err := json.Marshal(event.Metadata)
	if err != nil {
		return fmt.Errorf("marshal metadata: %w", err)
	}

	args := &redis.XAddArgs{
		Stream: streamKey,
		Values: map[string]interface{}{
			"id":             event.ID,
			"type":           string(event.Type),
			"version":        event.Version,
			"aggregate_type": string(event.AggregateType),
			"aggregate_id":   event.AggregateID.String(),
			"timestamp":      event.Timestamp.Format(time.RFC3339Nano),
			"payload":        string(payload),
			"metadata":       string(metadata),
		},
	}

	// Apply MAXLEN ~ to trim the stream approximately
	if b.maxLen > 0 {
		args.MaxLen = b.maxLen
		args.Approx = true
	}

	_, err = b.client.XAdd(ctx, args).Result()
	if err != nil {
		return fmt.Errorf("xadd to stream %s: %w", streamKey, err)
	}

	return nil
}

// PublishBatch publishes multiple events, grouping by stream for efficiency.
func (b *RedisEventBus) PublishBatch(ctx context.Context, events []DomainEvent) error {
	if len(events) == 0 {
		return nil
	}

	pipe := b.client.Pipeline()

	for _, event := range events {
		streamKey := event.Type.StreamKey()

		payload, err := json.Marshal(event.Payload)
		if err != nil {
			return fmt.Errorf("marshal payload for event %s: %w", event.ID, err)
		}

		metadata, err := json.Marshal(event.Metadata)
		if err != nil {
			return fmt.Errorf("marshal metadata for event %s: %w", event.ID, err)
		}

		args := &redis.XAddArgs{
			Stream: streamKey,
			Values: map[string]interface{}{
				"id":             event.ID,
				"type":           string(event.Type),
				"version":        event.Version,
				"aggregate_type": string(event.AggregateType),
				"aggregate_id":   event.AggregateID.String(),
				"timestamp":      event.Timestamp.Format(time.RFC3339Nano),
				"payload":        string(payload),
				"metadata":       string(metadata),
			},
		}

		if b.maxLen > 0 {
			args.MaxLen = b.maxLen
			args.Approx = true
		}

		pipe.XAdd(ctx, args)
	}

	_, err := pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("pipeline exec: %w", err)
	}

	return nil
}

// Close releases resources (no-op for Redis client as it's shared).
func (b *RedisEventBus) Close() error {
	return nil
}

// RedisEventConsumer implements EventConsumer using Redis Streams consumer groups.
type RedisEventConsumer struct {
	client  *redis.Client
	options SubscriptionOptions
}

// NewRedisEventConsumer creates a new Redis-backed event consumer.
func NewRedisEventConsumer(client *redis.Client, opts ...SubscriptionOptions) *RedisEventConsumer {
	options := DefaultSubscriptionOptions()
	if len(opts) > 0 {
		options = opts[0]
	}

	return &RedisEventConsumer{
		client:  client,
		options: options,
	}
}

// Subscribe starts consuming events from a stream using a consumer group.
func (c *RedisEventConsumer) Subscribe(
	ctx context.Context,
	streamKey, group, consumer string,
	handler EventHandler,
) error {
	// Create consumer group if it doesn't exist
	err := c.client.XGroupCreateMkStream(ctx, streamKey, group, "0").Err()
	if err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
		return fmt.Errorf("create consumer group: %w", err)
	}

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			if err := c.processMessages(ctx, streamKey, group, consumer, handler); err != nil {
				// Log error but continue processing
				// In production, add proper error handling/metrics here
				time.Sleep(time.Second) // Backoff on error
			}
		}
	}
}

func (c *RedisEventConsumer) processMessages(
	ctx context.Context,
	streamKey, group, consumer string,
	handler EventHandler,
) error {
	entries, err := c.client.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    group,
		Consumer: consumer,
		Streams:  []string{streamKey, c.options.StartPosition},
		Count:    c.options.BatchSize,
		Block:    time.Duration(c.options.BlockTimeout) * time.Millisecond,
	}).Result()

	if err != nil {
		if err == redis.Nil {
			return nil // No new messages
		}
		return fmt.Errorf("xreadgroup: %w", err)
	}

	for _, stream := range entries {
		for _, msg := range stream.Messages {
			event, err := parseRedisMessage(msg)
			if err != nil {
				// Send to DLQ instead of blocking the stream
				continue
			}

			if err := handler(ctx, *event, msg.ID); err != nil {
				// Handler failed - don't acknowledge
				continue
			}

			if c.options.AutoAcknowledge {
				if err := c.Acknowledge(ctx, streamKey, group, msg.ID); err != nil {
					// Log error but continue
					continue
				}
			}
		}
	}

	return nil
}

// Acknowledge marks a message as processed.
func (c *RedisEventConsumer) Acknowledge(ctx context.Context, streamKey, group, messageID string) error {
	_, err := c.client.XAck(ctx, streamKey, group, messageID).Result()
	if err != nil {
		return fmt.Errorf("xack: %w", err)
	}
	return nil
}

// GetPendingCount returns the number of pending messages in a consumer group.
func (c *RedisEventConsumer) GetPendingCount(ctx context.Context, streamKey, group string) (int64, error) {
	info, err := c.client.XPending(ctx, streamKey, group).Result()
	if err != nil {
		return 0, fmt.Errorf("xpending: %w", err)
	}
	return info.Count, nil
}

// Close releases resources (no-op for shared Redis client).
func (c *RedisEventConsumer) Close() error {
	return nil
}

// parseRedisMessage converts a Redis Stream message to a DomainEvent.
func parseRedisMessage(msg redis.XMessage) (*DomainEvent, error) {
	var event DomainEvent

	// Extract required fields
	id, ok := msg.Values["id"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid event id")
	}
	event.ID = id

	eventType, ok := msg.Values["type"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid event type")
	}
	event.Type = EventType(eventType)

	aggregateType, ok := msg.Values["aggregate_type"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid aggregate type")
	}
	event.AggregateType = AggregateType(aggregateType)

	aggregateID, ok := msg.Values["aggregate_id"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid aggregate id")
	}
	parsedUUID, err := parseUUID(aggregateID)
	if err != nil {
		return nil, fmt.Errorf("invalid aggregate id: %w", err)
	}
	event.AggregateID = parsedUUID

	timestamp, ok := msg.Values["timestamp"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid timestamp")
	}
	parsedTime, err := time.Parse(time.RFC3339Nano, timestamp)
	if err != nil {
		return nil, fmt.Errorf("invalid timestamp: %w", err)
	}
	event.Timestamp = parsedTime

	// Parse version (optional, default to 1)
	if version, ok := msg.Values["version"].(string); ok {
		var v int
		fmt.Sscanf(version, "%d", &v)
		event.Version = v
	} else {
		event.Version = 1
	}

	// Parse payload
	if payload, ok := msg.Values["payload"].(string); ok {
		if err := json.Unmarshal([]byte(payload), &event.Payload); err != nil {
			return nil, fmt.Errorf("invalid payload json: %w", err)
		}
	}

	// Parse metadata (optional)
	if metadata, ok := msg.Values["metadata"].(string); ok && metadata != "" {
		if err := json.Unmarshal([]byte(metadata), &event.Metadata); err != nil {
			// Non-fatal: metadata is optional
			event.Metadata = EventMetadata{}
		}
	}

	return &event, nil
}

// parseUUID parses a UUID string, handling the google/uuid library format.
func parseUUID(s string) (uuid.UUID, error) {
	return uuid.Parse(s)
}
