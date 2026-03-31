package agent

import (
	"context"
	"crypto/tls"
	"errors"
	"log"
	"sync"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

// ErrCircuitOpen is returned when the circuit breaker is open
var ErrCircuitOpen = errors.New("circuit breaker is open")

// ErrServiceUnavailable is returned when the agent service is unavailable
var ErrServiceUnavailable = errors.New("agent service unavailable")

type Client struct {
	conn   *grpc.ClientConn
	api    agentv1.AgentServiceClient
	config *config.Config
	connMu sync.RWMutex

	reconnectMu sync.Mutex
	dialOptions []grpc.DialOption

	// Health checker (optional)
	healthChecker *AgentHealthChecker
}

type traceIDKey struct{}

func WithTraceID(ctx context.Context, traceID string) context.Context {
	if traceID == "" {
		return ctx
	}
	return context.WithValue(ctx, traceIDKey{}, traceID)
}

func traceIDFromContext(ctx context.Context) string {
	if value := ctx.Value(traceIDKey{}); value != nil {
		if traceID, ok := value.(string); ok {
			return traceID
		}
	}
	return ""
}

func NewClient(cfg *config.Config) (*Client, error) {
	timeoutSeconds := cfg.GRPCTimeoutSeconds
	if timeoutSeconds <= 0 {
		timeoutSeconds = 5
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSeconds)*time.Second)
	defer cancel()

	dialOptions, err := buildDialOptions(cfg)
	if err != nil {
		return nil, err
	}

	conn, err := grpc.DialContext(ctx, cfg.AgentAddress, dialOptions...)
	if err != nil {
		log.Printf("Failed to connect to agent service at %s: %v", cfg.AgentAddress, err)
		return nil, err
	}

	client := agentv1.NewAgentServiceClient(conn)
	return &Client{
		conn:        conn,
		api:         client,
		config:      cfg,
		dialOptions: dialOptions,
	}, nil
}

func buildDialOptions(cfg *config.Config) ([]grpc.DialOption, error) {
	creds := insecure.NewCredentials()
	if cfg.AgentTLSEnabled {
		if cfg.AgentTLSCACertPath != "" {
			tlsCreds, err := credentials.NewClientTLSFromFile(cfg.AgentTLSCACertPath, cfg.AgentTLSServerName)
			if err != nil {
				log.Printf("Failed to load agent TLS CA cert: %v", err)
				return nil, err
			}
			creds = tlsCreds
		} else {
			creds = credentials.NewTLS(&tls.Config{
				ServerName:         cfg.AgentTLSServerName,
				InsecureSkipVerify: cfg.AgentTLSInsecure,
			})
		}
	}

	// Retry policy configuration
	retryPolicy := `{
		"methodConfig": [{
			"name": [{"service": "agent.v1.AgentService"}],
			"waitForReady": true,
			"retryPolicy": {
				"MaxAttempts": 4,
				"InitialBackoff": "0.5s",
				"MaxBackoff": "10s",
				"BackoffMultiplier": 2.0,
				"RetryableStatusCodes": ["UNAVAILABLE", "RESOURCE_EXHAUSTED"]
			}
		}]
	}`

	return []grpc.DialOption{
		grpc.WithTransportCredentials(creds),
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
		grpc.WithDefaultServiceConfig(retryPolicy),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                20 * time.Second,
			Timeout:             10 * time.Second,
			PermitWithoutStream: true,
		}),
		grpc.WithBlock(),
	}, nil
}

func (c *Client) currentConn() *grpc.ClientConn {
	c.connMu.RLock()
	defer c.connMu.RUnlock()
	return c.conn
}

func (c *Client) currentAPI() agentv1.AgentServiceClient {
	c.connMu.RLock()
	defer c.connMu.RUnlock()
	return c.api
}

func (c *Client) reconnect(ctx context.Context) error {
	if c == nil || c.config == nil {
		return ErrServiceUnavailable
	}

	c.reconnectMu.Lock()
	defer c.reconnectMu.Unlock()

	if conn := c.currentConn(); conn != nil {
		state := conn.GetState()
		if state == connectivity.Ready || state == connectivity.Idle {
			return nil
		}
	}

	timeoutSeconds := c.config.GRPCTimeoutSeconds
	if timeoutSeconds <= 0 {
		timeoutSeconds = 5
	}

	reconnectCtx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSeconds)*time.Second)
	defer cancel()

	newConn, err := grpc.DialContext(reconnectCtx, c.config.AgentAddress, c.dialOptions...)
	if err != nil {
		log.Printf("[AgentClient] Reconnect to %s failed: %v", c.config.AgentAddress, err)
		return err
	}

	c.connMu.Lock()
	oldConn := c.conn
	c.conn = newConn
	c.api = agentv1.NewAgentServiceClient(newConn)
	c.connMu.Unlock()

	if oldConn != nil {
		_ = oldConn.Close()
	}

	log.Printf("[AgentClient] Reconnected to agent service at %s", c.config.AgentAddress)
	return nil
}

