// Package metrics provides health check endpoints for the CQRS infrastructure.
package metrics

import (
	"context"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
)

// HealthStatus represents the health status of a component.
type HealthStatus string

const (
	HealthStatusHealthy   HealthStatus = "healthy"
	HealthStatusDegraded  HealthStatus = "degraded"
	HealthStatusUnhealthy HealthStatus = "unhealthy"
)

// ComponentHealth represents the health of a single component.
type ComponentHealth struct {
	Name        string            `json:"name"`
	Status      HealthStatus      `json:"status"`
	Message     string            `json:"message,omitempty"`
	LastChecked time.Time         `json:"last_checked"`
	Details     map[string]string `json:"details,omitempty"`
}

// CQRSHealth represents the overall health of the CQRS system.
type CQRSHealth struct {
	Status     HealthStatus      `json:"status"`
	Components []ComponentHealth `json:"components"`
	Timestamp  time.Time         `json:"timestamp"`
}

// HealthChecker performs health checks on CQRS components.
type HealthChecker struct {
	redis        *redis.Client
	metrics      *CQRSMetrics
	outboxGetter OutboxPendingGetter

	// Thresholds
	outboxWarningThreshold  int64
	outboxCriticalThreshold int64
	consumerLagWarning      int64
	consumerLagCritical     int64

	// Cache
	mu          sync.RWMutex
	lastCheck   *CQRSHealth
	lastCheckAt time.Time
	cacheTTL    time.Duration
}

// OutboxPendingGetter is an interface for getting outbox pending count.
type OutboxPendingGetter interface {
	GetPendingCount(ctx context.Context) (int64, error)
}

// HealthCheckerConfig configures the health checker.
type HealthCheckerConfig struct {
	OutboxWarningThreshold  int64
	OutboxCriticalThreshold int64
	ConsumerLagWarning      int64
	ConsumerLagCritical     int64
	CacheTTL                time.Duration
}

// DefaultHealthCheckerConfig returns sensible defaults.
func DefaultHealthCheckerConfig() HealthCheckerConfig {
	return HealthCheckerConfig{
		OutboxWarningThreshold:  100,
		OutboxCriticalThreshold: 1000,
		ConsumerLagWarning:      100,
		ConsumerLagCritical:     1000,
		CacheTTL:                5 * time.Second,
	}
}

// NewHealthChecker creates a new health checker.
func NewHealthChecker(
	redis *redis.Client,
	metrics *CQRSMetrics,
	outboxGetter OutboxPendingGetter,
	config ...HealthCheckerConfig,
) *HealthChecker {
	cfg := DefaultHealthCheckerConfig()
	if len(config) > 0 {
		cfg = config[0]
	}

	return &HealthChecker{
		redis:                   redis,
		metrics:                 metrics,
		outboxGetter:            outboxGetter,
		outboxWarningThreshold:  cfg.OutboxWarningThreshold,
		outboxCriticalThreshold: cfg.OutboxCriticalThreshold,
		consumerLagWarning:      cfg.ConsumerLagWarning,
		consumerLagCritical:     cfg.ConsumerLagCritical,
		cacheTTL:                cfg.CacheTTL,
	}
}

// Check performs a health check on the CQRS system.
func (h *HealthChecker) Check(ctx context.Context) *CQRSHealth {
	// Check cache
	h.mu.RLock()
	if h.lastCheck != nil && time.Since(h.lastCheckAt) < h.cacheTTL {
		cached := h.lastCheck
		h.mu.RUnlock()
		return cached
	}
	h.mu.RUnlock()

	// Perform checks
	components := make([]ComponentHealth, 0, 4)

	// Check Redis
	components = append(components, h.checkRedis(ctx))

	// Check Outbox
	components = append(components, h.checkOutbox(ctx))

	// Check Event Streams
	components = append(components, h.checkEventStreams(ctx))

	// Check DLQ
	components = append(components, h.checkDLQ(ctx))

	// Calculate overall status
	overallStatus := HealthStatusHealthy
	for _, c := range components {
		if c.Status == HealthStatusUnhealthy {
			overallStatus = HealthStatusUnhealthy
			break
		}
		if c.Status == HealthStatusDegraded && overallStatus == HealthStatusHealthy {
			overallStatus = HealthStatusDegraded
		}
	}

	health := &CQRSHealth{
		Status:     overallStatus,
		Components: components,
		Timestamp:  time.Now().UTC(),
	}

	// Update cache
	h.mu.Lock()
	h.lastCheck = health
	h.lastCheckAt = time.Now()
	h.mu.Unlock()

	return health
}

