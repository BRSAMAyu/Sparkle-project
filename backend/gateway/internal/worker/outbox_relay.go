package worker

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/lib/pq"
	amqp "github.com/rabbitmq/amqp091-go"
	"go.uber.org/zap"
)

type OutboxEvent struct {
	ID          int64           `json:"id"`
	AggregateID string          `json:"aggregate_id"`
	EventType   string          `json:"event_type"`
	Payload     json.RawMessage `json:"payload"`
	Status      string          `json:"status"`
}

type OutboxRelay struct {
	db       *sql.DB
	rabbitMQ *amqp.Connection
	channel  *amqp.Channel
	logger   *zap.Logger
}

func NewOutboxRelay(db *sql.DB, rabbitMQURL string, logger *zap.Logger) (*OutboxRelay, error) {
	conn, err := amqp.Dial(rabbitMQURL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to RabbitMQ: %w", err)
	}

	ch, err := conn.Channel()
	if err != nil {
		return nil, fmt.Errorf("failed to open a channel: %w", err)
	}

	// Declare exchange to ensure it exists
	err = ch.ExchangeDeclare(
		"sparkle_events", // name
		"topic",          // type
		true,             // durable
		false,            // auto-deleted
		false,            // internal
		false,            // no-wait
		nil,              // arguments
	)
	if err != nil {
		return nil, fmt.Errorf("failed to declare exchange: %w", err)
	}

	return &OutboxRelay{
		db:       db,
		rabbitMQ: conn,
		channel:  ch,
		logger:   logger,
	}, nil
}

func (r *OutboxRelay) Start(ctx context.Context) {
	r.logger.Info("Starting Outbox Relay")
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			r.logger.Info("Stopping Outbox Relay")
			r.Close()
			return
		case <-ticker.C:
			if err := r.processEvents(ctx); err != nil {
				r.logger.Error("Failed to process outbox events", zap.Error(err))
			}
		}
	}
}

func (r *OutboxRelay) processEvents(ctx context.Context) error {
	// 1. Fetch pending events (using FOR UPDATE SKIP LOCKED for concurrency safety)
	// This ensures multiple relay instances don't process the same event
	query := `
		SELECT id, aggregate_id, event_type, payload
		FROM outbox_events
		WHERE status = 'pending'
		ORDER BY created_at ASC
		LIMIT 50
		FOR UPDATE SKIP LOCKED
	`

	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	rows, err := tx.QueryContext(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to query outbox events: %w", err)
	}
	defer rows.Close()

	var events []OutboxEvent
	for rows.Next() {
		var evt OutboxEvent
		if err := rows.Scan(&evt.ID, &evt.AggregateID, &evt.EventType, &evt.Payload); err != nil {
			return fmt.Errorf("failed to scan event: %w", err)
		}
		events = append(events, evt)
	}

	if len(events) == 0 {
		return nil
	}

	processedIDs := []int64{}

	for _, evt := range events {
		// 2. Publish to RabbitMQ
		err := r.channel.PublishWithContext(ctx,
			"sparkle_events", // exchange
			evt.EventType,    // routing key
			false,            // mandatory
			false,            // immediate
			amqp.Publishing{
				DeliveryMode: amqp.Persistent,
				ContentType:  "application/json",
				Body:         evt.Payload,
				Timestamp:    time.Now(),
				MessageId:    fmt.Sprintf("%d", evt.ID),
			},
		)

		if err != nil {
			r.logger.Error("Failed to publish event to RabbitMQ",
				zap.Int64("id", evt.ID),
				zap.String("type", evt.EventType),
				zap.Error(err),
			)
			// Continue with other events, this one remains pending
			// In a real system, we might want to increment a retry counter
			continue
		}

		processedIDs = append(processedIDs, evt.ID)
	}

	if len(processedIDs) > 0 {
		// 3. Mark as published
		// Use pq.Array for efficient bulk update
		updateQuery := `
			UPDATE outbox_events
			SET status = 'published', published_at = NOW()
			WHERE id = ANY($1)
		`
		_, err = tx.ExecContext(ctx, updateQuery, pq.Array(processedIDs))
		if err != nil {
			return fmt.Errorf("failed to update event status: %w", err)
		}
	}

	return tx.Commit()
}

func (r *OutboxRelay) Close() {
	if r.channel != nil {
		r.channel.Close()
	}
	if r.rabbitMQ != nil {
		r.rabbitMQ.Close()
	}
}
