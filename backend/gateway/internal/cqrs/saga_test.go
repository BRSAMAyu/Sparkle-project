package cqrs

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

type mockEventBus struct {
	published []event.DomainEvent
	mu        sync.Mutex
}

func (m *mockEventBus) Publish(_ context.Context, evt event.DomainEvent) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.published = append(m.published, evt)
	return nil
}

func (m *mockEventBus) PublishBatch(_ context.Context, evts []event.DomainEvent) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.published = append(m.published, evts...)
	return nil
}

func (m *mockEventBus) Close() error { return nil }

func (m *mockEventBus) getPublished() []event.DomainEvent {
	m.mu.Lock()
	defer m.mu.Unlock()
	return append([]event.DomainEvent{}, m.published...)
}

// newTestLogger creates a discard logger for tests.
func newTestLogger() *zap.Logger {
	return zap.NewNop()
}

// ---------------------------------------------------------------------------
// SagaStatus tests
// ---------------------------------------------------------------------------

func TestSagaStatus_IsTerminal(t *testing.T) {
	tests := []struct {
		status   SagaStatus
		expected bool
	}{
		{SagaStatusPending, false},
		{SagaStatusRunning, false},
		{SagaStatusCompensating, false},
		{SagaStatusCompleted, true},
		{SagaStatusCompensated, true},
		{SagaStatusFailed, true},
	}
	for _, tt := range tests {
		t.Run(string(tt.status), func(t *testing.T) {
			assert.Equal(t, tt.expected, tt.status.IsTerminal())
		})
	}
}

// ---------------------------------------------------------------------------
// StepFunc adapter tests
// ---------------------------------------------------------------------------

func TestStepFunc_Name(t *testing.T) {
	sf := StepFunc{StepName: "test_step"}
	assert.Equal(t, "test_step", sf.Name())
}

func TestStepFunc_Execute(t *testing.T) {
	called := false
	sf := StepFunc{
		StepName: "step",
		ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
			called = true
			return map[string]interface{}{"result": "ok"}, nil
		},
	}
	out, err := sf.Execute(context.Background(), nil)
	assert.NoError(t, err)
	assert.True(t, called)
	assert.Equal(t, "ok", out["result"])
}

func TestStepFunc_Compensate_Nil(t *testing.T) {
	sf := StepFunc{StepName: "step"}
	err := sf.Compensate(context.Background(), nil)
	assert.NoError(t, err)
}

func TestStepFunc_Compensate_Custom(t *testing.T) {
	called := false
	sf := StepFunc{
		StepName: "step",
		CompensateFn: func(_ context.Context, _ map[string]interface{}) error {
			called = true
			return nil
		},
	}
	err := sf.Compensate(context.Background(), nil)
	assert.NoError(t, err)
	assert.True(t, called)
}

// ---------------------------------------------------------------------------
// RetryPolicy tests
// ---------------------------------------------------------------------------

func TestDefaultRetryPolicy(t *testing.T) {
	p := DefaultRetryPolicy()
	assert.Equal(t, 3, p.MaxRetries)
	assert.Equal(t, 100*time.Millisecond, p.InitialBackoff)
	assert.Equal(t, 5*time.Second, p.MaxBackoff)
	assert.Equal(t, 2.0, p.Multiplier)
}

// ---------------------------------------------------------------------------
// Saga Definition constructors
// ---------------------------------------------------------------------------

func TestNewTaskCreateSaga(t *testing.T) {
	s1 := StepFunc{StepName: "create_task"}
	s2 := StepFunc{StepName: "notify"}
	s3 := StepFunc{StepName: "crdt_sync"}

	def := NewTaskCreateSaga(s1, s2, s3)
	assert.Equal(t, "task_create_saga", def.Name)
	assert.Len(t, def.Steps, 3)
	assert.Equal(t, "create_task", def.Steps[0].Name())
	assert.Equal(t, "notify", def.Steps[1].Name())
	assert.Equal(t, "crdt_sync", def.Steps[2].Name())
}

func TestNewSourceUploadSaga(t *testing.T) {
	def := NewSourceUploadSaga(
		StepFunc{StepName: "upload"},
		StepFunc{StepName: "parse"},
		StepFunc{StepName: "mount"},
	)
	assert.Equal(t, "source_upload_saga", def.Name)
	assert.Len(t, def.Steps, 3)
}

func TestNewExperimentPromotionSaga(t *testing.T) {
	def := NewExperimentPromotionSaga(
		StepFunc{StepName: "promote"},
		StepFunc{StepName: "notify"},
		StepFunc{StepName: "audit"},
	)
	assert.Equal(t, "experiment_promotion_saga", def.Name)
	assert.Len(t, def.Steps, 3)
}

