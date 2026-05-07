package agent

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"errors"
	"fmt"
	"os"
	"sync"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/otel/trace"
	"go.uber.org/zap"
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

	reconnectMu     sync.Mutex
	lastReconnectAt time.Time
	minReconnectGap time.Duration // R5-G07: minimum gap between reconnect attempts
	dialOptions     []grpc.DialOption

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
		zap.L().Error("Failed to connect to agent service",
			zap.String("address", cfg.AgentAddress),
			zap.Error(err),
		)
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
		tlsCfg := &tls.Config{
			MinVersion:         tls.VersionTLS12,
			ServerName:         cfg.AgentTLSServerName,
			InsecureSkipVerify: cfg.AgentTLSInsecure,
		}
		// Load CA cert for server verification
		if cfg.AgentTLSCACertPath != "" {
			caCert, err := os.ReadFile(cfg.AgentTLSCACertPath)
			if err != nil {
				zap.L().Error("Failed to read agent TLS CA cert",
					zap.String("ca_cert_path", cfg.AgentTLSCACertPath),
					zap.Error(err),
				)
				return nil, err
			}
			tlsCfg.RootCAs = x509.NewCertPool()
			if !tlsCfg.RootCAs.AppendCertsFromPEM(caCert) {
				zap.L().Error("Failed to parse agent TLS CA cert",
					zap.String("ca_cert_path", cfg.AgentTLSCACertPath),
				)
				return nil, fmt.Errorf("failed to parse CA cert: %s", cfg.AgentTLSCACertPath)
			}
			tlsCfg.InsecureSkipVerify = false
		}
		// P2-28: Load client cert for mTLS
		if cfg.AgentTLSClientCertPath != "" && cfg.AgentTLSClientKeyPath != "" {
			clientCert, err := tls.LoadX509KeyPair(cfg.AgentTLSClientCertPath, cfg.AgentTLSClientKeyPath)
			if err != nil {
				zap.L().Error("Failed to load agent mTLS client cert/key",
					zap.String("cert_path", cfg.AgentTLSClientCertPath),
					zap.String("key_path", cfg.AgentTLSClientKeyPath),
					zap.Error(err),
				)
				return nil, err
			}
			tlsCfg.Certificates = []tls.Certificate{clientCert}
		}
		creds = credentials.NewTLS(tlsCfg)
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
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(50*1024*1024),
			grpc.MaxCallSendMsgSize(50*1024*1024),
		),
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

	// R5-G07: Rate-limit reconnect attempts (minimum 2s between attempts)
	minGap := c.minReconnectGap
	if minGap == 0 {
		minGap = 2 * time.Second
	}
	if elapsed := time.Since(c.lastReconnectAt); elapsed < minGap {
		time.Sleep(minGap - elapsed)
	}
	c.lastReconnectAt = time.Now()

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
		zap.L().Error("Agent client reconnect failed",
			zap.String("address", c.config.AgentAddress),
			zap.Error(err),
		)
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

	zap.L().Info("Agent client reconnected",
		zap.String("address", c.config.AgentAddress),
	)
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

	zap.L().Info("Agent health checker started",
		zap.Duration("interval", healthCheckInterval),
		zap.Duration("timeout", healthCheckTimeout),
	)

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

// injectMetadata creates an outgoing context with user-id, internal API key, and trace ID.
func (c *Client) injectMetadata(ctx context.Context, userID string) context.Context {
	pairs := []string{
		"x-internal-api-key", c.config.InternalAPIKey,
	}
	if userID != "" {
		pairs = append(pairs, "user-id", userID)
	}
	if traceID := traceIDFromContext(ctx); traceID != "" {
		pairs = append(pairs, "x-trace-id", traceID)
	} else if span := trace.SpanFromContext(ctx); span.SpanContext().IsValid() {
		pairs = append(pairs, "x-trace-id", span.SpanContext().TraceID().String())
	}
	return metadata.NewOutgoingContext(ctx, metadata.Pairs(pairs...))
}

func (c *Client) StreamChat(ctx context.Context, req *agentv1.ChatRequest) (agentv1.AgentService_StreamChatClient, error) {
	start := time.Now()
	outCtx := c.injectMetadata(ctx, req.UserId)
	stream, err := c.currentAPI().StreamChat(outCtx, req)
	if !shouldReconnect(err) {
		grpcCallDuration.WithLabelValues("StreamChat", statusCodeLabel(err)).Observe(time.Since(start).Seconds())
		return stream, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		grpcCallDuration.WithLabelValues("StreamChat", statusCodeLabel(err)).Observe(time.Since(start).Seconds())
		return nil, err
	}
	// Use fresh context with fresh timeout after reconnection
	retryCtx := c.injectMetadata(ctx, req.UserId)
	stream, retryErr := c.currentAPI().StreamChat(retryCtx, req)
	grpcCallDuration.WithLabelValues("StreamChat", statusCodeLabel(retryErr)).Observe(time.Since(start).Seconds())
	return stream, retryErr
}

func (c *Client) SubmitResponseFeedback(ctx context.Context, req *agentv1.ResponseFeedbackRequest) (*agentv1.ResponseFeedbackResponse, error) {
	start := time.Now()
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().SubmitResponseFeedback(outCtx, req)
	if !shouldReconnect(err) {
		grpcCallDuration.WithLabelValues("SubmitResponseFeedback", statusCodeLabel(err)).Observe(time.Since(start).Seconds())
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		grpcCallDuration.WithLabelValues("SubmitResponseFeedback", statusCodeLabel(err)).Observe(time.Since(start).Seconds())
		return nil, err
	}
	resp, retryErr := c.currentAPI().SubmitResponseFeedback(outCtx, req)
	grpcCallDuration.WithLabelValues("SubmitResponseFeedback", statusCodeLabel(retryErr)).Observe(time.Since(start).Seconds())
	return resp, retryErr
}

