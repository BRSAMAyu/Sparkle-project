package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	cqrsEvent "github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	cqrsWorker "github.com/sparkle/gateway/internal/cqrs/worker"
	"github.com/sparkle/gateway/internal/db"
	"go.uber.org/zap"
)

const (
	// TaskStreamKey is the Redis stream for task events.
	TaskStreamKey = "cqrs:stream:task"
	// TaskConsumerGroup is the consumer group for task projection.
	TaskConsumerGroup = "task_projection_group"
)

// TaskView represents the read model for a task.
type TaskView struct {
	ID               string     `json:"id"`
	UserID           string     `json:"user_id"`
	PlanID           string     `json:"plan_id,omitempty"`
	Title            string     `json:"title"`
	Type             string     `json:"type"`
	Tags             []string   `json:"tags"`
	EstimatedMinutes int32      `json:"estimated_minutes"`
	Difficulty       int32      `json:"difficulty"`
	EnergyCost       int32      `json:"energy_cost"`
	Priority         int32      `json:"priority"`
	Status           string     `json:"status"`
	StartedAt        *time.Time `json:"started_at,omitempty"`
	CompletedAt      *time.Time `json:"completed_at,omitempty"`
	ActualMinutes    int32      `json:"actual_minutes,omitempty"`
	DueDate          *time.Time `json:"due_date,omitempty"`
	CreatedAt        time.Time  `json:"created_at"`
	UpdatedAt        time.Time  `json:"updated_at"`
}

// UserTaskStats represents aggregated task statistics for a user.
type UserTaskStats struct {
	UserID           string `json:"user_id"`
	TotalTasks       int    `json:"total_tasks"`
	PendingTasks     int    `json:"pending_tasks"`
	InProgressTasks  int    `json:"in_progress_tasks"`
	CompletedTasks   int    `json:"completed_tasks"`
	AbandonedTasks   int    `json:"abandoned_tasks"`
	TotalMinutes     int    `json:"total_minutes"`
	CompletedMinutes int    `json:"completed_minutes"`
}

// TaskSyncWorker synchronizes task events to Redis read models.
type TaskSyncWorker struct {
	baseWorker *cqrsWorker.BaseWorker
	redis      *redis.Client
	queries    *db.Queries
	logger     *zap.Logger
}

// TaskSyncWorkerConfig configures the task sync worker.
type TaskSyncWorkerConfig struct {
	ConsumerName string
	Options      cqrsWorker.WorkerOptions
}

// DefaultTaskSyncWorkerConfig returns sensible defaults.
func DefaultTaskSyncWorkerConfig() TaskSyncWorkerConfig {
	return TaskSyncWorkerConfig{
		ConsumerName: "task_worker_1",
		Options:      cqrsWorker.DefaultWorkerOptions(),
	}
}

// NewTaskSyncWorker creates a new task sync worker.
func NewTaskSyncWorker(
	rdb *redis.Client,
	pool *pgxpool.Pool,
	cqrsMetrics *metrics.CQRSMetrics,
	logger *zap.Logger,
	config ...TaskSyncWorkerConfig,
) *TaskSyncWorker {
	cfg := DefaultTaskSyncWorkerConfig()
	if len(config) > 0 {
		cfg = config[0]
	}

	queries := db.New(pool)
	processedEvents := outbox.NewProcessedEventsRepository(pool)

	baseWorker := cqrsWorker.NewBaseWorker(
		rdb,
		processedEvents,
		cqrsMetrics,
		logger,
		TaskStreamKey,
		TaskConsumerGroup,
		cfg.ConsumerName,
		cfg.Options,
	)

	return &TaskSyncWorker{
		baseWorker: baseWorker,
		redis:      rdb,
		queries:    queries,
		logger:     logger.Named("task-sync"),
	}
}

// Run starts the worker. Blocks until context is cancelled.
func (w *TaskSyncWorker) Run(ctx context.Context) error {
	return w.baseWorker.Run(ctx, w.handleEvent)
}

// IsRunning returns true if the worker is currently running.
func (w *TaskSyncWorker) IsRunning() bool {
	return w.baseWorker.IsRunning()
}

