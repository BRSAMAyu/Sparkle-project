// Package projection provides projection lifecycle management for CQRS.
package projection

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sparkle/gateway/internal/db"
	"go.uber.org/zap"
)

// ProjectionStatus represents the status of a projection.
type ProjectionStatus string

const (
	StatusActive   ProjectionStatus = "active"
	StatusPaused   ProjectionStatus = "paused"
	StatusError    ProjectionStatus = "error"
	StatusBuilding ProjectionStatus = "building"
)

// ProjectionInfo contains runtime information about a projection.
type ProjectionInfo struct {
	Name                  string           `json:"name"`
	Status                ProjectionStatus `json:"status"`
	LastProcessedPosition int64            `json:"last_processed_position,omitempty"`
	LastProcessedAt       *time.Time       `json:"last_processed_at,omitempty"`
	Version               int              `json:"version"`
	ErrorMessage          string           `json:"error_message,omitempty"`
	CreatedAt             time.Time        `json:"created_at"`
	UpdatedAt             time.Time        `json:"updated_at"`
}

// ProjectionHandler defines the interface for handling projection events.
type ProjectionHandler interface {
	// Name returns the projection name.
	Name() string
	// HandleEvent processes a single event.
	HandleEvent(ctx context.Context, eventData []byte) error
	// Reset clears the projection state.
	Reset(ctx context.Context) error
}

// Manager manages projection lifecycle and metadata.
type Manager struct {
	pool       *pgxpool.Pool
	queries    *db.Queries
	logger     *zap.Logger
	handlers   map[string]ProjectionHandler
	handlersMu sync.RWMutex
}

// NewManager creates a new projection manager.
func NewManager(pool *pgxpool.Pool, logger *zap.Logger) *Manager {
	return &Manager{
		pool:     pool,
		queries:  db.New(pool),
		logger:   logger.Named("projection-manager"),
		handlers: make(map[string]ProjectionHandler),
	}
}

// RegisterHandler registers a projection handler.
func (m *Manager) RegisterHandler(handler ProjectionHandler) error {
	m.handlersMu.Lock()
	defer m.handlersMu.Unlock()

	name := handler.Name()
	if _, exists := m.handlers[name]; exists {
		return fmt.Errorf("handler already registered: %s", name)
	}

	m.handlers[name] = handler

	// Ensure projection metadata exists
	ctx := context.Background()
	if err := m.queries.UpsertProjectionMetadata(ctx, name); err != nil {
		return fmt.Errorf("failed to upsert projection metadata: %w", err)
	}

	m.logger.Info("Projection handler registered", zap.String("name", name))
	return nil
}

// GetHandler returns a registered handler by name.
func (m *Manager) GetHandler(name string) (ProjectionHandler, bool) {
	m.handlersMu.RLock()
	defer m.handlersMu.RUnlock()
	handler, ok := m.handlers[name]
	return handler, ok
}

// GetProjectionInfo retrieves current projection metadata.
func (m *Manager) GetProjectionInfo(ctx context.Context, name string) (*ProjectionInfo, error) {
	meta, err := m.queries.GetProjectionMetadata(ctx, name)
	if err != nil {
		return nil, fmt.Errorf("failed to get projection metadata: %w", err)
	}

	info := &ProjectionInfo{
		Name:      meta.ProjectionName,
		Status:    ProjectionStatus(meta.Status),
		Version:   int(meta.Version),
		CreatedAt: meta.CreatedAt.Time,
		UpdatedAt: meta.UpdatedAt.Time,
	}

	if meta.LastProcessedPosition > 0 {
		info.LastProcessedPosition = meta.LastProcessedPosition
	}

	if meta.LastProcessedAt.Valid {
		info.LastProcessedAt = &meta.LastProcessedAt.Time
	}

	if meta.ErrorMessage.Valid {
		info.ErrorMessage = meta.ErrorMessage.String
	}

	return info, nil
}

// GetAllProjections retrieves all projection statuses.
func (m *Manager) GetAllProjections(ctx context.Context) ([]ProjectionInfo, error) {
	metas, err := m.queries.GetAllProjectionMetadata(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get all projection metadata: %w", err)
	}

	infos := make([]ProjectionInfo, 0, len(metas))
	for _, meta := range metas {
		info := ProjectionInfo{
			Name:      meta.ProjectionName,
			Status:    ProjectionStatus(meta.Status),
			Version:   int(meta.Version),
			CreatedAt: meta.CreatedAt.Time,
			UpdatedAt: meta.UpdatedAt.Time,
		}

		if meta.LastProcessedPosition > 0 {
			info.LastProcessedPosition = meta.LastProcessedPosition
		}

		if meta.LastProcessedAt.Valid {
			info.LastProcessedAt = &meta.LastProcessedAt.Time
		}

		if meta.ErrorMessage.Valid {
			info.ErrorMessage = meta.ErrorMessage.String
		}

		infos = append(infos, info)
	}

	return infos, nil
}

// UpdatePosition updates the last processed position for a projection.
func (m *Manager) UpdatePosition(ctx context.Context, name string, position int64) error {
	return m.queries.UpdateProjectionPosition(ctx, db.UpdateProjectionPositionParams{
		ProjectionName:        name,
		LastProcessedPosition: position,
	})
}

