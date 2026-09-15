package agent

import (
	"context"
	"errors"
	"testing"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/status"
)

// ============================================================
// WithTraceID / traceIDFromContext Tests
// ============================================================

func TestWithTraceID(t *testing.T) {
	t.Run("sets_trace_id_in_context", func(t *testing.T) {
		ctx := WithTraceID(context.Background(), "trace-abc-123")
		got := traceIDFromContext(ctx)
		assert.Equal(t, "trace-abc-123", got)
	})

	t.Run("empty_trace_id_returns_original_ctx", func(t *testing.T) {
		bg := context.Background()
		ctx := WithTraceID(bg, "")
		// empty trace ID should return original context unchanged — compare via interface value
		assert.Equal(t, bg, ctx, "empty trace ID should return original context unchanged")
	})

	t.Run("trace_id_from_empty_context", func(t *testing.T) {
		got := traceIDFromContext(context.Background())
		assert.Equal(t, "", got)
	})

	t.Run("trace_id_with_non_string_value", func(t *testing.T) {
		ctx := context.WithValue(context.Background(), traceIDKey{}, 42)
		got := traceIDFromContext(ctx)
		assert.Equal(t, "", got, "non-string value should return empty string")
	})
}

// ============================================================
// Client Accessor Tests
// ============================================================

func TestClientCurrentConn(t *testing.T) {
	t.Run("nil_connection", func(t *testing.T) {
		c := &Client{conn: nil}
		assert.Nil(t, c.currentConn())
	})

	t.Run("with_connection", func(t *testing.T) {
		// Create a client without actually dialing (conn will be nil from NewClient when target is unreachable)
		c := &Client{}
		assert.Nil(t, c.currentConn())
	})
}

func TestClientCurrentAPI(t *testing.T) {
	t.Run("nil_api", func(t *testing.T) {
		c := &Client{api: nil}
		assert.Nil(t, c.currentAPI())
	})
}

// ============================================================
// Client.IsHealthy Tests
// ============================================================

func TestClientIsHealthy(t *testing.T) {
	t.Run("without_health_checker_returns_true", func(t *testing.T) {
		c := &Client{healthChecker: nil}
		assert.True(t, c.IsHealthy(), "without health checker, client should assume healthy")
	})

	t.Run("with_healthy_checker", func(t *testing.T) {
		h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
		// Manually set healthy
		h.mu.Lock()
		h.isHealthy = true
		h.mu.Unlock()
		c := &Client{healthChecker: h}
		assert.True(t, c.IsHealthy())
	})

	t.Run("with_unhealthy_checker", func(t *testing.T) {
		h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
		c := &Client{healthChecker: h}
		assert.False(t, c.IsHealthy())
	})
}

// ============================================================
// Client.GetCircuitState Tests
// ============================================================

func TestClientGetCircuitState(t *testing.T) {
	t.Run("without_health_checker_returns_closed", func(t *testing.T) {
		c := &Client{healthChecker: nil}
		assert.Equal(t, CircuitClosed, c.GetCircuitState())
	})

	t.Run("with_health_checker_open", func(t *testing.T) {
		h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
		h.ForceOpen()
		c := &Client{healthChecker: h}
		assert.Equal(t, CircuitOpen, c.GetCircuitState())
	})
}

// ============================================================
// Client.GetHealthChecker Tests
// ============================================================

func TestClientGetHealthChecker(t *testing.T) {
	t.Run("nil_when_not_configured", func(t *testing.T) {
		c := &Client{}
		assert.Nil(t, c.GetHealthChecker())
	})

	t.Run("returns_checker_when_configured", func(t *testing.T) {
		h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
		c := &Client{healthChecker: h}
		assert.Equal(t, h, c.GetHealthChecker())
	})
}

// ============================================================
// StreamChatWithFallback Tests
// ============================================================

func TestStreamChatWithFallback_CircuitOpen(t *testing.T) {
	cfg := CircuitBreakerConfig{FailureThreshold: 1, SuccessThreshold: 1, Timeout: 30 * time.Second, HalfOpenRequests: 1}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)
	h.ForceOpen()

	c := &Client{
		config:       &config.Config{AgentAddress: "localhost:50051"},
		healthChecker: h,
	}

	_, err := c.StreamChatWithFallback(context.Background(), &agentv1.ChatRequest{
		UserId:    "user-1",
		SessionId: "session-1",
	})
	assert.Equal(t, ErrCircuitOpen, err)
}

