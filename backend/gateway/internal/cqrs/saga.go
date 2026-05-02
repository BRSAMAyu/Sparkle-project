// Package cqrs provides the Saga pattern for distributed transactions with
// compensation support, integrated with the existing CQRS infrastructure.
package cqrs

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	"go.uber.org/zap"
)

// ---------------------------------------------------------------------------
// Saga Status
// ---------------------------------------------------------------------------

// SagaStatus represents the current state of a saga instance.
type SagaStatus string

const (
	SagaStatusPending      SagaStatus = "pending"
	SagaStatusRunning      SagaStatus = "running"
	SagaStatusCompleted    SagaStatus = "completed"
	SagaStatusCompensating SagaStatus = "compensating"
	SagaStatusCompensated  SagaStatus = "compensated"
	SagaStatusFailed       SagaStatus = "failed"
)

// IsTerminal returns true if the saga is in a terminal state.
func (s SagaStatus) IsTerminal() bool {
	return s == SagaStatusCompleted || s == SagaStatusCompensated || s == SagaStatusFailed
}

// ---------------------------------------------------------------------------
// Saga Step
// ---------------------------------------------------------------------------

// SagaStep defines a single step in a saga with forward execution and
// backward compensation. Implementations must be idempotent.
type SagaStep interface {
	// Name returns a human-readable identifier for this step.
	Name() string

	// Execute performs the forward action. It returns output data that is
	// passed to subsequent steps and is available to Compensate for rollback.
	Execute(ctx context.Context, sagaData map[string]interface{}) (map[string]interface{}, error)

	// Compensate rolls back the side effects of a successful Execute.
	// It receives the saga data including the output from the corresponding Execute.
	Compensate(ctx context.Context, sagaData map[string]interface{}) error
}

// StepFunc is a convenience adapter that wraps plain functions as a SagaStep.
type StepFunc struct {
	StepName     string
	ExecuteFn   func(ctx context.Context, data map[string]interface{}) (map[string]interface{}, error)
	CompensateFn func(ctx context.Context, data map[string]interface{}) error
}

func (s StepFunc) Name() string { return s.StepName }
func (s StepFunc) Execute(ctx context.Context, data map[string]interface{}) (map[string]interface{}, error) {
	return s.ExecuteFn(ctx, data)
}
func (s StepFunc) Compensate(ctx context.Context, data map[string]interface{}) error {
	if s.CompensateFn == nil {
		return nil
	}
	return s.CompensateFn(ctx, data)
}

// ---------------------------------------------------------------------------
// Retry Policy
// ---------------------------------------------------------------------------

// RetryPolicy configures per-step retry behavior with exponential backoff.
type RetryPolicy struct {
	MaxRetries     int
	InitialBackoff time.Duration
	MaxBackoff     time.Duration
	Multiplier     float64
}

// DefaultRetryPolicy returns sensible defaults.
func DefaultRetryPolicy() RetryPolicy {
	return RetryPolicy{
		MaxRetries:     3,
		InitialBackoff: 100 * time.Millisecond,
		MaxBackoff:     5 * time.Second,
		Multiplier:     2.0,
	}
}

// ---------------------------------------------------------------------------
// Saga Definition
// ---------------------------------------------------------------------------

// SagaDefinition describes a saga template with a name and ordered steps.
type SagaDefinition struct {
	Name        string
	Steps       []SagaStep
	RetryPolicy RetryPolicy
}

// ---------------------------------------------------------------------------
// Saga Instance (runtime state)
// ---------------------------------------------------------------------------

// StepResult records the outcome of a single step execution.
type StepResult struct {
	StepName  string                 `json:"step_name"`
	Status    string                 `json:"status"` // "completed" | "compensated" | "failed"
	Output    map[string]interface{} `json:"output,omitempty"`
	Error     string                 `json:"error,omitempty"`
	StartedAt time.Time              `json:"started_at"`
	EndedAt   time.Time              `json:"ended_at"`
}

// SagaInstance represents a running or completed saga execution.
type SagaInstance struct {
	ID            uuid.UUID              `json:"id"`
	SagaType      string                 `json:"saga_type"`
	Status        SagaStatus             `json:"status"`
	CurrentStep   int                    `json:"current_step"`
	InputData     map[string]interface{} `json:"input_data"`
	StepResults   []StepResult           `json:"step_results"`
	CreatedAt     time.Time              `json:"created_at"`
	UpdatedAt     time.Time              `json:"updated_at"`
	Error         string                 `json:"error,omitempty"`
	CorrelationID string                `json:"correlation_id,omitempty"`
}

