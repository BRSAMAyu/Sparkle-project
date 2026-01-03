package handler

import (
	"context"
	"net/http"
	"runtime"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

// P3: Comprehensive health check handler for production readiness
// Provides Kubernetes-compatible liveness/readiness probes and detailed health info

// HealthHandler provides health check endpoints
type HealthHandler struct {
	db        *pgxpool.Pool
	redis     *redis.Client
	startTime time.Time
	version   string

	// Cache to avoid excessive health checks
	mu          sync.RWMutex
	cachedCheck *HealthResponse
	cachedAt    time.Time
	cacheTTL    time.Duration
}

// HealthResponse represents the full health check response
type HealthResponse struct {
	Status     string                 `json:"status"`
	Version    string                 `json:"version"`
	Uptime     string                 `json:"uptime"`
	Timestamp  time.Time              `json:"timestamp"`
	Components map[string]ComponentStatus `json:"components"`
	System     *SystemInfo            `json:"system,omitempty"`
}

// ComponentStatus represents the health of a single component
type ComponentStatus struct {
	Status  string  `json:"status"`
	Latency float64 `json:"latency_ms,omitempty"`
	Message string  `json:"message,omitempty"`
}

// SystemInfo provides system-level information
type SystemInfo struct {
	GoVersion    string `json:"go_version"`
	NumGoroutine int    `json:"num_goroutines"`
	NumCPU       int    `json:"num_cpu"`
	MemAllocMB   uint64 `json:"mem_alloc_mb"`
}

// NewHealthHandler creates a new health handler
func NewHealthHandler(db *pgxpool.Pool, redis *redis.Client, version string) *HealthHandler {
	return &HealthHandler{
		db:        db,
		redis:     redis,
		startTime: time.Now(),
		version:   version,
		cacheTTL:  5 * time.Second,
	}
}

// RegisterRoutes registers health check routes
func (h *HealthHandler) RegisterRoutes(r *gin.Engine) {
	// Kubernetes probes
	r.GET("/healthz", h.handleLiveness)
	r.GET("/readyz", h.handleReadiness)

	// Detailed health check
	r.GET("/health", h.handleHealth)
	r.GET("/health/live", h.handleLiveness)
	r.GET("/health/ready", h.handleReadiness)
}

// handleLiveness handles the liveness probe (is the service running?)
func (h *HealthHandler) handleLiveness(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":    "alive",
		"timestamp": time.Now().UTC(),
	})
}

// handleReadiness handles the readiness probe (can the service handle requests?)
func (h *HealthHandler) handleReadiness(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 3*time.Second)
	defer cancel()

	// Check critical dependencies
	dbOK := h.checkDatabase(ctx)
	redisOK := h.checkRedis(ctx)

	if !dbOK.isHealthy() || !redisOK.isHealthy() {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status":    "not_ready",
			"timestamp": time.Now().UTC(),
			"database":  dbOK.Status,
			"redis":     redisOK.Status,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":    "ready",
		"timestamp": time.Now().UTC(),
	})
}

// handleHealth handles the detailed health check
func (h *HealthHandler) handleHealth(c *gin.Context) {
	// Check cache
	h.mu.RLock()
	if h.cachedCheck != nil && time.Since(h.cachedAt) < h.cacheTTL {
		cached := h.cachedCheck
		h.mu.RUnlock()
		h.respondWithHealth(c, cached)
		return
	}
	h.mu.RUnlock()

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	// Build health response
	components := make(map[string]ComponentStatus)
	components["database"] = h.checkDatabase(ctx)
	components["redis"] = h.checkRedis(ctx)

	// Calculate overall status
	overallStatus := "healthy"
	for _, comp := range components {
		if comp.Status == "unhealthy" {
			overallStatus = "unhealthy"
			break
		}
		if comp.Status == "degraded" {
			overallStatus = "degraded"
		}
	}

	// Get system info
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)

	health := &HealthResponse{
		Status:     overallStatus,
		Version:    h.version,
		Uptime:     time.Since(h.startTime).Round(time.Second).String(),
		Timestamp:  time.Now().UTC(),
		Components: components,
		System: &SystemInfo{
			GoVersion:    runtime.Version(),
			NumGoroutine: runtime.NumGoroutine(),
			NumCPU:       runtime.NumCPU(),
			MemAllocMB:   memStats.Alloc / 1024 / 1024,
		},
	}

	// Update cache
	h.mu.Lock()
	h.cachedCheck = health
	h.cachedAt = time.Now()
	h.mu.Unlock()

	h.respondWithHealth(c, health)
}

func (h *HealthHandler) respondWithHealth(c *gin.Context, health *HealthResponse) {
	statusCode := http.StatusOK
	if health.Status == "unhealthy" {
		statusCode = http.StatusServiceUnavailable
	}
	c.JSON(statusCode, health)
}

func (h *HealthHandler) checkDatabase(ctx context.Context) ComponentStatus {
	if h.db == nil {
		return ComponentStatus{Status: "unhealthy", Message: "database not configured"}
	}

	start := time.Now()
	err := h.db.Ping(ctx)
	latency := float64(time.Since(start).Microseconds()) / 1000.0

	if err != nil {
		return ComponentStatus{
			Status:  "unhealthy",
			Latency: latency,
			Message: err.Error(),
		}
	}

	status := "healthy"
	if latency > 100 {
		status = "degraded"
	}

	return ComponentStatus{
		Status:  status,
		Latency: latency,
	}
}

func (h *HealthHandler) checkRedis(ctx context.Context) ComponentStatus {
	if h.redis == nil {
		return ComponentStatus{Status: "unhealthy", Message: "redis not configured"}
	}

	start := time.Now()
	_, err := h.redis.Ping(ctx).Result()
	latency := float64(time.Since(start).Microseconds()) / 1000.0

	if err != nil {
		return ComponentStatus{
			Status:  "unhealthy",
			Latency: latency,
			Message: err.Error(),
		}
	}

	status := "healthy"
	if latency > 50 {
		status = "degraded"
	}

	return ComponentStatus{
		Status:  status,
		Latency: latency,
	}
}

func (cs ComponentStatus) isHealthy() bool {
	return cs.Status == "healthy" || cs.Status == "degraded"
}