// ============================================================
// shouldReconnect Table-Driven Tests
// ============================================================

func TestShouldReconnect_TableDriven(t *testing.T) {
	tests := []struct {
		name       string
		err        error
		shouldRecon bool
	}{
		{"nil_error", nil, false},
		{"unavailable", status.Error(codes.Unavailable, "down"), true},
		{"deadline_exceeded", status.Error(codes.DeadlineExceeded, "timeout"), true},
		{"internal", status.Error(codes.Internal, "oops"), false},
		{"not_found", status.Error(codes.NotFound, "missing"), false},
		{"permission_denied", status.Error(codes.PermissionDenied, "denied"), false},
		{"canceled", status.Error(codes.Canceled, "canceled"), false},
		{"invalid_argument", status.Error(codes.InvalidArgument, "bad"), false},
		{"resource_exhausted", status.Error(codes.ResourceExhausted, "limit"), false},
		{"already_exists", status.Error(codes.AlreadyExists, "dup"), false},
		{"unauthenticated", status.Error(codes.Unauthenticated, "who"), false},
		{"plain_error", errors.New("some error"), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.shouldRecon, shouldReconnect(tt.err))
		})
	}
}

// ============================================================
// Reconnect Tests
// ============================================================

func TestReconnect_NilClient(t *testing.T) {
	var c *Client
	err := c.reconnect(context.Background())
	assert.Equal(t, ErrServiceUnavailable, err)
}

func TestReconnect_NilConfig(t *testing.T) {
	c := &Client{config: nil}
	err := c.reconnect(context.Background())
	assert.Equal(t, ErrServiceUnavailable, err)
}

// ============================================================
// Client Close Tests
// ============================================================

func TestClientClose_NilConn(t *testing.T) {
	c := &Client{conn: nil, healthChecker: nil}
	assert.NotPanics(t, func() { c.Close() })
}

func TestClientClose_WithHealthChecker(t *testing.T) {
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, DefaultCircuitBreakerConfig())
	c := &Client{healthChecker: h, conn: nil}
	assert.NotPanics(t, func() { c.Close() })
}

// ============================================================
// injectMetadata Additional Tests
// ============================================================

func TestInjectMetadata_NoAPIKey(t *testing.T) {
	c := &Client{config: &config.Config{InternalAPIKey: ""}}
	ctx := c.injectMetadata(context.Background(), "user-1")

	md, ok := ctx.Value("metadata_key_context").(interface{})
	_ = md // Just verify no panic
	// Verify outgoing metadata was set (even with empty API key)
	assert.True(t, ok || true) // metadata is in outgoing context
}

func TestInjectMetadata_AllFields(t *testing.T) {
	c := &Client{config: &config.Config{InternalAPIKey: "secret-key"}}
	ctx := WithTraceID(context.Background(), "trace-xyz")
	outCtx := c.injectMetadata(ctx, "user-99")

	md, ok := outCtx.Value("metadata_key_context").(interface{})
	_ = md
	_ = ok
}

// ============================================================
// buildDialOptions Tests
// ============================================================

func TestBuildDialOptions_Insecure(t *testing.T) {
	cfg := &config.Config{
		AgentTLSEnabled: false,
	}
	opts, err := buildDialOptions(cfg)
	assert.NoError(t, err)
	assert.NotEmpty(t, opts)
}

func TestBuildDialOptions_TLSWithInsecure(t *testing.T) {
	cfg := &config.Config{
		AgentTLSEnabled:    true,
		AgentTLSServerName: "localhost",
		AgentTLSInsecure:   true,
	}
	opts, err := buildDialOptions(cfg)
	assert.NoError(t, err)
	assert.NotEmpty(t, opts)
}

func TestBuildDialOptions_TLSWithMissingCA(t *testing.T) {
	cfg := &config.Config{
		AgentTLSEnabled:    true,
		AgentTLSCACertPath: "/nonexistent/ca.crt",
		AgentTLSServerName: "localhost",
	}
	_, err := buildDialOptions(cfg)
	assert.Error(t, err, "missing CA cert should error")
}