// ---------------------------------------------------------------------------
// Prometheus Metrics
// ---------------------------------------------------------------------------

var (
	sagaStartedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Namespace: "sparkle", Subsystem: "saga", Name: "started_total",
		Help: "Total number of saga instances started by type",
	}, []string{"saga_type"})

	sagaCompletedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Namespace: "sparkle", Subsystem: "saga", Name: "completed_total",
		Help: "Total number of saga instances completed by type and status",
	}, []string{"saga_type", "status"})

	sagaStepDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Namespace: "sparkle", Subsystem: "saga", Name: "step_duration_seconds",
		Help:   "Duration of individual saga step execution",
		Buckets: []float64{0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10},
	}, []string{"saga_type", "step_name"})

	sagaCompensationTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Namespace: "sparkle", Subsystem: "saga", Name: "compensation_total",
		Help: "Total number of step compensations executed",
	}, []string{"saga_type", "step_name"})

	sagaActiveGauge = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Namespace: "sparkle", Subsystem: "saga", Name: "active_instances",
		Help: "Number of currently active (running/compensating) saga instances",
	}, []string{"saga_type"})

	sagaStepRetryTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Namespace: "sparkle", Subsystem: "saga", Name: "step_retry_total",
		Help: "Total number of step retry attempts",
	}, []string{"saga_type", "step_name"})
)

// ---------------------------------------------------------------------------
// Saga Coordinator
// ---------------------------------------------------------------------------

// SagaCoordinator orchestrates saga execution, persistence, and compensation.
type SagaCoordinator struct {
	pool     *pgxpool.Pool
	uow      *outbox.UnitOfWork
	eventBus event.EventBus
	logger   *zap.Logger

	mu       sync.RWMutex
	registry map[string]*SagaDefinition
}

// NewSagaCoordinator creates a new saga coordinator.
func NewSagaCoordinator(
	pool *pgxpool.Pool,
	eventBus event.EventBus,
	logger *zap.Logger,
) *SagaCoordinator {
	return &SagaCoordinator{
		pool:     pool,
		uow:      outbox.NewUnitOfWork(pool),
		eventBus: eventBus,
		logger:   logger.Named("saga"),
		registry: make(map[string]*SagaDefinition),
	}
}

// Register adds a saga definition to the coordinator.
func (c *SagaCoordinator) Register(def *SagaDefinition) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.registry[def.Name] = def
	c.logger.Info("Saga definition registered", zap.String("saga_type", def.Name))
}

// Execute starts a new saga instance and runs it to completion or compensation.
func (c *SagaCoordinator) Execute(ctx context.Context, sagaType string, inputData map[string]interface{}) (*SagaInstance, error) {
	c.mu.RLock()
	def, ok := c.registry[sagaType]
	c.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("saga definition not found: %s", sagaType)
	}

	if def.RetryPolicy.MaxRetries == 0 {
		p := DefaultRetryPolicy()
		def.RetryPolicy = p
	}

	instance := &SagaInstance{
		ID:            uuid.New(),
		SagaType:      sagaType,
		Status:        SagaStatusPending,
		CurrentStep:   0,
		InputData:     inputData,
		StepResults:   make([]StepResult, 0, len(def.Steps)),
		CreatedAt:     time.Now().UTC(),
		UpdatedAt:     time.Now().UTC(),
		CorrelationID: uuid.New().String(),
	}

	if err := c.persistInstance(ctx, instance); err != nil {
		return nil, fmt.Errorf("persist saga instance: %w", err)
	}

	sagaStartedTotal.WithLabelValues(sagaType).Inc()
	sagaActiveGauge.WithLabelValues(sagaType).Inc()

	instance.Status = SagaStatusRunning
	_ = c.updateStatus(ctx, instance, SagaStatusRunning)

	// Execute steps sequentially.
	sagaData := copyMap(inputData)
	for i, step := range def.Steps {
		instance.CurrentStep = i
		result := c.executeStepWithRetry(ctx, def, step, sagaData)

		instance.StepResults = append(instance.StepResults, result)
		instance.UpdatedAt = time.Now().UTC()

		if result.Status == "failed" {
			instance.Error = result.Error
			_ = c.updateStatus(ctx, instance, SagaStatusCompensating)
			c.compensate(ctx, def, instance, i-1, sagaData)

			sagaActiveGauge.WithLabelValues(sagaType).Dec()
			_ = c.persistInstance(ctx, instance)
			return instance, fmt.Errorf("saga step %q failed: %s", step.Name(), result.Error)
		}

		// Merge step output into saga data for next step.
		for k, v := range result.Output {
			sagaData[k] = v
		}

		_ = c.persistInstance(ctx, instance)
	}

	instance.Status = SagaStatusCompleted
	instance.UpdatedAt = time.Now().UTC()
	_ = c.updateStatus(ctx, instance, SagaStatusCompleted)
	_ = c.persistInstance(ctx, instance)

	sagaActiveGauge.WithLabelValues(sagaType).Dec()
	sagaCompletedTotal.WithLabelValues(sagaType, string(SagaStatusCompleted)).Inc()
	c.publishSagaEvent(ctx, instance, "saga.completed")
	return instance, nil
}