// SetStatus updates the status of a projection.
func (m *Manager) SetStatus(ctx context.Context, name string, status ProjectionStatus, errorMsg string) error {
	return m.queries.SetProjectionStatus(ctx, db.SetProjectionStatusParams{
		ProjectionName: name,
		Status:         string(status),
		ErrorMessage:   pgtype.Text{String: errorMsg, Valid: errorMsg != ""},
	})
}

// PauseProjection pauses a projection.
func (m *Manager) PauseProjection(ctx context.Context, name string) error {
	return m.SetStatus(ctx, name, StatusPaused, "")
}

// ResumeProjection resumes a paused projection.
func (m *Manager) ResumeProjection(ctx context.Context, name string) error {
	return m.SetStatus(ctx, name, StatusActive, "")
}

// ResetProjection resets a projection to rebuild from scratch.
func (m *Manager) ResetProjection(ctx context.Context, name string) error {
	m.handlersMu.RLock()
	handler, ok := m.handlers[name]
	m.handlersMu.RUnlock()

	if !ok {
		return fmt.Errorf("projection handler not found: %s", name)
	}

	// Set status to building
	if err := m.SetStatus(ctx, name, StatusBuilding, ""); err != nil {
		return fmt.Errorf("failed to set status: %w", err)
	}

	// Reset the projection state
	if err := handler.Reset(ctx); err != nil {
		_ = m.SetStatus(ctx, name, StatusError, err.Error())
		return fmt.Errorf("failed to reset projection: %w", err)
	}

	// Clear position
	if err := m.queries.UpdateProjectionPosition(ctx, db.UpdateProjectionPositionParams{
		ProjectionName:        name,
		LastProcessedPosition: 0,
	}); err != nil {
		return fmt.Errorf("failed to clear position: %w", err)
	}

	// Set status back to active
	if err := m.SetStatus(ctx, name, StatusActive, ""); err != nil {
		return fmt.Errorf("failed to set active status: %w", err)
	}

	m.logger.Info("Projection reset", zap.String("name", name))
	return nil
}

// SnapshotManager manages projection snapshots.
type SnapshotManager struct {
	pool    *pgxpool.Pool
	queries *db.Queries
	logger  *zap.Logger
}

// NewSnapshotManager creates a new snapshot manager.
func NewSnapshotManager(pool *pgxpool.Pool, logger *zap.Logger) *SnapshotManager {
	return &SnapshotManager{
		pool:    pool,
		queries: db.New(pool),
		logger:  logger.Named("snapshot-manager"),
	}
}

// Snapshot represents a projection snapshot.
type Snapshot struct {
	ID             uuid.UUID
	ProjectionName string
	AggregateID    *uuid.UUID
	Data           map[string]interface{}
	StreamPosition int64
	CreatedAt      time.Time
}

// SaveSnapshot saves a snapshot for a projection.
func (s *SnapshotManager) SaveSnapshot(ctx context.Context, projectionName string, aggregateID *uuid.UUID, data map[string]interface{}, streamPosition int64) error {
	dataJSON, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("failed to marshal snapshot data: %w", err)
	}

	aggID := pgtype.Text{}
	if aggregateID != nil {
		aggID = pgtype.Text{String: aggregateID.String(), Valid: true}
	}

	return s.queries.SaveSnapshot(ctx, db.SaveSnapshotParams{
		ID:             pgtype.UUID{Bytes: uuid.New(), Valid: true},
		ProjectionName: projectionName,
		AggregateID:    aggID,
		SnapshotData:   dataJSON,
		StreamPosition: streamPosition,
	})
}

// GetLatestSnapshot retrieves the latest snapshot for a projection.
func (s *SnapshotManager) GetLatestSnapshot(ctx context.Context, projectionName string, aggregateID *uuid.UUID) (*Snapshot, error) {
	aggID := pgtype.Text{}
	if aggregateID != nil {
		aggID = pgtype.Text{String: aggregateID.String(), Valid: true}
	}

	row, err := s.queries.GetLatestSnapshot(ctx, db.GetLatestSnapshotParams{
		ProjectionName: projectionName,
		AggregateID:    aggID,
	})
	if err != nil {
		return nil, err
	}

	var data map[string]interface{}
	if err := json.Unmarshal(row.SnapshotData, &data); err != nil {
		return nil, fmt.Errorf("failed to unmarshal snapshot data: %w", err)
	}

	snapshotID, _ := uuid.FromBytes(row.ID.Bytes[:])

	snapshot := &Snapshot{
		ID:             snapshotID,
		ProjectionName: row.ProjectionName,
		Data:           data,
		StreamPosition: row.StreamPosition,
		CreatedAt:      row.CreatedAt.Time,
	}

	if row.AggregateID.Valid {
		if aggUUID, err := uuid.Parse(row.AggregateID.String); err == nil {
			snapshot.AggregateID = &aggUUID
		}
	}

	return snapshot, nil
}

// DeleteSnapshots deletes all snapshots for a projection.
func (s *SnapshotManager) DeleteSnapshots(ctx context.Context, projectionName string) (int64, error) {
	return s.queries.DeleteSnapshotsByProjection(ctx, projectionName)
}

// GetSnapshotCount returns the number of snapshots for a projection.
func (s *SnapshotManager) GetSnapshotCount(ctx context.Context, projectionName string) (int64, error) {
	return s.queries.GetSnapshotCount(ctx, projectionName)
}