// handleEvent processes a single task event.
func (w *TaskSyncWorker) handleEvent(ctx context.Context, evt cqrsEvent.DomainEvent, messageID string) error {
	switch evt.Type {
	case cqrsEvent.EventTaskCreated:
		return w.handleTaskCreated(ctx, evt)
	case cqrsEvent.EventTaskStarted:
		return w.handleTaskStarted(ctx, evt)
	case cqrsEvent.EventTaskCompleted:
		return w.handleTaskCompleted(ctx, evt)
	case cqrsEvent.EventTaskAbandoned:
		return w.handleTaskAbandoned(ctx, evt)
	case cqrsEvent.EventTaskDeleted:
		return w.handleTaskDeleted(ctx, evt)
	case cqrsEvent.EventTaskUpdated:
		return w.handleTaskUpdated(ctx, evt)
	default:
		w.logger.Debug("Ignoring unhandled event type",
			zap.String("event_type", string(evt.Type)),
			zap.String("event_id", evt.ID),
		)
		return nil
	}
}

// handleTaskCreated processes a TaskCreated event.
func (w *TaskSyncWorker) handleTaskCreated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	taskID, err := uuid.Parse(taskIDStr)
	if err != nil {
		return fmt.Errorf("invalid task_id: %w", err)
	}

	// Fetch task from database
	task, err := w.getTask(ctx, taskID)
	if err != nil {
		return fmt.Errorf("fetch task: %w", err)
	}

	// Build view model
	view := w.buildTaskView(task)

	viewJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal view: %w", err)
	}

	// Update Redis
	pipe := w.redis.Pipeline()

	// Task view
	pipe.Set(ctx, "task:view:"+taskIDStr, viewJSON, 0)

	// User's task list (sorted by created_at)
	pipe.ZAdd(ctx, "user:tasks:"+userIDStr, redis.Z{
		Score:  float64(task.CreatedAt.Time.Unix()),
		Member: taskIDStr,
	})

	// Pending tasks list (sorted by priority, due_date)
	if task.Status == db.TaskstatusPENDING {
		pipe.ZAdd(ctx, "user:tasks:pending:"+userIDStr, redis.Z{
			Score:  float64(task.Priority),
			Member: taskIDStr,
		})
	}

	// Increment user stats
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "total_tasks", 1)
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "pending_tasks", 1)
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "total_minutes", int64(task.EstimatedMinutes))

	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Info("Task view created",
		zap.String("task_id", taskIDStr),
		zap.String("user_id", userIDStr),
	)

	return nil
}

// handleTaskStarted processes a TaskStarted event.
func (w *TaskSyncWorker) handleTaskStarted(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	// Update view
	if err := w.updateTaskStatus(ctx, taskIDStr, "in_progress"); err != nil {
		return err
	}

	// Update stats
	pipe := w.redis.Pipeline()
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "pending_tasks", -1)
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "in_progress_tasks", 1)
	pipe.ZRem(ctx, "user:tasks:pending:"+userIDStr, taskIDStr)
	pipe.ZAdd(ctx, "user:tasks:in_progress:"+userIDStr, redis.Z{
		Score:  float64(time.Now().Unix()),
		Member: taskIDStr,
	})
	_, err := pipe.Exec(ctx)

	w.logger.Debug("Task started",
		zap.String("task_id", taskIDStr),
		zap.String("user_id", userIDStr),
	)

	return err
}

// handleTaskCompleted processes a TaskCompleted event.
func (w *TaskSyncWorker) handleTaskCompleted(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	actualMinutes := int64(0)
	if am, ok := evt.Payload["actual_minutes"].(float64); ok {
		actualMinutes = int64(am)
	}

	// Update view
	if err := w.updateTaskStatus(ctx, taskIDStr, "completed"); err != nil {
		return err
	}

	// Update stats
	pipe := w.redis.Pipeline()
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "in_progress_tasks", -1)
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "completed_tasks", 1)
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "completed_minutes", actualMinutes)
	pipe.ZRem(ctx, "user:tasks:in_progress:"+userIDStr, taskIDStr)
	pipe.ZAdd(ctx, "user:tasks:completed:"+userIDStr, redis.Z{
		Score:  float64(time.Now().Unix()),
		Member: taskIDStr,
	})
	_, err := pipe.Exec(ctx)

	w.logger.Info("Task completed",
		zap.String("task_id", taskIDStr),
		zap.String("user_id", userIDStr),
		zap.Int64("actual_minutes", actualMinutes),
	)

	return err
}

// handleTaskAbandoned processes a TaskAbandoned event.
func (w *TaskSyncWorker) handleTaskAbandoned(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	// Update view
	if err := w.updateTaskStatus(ctx, taskIDStr, "abandoned"); err != nil {
		return err
	}

	// Update stats (assume it was in_progress, but handle pending too)
	pipe := w.redis.Pipeline()
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "abandoned_tasks", 1)
	pipe.ZRem(ctx, "user:tasks:pending:"+userIDStr, taskIDStr)
	pipe.ZRem(ctx, "user:tasks:in_progress:"+userIDStr, taskIDStr)
	_, err := pipe.Exec(ctx)

	w.logger.Info("Task abandoned",
		zap.String("task_id", taskIDStr),
		zap.String("user_id", userIDStr),
	)

	return err
}

