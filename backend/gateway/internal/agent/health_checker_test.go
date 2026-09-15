package agent

import (
	"errors"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func TestCircuitState_String(t *testing.T) {
	assert.Equal(t, "closed", CircuitClosed.String())
	assert.Equal(t, "open", CircuitOpen.String())
	assert.Equal(t, "half-open", CircuitHalfOpen.String())
	assert.Equal(t, "unknown", CircuitState(99).String())
}

func TestDefaultCircuitBreakerConfig(t *testing.T) {
	cfg := DefaultCircuitBreakerConfig()
	assert.Equal(t, 5, cfg.FailureThreshold)
	assert.Equal(t, 2, cfg.SuccessThreshold)
	assert.Equal(t, 30*time.Second, cfg.Timeout)
	assert.Equal(t, 3, cfg.HalfOpenRequests)
}

func TestNewAgentHealthChecker(t *testing.T) {
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
	assert.NotNil(t, h)
	assert.Equal(t, CircuitClosed, h.GetCircuitState())
	assert.False(t, h.IsHealthy()) // Initial state: never checked
}

func TestGetStatus_Initial(t *testing.T) {
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
	status := h.GetStatus()
	assert.False(t, status.IsHealthy)
	assert.Equal(t, CircuitClosed, status.CircuitState)
	assert.Equal(t, 0, status.Failures)
}

func TestAllowRequest_ClosedState(t *testing.T) {
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
	assert.True(t, h.AllowRequest()) // Closed → always allow
}

func TestAllowRequest_OpenState(t *testing.T) {
	cfg := CircuitBreakerConfig{
		FailureThreshold: 1,
		SuccessThreshold: 1,
		Timeout:          50 * time.Millisecond,
		HalfOpenRequests: 1,
	}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	// Force open
	h.ForceOpen()
	assert.False(t, h.AllowRequest()) // Open → block

	// Wait for timeout → should transition to half-open
	time.Sleep(100 * time.Millisecond)
	// Open→HalfOpen transition returns true without incrementing halfOpenCount
	assert.True(t, h.AllowRequest())  // HalfOpen probe (halfOpenCount still 0)
	assert.True(t, h.AllowRequest())  // HalfOpen → halfOpenCount=1=limit, still allows
	assert.False(t, h.AllowRequest()) // HalfOpen → halfOpenCount=1, limit reached
}

func TestCircuitBreaker_ClosedToOpen(t *testing.T) {
	cfg := CircuitBreakerConfig{
		FailureThreshold: 3,
		SuccessThreshold: 1,
		Timeout:          30 * time.Second,
		HalfOpenRequests: 1,
	}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	// Record failures up to threshold
	for i := 0; i < cfg.FailureThreshold; i++ {
		h.RecordRequestResult(status.Error(codes.Unavailable, "service down"))
	}

	assert.Equal(t, CircuitOpen, h.GetCircuitState())
	assert.False(t, h.IsHealthy())
}

func TestCircuitBreaker_HalfOpenToClosed(t *testing.T) {
	cfg := CircuitBreakerConfig{
		FailureThreshold: 1,
		SuccessThreshold: 2,
		Timeout:          50 * time.Millisecond,
		HalfOpenRequests: 2,
	}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	// Trip to open
	h.RecordRequestResult(status.Error(codes.Unavailable, "down"))
	assert.Equal(t, CircuitOpen, h.GetCircuitState())

	// Wait for timeout → transition to half-open
	time.Sleep(60 * time.Millisecond)
	h.AllowRequest() // Triggers transition to half-open
	assert.Equal(t, CircuitHalfOpen, h.GetCircuitState())

	// Record successes to close
	h.RecordRequestResult(nil) // success 1
	assert.Equal(t, CircuitHalfOpen, h.GetCircuitState())
	h.RecordRequestResult(nil) // success 2 → close
	assert.Equal(t, CircuitClosed, h.GetCircuitState())
}

func TestCircuitBreaker_HalfOpenToOpen(t *testing.T) {
	cfg := CircuitBreakerConfig{
		FailureThreshold: 1,
		SuccessThreshold: 2,
		Timeout:          50 * time.Millisecond,
		HalfOpenRequests: 2,
	}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	// Trip to open
	h.RecordRequestResult(status.Error(codes.Unavailable, "down"))
	time.Sleep(60 * time.Millisecond)
	h.AllowRequest() // → half-open
	assert.Equal(t, CircuitHalfOpen, h.GetCircuitState())

	// Any failure in half-open → back to open
	h.RecordRequestResult(status.Error(codes.DeadlineExceeded, "timeout"))
	assert.Equal(t, CircuitOpen, h.GetCircuitState())
}

func TestRecordRequestResult_NonFailureCodes(t *testing.T) {
	cfg := CircuitBreakerConfig{FailureThreshold: 1, SuccessThreshold: 1, Timeout: 30 * time.Second, HalfOpenRequests: 1}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	// These error codes should NOT count as failures
	h.RecordRequestResult(status.Error(codes.Canceled, "canceled"))
	assert.Equal(t, CircuitClosed, h.GetCircuitState())

	h.RecordRequestResult(status.Error(codes.NotFound, "not found"))
	assert.Equal(t, CircuitClosed, h.GetCircuitState())

	h.RecordRequestResult(status.Error(codes.PermissionDenied, "denied"))
	assert.Equal(t, CircuitClosed, h.GetCircuitState())
}

func TestRecordRequestResult_FailureCodes(t *testing.T) {
	cfg := CircuitBreakerConfig{FailureThreshold: 1, SuccessThreshold: 1, Timeout: 30 * time.Second, HalfOpenRequests: 1}

	// These codes should count as failures
	failureCodes := []codes.Code{codes.Unavailable, codes.DeadlineExceeded, codes.Internal, codes.ResourceExhausted, codes.Aborted}
	for _, code := range failureCodes {
		h2 := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)
		h2.RecordRequestResult(status.Error(code, "fail"))
		assert.Equal(t, CircuitOpen, h2.GetCircuitState(), "Expected open for code %v", code)
	}
}

