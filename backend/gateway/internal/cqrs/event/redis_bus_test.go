package event

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
)

func TestRedisEventBus_Integration(t *testing.T) {
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		// Based on .env: redis://:devpassword@localhost:6379/0
		redisURL = "redis://:devpassword@127.0.0.1:6379/0"
	}

	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		t.Logf("Failed to parse URL: %v", err)
		t.Skip("Redis not available")
	}

	client := redis.NewClient(opt)
	defer client.Close()

	if err := client.Ping(context.Background()).Err(); err != nil {
		t.Logf("Failed to ping Redis with URL %s: %v", redisURL, err)
		t.Skip("Redis not reachable")
	}

	bus := NewRedisEventBus(client)
	consumer := NewRedisEventConsumer(client)

	streamKey := "cqrs:stream:test_bus"
	group := "test_group"
	consumerName := "test_consumer"

	// Ensure clean state
	client.Del(context.Background(), streamKey)

	payload := map[string]interface{}{"key": "value"}
	aggregateID := uuid.New()
	event := DomainEvent{
		ID:            uuid.New().String(),
		Type:          EventType("test.event"),
		AggregateType: AggregateType("TestAggregate"),
		AggregateID:   aggregateID,
		Timestamp:     time.Now().UTC(),
		Payload:       payload,
	}

	// Override stream key for testing
	// In production it uses EventType.StreamKey(), but for test isolation we might want to check if we can mock it
	// Since EventType is a string, we can't easily override its methods.
	// We'll use a real EventType that maps to a known stream.
	event.Type = EventTaskCreated
	realStreamKey := event.Type.StreamKey()
	client.Del(context.Background(), realStreamKey)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	received := make(chan DomainEvent, 1)
	handler := func(ctx context.Context, ev DomainEvent, msgID string) error {
		received <- ev
		return nil
	}

	// Start consumer in goroutine
	go func() {
		consumer.Subscribe(ctx, realStreamKey, group, consumerName, handler)
	}()

	// Wait a bit for consumer to be ready
	time.Sleep(500 * time.Millisecond)

	err = bus.Publish(context.Background(), event)
	assert.NoError(t, err)

	select {
	case ev := <-received:
		assert.Equal(t, event.ID, ev.ID)
		assert.Equal(t, event.Payload["key"], ev.Payload["key"])
	case <-time.After(2 * time.Second):
		t.Fatal("Timed out waiting for event")
	}
}