func shouldReconnect(err error) bool {
	if err == nil {
		return false
	}

	st, ok := status.FromError(err)
	if !ok {
		return false
	}

	switch st.Code() {
	case codes.Unavailable, codes.DeadlineExceeded:
		return true
	default:
		return false
	}
}

// NewClientWithHealthCheck creates a client with health checking enabled
func NewClientWithHealthCheck(cfg *config.Config, healthCheckInterval, healthCheckTimeout time.Duration) (*Client, error) {
	c, err := NewClient(cfg)
	if err != nil {
		return nil, err
	}

	// Setup health checker with circuit breaker
	cbConfig := DefaultCircuitBreakerConfig()
	if cfg.CircuitBreakerThreshold > 0 {
		cbConfig.FailureThreshold = cfg.CircuitBreakerThreshold
	}

	c.healthChecker = NewAgentHealthChecker(c, healthCheckInterval, healthCheckTimeout, cbConfig)
	c.healthChecker.Start()

	log.Printf("[AgentClient] Health checker started (interval: %v, timeout: %v)", healthCheckInterval, healthCheckTimeout)

	return c, nil
}

func (c *Client) Close() {
	if c.healthChecker != nil {
		c.healthChecker.Stop()
	}
	if conn := c.currentConn(); conn != nil {
		conn.Close()
	}
}

// GetHealthChecker returns the health checker (may be nil if not configured)
func (c *Client) GetHealthChecker() *AgentHealthChecker {
	return c.healthChecker
}

// IsHealthy returns true if the agent service is healthy
func (c *Client) IsHealthy() bool {
	if c.healthChecker != nil {
		return c.healthChecker.IsHealthy()
	}
	// Without health checker, assume healthy
	return true
}

// GetCircuitState returns the current circuit breaker state
func (c *Client) GetCircuitState() CircuitState {
	if c.healthChecker != nil {
		return c.healthChecker.GetCircuitState()
	}
	return CircuitClosed
}

// StreamChatWithFallback executes StreamChat with circuit breaker protection
// Returns ErrCircuitOpen if the circuit is open
func (c *Client) StreamChatWithFallback(ctx context.Context, req *agentv1.ChatRequest) (agentv1.AgentService_StreamChatClient, error) {
	// Check circuit breaker
	if c.healthChecker != nil && !c.healthChecker.AllowRequest() {
		return nil, ErrCircuitOpen
	}

	stream, err := c.StreamChat(ctx, req)

	// Record result for circuit breaker tracking
	if c.healthChecker != nil {
		c.healthChecker.RecordRequestResult(err)
	}

	return stream, err
}

func (c *Client) StreamChat(ctx context.Context, req *agentv1.ChatRequest) (agentv1.AgentService_StreamChatClient, error) {
	// Inject Metadata for business context
	md := metadata.New(map[string]string{
		"user-id":            req.UserId,
		"x-internal-api-key": c.config.InternalAPIKey,
	})
	if traceID := traceIDFromContext(ctx); traceID != "" {
		md.Set("x-trace-id", traceID)
	} else if span := trace.SpanFromContext(ctx); span.SpanContext().IsValid() {
		md.Set("x-trace-id", span.SpanContext().TraceID().String())
	}

	outCtx := metadata.NewOutgoingContext(ctx, md)

	// StreamChat is server-side streaming: single request, stream of responses
	// otelgrpc interceptor will handle the TraceContext propagation automatically
	stream, err := c.currentAPI().StreamChat(outCtx, req)
	if !shouldReconnect(err) {
		return stream, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().StreamChat(outCtx, req)
}

func (c *Client) SubmitResponseFeedback(ctx context.Context, req *agentv1.ResponseFeedbackRequest) (*agentv1.ResponseFeedbackResponse, error) {
	md := metadata.New(map[string]string{
		"user-id":            req.UserId,
		"x-internal-api-key": c.config.InternalAPIKey,
	})
	if traceID := traceIDFromContext(ctx); traceID != "" {
		md.Set("x-trace-id", traceID)
	} else if span := trace.SpanFromContext(ctx); span.SpanContext().IsValid() {
		md.Set("x-trace-id", span.SpanContext().TraceID().String())
	}
	outCtx := metadata.NewOutgoingContext(ctx, md)
	resp, err := c.currentAPI().SubmitResponseFeedback(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().SubmitResponseFeedback(outCtx, req)
}

func (c *Client) SubmitPlanReview(ctx context.Context, req *agentv1.PlanReviewRequest) (*agentv1.PlanReviewResponse, error) {
	md := metadata.New(map[string]string{
		"user-id":            req.UserId,
		"x-internal-api-key": c.config.InternalAPIKey,
	})
	if traceID := traceIDFromContext(ctx); traceID != "" {
		md.Set("x-trace-id", traceID)
	} else if span := trace.SpanFromContext(ctx); span.SpanContext().IsValid() {
		md.Set("x-trace-id", span.SpanContext().TraceID().String())
	}
	outCtx := metadata.NewOutgoingContext(ctx, md)
	resp, err := c.currentAPI().SubmitPlanReview(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().SubmitPlanReview(outCtx, req)
}