func TestNewSkillPublishSaga(t *testing.T) {
	def := NewSkillPublishSaga(
		StepFunc{StepName: "publish"},
		StepFunc{StepName: "marketplace"},
		StepFunc{StepName: "notify"},
	)
	assert.Equal(t, "skill_publish_saga", def.Name)
	assert.Len(t, def.Steps, 3)
}

// ---------------------------------------------------------------------------
// copyMap tests
// ---------------------------------------------------------------------------

func TestCopyMap(t *testing.T) {
	original := map[string]interface{}{
		"key1": "value1",
		"key2": 42,
	}
	copied := copyMap(original)

	assert.Equal(t, original, copied)
	copied["key1"] = "modified"
	assert.NotEqual(t, original["key1"], copied["key1"])
}

// ---------------------------------------------------------------------------
// Coordinator tests (in-memory, no DB)
// ---------------------------------------------------------------------------

func newTestCoordinator(bus event.EventBus) *SagaCoordinator {
	mr, _ := miniredis.Run()
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	_ = rdb // not used by coordinator directly but satisfies constructor

	return &SagaCoordinator{
		pool:     nil, // nil pool is fine for in-memory tests
		uow:      nil,
		eventBus: bus,
		logger:   newTestLogger(),
		registry: make(map[string]*SagaDefinition),
	}
}

func TestCoordinator_Register(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	def := &SagaDefinition{
		Name:  "test_saga",
		Steps: []SagaStep{StepFunc{StepName: "step1"}},
	}
	coord.Register(def)

	assert.Contains(t, coord.registry, "test_saga")
}

func TestCoordinator_Execute_UnknownSaga(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	_, err := coord.Execute(context.Background(), "nonexistent", nil)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "saga definition not found")
}

func TestCoordinator_Execute_AllStepsSucceed(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	var execOrder []string
	s1 := StepFunc{
		StepName: "step_a",
		ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
			execOrder = append(execOrder, "a")
			return map[string]interface{}{"a_done": true}, nil
		},
	}
	s2 := StepFunc{
		StepName: "step_b",
		ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
			execOrder = append(execOrder, "b")
			assert.Equal(t, true, data["a_done"])
			return map[string]interface{}{"b_done": true}, nil
		},
	}
	s3 := StepFunc{
		StepName: "step_c",
		ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
			execOrder = append(execOrder, "c")
			assert.Equal(t, true, data["b_done"])
			return map[string]interface{}{"c_done": true}, nil
		},
	}

	def := &SagaDefinition{
		Name:        "happy_path_saga",
		Steps:       []SagaStep{s1, s2, s3},
		RetryPolicy: RetryPolicy{MaxRetries: 0}, // will be set to default
	}
	coord.Register(def)

	inst, err := coord.Execute(context.Background(), "happy_path_saga", map[string]interface{}{"initial": true})
	require.NoError(t, err)
	assert.Equal(t, SagaStatusCompleted, inst.Status)
	assert.Equal(t, []string{"a", "b", "c"}, execOrder)
	assert.Len(t, inst.StepResults, 3)
	for _, sr := range inst.StepResults {
		assert.Equal(t, "completed", sr.Status)
	}

	// Verify saga event published.
	published := bus.getPublished()
	assert.Len(t, published, 1)
	assert.Equal(t, event.EventType("saga.completed"), published[0].Type)
}

func TestCoordinator_Execute_Step2Fails_Compensates1(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	var compensateOrder []string
	s1 := StepFunc{
		StepName: "step_a",
		ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
			return map[string]interface{}{"a_done": true}, nil
		},
		CompensateFn: func(_ context.Context, _ map[string]interface{}) error {
			compensateOrder = append(compensateOrder, "compensate_a")
			return nil
		},
	}
	s2 := StepFunc{
		StepName: "step_b",
		ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
			return nil, errors.New("step_b failed")
		},
	}

	def := &SagaDefinition{
		Name:        "failure_saga",
		Steps:       []SagaStep{s1, s2},
		RetryPolicy: RetryPolicy{MaxRetries: 0},
	}
	coord.Register(def)

	inst, err := coord.Execute(context.Background(), "failure_saga", nil)
	assert.Error(t, err)
	assert.Equal(t, SagaStatusCompensated, inst.Status)
	assert.Equal(t, []string{"compensate_a"}, compensateOrder)
	assert.Len(t, inst.StepResults, 2)
	assert.Equal(t, "compensated", inst.StepResults[0].Status) // step 1 compensated
	assert.Equal(t, "failed", inst.StepResults[1].Status)      // step 2 failed execution
}

