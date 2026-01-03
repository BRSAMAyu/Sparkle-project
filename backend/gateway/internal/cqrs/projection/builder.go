package projection

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
	"github.com/sparkle/gateway/internal/db"
	"go.uber.org/zap"
)

// RebuildOptions configures projection rebuilding.
type RebuildOptions struct {
	// BatchSize is the number of events to process in each batch.
	BatchSize int
	// FromSequence is the sequence number to start from (0 for beginning).
	FromSequence int64
	// ProgressCallback is called after each batch with progress info.
	ProgressCallback func(processed, total int64)
}

// DefaultRebuildOptions returns default rebuild options.
func DefaultRebuildOptions() RebuildOptions {
	return RebuildOptions{
		BatchSize:    1000,
		FromSequence: 0,
	}
}

// Builder handles projection rebuilding from the event store.
type Builder struct {
	pool            *pgxpool.Pool
	queries         *db.Queries
	manager         *Manager
	snapshotManager *SnapshotManager
	metrics         *metrics.CQRSMetrics
	logger          *zap.Logger
}

// NewBuilder creates a new projection builder.
func NewBuilder(
	pool *pgxpool.Pool,
	manager *Manager,
	snapshotManager *SnapshotManager,
	cqrsMetrics *metrics.CQRSMetrics,
	logger *zap.Logger,
) *Builder {
	return &Builder{
		pool:            pool,
		queries:         db.New(pool),
		manager:         manager,
		snapshotManager: snapshotManager,
		metrics:         cqrsMetrics,
		logger:          logger.Named("projection-builder"),
	}
}

// RebuildProgress contains progress information for a rebuild.
type RebuildProgress struct {
	ProjectionName string        `json:"projection_name"`
	Status         string        `json:"status"`
	TotalEvents    int64         `json:"total_events"`
	ProcessedEvents int64        `json:"processed_events"`
	PercentComplete float64      `json:"percent_complete"`
	Duration        time.Duration `json:"duration"`
	StartedAt       time.Time    `json:"started_at"`
}

// RebuildFromEventStore rebuilds a projection from the event store.
func (b *Builder) RebuildFromEventStore(
	ctx context.Context,
	projectionName string,
	aggregateType event.AggregateType,
	opts RebuildOptions,
) (*RebuildProgress, error) {
	handler, ok := b.manager.GetHandler(projectionName)
	if !ok {
		return nil, fmt.Errorf("projection handler not found: %s", projectionName)
	}

	startTime := time.Now()

	// Set status to building
	if err := b.manager.SetStatus(ctx, projectionName, StatusBuilding, ""); err != nil {
		return nil, fmt.Errorf("failed to set building status: %w", err)
	}

	// Get total event count
	totalEvents, err := b.queries.GetEventStoreCount(ctx, string(aggregateType))
	if err != nil {
		_ = b.manager.SetStatus(ctx, projectionName, StatusError, err.Error())
		return nil, fmt.Errorf("failed to get event count: %w", err)
	}

	b.logger.Info("Starting projection rebuild",
		zap.String("projection", projectionName),
		zap.String("aggregate_type", string(aggregateType)),
		zap.Int64("total_events", totalEvents),
	)

	// Reset projection state
	if err := handler.Reset(ctx); err != nil {
		_ = b.manager.SetStatus(ctx, projectionName, StatusError, err.Error())
		return nil, fmt.Errorf("failed to reset projection: %w", err)
	}

	// Process events in batches
	var processedCount int64
	lastSequence := opts.FromSequence

	for {
		// Check for context cancellation
		select {
		case <-ctx.Done():
			_ = b.manager.SetStatus(ctx, projectionName, StatusPaused, "rebuild cancelled")
			return nil, ctx.Err()
		default:
		}

		// Fetch batch of events
		events, err := b.getEventBatch(ctx, aggregateType, lastSequence, int32(opts.BatchSize))
		if err != nil {
			_ = b.manager.SetStatus(ctx, projectionName, StatusError, err.Error())
			return nil, fmt.Errorf("failed to fetch events: %w", err)
		}

		if len(events) == 0 {
			break // No more events
		}

		// Process batch
		for _, evt := range events {
			eventData, err := json.Marshal(evt)
			if err != nil {
				eventID, _ := uuid.FromBytes(evt.ID.Bytes[:])
				b.logger.Error("Failed to marshal event",
					zap.Error(err),
					zap.String("event_id", eventID.String()),
				)
				continue
			}

			if err := handler.HandleEvent(ctx, eventData); err != nil {
				eventID, _ := uuid.FromBytes(evt.ID.Bytes[:])
				b.logger.Error("Failed to handle event during rebuild",
					zap.Error(err),
					zap.String("event_id", eventID.String()),
				)
				// Continue processing other events
			}

			processedCount++
			lastSequence = evt.SequenceNumber
		}

		// Update progress
		if opts.ProgressCallback != nil {
			opts.ProgressCallback(processedCount, totalEvents)
		}

		// Update position
		if err := b.manager.UpdatePosition(ctx, projectionName, fmt.Sprintf("%d", lastSequence)); err != nil {
			b.logger.Warn("Failed to update position", zap.Error(err))
		}

		b.logger.Debug("Processed batch",
			zap.Int64("processed", processedCount),
			zap.Int64("total", totalEvents),
		)
	}

	// Set status back to active
	if err := b.manager.SetStatus(ctx, projectionName, StatusActive, ""); err != nil {
		return nil, fmt.Errorf("failed to set active status: %w", err)
	}

	duration := time.Since(startTime)

	progress := &RebuildProgress{
		ProjectionName:  projectionName,
		Status:          "completed",
		TotalEvents:     totalEvents,
		ProcessedEvents: processedCount,
		PercentComplete: 100.0,
		Duration:        duration,
		StartedAt:       startTime,
	}

	b.logger.Info("Projection rebuild completed",
		zap.String("projection", projectionName),
		zap.Int64("processed", processedCount),
		zap.Duration("duration", duration),
	)

	return progress, nil
}

