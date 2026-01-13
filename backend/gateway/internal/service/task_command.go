package service

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	"github.com/sparkle/gateway/internal/db"
)

// CreateTaskRequest contains data for creating a new task.
type CreateTaskRequest struct {
	UserID           uuid.UUID
	PlanID           *uuid.UUID
	Title            string
	Type             db.Tasktype
	Tags             []string
	EstimatedMinutes int32
	Difficulty       int32
	EnergyCost       int32
	GuideContent     string
	Priority         int32
	DueDate          *time.Time
	KnowledgeNodeID  *uuid.UUID
	ToolResultID     string
}

// UpdateTaskRequest contains data for updating a task.
type UpdateTaskRequest struct {
	TaskID           uuid.UUID
	UserID           uuid.UUID
	Title            *string
	EstimatedMinutes *int32
	Difficulty       *int32
	Priority         *int32
	DueDate          *time.Time
	GuideContent     *string
}

// TaskCommandService handles write operations for the task module.
// Uses the Outbox pattern for reliable event publishing with transactional consistency.
type TaskCommandService struct {
	pool       *pgxpool.Pool
	queries    *db.Queries
	unitOfWork *outbox.UnitOfWork
}

// NewTaskCommandService creates a new task command service.
func NewTaskCommandService(pool *pgxpool.Pool) *TaskCommandService {
	return &TaskCommandService{
		pool:       pool,
		queries:    db.New(pool),
		unitOfWork: outbox.NewUnitOfWork(pool),
	}
}