// executeStepWithRetry runs a single step with the configured retry policy.
func (c *SagaCoordinator) executeStepWithRetry(
	ctx context.Context,
	def *SagaDefinition,
	step SagaStep,
	sagaData map[string]interface{},
) StepResult {
	result := StepResult{
		StepName:  step.Name(),
		Status:    "completed",
		StartedAt: time.Now().UTC(),
	}

	policy := def.RetryPolicy
	var lastErr error

	for attempt := 0; attempt <= policy.MaxRetries; attempt++ {
		if attempt > 0 {
			sagaStepRetryTotal.WithLabelValues(def.Name, step.Name()).Inc()

			backoff := policy.InitialBackoff
			for b := 1; b < attempt; b++ {
				backoff = time.Duration(float64(backoff) * policy.Multiplier)
				if backoff > policy.MaxBackoff {
					backoff = policy.MaxBackoff
				}
			}
			select {
			case <-ctx.Done():
				result.Status = "failed"
				result.Error = ctx.Err().Error()
				result.EndedAt = time.Now().UTC()
				return result
			case <-time.After(backoff):
			}
		}

		start := time.Now()
		output, err := step.Execute(ctx, sagaData)
		sagaStepDuration.WithLabelValues(def.Name, step.Name()).Observe(time.Since(start).Seconds())

		if err == nil {
			result.Output = output
			result.EndedAt = time.Now().UTC()
			return result
		}
		lastErr = err
		c.logger.Warn("Saga step failed, retrying",
			zap.String("step", step.Name()),
			zap.Int("attempt", attempt+1),
			zap.Error(err),
		)
	}

	result.Status = "failed"
	result.Error = lastErr.Error()
	result.EndedAt = time.Now().UTC()
	return result
}

// compensate runs compensating actions in reverse order from failedStepIndex down to 0.
func (c *SagaCoordinator) compensate(
	ctx context.Context,
	def *SagaDefinition,
	instance *SagaInstance,
	failedStepIndex int,
	sagaData map[string]interface{},
) {
	c.logger.Warn("Starting saga compensation",
		zap.String("saga_id", instance.ID.String()),
		zap.String("saga_type", instance.SagaType),
		zap.Int("from_step", failedStepIndex),
	)

	instance.Status = SagaStatusCompensating

	compensationFailed := false
	for i := failedStepIndex; i >= 0; i-- {
		step := def.Steps[i]
		sagaCompensationTotal.WithLabelValues(def.Name, step.Name()).Inc()

		compCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
		err := step.Compensate(compCtx, sagaData)
		cancel()

		if i < len(instance.StepResults) {
			if err != nil {
				compensationFailed = true
				instance.StepResults[i].Status = "compensation_failed"
				c.logger.Error("Compensation failed",
					zap.String("step", step.Name()),
					zap.Error(err),
				)
			} else {
				instance.StepResults[i].Status = "compensated"
			}
		}

		_ = c.persistInstance(ctx, instance)
	}

	if !compensationFailed {
		instance.Status = SagaStatusCompensated
		sagaCompletedTotal.WithLabelValues(def.Name, string(SagaStatusCompensated)).Inc()
		c.publishSagaEvent(ctx, instance, "saga.compensated")
	} else {
		instance.Status = SagaStatusFailed
		sagaCompletedTotal.WithLabelValues(def.Name, string(SagaStatusFailed)).Inc()
		c.publishSagaEvent(ctx, instance, "saga.failed")
	}

	instance.UpdatedAt = time.Now().UTC()
}

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