// handleTaskDeleted processes a TaskDeleted event.
func (w *TaskSyncWorker) handleTaskDeleted(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	// Remove from Redis
	pipe := w.redis.Pipeline()
	pipe.Del(ctx, "task:view:"+taskIDStr)
	pipe.ZRem(ctx, "user:tasks:"+userIDStr, taskIDStr)
	pipe.ZRem(ctx, "user:tasks:pending:"+userIDStr, taskIDStr)
	pipe.ZRem(ctx, "user:tasks:in_progress:"+userIDStr, taskIDStr)
	pipe.ZRem(ctx, "user:tasks:completed:"+userIDStr, taskIDStr)
	_, err := pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("remove from redis: %w", err)
	}

	w.logger.Info("Task view deleted",
		zap.String("task_id", taskIDStr),
		zap.String("user_id", userIDStr),
	)

	return nil
}

// handleTaskUpdated processes a TaskUpdated event.
func (w *TaskSyncWorker) handleTaskUpdated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	taskID, err := uuid.Parse(taskIDStr)
	if err != nil {
		return fmt.Errorf("invalid task_id: %w", err)
	}

	// Refetch task and rebuild view
	task, err := w.getTask(ctx, taskID)
	if err != nil {
		return fmt.Errorf("fetch task: %w", err)
	}

	view := w.buildTaskView(task)
	viewJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal view: %w", err)
	}

	if err := w.redis.Set(ctx, "task:view:"+taskIDStr, viewJSON, 0).Err(); err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Debug("Task view updated",
		zap.String("task_id", taskIDStr),
	)

	return nil
}

// updateTaskStatus updates the status field in a task view.
func (w *TaskSyncWorker) updateTaskStatus(ctx context.Context, taskIDStr, status string) error {
	viewJSON, err := w.redis.Get(ctx, "task:view:"+taskIDStr).Bytes()
	if err != nil {
		if err == redis.Nil {
			w.logger.Warn("Task view not found", zap.String("task_id", taskIDStr))
			return nil
		}
		return fmt.Errorf("get task view: %w", err)
	}

	var view TaskView
	if err := json.Unmarshal(viewJSON, &view); err != nil {
		return fmt.Errorf("unmarshal view: %w", err)
	}

	view.Status = status
	now := time.Now()
	view.UpdatedAt = now

	if status == "in_progress" {
		view.StartedAt = &now
	} else if status == "completed" || status == "abandoned" {
		view.CompletedAt = &now
	}

	updatedJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal updated view: %w", err)
	}

	return w.redis.Set(ctx, "task:view:"+taskIDStr, updatedJSON, 0).Err()
}

// getTask fetches a task from the database.
func (w *TaskSyncWorker) getTask(ctx context.Context, taskID uuid.UUID) (*db.Task, error) {
	task, err := w.queries.GetTaskByID(ctx, pgtype.UUID{Bytes: taskID, Valid: true})
	if err != nil {
		return nil, err
	}
	return &task, nil
}

// buildTaskView constructs a TaskView from a db.Task.
func (w *TaskSyncWorker) buildTaskView(task *db.Task) TaskView {
	taskID, _ := uuid.FromBytes(task.ID.Bytes[:])
	userID, _ := uuid.FromBytes(task.UserID.Bytes[:])

	var tags []string
	if task.Tags != nil {
		_ = json.Unmarshal(task.Tags, &tags)
	}

	view := TaskView{
		ID:               taskID.String(),
		UserID:           userID.String(),
		Title:            task.Title,
		Type:             string(task.Type),
		Tags:             tags,
		EstimatedMinutes: task.EstimatedMinutes,
		Difficulty:       task.Difficulty,
		EnergyCost:       task.EnergyCost,
		Priority:         task.Priority,
		Status:           string(task.Status),
		CreatedAt:        task.CreatedAt.Time,
		UpdatedAt:        task.UpdatedAt.Time,
	}

	if task.PlanID.Valid {
		planID, _ := uuid.FromBytes(task.PlanID.Bytes[:])
		view.PlanID = planID.String()
	}

	if task.StartedAt.Valid {
		view.StartedAt = &task.StartedAt.Time
	}

	if task.CompletedAt.Valid {
		view.CompletedAt = &task.CompletedAt.Time
	}

	if task.ActualMinutes.Valid {
		view.ActualMinutes = task.ActualMinutes.Int32
	}

	if task.DueDate.Valid {
		view.DueDate = &task.DueDate.Time
	}

	return view
}
