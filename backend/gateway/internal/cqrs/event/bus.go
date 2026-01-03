// Package event provides the event bus interface and implementations for CQRS.
package event

import (
	"context"
)

// EventBus defines the interface for publishing domain events.
type EventBus interface {
	// Publish publishes a single event to the appropriate stream.
	Publish(ctx context.Context, event DomainEvent) error

	// PublishBatch publishes multiple events atomically (when possible).
	PublishBatch(ctx context.Context, events []DomainEvent) error

	// Close releases any resources held by the event bus.
	Close() error
}

// EventConsumer defines the interface for consuming events from a stream.
type EventConsumer interface {
	// Subscribe starts consuming events from a stream.
	// The handler is called for each event. If the handler returns an error,
	// the event may be retried based on the retry policy.
	Subscribe(ctx context.Context, streamKey, group, consumer string, handler EventHandler) error

	// Acknowledge marks an event as successfully processed.
	Acknowledge(ctx context.Context, streamKey, group, messageID string) error

	// GetPendingCount returns the number of pending messages in a consumer group.
	GetPendingCount(ctx context.Context, streamKey, group string) (int64, error)

	// Close releases any resources held by the consumer.
	Close() error
}

// EventHandler processes a single domain event.
// The messageID is the Redis Stream message ID, used for acknowledgment.
type EventHandler func(ctx context.Context, event DomainEvent, messageID string) error

// StreamPosition represents a position in an event stream.
type StreamPosition struct {
	StreamKey string
	MessageID string
}

// String returns a string representation of the stream position.
func (p StreamPosition) String() string {
	return p.StreamKey + ":" + p.MessageID
}

// SubscriptionOptions configures event subscription behavior.
type SubscriptionOptions struct {
	// BatchSize is the maximum number of events to fetch per read.
	BatchSize int64

	// BlockTimeout is how long to wait for new events (in milliseconds).
	// 0 means non-blocking, -1 means block indefinitely.
	BlockTimeout int64

	// StartPosition is where to start reading from.
	// Use "0" for the beginning, ">" for new messages only, or a specific message ID.
	StartPosition string

	// AutoAcknowledge automatically acknowledges events after the handler returns nil.
	AutoAcknowledge bool
}

// DefaultSubscriptionOptions returns sensible defaults for subscription options.
func DefaultSubscriptionOptions() SubscriptionOptions {
	return SubscriptionOptions{
		BatchSize:       10,
		BlockTimeout:    2000, // 2 seconds
		StartPosition:   ">",  // New messages only
		AutoAcknowledge: true,
	}
}

// PublishResult contains the result of publishing an event.
type PublishResult struct {
	MessageID string
	StreamKey string
	Error     error
}

// BatchPublishResult contains results for batch publishing.
type BatchPublishResult struct {
	Succeeded []PublishResult
	Failed    []PublishResult
}

// HasErrors returns true if any events failed to publish.
func (r BatchPublishResult) HasErrors() bool {
	return len(r.Failed) > 0
}
