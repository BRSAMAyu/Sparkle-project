package agent

import (
	"context"
	"log"
	"sync"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
)

// CircuitState represents the state of a circuit breaker
type CircuitState int

const (
	// CircuitClosed means requests flow normally
	CircuitClosed CircuitState = iota
	// CircuitOpen means requests are blocked
	CircuitOpen
	// CircuitHalfOpen means limited requests are allowed for probing
	CircuitHalfOpen
)

func (s CircuitState) String() string {
	switch s {
	case CircuitClosed:
		return "closed"
	case CircuitOpen:
		return "open"
	case CircuitHalfOpen:
		return "half-open"
	default:
		return "unknown"
	}
}

// CircuitBreakerConfig holds configuration for the circuit breaker
type CircuitBreakerConfig struct {
	// FailureThreshold is the number of consecutive failures to trip the circuit
	FailureThreshold int
	// SuccessThreshold is the number of consecutive successes to close the circuit
	SuccessThreshold int
	// Timeout is how long the circuit stays open before transitioning to half-open
	Timeout time.Duration
	// HalfOpenRequests is the number of requests allowed in half-open state
	HalfOpenRequests int
}

// DefaultCircuitBreakerConfig returns sensible defaults
func DefaultCircuitBreakerConfig() CircuitBreakerConfig {
	return CircuitBreakerConfig{
		FailureThreshold: 5,
		SuccessThreshold: 2,
		Timeout:          30 * time.Second,
		HalfOpenRequests: 3,
	}
}

// HealthStatus represents the health check result
type HealthStatus struct {
	IsHealthy   bool
	LastCheck   time.Time
	Latency     time.Duration
	LastError   error
	CircuitState CircuitState
	Failures    int
}

// AgentHealthChecker performs periodic health checks on the gRPC agent service
type AgentHealthChecker struct {
	client    *Client
	interval  time.Duration
	timeout   time.Duration
	cbConfig  CircuitBreakerConfig

	mu          sync.RWMutex
	lastCheck   time.Time
	isHealthy   bool
	latency     time.Duration
	lastError   error

	// Circuit breaker state
	failures      int
	successes     int
	lastFailure   time.Time
	circuitState  CircuitState
	halfOpenCount int

	// Health check client (dedicated connection for health checks)
	healthClient agentv1.AgentServiceClient

	// Callbacks
	onStateChange func(old, new CircuitState)

	// Control
	stopCh chan struct{}
	wg     sync.WaitGroup
}

// NewAgentHealthChecker creates a new health checker
func NewAgentHealthChecker(client *Client, interval, timeout time.Duration, cbConfig CircuitBreakerConfig) *AgentHealthChecker {
	return &AgentHealthChecker{
		client:       client,
		interval:     interval,
		timeout:      timeout,
		cbConfig:     cbConfig,
		circuitState: CircuitClosed,
		stopCh:       make(chan struct{}),
	}
}

// SetOnStateChange sets a callback for circuit state changes
func (h *AgentHealthChecker) SetOnStateChange(fn func(old, new CircuitState)) {
	h.onStateChange = fn
}

// Start begins periodic health checking
func (h *AgentHealthChecker) Start() {
	h.wg.Add(1)
	go h.run()
}

// Stop stops the health checker
func (h *AgentHealthChecker) Stop() {
	close(h.stopCh)
	h.wg.Wait()
}

func (h *AgentHealthChecker) run() {
	defer h.wg.Done()

	// Do initial check
	h.check()

	ticker := time.NewTicker(h.interval)
	defer ticker.Stop()

	for {
		select {
		case <-h.stopCh:
			return
		case <-ticker.C:
			h.check()
		}
	}
}

func (h *AgentHealthChecker) check() {
	ctx, cancel := context.WithTimeout(context.Background(), h.timeout)
	defer cancel()

	start := time.Now()

	// Perform a lightweight health check using a simple gRPC call
	// We use StreamChat with an empty message as a health probe
	// The Python backend should handle this gracefully
	var err error
	func() {
		defer func() {
			if r := recover(); r != nil {
				err = status.Error(codes.Internal, "health check panic")
			}
		}()

		// Create a health check request - minimal overhead
		// Using a simple ping-like approach with timeout context
		_, err = h.client.api.StreamChat(ctx, &agentv1.ChatRequest{
			UserId:    "__health_check__",
			SessionId: "__health_check__",
			Input:     &agentv1.ChatRequest_Message{Message: ""}, // Empty message for health check
		})
	}()

	latency := time.Since(start)

	h.mu.Lock()
	defer h.mu.Unlock()

	h.lastCheck = time.Now()
	h.latency = latency
	h.lastError = err

	if err != nil {
		// Health check failed
		h.isHealthy = false
		h.recordFailure()
		log.Printf("[AgentHealthChecker] Health check failed: %v (latency: %v)", err, latency)
	} else {
		// Health check succeeded
		h.isHealthy = true
		h.recordSuccess()
	}
}

func (h *AgentHealthChecker) recordFailure() {
	h.failures++
	h.successes = 0

	switch h.circuitState {
	case CircuitClosed:
		if h.failures >= h.cbConfig.FailureThreshold {
			h.transitionTo(CircuitOpen)
		}
	case CircuitHalfOpen:
		h.transitionTo(CircuitOpen)
	}
}

func (h *AgentHealthChecker) recordSuccess() {
	h.failures = 0
	h.successes++

	switch h.circuitState {
	case CircuitHalfOpen:
		if h.successes >= h.cbConfig.SuccessThreshold {
			h.transitionTo(CircuitClosed)
		}
	case CircuitOpen:
		// Should not happen, but handle gracefully
		if time.Since(h.lastFailure) > h.cbConfig.Timeout {
			h.transitionTo(CircuitHalfOpen)
		}
	}
}

