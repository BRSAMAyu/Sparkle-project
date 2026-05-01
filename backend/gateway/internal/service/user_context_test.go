package service

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/db"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ============================================================
// buildTaskLines Tests
// ============================================================

func TestBuildTaskLines(t *testing.T) {
	t.Run("empty_tasks", func(t *testing.T) {
		lines := buildTaskLines([]TaskSummary{})
		assert.Equal(t, 0, len(lines))
	})

	t.Run("single_task", func(t *testing.T) {
		id := uuid.New()
		tasks := []TaskSummary{
			{ID: id, Title: "Read chapter 5", Type: "study", EstimatedMinutes: 30, Priority: 3},
		}
		lines := buildTaskLines(tasks)
		assert.Equal(t, 1, len(lines))
		assert.Contains(t, lines[0], id.String())
		assert.Contains(t, lines[0], "Read chapter 5")
		assert.Contains(t, lines[0], "study")
	})

	t.Run("multiple_tasks", func(t *testing.T) {
		tasks := []TaskSummary{
			{ID: uuid.New(), Title: "Task A", Type: "study", Priority: 5},
			{ID: uuid.New(), Title: "Task B", Type: "exercise", Priority: 3},
		}
		lines := buildTaskLines(tasks)
		assert.Equal(t, 2, len(lines))
	})
}

func TestBuildTaskLines_WithDueDate(t *testing.T) {
	now := time.Now()
	id := uuid.New()
	tasks := []TaskSummary{
		{ID: id, Title: "Urgent", Type: "study", DueDate: &now, Priority: 1},
	}
	lines := buildTaskLines(tasks)
	assert.Equal(t, 1, len(lines))
	assert.Contains(t, lines[0], "Urgent")
}

// ============================================================
// buildPlanLines Tests
// ============================================================

func TestBuildPlanLines(t *testing.T) {
	t.Run("empty_plans", func(t *testing.T) {
		lines := buildPlanLines([]PlanSummary{})
		assert.Equal(t, 0, len(lines))
	})

	t.Run("single_plan", func(t *testing.T) {
		id := uuid.New()
		plans := []PlanSummary{
			{ID: id, Title: "Exam Prep", Type: "sprint", Progress: 65.5},
		}
		lines := buildPlanLines(plans)
		assert.Equal(t, 1, len(lines))
		assert.Contains(t, lines[0], id.String())
		assert.Contains(t, lines[0], "Exam Prep")
		assert.Contains(t, lines[0], "sprint")
	})
}

func TestBuildPlanLines_WithTargetDate(t *testing.T) {
	future := time.Now().Add(7 * 24 * time.Hour)
	plans := []PlanSummary{
		{ID: uuid.New(), Title: "Goal", Type: "long_term", TargetDate: &future, Progress: 30.0},
	}
	lines := buildPlanLines(plans)
	assert.Equal(t, 1, len(lines))
}

// ============================================================
// buildFocusLines Tests
// ============================================================

func TestBuildFocusLines(t *testing.T) {
	t.Run("basic_stats", func(t *testing.T) {
		stats := FocusStatsSummary{
			TotalSessionsToday:  3,
			TotalMinutesToday:   90,
			AverageFocusMinutes: 30,
			Streak:              5,
		}
		lines := buildFocusLines(stats)
		assert.Equal(t, 1, len(lines))
		assert.Contains(t, lines[0], "3")   // sessions
		assert.Contains(t, lines[0], "90")  // minutes
		assert.Contains(t, lines[0], "30")  // avg
		assert.Contains(t, lines[0], "5")   // streak
	})

	t.Run("with_last_session", func(t *testing.T) {
		ts := time.Now()
		stats := FocusStatsSummary{
			TotalSessionsToday:   1,
			TotalMinutesToday:    25,
			LastSessionTimestamp: &ts,
		}
		lines := buildFocusLines(stats)
		assert.Equal(t, 1, len(lines))
	})
}

// ============================================================
// buildProgressLines Tests
// ============================================================

func TestBuildProgressLines(t *testing.T) {
	t.Run("empty_progress", func(t *testing.T) {
		lines := buildProgressLines([]ProgressEvent{})
		assert.Equal(t, 0, len(lines))
	})

	t.Run("single_event", func(t *testing.T) {
		id := uuid.New()
		events := []ProgressEvent{
			{TaskID: id, TaskTitle: "Completed math exercise", CompletedAt: time.Now(), TimeSpentMin: 45},
		}
		lines := buildProgressLines(events)
		assert.Equal(t, 1, len(lines))
		assert.Contains(t, lines[0], id.String())
		assert.Contains(t, lines[0], "Completed math exercise")
	})

	t.Run("multiple_events", func(t *testing.T) {
		events := []ProgressEvent{
			{TaskID: uuid.New(), TaskTitle: "Task 1", CompletedAt: time.Now(), TimeSpentMin: 20},
			{TaskID: uuid.New(), TaskTitle: "Task 2", CompletedAt: time.Now(), TimeSpentMin: 35},
		}
		lines := buildProgressLines(events)
		assert.Equal(t, 2, len(lines))
	})
}

// ============================================================
// buildRealtimeVersions Tests
// ============================================================

func TestBuildRealtimeVersions(t *testing.T) {
	// We can't call this directly since it's on UserContextService,
	// but we can test via a nil service pointer since the function
	// only depends on the inputs
	s := &UserContextService{}
	tasks := []TaskSummary{{ID: uuid.New(), Title: "T1", Priority: 1}}
	plans := []PlanSummary{{ID: uuid.New(), Title: "P1"}}
	stats := FocusStatsSummary{TotalSessionsToday: 2}
	progress := []ProgressEvent{{TaskID: uuid.New(), TaskTitle: "E1"}}

	versions := s.buildRealtimeVersions(tasks, plans, stats, progress)
	assert.NotNil(t, versions)
	assert.Contains(t, versions, "tasks")
	assert.Contains(t, versions, "plans")
	assert.Contains(t, versions, "focus")
	assert.Contains(t, versions, "progress")
	assert.True(t, len(versions["tasks"]) > 0)
}

