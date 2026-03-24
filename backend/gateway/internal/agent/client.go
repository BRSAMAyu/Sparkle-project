package agent

import (
	"context"
	"crypto/tls"
	"errors"
	"log"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/metadata"
)

// ErrCircuitOpen is returned when the circuit breaker is open
var ErrCircuitOpen = errors.New("circuit breaker is open")

// ErrServiceUnavailable is returned when the agent service is unavailable
var ErrServiceUnavailable = errors.New("agent service unavailable")

type Client struct {
	conn   *grpc.ClientConn
	api    agentv1.AgentServiceClient
	config *config.Config

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
	// Simple retry logic or keepalive can be added here
	timeoutSeconds := cfg.GRPCTimeoutSeconds
	if timeoutSeconds <= 0 {
		timeoutSeconds = 5
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSeconds)*time.Second)
	defer cancel()

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
				"InitialBackoff": ".01s",
				"MaxBackoff": ".1s",
				"BackoffMultiplier": 1.0,
				"RetryableStatusCodes": ["UNAVAILABLE", "RESOURCE_EXHAUSTED"]
			}
		}]
	}`

	conn, err := grpc.DialContext(ctx, cfg.AgentAddress,
		grpc.WithTransportCredentials(creds),
		grpc.WithBlock(),
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
		grpc.WithDefaultServiceConfig(retryPolicy),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                20 * time.Second,
			Timeout:             10 * time.Second,
			PermitWithoutStream: true,
		}),
	)
	if err != nil {
		log.Printf("Failed to connect to agent service at %s: %v", cfg.AgentAddress, err)
		return nil, err
	}

	client := agentv1.NewAgentServiceClient(conn)
	return &Client{conn: conn, api: client, config: cfg}, nil
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
	if c.conn != nil {
		c.conn.Close()
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
	return c.api.StreamChat(outCtx, req)
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
	return c.api.SubmitResponseFeedback(outCtx, req)
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
	return c.api.SubmitPlanReview(outCtx, req)
}
