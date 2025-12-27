// Package outbox provides the Outbox pattern implementation for reliable event publishing.
package outbox

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sparkle/gateway/internal/cqrs/event"
)

// Repository handles outbox table operations.
type Repository interface {
	// InsertWithTx inserts an outbox entry within an existing transaction.
	// This ensures the event is stored atomically with the business data.
	InsertWithTx(ctx context.Context, tx pgx.Tx, entry *event.OutboxEntry) error

	// Insert inserts an outbox entry (creates its own transaction).
	Insert(ctx context.Context, entry *event.OutboxEntry) error

	// GetUnpublished retrieves unpublished entries ordered by creation time.
	GetUnpublished(ctx context.Context, limit int) ([]*event.OutboxEntry, error)

	// MarkPublished marks entries as published.
	MarkPublished(ctx context.Context, ids []uuid.UUID) error

	// DeleteOld removes published entries older than the retention period.
	DeleteOld(ctx context.Context, retentionDays int) (int64, error)

	// GetPendingCount returns the count of unpublished entries.
	GetPendingCount(ctx context.Context) (int64, error)
}

// PostgresRepository implements Repository using PostgreSQL.
type PostgresRepository struct {
	pool *pgxpool.Pool
}

// NewPostgresRepository creates a new PostgreSQL-backed outbox repository.
func NewPostgresRepository(pool *pgxpool.Pool) *PostgresRepository {
	return &PostgresRepository{pool: pool}
}

// InsertWithTx inserts an outbox entry within an existing transaction.
func (r *PostgresRepository) InsertWithTx(ctx context.Context, tx pgx.Tx, entry *event.OutboxEntry) error {
	query := `
		INSERT INTO event_outbox (
			id, aggregate_type, aggregate_id, event_type,
			event_version, payload, metadata, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`

	_, err := tx.Exec(ctx, query,
		entry.ID,
		string(entry.AggregateType),
		entry.AggregateID,
		string(entry.EventType),
		entry.EventVersion,
		entry.Payload,
		entry.Metadata,
		entry.CreatedAt,
	)

	if err != nil {
		return fmt.Errorf("insert outbox entry: %w", err)
	}

	return nil
}

// Insert inserts an outbox entry with its own transaction.
func (r *PostgresRepository) Insert(ctx context.Context, entry *event.OutboxEntry) error {
	return pgx.BeginFunc(ctx, r.pool, func(tx pgx.Tx) error {
		return r.InsertWithTx(ctx, tx, entry)
	})
}

// GetUnpublished retrieves unpublished entries ordered by creation time.
func (r *PostgresRepository) GetUnpublished(ctx context.Context, limit int) ([]*event.OutboxEntry, error) {
	query := `
		SELECT id, aggregate_type, aggregate_id, event_type,
		       event_version, payload, metadata, sequence_number,
		       created_at, published_at
		FROM event_outbox
		WHERE published_at IS NULL
		ORDER BY created_at ASC
		LIMIT $1
		FOR UPDATE SKIP LOCKED
	`

	rows, err := r.pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("query unpublished: %w", err)
	}
	defer rows.Close()

	var entries []*event.OutboxEntry
	for rows.Next() {
		entry := &event.OutboxEntry{}
		var aggregateType, eventType string
		var metadata []byte

		err := rows.Scan(
			&entry.ID,
			&aggregateType,
			&entry.AggregateID,
			&eventType,
			&entry.EventVersion,
			&entry.Payload,
			&metadata,
			&entry.SequenceNumber,
			&entry.CreatedAt,
			&entry.PublishedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("scan row: %w", err)
		}

		entry.AggregateType = event.AggregateType(aggregateType)
		entry.EventType = event.EventType(eventType)
		entry.Metadata = metadata

		entries = append(entries, entry)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows error: %w", err)
	}

	return entries, nil
}

// MarkPublished marks entries as published.
func (r *PostgresRepository) MarkPublished(ctx context.Context, ids []uuid.UUID) error {
	if len(ids) == 0 {
		return nil
	}

	query := `
		UPDATE event_outbox
		SET published_at = NOW()
		WHERE id = ANY($1)
	`

	_, err := r.pool.Exec(ctx, query, ids)
	if err != nil {
		return fmt.Errorf("mark published: %w", err)
	}

	return nil
}

// DeleteOld removes published entries older than the retention period.
func (r *PostgresRepository) DeleteOld(ctx context.Context, retentionDays int) (int64, error) {
	query := `
		DELETE FROM event_outbox
		WHERE published_at IS NOT NULL
		  AND published_at < NOW() - INTERVAL '1 day' * $1
	`

	result, err := r.pool.Exec(ctx, query, retentionDays)
	if err != nil {
		return 0, fmt.Errorf("delete old: %w", err)
	}

	return result.RowsAffected(), nil
}

