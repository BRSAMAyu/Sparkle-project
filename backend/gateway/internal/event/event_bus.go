package event

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

const (
	StreamKey = "community_events"
)

type EventType string

const (
	EventPostCreated EventType = "post_created"
	EventPostLiked   EventType = "post_liked"
)

type DomainEvent struct {
	ID        string      `json:"id"`
	Type      EventType   `json:"type"`
	Timestamp time.Time   `json:"timestamp"`
	Payload   interface{} `json:"payload"`
}

type EventBus interface {
	Publish(ctx context.Context, event DomainEvent) error
}

type RedisEventBus struct {
	client *redis.Client
}

func NewRedisEventBus(client *redis.Client) *RedisEventBus {
	return &RedisEventBus{client: client}
}

func (b *RedisEventBus) Publish(ctx context.Context, event DomainEvent) error {
	payloadBytes, err := json.Marshal(event.Payload)
	if err != nil {
		return fmt.Errorf("failed to marshal event payload: %w", err)
	}

	// Use XADD to add to stream
	return b.client.XAdd(ctx, &redis.XAddArgs{
		Stream: StreamKey,
		Values: map[string]interface{}{
			"type":      string(event.Type),
			"payload":   string(payloadBytes),
			"timestamp": event.Timestamp.Format(time.RFC3339),
		},
	}).Err()
}
