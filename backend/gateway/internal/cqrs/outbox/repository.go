// Package outbox provides the Outbox pattern implementation for reliable event publishing.
package outbox

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/db"
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
	pool    *pgxpool.Pool
	queries *db.Queries
}

// NewPostgresRepository creates a new PostgreSQL-backed outbox repository.
func NewPostgresRepository(pool *pgxpool.Pool) *PostgresRepository {
	return &PostgresRepository{
		pool:    pool,
		queries: db.New(pool),
	}
}

// InsertWithTx inserts an outbox entry within an existing transaction.
func (r *PostgresRepository) InsertWithTx(ctx context.Context, tx pgx.Tx, entry *event.OutboxEntry) error {
	params := db.InsertOutboxEntryParams{
		ID:            toPgUUID(entry.ID),
		AggregateType: string(entry.AggregateType),
		AggregateID:   toPgUUID(entry.AggregateID),
		EventType:     string(entry.EventType),
		EventVersion:  int32(entry.EventVersion),
		Payload:       entry.Payload,
		Metadata:      entry.Metadata,
		CreatedAt: pgtype.Timestamp{
			Time:  entry.CreatedAt,
			Valid: true,
		},
	}

	err := r.queries.WithTx(tx).InsertOutboxEntry(ctx, params)
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
	rows, err := r.queries.GetUnpublishedOutboxEntries(ctx, int32(limit))
	if err != nil {
		return nil, fmt.Errorf("query unpublished: %w", err)
	}

	entries := make([]*event.OutboxEntry, len(rows))
	for i, row := range rows {
		entries[i] = &event.OutboxEntry{
			ID:             fromPgUUID(row.ID),
			AggregateType:  event.AggregateType(row.AggregateType),
			AggregateID:    fromPgUUID(row.AggregateID),
			EventType:      event.EventType(row.EventType),
			EventVersion:   int(row.EventVersion),
			Payload:        row.Payload,
			Metadata:       row.Metadata,
			SequenceNumber: row.SequenceNumber,
			CreatedAt:      row.CreatedAt.Time,
		}
		if row.PublishedAt.Valid {
			entries[i].PublishedAt = &row.PublishedAt.Time
		}
	}

	return entries, nil
}

// MarkPublished marks entries as published.
func (r *PostgresRepository) MarkPublished(ctx context.Context, ids []uuid.UUID) error {
	if len(ids) == 0 {
		return nil
	}

	pgIDs := make([]pgtype.UUID, len(ids))
	for i, id := range ids {
		pgIDs[i] = toPgUUID(id)
	}

	err := r.queries.MarkOutboxEntriesPublished(ctx, pgIDs)
	if err != nil {
		return fmt.Errorf("mark published: %w", err)
	}

	return nil
}

// DeleteOld removes published entries older than the retention period.
func (r *PostgresRepository) DeleteOld(ctx context.Context, retentionDays int) (int64, error) {
	count, err := r.queries.DeleteOldOutboxEntries(ctx, int32(retentionDays))
	if err != nil {
		return 0, fmt.Errorf("delete old: %w", err)
	}

	return count, nil
}

// GetPendingCount returns the count of unpublished entries.
func (r *PostgresRepository) GetPendingCount(ctx context.Context) (int64, error) {
	count, err := r.queries.GetOutboxPendingCount(ctx)
	if err != nil {
		return 0, fmt.Errorf("count pending: %w", err)
	}

	return count, nil
}

// EventStoreRepository handles event store operations.
type EventStoreRepository struct {
	pool    *pgxpool.Pool
	queries *db.Queries
}

// NewEventStoreRepository creates a new event store repository.
func NewEventStoreRepository(pool *pgxpool.Pool) *EventStoreRepository {
	return &EventStoreRepository{
		pool:    pool,
		queries: db.New(pool),
	}
}

// SaveWithTx saves an event to the event store within an existing transaction.
func (r *EventStoreRepository) SaveWithTx(ctx context.Context, tx pgx.Tx, entry *event.EventStoreEntry) error {
	params := db.InsertEventStoreEntryParams{
		ID:             toPgUUID(entry.ID),
		AggregateType:  string(entry.AggregateType),
		AggregateID:    toPgUUID(entry.AggregateID),
		EventType:      string(entry.EventType),
		EventVersion:   int32(entry.EventVersion),
		SequenceNumber: entry.SequenceNumber,
		Payload:        entry.Payload,
		Metadata:       entry.Metadata,
		CreatedAt: pgtype.Timestamp{
			Time:  entry.CreatedAt,
			Valid: true,
		},
	}

	err := r.queries.WithTx(tx).InsertEventStoreEntry(ctx, params)
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
	params := db.GetEventsByAggregateParams{
		AggregateType: string(aggregateType),
		AggregateID:   toPgUUID(aggregateID),
	}

	rows, err := r.queries.GetEventsByAggregate(ctx, params)
	if err != nil {
		return nil, fmt.Errorf("query events: %w", err)
	}

	return r.mapEventStoreEntries(rows), nil
}