func (h *AgentHealthChecker) transitionTo(newState CircuitState) {
	if h.circuitState == newState {
		return
	}

	oldState := h.circuitState
	h.circuitState = newState

	if newState == CircuitOpen {
		h.lastFailure = time.Now()
	} else if newState == CircuitHalfOpen {
		h.halfOpenCount = 0
		h.successes = 0
	} else if newState == CircuitClosed {
		h.failures = 0
		h.successes = 0
	}

	log.Printf("[AgentHealthChecker] Circuit breaker transitioned: %s -> %s", oldState, newState)

	if h.onStateChange != nil {
		go h.onStateChange(oldState, newState)
	}
}

// GetStatus returns the current health status
func (h *AgentHealthChecker) GetStatus() HealthStatus {
	h.mu.RLock()
	defer h.mu.RUnlock()

	return HealthStatus{
		IsHealthy:    h.isHealthy,
		LastCheck:    h.lastCheck,
		Latency:      h.latency,
		LastError:    h.lastError,
		CircuitState: h.circuitState,
		Failures:     h.failures,
	}
}

// IsHealthy returns true if the agent service is healthy
func (h *AgentHealthChecker) IsHealthy() bool {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.isHealthy
}

// GetCircuitState returns the current circuit breaker state
func (h *AgentHealthChecker) GetCircuitState() CircuitState {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.circuitState
}

// AllowRequest checks if a request should be allowed based on circuit state
func (h *AgentHealthChecker) AllowRequest() bool {
	h.mu.Lock()
	defer h.mu.Unlock()

	switch h.circuitState {
	case CircuitClosed:
		return true
	case CircuitOpen:
		// Check if we should transition to half-open
		if time.Since(h.lastFailure) > h.cbConfig.Timeout {
			h.transitionTo(CircuitHalfOpen)
			return true
		}
		return false
	case CircuitHalfOpen:
		// Allow limited requests in half-open state
		if h.halfOpenCount < h.cbConfig.HalfOpenRequests {
			h.halfOpenCount++
			return true
		}
		return false
	default:
		return false
	}
}

// RecordRequestResult records the result of a request for circuit breaker tracking
// This should be called after every request (success or failure)
func (h *AgentHealthChecker) RecordRequestResult(err error) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if err != nil {
		// Only count certain errors as failures
		st, ok := status.FromError(err)
		if !ok {
			return
		}

		switch st.Code() {
		case codes.Unavailable, codes.DeadlineExceeded, codes.Internal,
			codes.ResourceExhausted, codes.Aborted:
			h.isHealthy = false
			h.recordFailure()
		}
	} else {
		h.isHealthy = true
		h.recordSuccess()
	}
}

// ForceOpen forces the circuit to open (for manual intervention)
func (h *AgentHealthChecker) ForceOpen() {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.transitionTo(CircuitOpen)
	h.lastFailure = time.Now()
}

// ForceClose forces the circuit to close (for manual intervention)
func (h *AgentHealthChecker) ForceClose() {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.transitionTo(CircuitClosed)
	h.failures = 0
	h.successes = 0
}

// CheckNow performs an immediate health check (synchronous)
func (h *AgentHealthChecker) CheckNow() HealthStatus {
	h.check()
	return h.GetStatus()
}

// HealthCheckerMetrics returns metrics for monitoring
type HealthCheckerMetrics struct {
	IsHealthy       bool          `json:"is_healthy"`
	CircuitState    string        `json:"circuit_state"`
	FailureCount    int           `json:"failure_count"`
	LastCheckTime   time.Time     `json:"last_check_time"`
	LastCheckLatency time.Duration `json:"last_check_latency_ms"`
	LastError       string        `json:"last_error,omitempty"`
}

// GetMetrics returns current metrics for monitoring
func (h *AgentHealthChecker) GetMetrics() HealthCheckerMetrics {
	h.mu.RLock()
	defer h.mu.RUnlock()

	var lastErr string
	if h.lastError != nil {
		lastErr = h.lastError.Error()
	}

	return HealthCheckerMetrics{
		IsHealthy:       h.isHealthy,
		CircuitState:    h.circuitState.String(),
		FailureCount:    h.failures,
		LastCheckTime:   h.lastCheck,
		LastCheckLatency: h.latency,
		LastError:       lastErr,
	}
}

// GRPCHealthClient creates a dedicated health check client
// This can be used for standard gRPC health checking protocol
type GRPCHealthClient struct {
	conn   *grpc.ClientConn
	client agentv1.AgentServiceClient
}

// NewGRPCHealthClient creates a new health check client
func NewGRPCHealthClient(address string) (*GRPCHealthClient, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(ctx, address,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
		grpc.WithIdleTimeout(30*time.Second),
	)
	if err != nil {
		return nil, err
	}

	return &GRPCHealthClient{
		conn:   conn,
		client: agentv1.NewAgentServiceClient(conn),
	}, nil
}

// Close closes the health check client
func (c *GRPCHealthClient) Close() {
	if c.conn != nil {
		c.conn.Close()
	}
}

// Check performs a health check
func (c *GRPCHealthClient) Check(ctx context.Context) error {
	_, err := c.client.StreamChat(ctx, &agentv1.ChatRequest{
		UserId:    "__health_check__",
		SessionId: "__health_check__",
		Input:     &agentv1.ChatRequest_Message{Message: ""},
	})
	return err
}