// RebuildFromSnapshot rebuilds a projection starting from a snapshot.
func (b *Builder) RebuildFromSnapshot(
	ctx context.Context,
	projectionName string,
	aggregateType event.AggregateType,
	opts RebuildOptions,
) (*RebuildProgress, error) {
	// Try to get latest snapshot
	snapshot, err := b.snapshotManager.GetLatestSnapshot(ctx, projectionName, nil)
	if err != nil {
		b.logger.Info("No snapshot found, rebuilding from beginning",
			zap.String("projection", projectionName),
		)
		return b.RebuildFromEventStore(ctx, projectionName, aggregateType, opts)
	}

	b.logger.Info("Found snapshot, rebuilding from position",
		zap.String("projection", projectionName),
		zap.String("position", snapshot.StreamPosition),
	)

	// Parse stream position to sequence number
	var fromSequence int64
	_, _ = fmt.Sscanf(snapshot.StreamPosition, "%d", &fromSequence)

	opts.FromSequence = fromSequence
	return b.RebuildFromEventStore(ctx, projectionName, aggregateType, opts)
}

// getEventBatch fetches a batch of events from the event store.
func (b *Builder) getEventBatch(
	ctx context.Context,
	aggregateType event.AggregateType,
	afterSequence int64,
	limit int32,
) ([]db.EventStore, error) {
	// We need a custom query for this
	rows, err := b.pool.Query(ctx, `
		SELECT id, aggregate_type, aggregate_id, event_type, event_version,
		       sequence_number, payload, metadata, created_at
		FROM event_store
		WHERE aggregate_type = $1 AND sequence_number > $2
		ORDER BY sequence_number ASC
		LIMIT $3
	`, string(aggregateType), afterSequence, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var events []db.EventStore
	for rows.Next() {
		var evt db.EventStore
		if err := rows.Scan(
			&evt.ID,
			&evt.AggregateType,
			&evt.AggregateID,
			&evt.EventType,
			&evt.EventVersion,
			&evt.SequenceNumber,
			&evt.Payload,
			&evt.Metadata,
			&evt.CreatedAt,
		); err != nil {
			return nil, err
		}
		events = append(events, evt)
	}

	return events, rows.Err()
}

// CreateSnapshot creates a snapshot for a projection.
func (b *Builder) CreateSnapshot(
	ctx context.Context,
	projectionName string,
	data map[string]interface{},
) error {
	// Get current position
	info, err := b.manager.GetProjectionInfo(ctx, projectionName)
	if err != nil {
		return fmt.Errorf("failed to get projection info: %w", err)
	}

	if err := b.snapshotManager.SaveSnapshot(ctx, projectionName, nil, data, info.LastProcessedPosition); err != nil {
		return fmt.Errorf("failed to save snapshot: %w", err)
	}

	b.logger.Info("Snapshot created",
		zap.String("projection", projectionName),
		zap.String("position", info.LastProcessedPosition),
	)

	return nil
}