func (h *HealthChecker) checkRedis(ctx context.Context) ComponentHealth {
	health := ComponentHealth{
		Name:        "redis",
		LastChecked: time.Now().UTC(),
		Details:     make(map[string]string),
	}

	// Ping Redis
	start := time.Now()
	_, err := h.redis.Ping(ctx).Result()
	latency := time.Since(start)

	health.Details["latency_ms"] = latency.String()

	if err != nil {
		health.Status = HealthStatusUnhealthy
		health.Message = "Redis ping failed: " + err.Error()
		return health
	}

	if latency > 100*time.Millisecond {
		health.Status = HealthStatusDegraded
		health.Message = "Redis latency is high"
		return health
	}

	health.Status = HealthStatusHealthy
	health.Message = "Redis is healthy"
	return health
}

func (h *HealthChecker) checkOutbox(ctx context.Context) ComponentHealth {
	health := ComponentHealth{
		Name:        "outbox",
		LastChecked: time.Now().UTC(),
		Details:     make(map[string]string),
	}

	if h.outboxGetter == nil {
		health.Status = HealthStatusHealthy
		health.Message = "Outbox getter not configured"
		return health
	}

	count, err := h.outboxGetter.GetPendingCount(ctx)
	if err != nil {
		health.Status = HealthStatusDegraded
		health.Message = "Failed to get outbox count: " + err.Error()
		return health
	}

	health.Details["pending_count"] = formatInt64(count)

	if count >= h.outboxCriticalThreshold {
		health.Status = HealthStatusUnhealthy
		health.Message = "Outbox backlog is critical"
		return health
	}

	if count >= h.outboxWarningThreshold {
		health.Status = HealthStatusDegraded
		health.Message = "Outbox backlog is building up"
		return health
	}

	health.Status = HealthStatusHealthy
	health.Message = "Outbox is healthy"
	return health
}

func (h *HealthChecker) checkEventStreams(ctx context.Context) ComponentHealth {
	health := ComponentHealth{
		Name:        "event_streams",
		LastChecked: time.Now().UTC(),
		Details:     make(map[string]string),
	}

	streams := []string{
		"cqrs:stream:community",
		"cqrs:stream:task",
		"cqrs:stream:galaxy",
	}

	for _, stream := range streams {
		info, err := h.redis.XInfoStream(ctx, stream).Result()
		if err != nil {
			if err == redis.Nil {
				health.Details[stream] = "not_created"
				continue
			}
			health.Status = HealthStatusDegraded
			health.Message = "Failed to get stream info: " + err.Error()
			return health
		}
		health.Details[stream+"_length"] = formatInt64(info.Length)
	}

	health.Status = HealthStatusHealthy
	health.Message = "Event streams are healthy"
	return health
}

func (h *HealthChecker) checkDLQ(ctx context.Context) ComponentHealth {
	health := ComponentHealth{
		Name:        "dlq",
		LastChecked: time.Now().UTC(),
		Details:     make(map[string]string),
	}

	dlqKey := "cqrs:dlq"

	// Check DLQ length
	length, err := h.redis.XLen(ctx, dlqKey).Result()
	if err != nil && err != redis.Nil {
		health.Status = HealthStatusDegraded
		health.Message = "Failed to check DLQ: " + err.Error()
		return health
	}

	health.Details["pending_count"] = formatInt64(length)

	if length > 100 {
		health.Status = HealthStatusDegraded
		health.Message = "DLQ has accumulated messages"
		return health
	}

	health.Status = HealthStatusHealthy
	health.Message = "DLQ is healthy"
	return health
}

// RegisterRoutes registers health check routes with Gin.
func (h *HealthChecker) RegisterRoutes(router *gin.RouterGroup) {
	router.GET("/health/cqrs", h.handleHealthCheck)
	router.GET("/health/cqrs/live", h.handleLivenessCheck)
	router.GET("/health/cqrs/ready", h.handleReadinessCheck)
}

func (h *HealthChecker) handleHealthCheck(c *gin.Context) {
	health := h.Check(c.Request.Context())

	statusCode := http.StatusOK
	if health.Status == HealthStatusUnhealthy {
		statusCode = http.StatusServiceUnavailable
	} else if health.Status == HealthStatusDegraded {
		statusCode = http.StatusOK // Still operational but degraded
	}

	c.JSON(statusCode, health)
}

func (h *HealthChecker) handleLivenessCheck(c *gin.Context) {
	// Simple liveness check - just verify the service is running
	c.JSON(http.StatusOK, gin.H{
		"status":    "alive",
		"timestamp": time.Now().UTC(),
	})
}

func (h *HealthChecker) handleReadinessCheck(c *gin.Context) {
	health := h.Check(c.Request.Context())

	if health.Status == HealthStatusUnhealthy {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status":    "not_ready",
			"timestamp": time.Now().UTC(),
			"reason":    "CQRS system is unhealthy",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":    "ready",
		"timestamp": time.Now().UTC(),
	})
}

func formatInt64(n int64) string {
	return strconv.FormatInt(n, 10)
}
