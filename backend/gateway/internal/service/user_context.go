package service

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sparkle/gateway/internal/db"
	"log"
)

// TaskSummary represents a summary of a pending task
type TaskSummary struct {
	ID               uuid.UUID `json:"id"`
	Title            string    `json:"title"`
	Type             string    `json:"type"`
	EstimatedMinutes int32     `json:"estimated_minutes"`
	Priority         int32     `json:"priority"`
	DueDate          *time.Time `json:"due_date,omitempty"`
}

// PlanSummary represents a summary of an active plan
type PlanSummary struct {
	ID         uuid.UUID  `json:"id"`
	Title      string     `json:"title"`
	Type       string     `json:"type"`
	TargetDate *time.Time `json:"target_date,omitempty"`
	Progress   int32      `json:"progress"`
}

// FocusStatsSummary represents today's focus statistics
type FocusStatsSummary struct {
	TotalSessionsToday    int32   `json:"total_sessions_today"`
	TotalMinutesToday     int32   `json:"total_minutes_today"`
	AverageFocusMinutes   int32   `json:"average_focus_minutes"`
	Streak                int32   `json:"streak"`
	LastSessionTimestamp  *time.Time `json:"last_session_timestamp,omitempty"`
}

// ProgressEvent represents a recent task completion
type ProgressEvent struct {
	TaskID        uuid.UUID `json:"task_id"`
	TaskTitle     string    `json:"task_title"`
	CompletedAt   time.Time `json:"completed_at"`
	TimeSpentMin  int32     `json:"time_spent_min"`
}

// UserContextData holds all context information for a user
type UserContextData struct {
	PendingTasks   []TaskSummary       `json:"pending_tasks"`
	ActivePlans    []PlanSummary       `json:"active_plans"`
	FocusStats     FocusStatsSummary   `json:"focus_stats"`
	RecentProgress []ProgressEvent     `json:"recent_progress"`
}

// UserContextService handles fetching user context data for the orchestrator
type UserContextService struct {
	pool    *pgxpool.Pool
	queries *db.Queries
}

// NewUserContextService creates a new user context service
func NewUserContextService(pool *pgxpool.Pool) *UserContextService {
	return &UserContextService{
		pool:    pool,
		queries: db.New(pool),
	}
}

// GetPendingTasks fetches up to `limit` pending tasks for a user, ordered by priority and due date
func (s *UserContextService) GetPendingTasks(ctx context.Context, userID uuid.UUID, limit int32) ([]TaskSummary, error) {
	if limit <= 0 {
		limit = 5
	}

	// Query pending tasks ordered by priority (DESC) and due date (ASC)
	rows, err := s.pool.Query(ctx, `
		SELECT id, title, type, estimated_minutes, priority, due_date
		FROM tasks
		WHERE user_id = $1 AND status = 'PENDING'
		ORDER BY priority DESC, due_date ASC, created_at DESC
		LIMIT $2
	`, userID, limit)
	if err != nil {
		log.Printf("Failed to fetch pending tasks: %v", err)
		return []TaskSummary{}, nil // Return empty list on error, not fatal
	}
	defer rows.Close()

	var tasks []TaskSummary
	for rows.Next() {
		var task TaskSummary
		if err := rows.Scan(&task.ID, &task.Title, &task.Type, &task.EstimatedMinutes, &task.Priority, &task.DueDate); err != nil {
			log.Printf("Failed to scan task: %v", err)
			continue
		}
		tasks = append(tasks, task)
	}

	return tasks, nil
}

// GetActivePlans fetches up to `limit` active plans for a user
func (s *UserContextService) GetActivePlans(ctx context.Context, userID uuid.UUID, limit int32) ([]PlanSummary, error) {
	if limit <= 0 {
		limit = 3
	}

	rows, err := s.pool.Query(ctx, `
		SELECT id, name, type, target_date, progress
		FROM plans
		WHERE user_id = $1 AND is_active = true
		ORDER BY created_at DESC
		LIMIT $2
	`, userID, limit)
	if err != nil {
		log.Printf("Failed to fetch active plans: %v", err)
		return []PlanSummary{}, nil
	}
	defer rows.Close()

	var plans []PlanSummary
	for rows.Next() {
		var plan PlanSummary
		if err := rows.Scan(&plan.ID, &plan.Title, &plan.Type, &plan.TargetDate, &plan.Progress); err != nil {
			log.Printf("Failed to scan plan: %v", err)
			continue
		}
		plans = append(plans, plan)
	}

	return plans, nil
}