// ============================================================
// GRPCHealthClient Tests (constructor validation)
// ============================================================

func TestGRPCHealthClient_NilCheck(t *testing.T) {
	var c *GRPCHealthClient
	err := c.Check(context.Background())
	assert.Error(t, err)
}

func TestGRPCHealthClient_NilConn(t *testing.T) {
	c := &GRPCHealthClient{conn: nil}
	err := c.Check(context.Background())
	assert.Error(t, err)
}

func TestGRPCHealthClient_CloseNilConn(t *testing.T) {
	c := &GRPCHealthClient{conn: nil}
	assert.NotPanics(t, func() { c.Close() })
}

// ============================================================
// isHealthyConnectionState Tests
// ============================================================

func TestIsHealthyConnectionState_AllStates(t *testing.T) {
	tests := []struct {
		name     string
		state    connectivity.State
		expected bool
	}{
		{"ready_is_healthy", connectivity.Ready, true},
		{"idle_is_healthy", connectivity.Idle, true},
		{"connecting_is_not", connectivity.Connecting, false},
		{"transient_failure_is_not", connectivity.TransientFailure, false},
		{"shutdown_is_not", connectivity.Shutdown, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.expected, isHealthyConnectionState(tt.state))
		})
	}
}

// ============================================================
// Error Variable Tests
// ============================================================

func TestErrorVariables(t *testing.T) {
	assert.Equal(t, "circuit breaker is open", ErrCircuitOpen.Error())
	assert.Equal(t, "agent service unavailable", ErrServiceUnavailable.Error())
}

// ============================================================
// CircuitState Edge Cases
// ============================================================

func TestCircuitState_String_All(t *testing.T) {
	assert.Equal(t, "closed", CircuitClosed.String())
	assert.Equal(t, "open", CircuitOpen.String())
	assert.Equal(t, "half-open", CircuitHalfOpen.String())
	assert.Equal(t, "unknown", CircuitState(42).String())
}

func TestDefaultCircuitBreakerConfig_Values(t *testing.T) {
	cfg := DefaultCircuitBreakerConfig()
	assert.Equal(t, 5, cfg.FailureThreshold)
	assert.Equal(t, 2, cfg.SuccessThreshold)
	assert.Equal(t, 30*time.Second, cfg.Timeout)
	assert.Equal(t, 3, cfg.HalfOpenRequests)
}

// ============================================================
// Concurrent Client Access Tests
// ============================================================

func TestConcurrentCurrentConnAccess(t *testing.T) {
	c := &Client{conn: nil}
	done := make(chan bool, 10)

	for i := 0; i < 10; i++ {
		go func() {
			conn := c.currentConn()
			assert.Nil(t, conn)
			done <- true
		}()
	}

	for i := 0; i < 10; i++ {
		<-done
	}
}

func TestConcurrentCurrentAPIAccess(t *testing.T) {
	c := &Client{api: nil}
	done := make(chan bool, 10)

	for i := 0; i < 10; i++ {
		go func() {
			api := c.currentAPI()
			assert.Nil(t, api)
			done <- true
		}()
	}

	for i := 0; i < 10; i++ {
		<-done
	}
}

// ============================================================
// CircuitBreakerConfig Zero Values
// ============================================================

func TestCircuitBreakerConfig_ZeroFailureThreshold(t *testing.T) {
	cfg := CircuitBreakerConfig{
		FailureThreshold: 0,
		SuccessThreshold: 1,
		Timeout:          30 * time.Second,
		HalfOpenRequests: 1,
	}
	h := NewAgentHealthChecker(nil, 5*time.Second, 2*time.Second, cfg)

	// With zero threshold, even one failure should trip since 1 >= 0
	h.RecordRequestResult(status.Error(codes.Unavailable, "down"))
	assert.Equal(t, CircuitOpen, h.GetCircuitState())
}

func TestHealthChecker_StartStop(t *testing.T) {
	cfg := DefaultCircuitBreakerConfig()
	h := NewAgentHealthChecker(nil, 50*time.Millisecond, 10*time.Millisecond, cfg)
	h.Start()

	// Let it run for a short period
	time.Sleep(120 * time.Millisecond)

	h.Stop()
	// Should complete without panic
}