// GetPendingCount returns the count of unpublished entries.
func (r *PostgresRepository) GetPendingCount(ctx context.Context) (int64, error) {
	query := `SELECT COUNT(*) FROM event_outbox WHERE published_at IS NULL`

	var count int64
	err := r.pool.QueryRow(ctx, query).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("count pending: %w", err)
	}

	return count, nil
}

// EventStoreRepository handles event store operations.
type EventStoreRepository struct {
	pool *pgxpool.Pool
}

// NewEventStoreRepository creates a new event store repository.
func NewEventStoreRepository(pool *pgxpool.Pool) *EventStoreRepository {
	return &EventStoreRepository{pool: pool}
}

// SaveWithTx saves an event to the event store within an existing transaction.
func (r *EventStoreRepository) SaveWithTx(ctx context.Context, tx pgx.Tx, entry *event.EventStoreEntry) error {
	query := `
		INSERT INTO event_store (
			id, aggregate_type, aggregate_id, event_type,
			event_version, sequence_number, payload, metadata, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
	`

	_, err := tx.Exec(ctx, query,
		entry.ID,
		string(entry.AggregateType),
		entry.AggregateID,
		string(entry.EventType),
		entry.EventVersion,
		entry.SequenceNumber,
		entry.Payload,
		entry.Metadata,
		entry.CreatedAt,
	)

	if err != nil {
		return fmt.Errorf("save event: %w", err)
	}

	return nil
}

// GetByAggregate retrieves all events for an aggregate.
func (r *EventStoreRepository) GetByAggregate(
	ctx context.Context,
	aggregateType event.AggregateType,
	aggregateID uuid.UUID,
) ([]*event.EventStoreEntry, error) {
	query := `
		SELECT id, aggregate_type, aggregate_id, event_type,
		       event_version, sequence_number, payload, metadata, created_at
		FROM event_store
		WHERE aggregate_type = $1 AND aggregate_id = $2
		ORDER BY sequence_number ASC
	`

	return r.queryEntries(ctx, query, string(aggregateType), aggregateID)
}

// GetAfterSequence retrieves events after a specific sequence number.
func (r *EventStoreRepository) GetAfterSequence(
	ctx context.Context,
	aggregateType event.AggregateType,
	aggregateID uuid.UUID,
	afterSequence int64,
) ([]*event.EventStoreEntry, error) {
	query := `
		SELECT id, aggregate_type, aggregate_id, event_type,
		       event_version, sequence_number, payload, metadata, created_at
		FROM event_store
		WHERE aggregate_type = $1 AND aggregate_id = $2 AND sequence_number > $3
		ORDER BY sequence_number ASC
	`

	return r.queryEntries(ctx, query, string(aggregateType), aggregateID, afterSequence)
}

// GetNextSequenceNumber returns the next sequence number for an aggregate.
func (r *EventStoreRepository) GetNextSequenceNumber(
	ctx context.Context,
	aggregateType event.AggregateType,
	aggregateID uuid.UUID,
) (int64, error) {
	query := `
		SELECT COALESCE(MAX(sequence_number), 0) + 1
		FROM event_store
		WHERE aggregate_type = $1 AND aggregate_id = $2
	`

	var nextSeq int64
	err := r.pool.QueryRow(ctx, query, string(aggregateType), aggregateID).Scan(&nextSeq)
	if err != nil {
		return 0, fmt.Errorf("get next sequence: %w", err)
	}

	return nextSeq, nil
}

func (r *EventStoreRepository) queryEntries(ctx context.Context, query string, args ...interface{}) ([]*event.EventStoreEntry, error) {
	rows, err := r.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("query events: %w", err)
	}
	defer rows.Close()

	var entries []*event.EventStoreEntry
	for rows.Next() {
		entry := &event.EventStoreEntry{}
		var aggregateType, eventType string

		err := rows.Scan(
			&entry.ID,
			&aggregateType,
			&entry.AggregateID,
			&eventType,
			&entry.EventVersion,
			&entry.SequenceNumber,
			&entry.Payload,
			&entry.Metadata,
			&entry.CreatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("scan row: %w", err)
		}

		entry.AggregateType = event.AggregateType(aggregateType)
		entry.EventType = event.EventType(eventType)

		entries = append(entries, entry)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows error: %w", err)
	}

	return entries, nil
}

// ProcessedEventsRepository handles idempotency tracking.
type ProcessedEventsRepository struct {
	pool *pgxpool.Pool
}

// NewProcessedEventsRepository creates a new processed events repository.
func NewProcessedEventsRepository(pool *pgxpool.Pool) *ProcessedEventsRepository {
	return &ProcessedEventsRepository{pool: pool}
}

// IsProcessed checks if an event has already been processed by a consumer group.
func (r *ProcessedEventsRepository) IsProcessed(ctx context.Context, eventID, consumerGroup string) (bool, error) {
	query := `SELECT EXISTS(SELECT 1 FROM processed_events WHERE event_id = $1 AND consumer_group = $2)`

	var exists bool
	err := r.pool.QueryRow(ctx, query, eventID, consumerGroup).Scan(&exists)
	if err != nil {
		return false, fmt.Errorf("check processed: %w", err)
	}

	return exists, nil
}