// persistInstance saves or updates the saga instance in PostgreSQL.
// No-ops if no pool is configured (in-memory mode for testing).
func (c *SagaCoordinator) persistInstance(ctx context.Context, inst *SagaInstance) error {
	if c.uow == nil {
		return nil
	}
	stepResultsJSON, err := json.Marshal(inst.StepResults)
	if err != nil {
		return fmt.Errorf("marshal step results: %w", err)
	}
	inputDataJSON, err := json.Marshal(inst.InputData)
	if err != nil {
		return fmt.Errorf("marshal input data: %w", err)
	}

	return c.uow.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		const upsertSQL = `
			INSERT INTO saga_instances
				(id, saga_type, status, current_step, input_data, step_results, error, correlation_id, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
			ON CONFLICT (id) DO UPDATE SET
				status = EXCLUDED.status,
				current_step = EXCLUDED.current_step,
				step_results = EXCLUDED.step_results,
				error = EXCLUDED.error,
				updated_at = EXCLUDED.updated_at
		`
		_, err := txCtx.Tx().Exec(ctx, upsertSQL,
			inst.ID,
			inst.SagaType,
			string(inst.Status),
			inst.CurrentStep,
			inputDataJSON,
			stepResultsJSON,
			inst.Error,
			inst.CorrelationID,
			inst.CreatedAt,
			inst.UpdatedAt,
		)
		return err
	})
}

// updateStatus is a lightweight status-only update.
// No-ops if no pool is configured.
func (c *SagaCoordinator) updateStatus(ctx context.Context, inst *SagaInstance, status SagaStatus) error {
	inst.Status = status
	if c.pool == nil {
		return nil
	}
	inst.UpdatedAt = time.Now().UTC()
	_, err := c.pool.Exec(ctx,
		`UPDATE saga_instances SET status = $1, updated_at = $2 WHERE id = $3`,
		string(status), inst.UpdatedAt, inst.ID,
	)
	return err
}

// GetInstance retrieves a saga instance by ID.
func (c *SagaCoordinator) GetInstance(ctx context.Context, id uuid.UUID) (*SagaInstance, error) {
	row := c.pool.QueryRow(ctx, `
		SELECT id, saga_type, status, current_step, input_data, step_results, error, correlation_id, created_at, updated_at
		FROM saga_instances WHERE id = $1
	`, id)

	var inst SagaInstance
	var inputData, stepResults []byte
	err := row.Scan(&inst.ID, &inst.SagaType, &inst.Status, &inst.CurrentStep,
		&inputData, &stepResults, &inst.Error, &inst.CorrelationID,
		&inst.CreatedAt, &inst.UpdatedAt)
	if err != nil {
		return nil, fmt.Errorf("query saga instance: %w", err)
	}

	_ = json.Unmarshal(inputData, &inst.InputData)
	_ = json.Unmarshal(stepResults, &inst.StepResults)
	return &inst, nil
}

// ListInstancesByStatus retrieves saga instances filtered by status.
func (c *SagaCoordinator) ListInstancesByStatus(ctx context.Context, status SagaStatus, limit int) ([]*SagaInstance, error) {
	rows, err := c.pool.Query(ctx, `
		SELECT id, saga_type, status, current_step, input_data, step_results, error, correlation_id, created_at, updated_at
		FROM saga_instances WHERE status = $1 ORDER BY created_at DESC LIMIT $2
	`, string(status), limit)
	if err != nil {
		return nil, fmt.Errorf("list saga instances: %w", err)
	}
	defer rows.Close()

	var instances []*SagaInstance
	for rows.Next() {
		var inst SagaInstance
		var inputData, stepResults []byte
		if err := rows.Scan(&inst.ID, &inst.SagaType, &inst.Status, &inst.CurrentStep,
			&inputData, &stepResults, &inst.Error, &inst.CorrelationID,
			&inst.CreatedAt, &inst.UpdatedAt); err != nil {
			return nil, err
		}
		_ = json.Unmarshal(inputData, &inst.InputData)
		_ = json.Unmarshal(stepResults, &inst.StepResults)
		instances = append(instances, &inst)
	}
	return instances, rows.Err()
}