// GetTodayStats fetches focus statistics for today
func (s *UserContextService) GetTodayStats(ctx context.Context, userID uuid.UUID) (FocusStatsSummary, error) {
	// Define "today" as midnight to now in user's timezone (default UTC+8)
	now := time.Now()
	todayStart := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location())

	stats := FocusStatsSummary{}

	// Query focus sessions for today
	row := s.pool.QueryRow(ctx, `
		SELECT
			COUNT(*) as total_sessions,
			COALESCE(SUM(CAST(duration_minutes AS INTEGER)), 0) as total_minutes,
			COALESCE(MAX(created_at), NULL) as last_session_time
		FROM focus_sessions
		WHERE user_id = $1 AND created_at >= $2
	`, userID, todayStart)

	var totalSessions int32
	var totalMinutes int32
	var lastSessionTime *time.Time

	if err := row.Scan(&totalSessions, &totalMinutes, &lastSessionTime); err != nil {
		log.Printf("Failed to fetch focus stats: %v", err)
		// Return empty stats on error
		return stats, nil
	}

	stats.TotalSessionsToday = totalSessions
	stats.TotalMinutesToday = totalMinutes
	stats.LastSessionTimestamp = lastSessionTime

	// Calculate average if there are sessions
	if totalSessions > 0 {
		stats.AverageFocusMinutes = totalMinutes / totalSessions
	}

	// Get current streak (simplified: sessions in last N days without gaps)
	streakRow := s.pool.QueryRow(ctx, `
		SELECT COUNT(DISTINCT DATE(created_at))
		FROM focus_sessions
		WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '30 days'
		ORDER BY created_at DESC
	`, userID)

	if err := streakRow.Scan(&stats.Streak); err != nil {
		// Streak calculation failed, leave as 0
		stats.Streak = 0
	}

	return stats, nil
}

// GetRecentProgress fetches recently completed tasks (last 24 hours)
func (s *UserContextService) GetRecentProgress(ctx context.Context, userID uuid.UUID, hours int) ([]ProgressEvent, error) {
	if hours <= 0 {
		hours = 24
	}

	sinceTime := time.Now().Add(time.Duration(-hours) * time.Hour)

	rows, err := s.pool.Query(ctx, `
		SELECT
			t.id,
			t.title,
			t.completed_at,
			COALESCE(t.estimated_minutes, 0) as time_spent_min
		FROM tasks t
		WHERE t.user_id = $1 AND t.status = 'COMPLETED' AND t.completed_at >= $2
		ORDER BY t.completed_at DESC
		LIMIT 10
	`, userID, sinceTime)
	if err != nil {
		log.Printf("Failed to fetch recent progress: %v", err)
		return []ProgressEvent{}, nil
	}
	defer rows.Close()

	var events []ProgressEvent
	for rows.Next() {
		var event ProgressEvent
		if err := rows.Scan(&event.TaskID, &event.TaskTitle, &event.CompletedAt, &event.TimeSpentMin); err != nil {
			log.Printf("Failed to scan progress event: %v", err)
			continue
		}
		events = append(events, event)
	}

	return events, nil
}

// GetUserContextData fetches all context data for a user and returns as JSON string
func (s *UserContextService) GetUserContextData(ctx context.Context, userID uuid.UUID) (string, error) {
	// Fetch all context in parallel
	tasksChan := make(chan []TaskSummary, 1)
	plansChan := make(chan []PlanSummary, 1)
	statsChan := make(chan FocusStatsSummary, 1)
	progressChan := make(chan []ProgressEvent, 1)
	errChan := make(chan error, 4)

	go func() {
		tasks, err := s.GetPendingTasks(ctx, userID, 5)
		if err != nil {
			errChan <- err
		}
		tasksChan <- tasks
	}()

	go func() {
		plans, err := s.GetActivePlans(ctx, userID, 3)
		if err != nil {
			errChan <- err
		}
		plansChan <- plans
	}()

	go func() {
		stats, err := s.GetTodayStats(ctx, userID)
		if err != nil {
			errChan <- err
		}
		statsChan <- stats
	}()

	go func() {
		progress, err := s.GetRecentProgress(ctx, userID, 24)
		if err != nil {
			errChan <- err
		}
		progressChan <- progress
	}()

	// Collect results (timeout protection: use context deadline)
	tasks := <-tasksChan
	plans := <-plansChan
	stats := <-statsChan
	progress := <-progressChan

	// Close error channel and check for errors (non-fatal)
	close(errChan)
	for err := range errChan {
		if err != nil {
			log.Printf("Warning: error fetching some context: %v", err)
		}
	}

	// Build context data
	contextData := UserContextData{
		PendingTasks:   tasks,
		ActivePlans:    plans,
		FocusStats:     stats,
		RecentProgress: progress,
	}

	// Serialize to JSON
	jsonData, err := json.Marshal(contextData)
	if err != nil {
		log.Printf("Failed to marshal context data: %v", err)
		return "", fmt.Errorf("failed to marshal context data: %w", err)
	}

	return string(jsonData), nil
}
