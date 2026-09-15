package service

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

// GAP-2: Unit tests for task_command.go.
// Tests that don't require a live DB cover validation logic and helpers.
// Integration tests (requiring DB) are skipped when INTEGRATION_TEST is not set.

func TestNilOrString(t *testing.T) {
	t.Run("nil pointer returns invalid pgtype.Text", func(t *testing.T) {
		result := nilOrString(nil)
		assert.False(t, result.Valid)
	})
	t.Run("non-nil pointer returns valid pgtype.Text", func(t *testing.T) {
		val := "hello"
		result := nilOrString(&val)
		assert.True(t, result.Valid)
		assert.Equal(t, "hello", result.String)
	})
}

func TestNilOrInt32(t *testing.T) {
	t.Run("nil pointer returns invalid pgtype.Int4", func(t *testing.T) {
		result := nilOrInt32(nil)
		assert.False(t, result.Valid)
	})
	t.Run("non-nil pointer returns valid pgtype.Int4", func(t *testing.T) {
		val := int32(42)
		result := nilOrInt32(&val)
		assert.True(t, result.Valid)
		assert.Equal(t, int32(42), result.Int32)
	})
}

func TestNilOrTime(t *testing.T) {
	t.Run("nil pointer returns invalid pgtype.Date", func(t *testing.T) {
		result := nilOrTime(nil)
		assert.False(t, result.Valid)
	})
	t.Run("non-nil pointer returns valid pgtype.Date", func(t *testing.T) {
		now := time.Now()
		result := nilOrTime(&now)
		assert.True(t, result.Valid)
		assert.Equal(t, now, result.Time)
	})
}

// TestCreateTaskRequiresTitle verifies the validation guard without a DB.
func TestCreateTaskRequiresTitle(t *testing.T) {
	svc := &TaskCommandService{} // nil pool — validation runs before any DB call
	_, err := svc.CreateTask(context.Background(), CreateTaskRequest{
		Title: "",
	})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "title cannot be empty")
}