func (c *Client) SubmitPlanReview(ctx context.Context, req *agentv1.PlanReviewRequest) (*agentv1.PlanReviewResponse, error) {
	start := time.Now()
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().SubmitPlanReview(outCtx, req)
	if !shouldReconnect(err) {
		grpcCallDuration.WithLabelValues("SubmitPlanReview", statusCodeLabel(err)).Observe(time.Since(start).Seconds())
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		grpcCallDuration.WithLabelValues("SubmitPlanReview", statusCodeLabel(err)).Observe(time.Since(start).Seconds())
		return nil, err
	}
	resp, retryErr := c.currentAPI().SubmitPlanReview(outCtx, req)
	grpcCallDuration.WithLabelValues("SubmitPlanReview", statusCodeLabel(retryErr)).Observe(time.Since(start).Seconds())
	return resp, retryErr
}

// ── Missing RPC wrappers (P0-4) ──────────────────────────────────────

func (c *Client) RetrieveMemory(ctx context.Context, req *agentv1.MemoryQuery) (*agentv1.MemoryResult, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().RetrieveMemory(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().RetrieveMemory(outCtx, req)
}

func (c *Client) GetUserProfile(ctx context.Context, req *agentv1.ProfileRequest) (*agentv1.UserProfile, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().GetUserProfile(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().GetUserProfile(outCtx, req)
}

func (c *Client) GetWeeklyReport(ctx context.Context, req *agentv1.WeeklyReportRequest) (*agentv1.WeeklyReport, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().GetWeeklyReport(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().GetWeeklyReport(outCtx, req)
}

func (c *Client) SubmitContentReviewFeedback(ctx context.Context, req *agentv1.ContentReviewFeedbackRequest) (*agentv1.ContentReviewFeedbackResponse, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().SubmitContentReviewFeedback(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().SubmitContentReviewFeedback(outCtx, req)
}

func (c *Client) SubmitReviewOverride(ctx context.Context, req *agentv1.ReviewOverrideRequest) (*agentv1.ReviewOverrideResponse, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().SubmitReviewOverride(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().SubmitReviewOverride(outCtx, req)
}

func (c *Client) SubmitReviewAppeal(ctx context.Context, req *agentv1.ReviewAppealRequest) (*agentv1.ReviewAppealResponse, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().SubmitReviewAppeal(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().SubmitReviewAppeal(outCtx, req)
}

func (c *Client) GetAppealStatus(ctx context.Context, req *agentv1.AppealStatusRequest) (*agentv1.AppealStatusResponse, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().GetAppealStatus(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().GetAppealStatus(outCtx, req)
}

func (c *Client) SubmitReviewFeedback(ctx context.Context, req *agentv1.ReviewFeedbackRequest) (*agentv1.ReviewFeedbackResponse, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().SubmitReviewFeedback(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().SubmitReviewFeedback(outCtx, req)
}

func (c *Client) RequestRegeneration(ctx context.Context, req *agentv1.RegenerationRequest) (*agentv1.RegenerationResponse, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().RequestRegeneration(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().RequestRegeneration(outCtx, req)
}

func (c *Client) GetFeedbackStatistics(ctx context.Context, req *agentv1.FeedbackStatisticsRequest) (*agentv1.FeedbackStatisticsResponse, error) {
	outCtx := c.injectMetadata(ctx, req.UserId)
	resp, err := c.currentAPI().GetFeedbackStatistics(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().GetFeedbackStatistics(outCtx, req)
}

func (c *Client) GetArbitrationQueue(ctx context.Context, req *agentv1.GetArbitrationQueueRequest) (*agentv1.GetArbitrationQueueResponse, error) {
	outCtx := c.injectMetadata(ctx, "")
	resp, err := c.currentAPI().GetArbitrationQueue(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().GetArbitrationQueue(outCtx, req)
}

func (c *Client) AssignArbitrationCase(ctx context.Context, req *agentv1.AssignArbitrationCaseRequest) (*agentv1.AssignArbitrationCaseResponse, error) {
	outCtx := c.injectMetadata(ctx, req.ArbitratorId)
	resp, err := c.currentAPI().AssignArbitrationCase(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().AssignArbitrationCase(outCtx, req)
}

func (c *Client) SubmitArbitrationDecision(ctx context.Context, req *agentv1.SubmitArbitrationDecisionRequest) (*agentv1.SubmitArbitrationDecisionResponse, error) {
	outCtx := c.injectMetadata(ctx, req.ArbitratorId)
	resp, err := c.currentAPI().SubmitArbitrationDecision(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().SubmitArbitrationDecision(outCtx, req)
}

func (c *Client) GetArbitrationQueueStats(ctx context.Context, req *agentv1.GetArbitrationQueueStatsRequest) (*agentv1.GetArbitrationQueueStatsResponse, error) {
	outCtx := c.injectMetadata(ctx, "")
	resp, err := c.currentAPI().GetArbitrationQueueStats(outCtx, req)
	if !shouldReconnect(err) {
		return resp, err
	}
	if reconnectErr := c.reconnect(ctx); reconnectErr != nil {
		return nil, err
	}
	return c.currentAPI().GetArbitrationQueueStats(outCtx, req)
}

// statusCodeLabel returns a short string label for the grpc status code for metrics.
func statusCodeLabel(err error) string {
	if err == nil {
		return "ok"
	}
	if st, ok := status.FromError(err); ok {
		return st.Code().String()
	}
	return "unknown"
}