func TestCoordinator_Execute_Step3Fails_Compensates1And2(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	var compensateOrder []string
	var mu sync.Mutex

	makeStep := func(name string, fail bool) StepFunc {
		return StepFunc{
			StepName: name,
			ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
				if fail {
					return nil, fmt.Errorf("%s failed", name)
				}
				return map[string]interface{}{name + "_done": true}, nil
			},
			CompensateFn: func(_ context.Context, _ map[string]interface{}) error {
				mu.Lock()
				compensateOrder = append(compensateOrder, "compensate_"+name)
				mu.Unlock()
				return nil
			},
		}
	}

	def := &SagaDefinition{
		Name:        "three_step_failure",
		Steps:       []SagaStep{makeStep("s1", false), makeStep("s2", false), makeStep("s3", true)},
		RetryPolicy: RetryPolicy{MaxRetries: 0},
	}
	coord.Register(def)

	inst, err := coord.Execute(context.Background(), "three_step_failure", nil)
	assert.Error(t, err)
	assert.Equal(t, SagaStatusCompensated, inst.Status)

	mu.Lock()
	assert.Equal(t, []string{"compensate_s2", "compensate_s1"}, compensateOrder)
	mu.Unlock()
}

func TestCoordinator_Execute_CompensationFailure_ResultsInFailed(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	s1 := StepFunc{
		StepName: "step_a",
		ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
			return nil, nil
		},
		CompensateFn: func(_ context.Context, _ map[string]interface{}) error {
			return errors.New("compensation failed")
		},
	}
	s2 := StepFunc{
		StepName: "step_b",
		ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
			return nil, errors.New("step_b failed")
		},
	}

	def := &SagaDefinition{
		Name:        "compensation_failure",
		Steps:       []SagaStep{s1, s2},
		RetryPolicy: RetryPolicy{MaxRetries: 0},
	}
	coord.Register(def)

	inst, err := coord.Execute(context.Background(), "compensation_failure", nil)
	assert.Error(t, err)
	assert.Equal(t, SagaStatusFailed, inst.Status)

	// Step 1 was compensated but it failed.
	assert.Equal(t, "compensation_failed", inst.StepResults[0].Status)
}

func TestCoordinator_Execute_RetryLogic(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	var attempts atomic.Int32
	s1 := StepFunc{
		StepName: "flaky_step",
		ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
			n := attempts.Add(1)
			if n < 3 {
				return nil, errors.New("transient error")
			}
			return map[string]interface{}{"success": true}, nil
		},
	}

	def := &SagaDefinition{
		Name:  "retry_saga",
		Steps: []SagaStep{s1},
		RetryPolicy: RetryPolicy{
			MaxRetries:     3,
			InitialBackoff: 10 * time.Millisecond,
			MaxBackoff:     50 * time.Millisecond,
			Multiplier:     2.0,
		},
	}
	coord.Register(def)

	inst, err := coord.Execute(context.Background(), "retry_saga", nil)
	require.NoError(t, err)
	assert.Equal(t, SagaStatusCompleted, inst.Status)
	assert.Equal(t, int32(3), attempts.Load())
}

func TestCoordinator_Execute_RetryExhausted(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	s1 := StepFunc{
		StepName: "always_fail",
		ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
			return nil, errors.New("permanent error")
		},
	}

	def := &SagaDefinition{
		Name:  "exhausted_saga",
		Steps: []SagaStep{s1},
		RetryPolicy: RetryPolicy{
			MaxRetries:     2,
			InitialBackoff: 5 * time.Millisecond,
			MaxBackoff:     20 * time.Millisecond,
			Multiplier:     2.0,
		},
	}
	coord.Register(def)

	inst, err := coord.Execute(context.Background(), "exhausted_saga", nil)
	assert.Error(t, err)
	// No completed steps, so compensation runs on 0..-1 which is a no-op.
	// Status should be compensated (allCompensated([]) == true).
	assert.Equal(t, SagaStatusCompensated, inst.Status)
}

func TestCoordinator_Execute_ContextCancelled(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // cancel immediately

	s1 := StepFunc{
		StepName: "cancelled_step",
		ExecuteFn: func(ctx context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
			return nil, ctx.Err()
		},
	}

	def := &SagaDefinition{
		Name:  "cancel_saga",
		Steps: []SagaStep{s1},
		RetryPolicy: RetryPolicy{
			MaxRetries:     1,
			InitialBackoff: 5 * time.Millisecond,
			MaxBackoff:     20 * time.Millisecond,
			Multiplier:     2.0,
		},
	}
	coord.Register(def)

	_, err := coord.Execute(ctx, "cancel_saga", nil)
	assert.Error(t, err)
}