// GetAfterSequence retrieves events after a specific sequence number.
func (r *EventStoreRepository) GetAfterSequence(
	ctx context.Context,
	aggregateType event.AggregateType,
	aggregateID uuid.UUID,
	afterSequence int64,
) ([]*event.EventStoreEntry, error) {
	params := db.GetEventsAfterSequenceParams{
		AggregateType:  string(aggregateType),
		AggregateID:    toPgUUID(aggregateID),
		SequenceNumber: afterSequence,
	}

	rows, err := r.queries.GetEventsAfterSequence(ctx, params)
	if err != nil {
		return nil, fmt.Errorf("query events: %w", err)
	}

	return r.mapEventStoreEntries(rows), nil
}

// GetNextSequenceNumber returns the next sequence number for an aggregate.
func (r *EventStoreRepository) GetNextSequenceNumber(
	ctx context.Context,
	aggregateType event.AggregateType,
	aggregateID uuid.UUID,
) (int64, error) {
	params := db.GetNextSequenceNumberParams{
		AggregateType: string(aggregateType),
		AggregateID:   toPgUUID(aggregateID),
	}

	nextSeq, err := r.queries.GetNextSequenceNumber(ctx, params)
	if err != nil {
		return 0, fmt.Errorf("get next sequence: %w", err)
	}

	return int64(nextSeq), nil
}

func (r *EventStoreRepository) mapEventStoreEntries(rows []db.EventStore) []*event.EventStoreEntry {
	entries := make([]*event.EventStoreEntry, len(rows))
	for i, row := range rows {
		entries[i] = &event.EventStoreEntry{
			ID:             fromPgUUID(row.ID),
			AggregateType:  event.AggregateType(row.AggregateType),
			AggregateID:    fromPgUUID(row.AggregateID),
			EventType:      event.EventType(row.EventType),
			EventVersion:   int(row.EventVersion),
			SequenceNumber: row.SequenceNumber,
			Payload:        row.Payload,
			Metadata:       row.Metadata,
			CreatedAt:      row.CreatedAt.Time,
		}
	}
	return entries
}

// ProcessedEventsRepository handles idempotency tracking.
type ProcessedEventsRepository struct {
	pool    *pgxpool.Pool
	queries *db.Queries
}

// NewProcessedEventsRepository creates a new processed events repository.
func NewProcessedEventsRepository(pool *pgxpool.Pool) *ProcessedEventsRepository {
	return &ProcessedEventsRepository{
		pool:    pool,
		queries: db.New(pool),
	}
}

// IsProcessed checks if an event has already been processed by a consumer group.
func (r *ProcessedEventsRepository) IsProcessed(ctx context.Context, eventID, consumerGroup string) (bool, error) {
	params := db.IsEventProcessedParams{
		EventID:       eventID,
		ConsumerGroup: consumerGroup,
	}
	exists, err := r.queries.IsEventProcessed(ctx, params)
	if err != nil {
		return false, fmt.Errorf("check processed: %w", err)
	}

	return exists, nil
}

// MarkProcessed marks an event as processed by a consumer group.
func (r *ProcessedEventsRepository) MarkProcessed(ctx context.Context, eventID, consumerGroup string) error {
	params := db.MarkEventProcessedParams{
		EventID:       eventID,
		ConsumerGroup: consumerGroup,
	}
	err := r.queries.MarkEventProcessed(ctx, params)
	if err != nil {
		return fmt.Errorf("mark processed: %w", err)
	}

	return nil
}

// Cleanup removes old processed event records.
func (r *ProcessedEventsRepository) Cleanup(ctx context.Context, retentionDays int) (int64, error) {
	count, err := r.queries.CleanupOldProcessedEvents(ctx, int32(retentionDays))
	if err != nil {
		return 0, fmt.Errorf("cleanup: %w", err)
	}

	return count, nil
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
			queries:        db.New(tx),
			outboxRepo:     u.outboxRepo,
			eventStoreRepo: u.eventStoreRepo,
		}
		return fn(txCtx)
	})
}

// TransactionContext provides access to repositories within a transaction.
type TransactionContext struct {
	tx             pgx.Tx
	queries        *db.Queries
	outboxRepo     *PostgresRepository
	eventStoreRepo *EventStoreRepository
}

// Tx returns the underlying transaction.
func (c *TransactionContext) Tx() pgx.Tx {
	return c.tx
}

// Queries returns the transaction-bound queries.
func (c *TransactionContext) Queries() *db.Queries {
	return c.queries
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
// Deprecated: Use Queries() and sqlc generated methods instead.
func (c *TransactionContext) Exec(ctx context.Context, sql string, args ...interface{}) error {
	_, err := c.tx.Exec(ctx, sql, args...)
	return err
}

// QueryRow executes a query that returns a single row within the transaction.
// Deprecated: Use Queries() and sqlc generated methods instead.
func (c *TransactionContext) QueryRow(ctx context.Context, sql string, args ...interface{}) pgx.Row {
	return c.tx.QueryRow(ctx, sql, args...)
}

func toPgUUID(id uuid.UUID) pgtype.UUID {
	return pgtype.UUID{Bytes: id, Valid: true}
}

func fromPgUUID(id pgtype.UUID) uuid.UUID {
	return uuid.UUID(id.Bytes)
}