// ---------------------------------------------------------------------------
// Event publishing
// ---------------------------------------------------------------------------

func (c *SagaCoordinator) publishSagaEvent(ctx context.Context, inst *SagaInstance, eventType string) {
	if c.eventBus == nil {
		return
	}
	evt := event.NewDomainEvent(
		event.EventType(eventType),
		event.AggregateType("Saga"),
		inst.ID,
		map[string]interface{}{
			"saga_type":      inst.SagaType,
			"status":         string(inst.Status),
			"current_step":   inst.CurrentStep,
			"error":          inst.Error,
			"correlation_id": inst.CorrelationID,
		},
		event.EventMetadata{
			CorrelationID: inst.CorrelationID,
			Source:        "saga_coordinator",
		},
	)
	if err := c.eventBus.Publish(ctx, evt); err != nil {
		c.logger.Error("Failed to publish saga event",
			zap.String("event_type", eventType),
			zap.Error(err),
		)
	}
}

// ---------------------------------------------------------------------------
// Production Saga Definitions: 4 cross-service flows
// ---------------------------------------------------------------------------

// NewTaskCreateSaga builds: task creation → notification → CRDT sync.
func NewTaskCreateSaga(taskCreateFn, notifyFn, crdtSyncFn SagaStep) *SagaDefinition {
	return &SagaDefinition{
		Name:        "task_create_saga",
		Steps:       []SagaStep{taskCreateFn, notifyFn, crdtSyncFn},
		RetryPolicy: DefaultRetryPolicy(),
	}
}

// NewSourceUploadSaga builds: source upload → parse → node mount.
func NewSourceUploadSaga(uploadFn, parseFn, mountFn SagaStep) *SagaDefinition {
	return &SagaDefinition{
		Name:        "source_upload_saga",
		Steps:       []SagaStep{uploadFn, parseFn, mountFn},
		RetryPolicy: DefaultRetryPolicy(),
	}
}

// NewExperimentPromotionSaga builds: experiment promotion → notification → audit.
func NewExperimentPromotionSaga(promoteFn, notifyFn, auditFn SagaStep) *SagaDefinition {
	return &SagaDefinition{
		Name:        "experiment_promotion_saga",
		Steps:       []SagaStep{promoteFn, notifyFn, auditFn},
		RetryPolicy: DefaultRetryPolicy(),
	}
}

// NewSkillPublishSaga builds: skill publish → marketplace register → notification.
func NewSkillPublishSaga(publishFn, marketplaceFn, notifyFn SagaStep) *SagaDefinition {
	return &SagaDefinition{
		Name:        "skill_publish_saga",
		Steps:       []SagaStep{publishFn, marketplaceFn, notifyFn},
		RetryPolicy: DefaultRetryPolicy(),
	}
}

// ---------------------------------------------------------------------------
// Schema initialization
// ---------------------------------------------------------------------------

// EnsureSchema creates the saga_instances table if it does not exist.
// Call this during application startup.
func (c *SagaCoordinator) EnsureSchema(ctx context.Context) error {
	_, err := c.pool.Exec(ctx, `
		CREATE TABLE IF NOT EXISTS saga_instances (
			id              UUID PRIMARY KEY,
			saga_type       TEXT        NOT NULL,
			status          TEXT        NOT NULL DEFAULT 'pending',
			current_step    INT         NOT NULL DEFAULT 0,
			input_data      JSONB       NOT NULL DEFAULT '{}',
			step_results    JSONB       NOT NULL DEFAULT '[]',
			error           TEXT        NOT NULL DEFAULT '',
			correlation_id  TEXT        NOT NULL DEFAULT '',
			created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
			updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
		);
		CREATE INDEX IF NOT EXISTS idx_saga_instances_status  ON saga_instances(status);
		CREATE INDEX IF NOT EXISTS idx_saga_instances_type    ON saga_instances(saga_type);
		CREATE INDEX IF NOT EXISTS idx_saga_instances_created ON saga_instances(created_at DESC);
	`)
	return err
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func copyMap(m map[string]interface{}) map[string]interface{} {
	out := make(map[string]interface{}, len(m))
	for k, v := range m {
		out[k] = v
	}
	return out
}