// MarkProcessed marks an event as processed by a consumer group.
func (r *ProcessedEventsRepository) MarkProcessed(ctx context.Context, eventID, consumerGroup string) error {
	query := `
		INSERT INTO processed_events (event_id, consumer_group, processed_at)
		VALUES ($1, $2, NOW())
		ON CONFLICT (event_id) DO NOTHING
	`

	_, err := r.pool.Exec(ctx, query, eventID, consumerGroup)
	if err != nil {
		return fmt.Errorf("mark processed: %w", err)
	}

	return nil
}

// Cleanup removes old processed event records.
func (r *ProcessedEventsRepository) Cleanup(ctx context.Context, retentionDays int) (int64, error) {
	query := `
		DELETE FROM processed_events
		WHERE processed_at < NOW() - INTERVAL '1 day' * $1
	`

	result, err := r.pool.Exec(ctx, query, retentionDays)
	if err != nil {
		return 0, fmt.Errorf("cleanup: %w", err)
	}

	return result.RowsAffected(), nil
}

// UnitOfWork provides transactional operations for CQRS.
type UnitOfWork struct {
	pool           *pgxpool.Pool
	outboxRepo     *PostgresRepository
	eventStoreRepo *EventStoreRepository
}

// NewUnitOfWork creates a new unit of work.
func NewUnitOfWork(pool *pgxpool.Pool) *UnitOfWork {
	return &UnitOfWork{
		pool:           pool,
		outboxRepo:     NewPostgresRepository(pool),
		eventStoreRepo: NewEventStoreRepository(pool),
	}
}

// ExecuteInTransaction executes a function within a transaction.
// The function receives a TransactionContext with repositories bound to the transaction.
func (u *UnitOfWork) ExecuteInTransaction(ctx context.Context, fn func(txCtx *TransactionContext) error) error {
	return pgx.BeginFunc(ctx, u.pool, func(tx pgx.Tx) error {
		txCtx := &TransactionContext{
			tx:             tx,
			outboxRepo:     u.outboxRepo,
			eventStoreRepo: u.eventStoreRepo,
		}
		return fn(txCtx)
	})
}

// TransactionContext provides access to repositories within a transaction.
type TransactionContext struct {
	tx             pgx.Tx
	outboxRepo     *PostgresRepository
	eventStoreRepo *EventStoreRepository
}

// Tx returns the underlying transaction.
func (c *TransactionContext) Tx() pgx.Tx {
	return c.tx
}

// SaveEventToOutbox saves an event to the outbox within the transaction.
func (c *TransactionContext) SaveEventToOutbox(ctx context.Context, domainEvent *event.DomainEvent) error {
	entry, err := domainEvent.ToOutboxEntry()
	if err != nil {
		return fmt.Errorf("convert to outbox entry: %w", err)
	}
	return c.outboxRepo.InsertWithTx(ctx, c.tx, entry)
}

// SaveEventToStore saves an event to the event store within the transaction.
func (c *TransactionContext) SaveEventToStore(ctx context.Context, domainEvent *event.DomainEvent, sequenceNumber int64) error {
	payload, err := json.Marshal(domainEvent.Payload)
	if err != nil {
		return fmt.Errorf("marshal payload: %w", err)
	}

	metadata, err := json.Marshal(domainEvent.Metadata)
	if err != nil {
		return fmt.Errorf("marshal metadata: %w", err)
	}

	entry := &event.EventStoreEntry{
		ID:             uuid.MustParse(domainEvent.ID),
		AggregateType:  domainEvent.AggregateType,
		AggregateID:    domainEvent.AggregateID,
		EventType:      domainEvent.Type,
		EventVersion:   domainEvent.Version,
		SequenceNumber: sequenceNumber,
		Payload:        payload,
		Metadata:       metadata,
		CreatedAt:      domainEvent.Timestamp,
	}

	return c.eventStoreRepo.SaveWithTx(ctx, c.tx, entry)
}

// SaveEventToBoth saves an event to both outbox and event store.
func (c *TransactionContext) SaveEventToBoth(ctx context.Context, domainEvent *event.DomainEvent, sequenceNumber int64) error {
	if err := c.SaveEventToOutbox(ctx, domainEvent); err != nil {
		return err
	}
	return c.SaveEventToStore(ctx, domainEvent, sequenceNumber)
}

// Exec executes a SQL statement within the transaction.
func (c *TransactionContext) Exec(ctx context.Context, sql string, args ...interface{}) error {
	_, err := c.tx.Exec(ctx, sql, args...)
	return err
}

// QueryRow executes a query that returns a single row within the transaction.
func (c *TransactionContext) QueryRow(ctx context.Context, sql string, args ...interface{}) pgx.Row {
	return c.tx.QueryRow(ctx, sql, args...)
}