// ---------------------------------------------------------------------------
// Cross-service flow simulation tests
// ---------------------------------------------------------------------------

func TestTaskCreateSaga_Simulation(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	var (
		taskCreated     bool
		notifSent       bool
		compensateOrder []string
		mu              sync.Mutex
	)

	def := NewTaskCreateSaga(
		StepFunc{
			StepName: "create_task",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				taskCreated = true
				return map[string]interface{}{"task_id": "task-123"}, nil
			},
			CompensateFn: func(_ context.Context, _ map[string]interface{}) error {
				mu.Lock()
				compensateOrder = append(compensateOrder, "delete_task")
				mu.Unlock()
				taskCreated = false
				return nil
			},
		},
		StepFunc{
			StepName: "send_notification",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				assert.Equal(t, "task-123", data["task_id"])
				notifSent = true
				return map[string]interface{}{"notif_id": "notif-456"}, nil
			},
			CompensateFn: func(_ context.Context, _ map[string]interface{}) error {
				mu.Lock()
				compensateOrder = append(compensateOrder, "cancel_notif")
				mu.Unlock()
				notifSent = false
				return nil
			},
		},
		StepFunc{
			StepName: "crdt_sync",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				// Simulate CRDT sync failure.
				return nil, errors.New("CRDT sync timeout")
			},
			CompensateFn: func(_ context.Context, _ map[string]interface{}) error {
				mu.Lock()
				compensateOrder = append(compensateOrder, "undo_crdt")
				mu.Unlock()
				return nil
			},
		},
	)
	def.RetryPolicy = RetryPolicy{MaxRetries: 1, InitialBackoff: 5 * time.Millisecond, MaxBackoff: 20 * time.Millisecond, Multiplier: 2}

	coord.Register(def)
	inst, err := coord.Execute(context.Background(), "task_create_saga", map[string]interface{}{
		"title":    "Study math",
		"user_id":  "user-789",
	})

	// Step 3 failed, so compensation should have run for steps 1 and 2.
	assert.Error(t, err)
	assert.Equal(t, SagaStatusCompensated, inst.Status)
	assert.False(t, taskCreated)  // compensated back
	assert.False(t, notifSent)    // compensated back

	mu.Lock()
	assert.Equal(t, []string{"cancel_notif", "delete_task"}, compensateOrder)
	mu.Unlock()
}

func TestSourceUploadSaga_Simulation(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	def := NewSourceUploadSaga(
		StepFunc{
			StepName: "upload_source",
			ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
				return map[string]interface{}{"source_id": "src-1", "file_path": "/uploads/a.pdf"}, nil
			},
		},
		StepFunc{
			StepName: "parse_content",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				assert.Equal(t, "src-1", data["source_id"])
				return map[string]interface{}{"parsed_nodes": 5}, nil
			},
		},
		StepFunc{
			StepName: "mount_nodes",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				assert.Equal(t, 5, data["parsed_nodes"])
				return map[string]interface{}{"mounted": true}, nil
			},
		},
	)
	def.RetryPolicy = RetryPolicy{MaxRetries: 2, InitialBackoff: 5 * time.Millisecond, MaxBackoff: 20 * time.Millisecond, Multiplier: 2}

	coord.Register(def)
	inst, err := coord.Execute(context.Background(), "source_upload_saga", map[string]interface{}{
		"filename": "textbook.pdf",
	})
	require.NoError(t, err)
	assert.Equal(t, SagaStatusCompleted, inst.Status)
	assert.Len(t, inst.StepResults, 3)
}

func TestExperimentPromotionSaga_Simulation(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	def := NewExperimentPromotionSaga(
		StepFunc{
			StepName: "promote_experiment",
			ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
				return map[string]interface{}{"experiment_id": "exp-1", "new_stage": "safe_live"}, nil
			},
		},
		StepFunc{
			StepName: "notify_stakeholders",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				assert.Equal(t, "safe_live", data["new_stage"])
				return map[string]interface{}{"notified": true}, nil
			},
		},
		StepFunc{
			StepName: "write_audit",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				assert.Equal(t, true, data["notified"])
				return map[string]interface{}{"audit_id": "aud-1"}, nil
			},
		},
	)
	def.RetryPolicy = RetryPolicy{MaxRetries: 2, InitialBackoff: 5 * time.Millisecond, MaxBackoff: 20 * time.Millisecond, Multiplier: 2}

	coord.Register(def)
	inst, err := coord.Execute(context.Background(), "experiment_promotion_saga", nil)
	require.NoError(t, err)
	assert.Equal(t, SagaStatusCompleted, inst.Status)
}