func TestRecordRequestResult_NonStatusError(t *testing.T) {
	cfg := CircuitBreakerConfig{FailureThreshold: 1, SuccessThreshold: 1, Timeout: 30 * time.Second, HalfOpenRequests: 1}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	// Plain error (not gRPC status) should not affect circuit
	h.RecordRequestResult(errors.New("some error"))
	assert.Equal(t, CircuitClosed, h.GetCircuitState())
}

func TestForceOpen(t *testing.T) {
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
	h.ForceOpen()
	assert.Equal(t, CircuitOpen, h.GetCircuitState())
}

func TestForceClose(t *testing.T) {
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
	h.ForceOpen()
	h.ForceClose()
	assert.Equal(t, CircuitClosed, h.GetCircuitState())
}

func TestGetMetrics(t *testing.T) {
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
	metrics := h.GetMetrics()
	assert.False(t, metrics.IsHealthy)
	assert.Equal(t, "closed", metrics.CircuitState)
	assert.Equal(t, 0, metrics.FailureCount)
}

func TestGetMetrics_WithError(t *testing.T) {
	cfg := CircuitBreakerConfig{FailureThreshold: 1, SuccessThreshold: 1, Timeout: 30 * time.Second, HalfOpenRequests: 1}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)
	h.RecordRequestResult(status.Error(codes.Unavailable, "connection refused"))

	metrics := h.GetMetrics()
	assert.False(t, metrics.IsHealthy)
	assert.Equal(t, "open", metrics.CircuitState)
	// lastError is only set by check(), not by RecordRequestResult
}

func TestSetOnStateChange(t *testing.T) {
	cfg := CircuitBreakerConfig{FailureThreshold: 1, SuccessThreshold: 1, Timeout: 30 * time.Second, HalfOpenRequests: 1}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	type stateChange struct {
		old, new CircuitState
	}
	ch := make(chan stateChange, 1)
	h.SetOnStateChange(func(old, new CircuitState) {
		ch <- stateChange{old, new}
	})

	h.RecordRequestResult(status.Error(codes.Unavailable, "down"))

	select {
	case sc := <-ch:
		assert.Equal(t, CircuitClosed, sc.old)
		assert.Equal(t, CircuitOpen, sc.new)
	case <-time.After(time.Second):
		t.Fatal("state change callback not received")
	}
}

func TestIsHealthyConnectionState(t *testing.T) {
	// These tests need connectivity states but we can test with nil client
	// Just verify the checker handles nil client gracefully
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
	status := h.CheckNow()
	assert.False(t, status.IsHealthy) // nil client → unhealthy
}

func TestSuccessResetsFailures(t *testing.T) {
	cfg := CircuitBreakerConfig{FailureThreshold: 5, SuccessThreshold: 1, Timeout: 30 * time.Second, HalfOpenRequests: 1}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	// Record 4 failures (below threshold)
	for i := 0; i < 4; i++ {
		h.RecordRequestResult(status.Error(codes.Unavailable, "down"))
	}
	assert.Equal(t, CircuitClosed, h.GetCircuitState())

	// One success resets failure counter
	h.RecordRequestResult(nil)
	s := h.GetStatus()
	assert.Equal(t, 0, s.Failures)
	assert.Equal(t, CircuitClosed, s.CircuitState)
}

func TestHealthCheckerMetrics_Struct(t *testing.T) {
	m := HealthCheckerMetrics{
		IsHealthy:        true,
		CircuitState:     "closed",
		FailureCount:     0,
		LastCheckTime:    time.Now(),
		LastCheckLatency: 10 * time.Millisecond,
	}
	assert.True(t, m.IsHealthy)
	assert.Equal(t, "closed", m.CircuitState)
}