// ============================================================
// buildProfilePreferences Tests
// ============================================================

func TestBuildProfilePreferences(t *testing.T) {
	user := db.User{
		DepthPreference:     0.75,
		CuriosityPreference: 0.85,
		FlameLevel:          3,
		FlameBrightness:     0.9,
		PhotonBalance:       1500,
	}

	explicit := map[string]any{
		"timezone": "America/New_York",
		"language": "en-US",
		"theme":    "dark",
	}

	prefs := buildProfilePreferences(user, explicit)
	assert.Equal(t, "0.75", prefs["depth_preference"])
	assert.Equal(t, "0.85", prefs["curiosity_preference"])
	assert.Equal(t, "3", prefs["flame_level"])
	assert.Equal(t, "0.90", prefs["flame_brightness"])
	assert.Equal(t, "1500", prefs["photon_balance"])
	assert.Equal(t, "America/New_York", prefs["timezone"])
	assert.Equal(t, "en-US", prefs["language"])
	assert.Equal(t, "dark", prefs["theme"])
}

func TestBuildProfilePreferences_EmptyExplicit(t *testing.T) {
	user := db.User{
		DepthPreference:     0.5,
		CuriosityPreference: 0.5,
		FlameLevel:          1,
		FlameBrightness:     0.5,
		PhotonBalance:       100,
	}

	prefs := buildProfilePreferences(user, nil)
	assert.Equal(t, "0.50", prefs["depth_preference"])
	assert.Equal(t, "0.50", prefs["curiosity_preference"])
	// Only system prefs, no explicit
	_, hasTimezone := prefs["timezone"]
	assert.False(t, hasTimezone)
}

func TestBuildProfilePreferences_NilValueFiltered(t *testing.T) {
	user := db.User{DepthPreference: 0.5, CuriosityPreference: 0.5, FlameLevel: 1, FlameBrightness: 0.5, PhotonBalance: 0}
	explicit := map[string]any{
		"empty_string": "",
		"nil_value":    nil,
	}
	prefs := buildProfilePreferences(user, explicit)
	_, hasEmpty := prefs["empty_string"]
	assert.False(t, hasEmpty, "empty string should be filtered")
	_, hasNil := prefs["nil_value"]
	assert.False(t, hasNil, "nil value should be filtered")
}

// ============================================================
// TaskSummary / PlanSummary JSON Tests
// ============================================================

func TestTaskSummary_JSONRoundTrip(t *testing.T) {
	task := TaskSummary{
		ID:               uuid.New(),
		Title:            "Read chapter",
		Type:             "study",
		EstimatedMinutes: 30,
		Priority:         5,
	}
	data, err := json.Marshal(task)
	require.NoError(t, err)

	var parsed TaskSummary
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)
	assert.Equal(t, task.ID, parsed.ID)
	assert.Equal(t, task.Title, parsed.Title)
	assert.Equal(t, task.Type, parsed.Type)
	assert.Equal(t, task.EstimatedMinutes, parsed.EstimatedMinutes)
	assert.Equal(t, task.Priority, parsed.Priority)
}

func TestPlanSummary_JSONRoundTrip(t *testing.T) {
	targetDate := time.Now().Add(7 * 24 * time.Hour)
	plan := PlanSummary{
		ID:         uuid.New(),
		Title:      "Final Exam Prep",
		Type:       "sprint",
		TargetDate: &targetDate,
		Progress:   42.5,
	}
	data, err := json.Marshal(plan)
	require.NoError(t, err)

	var parsed PlanSummary
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)
	assert.Equal(t, plan.ID, parsed.ID)
	assert.Equal(t, plan.Title, parsed.Title)
	assert.Equal(t, plan.Progress, parsed.Progress)
}

func TestFocusStatsSummary_JSONRoundTrip(t *testing.T) {
	stats := FocusStatsSummary{
		TotalSessionsToday:  5,
		TotalMinutesToday:   120,
		AverageFocusMinutes: 24,
		Streak:              7,
	}
	data, err := json.Marshal(stats)
	require.NoError(t, err)

	var parsed FocusStatsSummary
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)
	assert.Equal(t, stats.TotalSessionsToday, parsed.TotalSessionsToday)
	assert.Equal(t, stats.Streak, parsed.Streak)
}

// ============================================================
// SemanticCache CanonicalizeScope Tests
// ============================================================

func TestSemanticCacheService_CanonicalizeScope(t *testing.T) {
	s := &SemanticCacheService{}

	tests := []struct {
		name   string
		scope  string
		expect string
	}{
		{"empty_returns_global", "", "global"},
		{"whitespace_returns_global", "  ", "global"},
		{"spaces_replaced", "my scope", "my_scope"},
		{"colons_replaced", "user:123", "user_123"},
		{"pipes_replaced", "user|session", "user_session"},
		{"lowered", "MyScope", "myscope"},
		{"mixed", "User:Session | Test", "user_session___test"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := s.canonicalizeScope(tt.scope)
			assert.Equal(t, tt.expect, got)
		})
	}
}

// ============================================================
// pgtype helpers for test construction
// ============================================================

func TestPgtypeHelpers(t *testing.T) {
	// Verify pgtype.Text behaves as expected in tests
	validText := pgtype.Text{String: "hello", Valid: true}
	assert.True(t, validText.Valid)
	assert.Equal(t, "hello", validText.String)

	invalidText := pgtype.Text{Valid: false}
	assert.False(t, invalidText.Valid)
}