func TestSkillPublishSaga_Simulation(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	def := NewSkillPublishSaga(
		StepFunc{
			StepName: "publish_skill",
			ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
				return map[string]interface{}{"skill_id": "sk-1", "version": "2.0"}, nil
			},
		},
		StepFunc{
			StepName: "register_marketplace",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				assert.Equal(t, "sk-1", data["skill_id"])
				return map[string]interface{}{"listing_id": "list-1"}, nil
			},
		},
		StepFunc{
			StepName: "send_notification",
			ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
				assert.Equal(t, "list-1", data["listing_id"])
				return map[string]interface{}{"done": true}, nil
			},
		},
	)
	def.RetryPolicy = RetryPolicy{MaxRetries: 2, InitialBackoff: 5 * time.Millisecond, MaxBackoff: 20 * time.Millisecond, Multiplier: 2}

	coord.Register(def)
	inst, err := coord.Execute(context.Background(), "skill_publish_saga", nil)
	require.NoError(t, err)
	assert.Equal(t, SagaStatusCompleted, inst.Status)
}

// ---------------------------------------------------------------------------
// Saga instance ID uniqueness
// ---------------------------------------------------------------------------

func TestSagaInstance_UniqueID(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	def := &SagaDefinition{
		Name:  "id_test",
		Steps: []SagaStep{StepFunc{StepName: "noop", ExecuteFn: func(_ context.Context, d map[string]interface{}) (map[string]interface{}, error) { return d, nil }}},
	}
	coord.Register(def)

	inst1, _ := coord.Execute(context.Background(), "id_test", nil)
	inst2, _ := coord.Execute(context.Background(), "id_test", nil)
	assert.NotEqual(t, inst1.ID, inst2.ID)
}

// ---------------------------------------------------------------------------
// Saga correlation ID
// ---------------------------------------------------------------------------

func TestSagaInstance_CorrelationID(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	def := &SagaDefinition{
		Name:  "corr_test",
		Steps: []SagaStep{StepFunc{StepName: "noop", ExecuteFn: func(_ context.Context, d map[string]interface{}) (map[string]interface{}, error) { return d, nil }}},
	}
	coord.Register(def)

	inst, _ := coord.Execute(context.Background(), "corr_test", nil)
	assert.NotEmpty(t, inst.CorrelationID)
	_, err := uuid.Parse(inst.CorrelationID)
	assert.NoError(t, err)
}

// ---------------------------------------------------------------------------
// Data flow between steps
// ---------------------------------------------------------------------------

func TestCoordinator_DataFlowsBetweenSteps(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	def := &SagaDefinition{
		Name: "data_flow_test",
		Steps: []SagaStep{
			StepFunc{
				StepName: "producer",
				ExecuteFn: func(_ context.Context, _ map[string]interface{}) (map[string]interface{}, error) {
					return map[string]interface{}{
						"user_id":  "u-1",
						"task_ids": []string{"t-1", "t-2"},
					}, nil
				},
			},
			StepFunc{
				StepName: "consumer",
				ExecuteFn: func(_ context.Context, data map[string]interface{}) (map[string]interface{}, error) {
					assert.Equal(t, "u-1", data["user_id"])
					taskIDs, ok := data["task_ids"].([]string)
					if !ok {
						// JSON deserialization may produce []interface{}
						raw, _ := data["task_ids"].([]interface{})
						taskIDs = make([]string, len(raw))
						for i, v := range raw {
							taskIDs[i] = v.(string)
						}
					}
					assert.Len(t, taskIDs, 2)
					return map[string]interface{}{"processed": len(taskIDs)}, nil
				},
			},
		},
	}
	coord.Register(def)

	inst, err := coord.Execute(context.Background(), "data_flow_test", nil)
	require.NoError(t, err)
	assert.Equal(t, SagaStatusCompleted, inst.Status)
}

// ---------------------------------------------------------------------------
// Multiple saga types registered concurrently
// ---------------------------------------------------------------------------

func TestCoordinator_ConcurrentRegistration(t *testing.T) {
	bus := &mockEventBus{}
	coord := newTestCoordinator(bus)

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			name := fmt.Sprintf("saga_%d", idx)
			coord.Register(&SagaDefinition{
				Name:  name,
				Steps: []SagaStep{StepFunc{StepName: "step"}},
			})
		}(i)
	}
	wg.Wait()

	coord.mu.RLock()
	assert.Len(t, coord.registry, 100)
	coord.mu.RUnlock()
}