// CreateTask creates a new task and publishes a TaskCreated event atomically.
func (s *TaskCommandService) CreateTask(ctx context.Context, req CreateTaskRequest) (*db.Task, error) {
	if req.Title == "" {
		return nil, fmt.Errorf("title cannot be empty")
	}

	tagsJSON, err := json.Marshal(req.Tags)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal tags: %w", err)
	}

	var task db.Task

	err = s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Prepare nullable fields
		planID := pgtype.UUID{}
		if req.PlanID != nil {
			planID = pgtype.UUID{Bytes: *req.PlanID, Valid: true}
		}

		guideContent := pgtype.Text{}
		if req.GuideContent != "" {
			guideContent = pgtype.Text{String: req.GuideContent, Valid: true}
		}

		dueDate := pgtype.Date{}
		if req.DueDate != nil {
			dueDate = pgtype.Date{Time: *req.DueDate, Valid: true}
		}

		knowledgeNodeID := pgtype.UUID{}
		if req.KnowledgeNodeID != nil {
			knowledgeNodeID = pgtype.UUID{Bytes: *req.KnowledgeNodeID, Valid: true}
		}

		// Insert task in transaction
		row := txCtx.QueryRow(ctx, `
			INSERT INTO tasks (
				user_id, plan_id, title, type, tags,
				estimated_minutes, difficulty, energy_cost,
				guide_content, status, priority, due_date,
				knowledge_node_id, auto_expand_enabled,
				tool_result_id,
				created_at, updated_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'PENDING', $10, $11, $12, true, $13, NOW(), NOW())
			RETURNING id, user_id, plan_id, title, type, tags,
			          estimated_minutes, difficulty, energy_cost,
			          guide_content, status, started_at, completed_at,
			          actual_minutes, user_note, priority, due_date,
			          knowledge_node_id, auto_expand_enabled,
			          created_at, updated_at, deleted_at
		`,
			pgtype.UUID{Bytes: req.UserID, Valid: true},
			planID,
			req.Title,
			req.Type,
			tagsJSON,
			req.EstimatedMinutes,
			req.Difficulty,
			req.EnergyCost,
			guideContent,
			req.Priority,
			dueDate,
			knowledgeNodeID,
			pgtype.Text{String: req.ToolResultID, Valid: req.ToolResultID != ""},
		)

		err := row.Scan(
			&task.ID,
			&task.UserID,
			&task.PlanID,
			&task.Title,
			&task.Type,
			&task.Tags,
			&task.EstimatedMinutes,
			&task.Difficulty,
			&task.EnergyCost,
			&task.GuideContent,
			&task.Status,
			&task.StartedAt,
			&task.CompletedAt,
			&task.ActualMinutes,
			&task.UserNote,
			&task.Priority,
			&task.DueDate,
			&task.KnowledgeNodeID,
			&task.AutoExpandEnabled,
			&task.CreatedAt,
			&task.UpdatedAt,
			&task.DeletedAt,
		)
		if err != nil {
			return fmt.Errorf("failed to create task: %w", err)
		}

		// Create domain event
		taskID, _ := uuid.FromBytes(task.ID.Bytes[:])
		domainEvent := event.NewDomainEvent(
			event.EventTaskCreated,
			event.AggregateTask,
			taskID,
			map[string]interface{}{
				"task_id":           taskID.String(),
				"user_id":           req.UserID.String(),
				"title":             req.Title,
				"type":              string(req.Type),
				"estimated_minutes": req.EstimatedMinutes,
				"priority":          req.Priority,
			},
			event.EventMetadata{
				UserID: req.UserID,
				Source: "task_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})

	if err != nil {
		return nil, err
	}

	return &task, nil
}

// StartTask starts a task and publishes a TaskStarted event atomically.
func (s *TaskCommandService) StartTask(ctx context.Context, userID, taskID uuid.UUID) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE tasks
			SET status = 'IN_PROGRESS', started_at = NOW(), updated_at = NOW()
			WHERE id = $1 AND user_id = $2 AND status = 'PENDING' AND deleted_at IS NULL
		`, pgtype.UUID{Bytes: taskID, Valid: true}, pgtype.UUID{Bytes: userID, Valid: true})

		if err != nil {
			return fmt.Errorf("failed to start task: %w", err)
		}

		if result.RowsAffected() == 0 {
			return fmt.Errorf("task not found or not in pending status")
		}

		domainEvent := event.NewDomainEvent(
			event.EventTaskStarted,
			event.AggregateTask,
			taskID,
			map[string]interface{}{
				"task_id": taskID.String(),
				"user_id": userID.String(),
			},
			event.EventMetadata{
				UserID: userID,
				Source: "task_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// CompleteTask completes a task and publishes a TaskCompleted event atomically.
func (s *TaskCommandService) CompleteTask(ctx context.Context, userID, taskID uuid.UUID, actualMinutes int32, userNote string) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE tasks
			SET status = 'COMPLETED', completed_at = NOW(), updated_at = NOW(),
			    actual_minutes = $3, user_note = $4
			WHERE id = $1 AND user_id = $2 AND status = 'IN_PROGRESS' AND deleted_at IS NULL
		`,
			pgtype.UUID{Bytes: taskID, Valid: true},
			pgtype.UUID{Bytes: userID, Valid: true},
			actualMinutes,
			pgtype.Text{String: userNote, Valid: userNote != ""},
		)

		if err != nil {
			return fmt.Errorf("failed to complete task: %w", err)
		}

		if result.RowsAffected() == 0 {
			return fmt.Errorf("task not found or not in progress")
		}

		domainEvent := event.NewDomainEvent(
			event.EventTaskCompleted,
			event.AggregateTask,
			taskID,
			map[string]interface{}{
				"task_id":        taskID.String(),
				"user_id":        userID.String(),
				"actual_minutes": actualMinutes,
			},
			event.EventMetadata{
				UserID: userID,
				Source: "task_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// AbandonTask abandons a task and publishes a TaskAbandoned event atomically.
func (s *TaskCommandService) AbandonTask(ctx context.Context, userID, taskID uuid.UUID, reason string) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE tasks
			SET status = 'ABANDONED', completed_at = NOW(), updated_at = NOW(),
			    user_note = $3
			WHERE id = $1 AND user_id = $2 AND status IN ('PENDING', 'IN_PROGRESS') AND deleted_at IS NULL
		`,
			pgtype.UUID{Bytes: taskID, Valid: true},
			pgtype.UUID{Bytes: userID, Valid: true},
			pgtype.Text{String: reason, Valid: reason != ""},
		)

		if err != nil {
			return fmt.Errorf("failed to abandon task: %w", err)
		}

		if result.RowsAffected() == 0 {
			return fmt.Errorf("task not found or already completed/abandoned")
		}

		domainEvent := event.NewDomainEvent(
			event.EventTaskAbandoned,
			event.AggregateTask,
			taskID,
			map[string]interface{}{
				"task_id": taskID.String(),
				"user_id": userID.String(),
				"reason":  reason,
			},
			event.EventMetadata{
				UserID: userID,
				Source: "task_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// DeleteTask soft deletes a task and publishes a TaskDeleted event atomically.
func (s *TaskCommandService) DeleteTask(ctx context.Context, userID, taskID uuid.UUID) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE tasks
			SET deleted_at = NOW(), updated_at = NOW()
			WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
		`, pgtype.UUID{Bytes: taskID, Valid: true}, pgtype.UUID{Bytes: userID, Valid: true})

		if err != nil {
			return fmt.Errorf("failed to delete task: %w", err)
		}

		if result.RowsAffected() == 0 {
			return fmt.Errorf("task not found or already deleted")
		}

		domainEvent := event.NewDomainEvent(
			event.EventTaskDeleted,
			event.AggregateTask,
			taskID,
			map[string]interface{}{
				"task_id": taskID.String(),
				"user_id": userID.String(),
			},
			event.EventMetadata{
				UserID: userID,
				Source: "task_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// UpdateTask updates a task and publishes a TaskUpdated event atomically.
func (s *TaskCommandService) UpdateTask(ctx context.Context, req UpdateTaskRequest) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Build dynamic update query
		updates := make(map[string]interface{})
		if req.Title != nil {
			updates["title"] = *req.Title
		}
		if req.EstimatedMinutes != nil {
			updates["estimated_minutes"] = *req.EstimatedMinutes
		}
		if req.Difficulty != nil {
			updates["difficulty"] = *req.Difficulty
		}
		if req.Priority != nil {
			updates["priority"] = *req.Priority
		}
		if req.GuideContent != nil {
			updates["guide_content"] = *req.GuideContent
		}
		if req.DueDate != nil {
			updates["due_date"] = *req.DueDate
		}

		if len(updates) == 0 {
			return nil // Nothing to update
		}

		// Simple update - in production, you'd want a more sophisticated query builder
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE tasks
			SET title = COALESCE($3, title),
			    estimated_minutes = COALESCE($4, estimated_minutes),
			    difficulty = COALESCE($5, difficulty),
			    priority = COALESCE($6, priority),
			    guide_content = COALESCE($7, guide_content),
			    due_date = COALESCE($8, due_date),
			    updated_at = NOW()
			WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
		`,
			pgtype.UUID{Bytes: req.TaskID, Valid: true},
			pgtype.UUID{Bytes: req.UserID, Valid: true},
			nilOrString(req.Title),
			nilOrInt32(req.EstimatedMinutes),
			nilOrInt32(req.Difficulty),
			nilOrInt32(req.Priority),
			nilOrString(req.GuideContent),
			nilOrTime(req.DueDate),
		)

		if err != nil {
			return fmt.Errorf("failed to update task: %w", err)
		}

		if result.RowsAffected() == 0 {
			return fmt.Errorf("task not found")
		}

		domainEvent := event.NewDomainEvent(
			event.EventTaskUpdated,
			event.AggregateTask,
			req.TaskID,
			map[string]interface{}{
				"task_id": req.TaskID.String(),
				"user_id": req.UserID.String(),
				"updates": updates,
			},
			event.EventMetadata{
				UserID: req.UserID,
				Source: "task_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// ConfirmGeneratedTasks confirms a batch of generated tasks.
func (s *TaskCommandService) ConfirmGeneratedTasks(ctx context.Context, userID uuid.UUID, toolResultID string) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE tasks
			SET status = 'IN_PROGRESS', confirmed_at = NOW(), updated_at = NOW()
			WHERE user_id = $1 AND tool_result_id = $2 AND status = 'PENDING' AND deleted_at IS NULL
		`,
			pgtype.UUID{Bytes: userID, Valid: true},
			pgtype.Text{String: toolResultID, Valid: true},
		)

		if err != nil {
			return fmt.Errorf("failed to confirm tasks: %w", err)
		}

		rowsAffected := result.RowsAffected()
		if rowsAffected == 0 {
			// Not necessarily an error, might have been confirmed already or no tasks found
			return nil
		}

		// Publish event
		domainEvent := event.NewDomainEvent(
			"task.confirmed_batch", // Custom event type
			event.AggregateTask,
			userID, // Use userID as aggregate ID for batch ops? Or just a random one
			map[string]interface{}{
				"user_id":        userID.String(),
				"tool_result_id": toolResultID,
				"count":          rowsAffected,
			},
			event.EventMetadata{
				UserID: userID,
				Source: "task_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// Helper functions for nullable types
func nilOrString(s *string) pgtype.Text {
	if s == nil {
		return pgtype.Text{}
	}
	return pgtype.Text{String: *s, Valid: true}
}

func nilOrInt32(i *int32) pgtype.Int4 {
	if i == nil {
		return pgtype.Int4{}
	}
	return pgtype.Int4{Int32: *i, Valid: true}
}

func nilOrTime(t *time.Time) pgtype.Date {
	if t == nil {
		return pgtype.Date{}
	}
	return pgtype.Date{Time: *t, Valid: true}
}
