package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"github.com/gin-gonic/gin"
	redisv9 "github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/galaxy"
)

// GalaxyHandler handles HTTP requests for the Galaxy service.
// It provides authentication passthrough and rate limiting for Galaxy REST endpoints.
// High-frequency endpoints (spark, mastery) use gRPC direct calls.
// Other endpoints proxy to Python backend.
type GalaxyHandler struct {
	galaxyClient *galaxy.Client
	cache        *redisv9.Client
	backendURL   string
	proxy        *httputil.ReverseProxy
}

// NewGalaxyHandler creates a new GalaxyHandler.
func NewGalaxyHandler(
	galaxyClient *galaxy.Client,
	cache *redisv9.Client,
	backendURL string,
) *GalaxyHandler {
	targetURL, err := url.Parse(backendURL)
	if err != nil {
		log.Printf("Failed to parse backend URL: %v", err)
		return nil
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.FlushInterval = -1 // Flush immediately for SSE support
	proxy.Director = func(req *http.Request) {
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
	}

	return &GalaxyHandler{
		galaxyClient: galaxyClient,
		cache:        cache,
		backendURL:   backendURL,
		proxy:        proxy,
	}
}

// RegisterRoutes registers the galaxy routes with authentication and rate limiting.
func (h *GalaxyHandler) RegisterRoutes(r *gin.RouterGroup, authMiddleware gin.HandlerFunc, rateLimit gin.HandlerFunc) {
	galaxy := r.Group("/galaxy")
	galaxy.Use(authMiddleware)

	{
		// Core study interactions are part of the primary product loop.
		// The shared global limiter was causing normal taps/updates to fail with 429,
		// so keep these outside that narrow limiter and rely on auth/business checks.
		galaxy.POST("/node/:id/spark", h.SparkNode)
		galaxy.POST("/nodes/:id/spark", h.SparkNode)
		galaxy.POST("/node/:id/mastery", h.UpdateMastery)
		galaxy.POST("/nodes/:id/mastery", h.UpdateMastery)
		galaxy.POST("/node/:id/update-mastery", h.UpdateMastery)
		galaxy.POST("/nodes/:id/update-mastery", h.UpdateMastery)

		// Read-heavy graph endpoints are used by page rendering and AI context hydration.
		// Do not put them behind the tight shared rate limiter, or normal navigation can
		// sporadically fail with 429 and break the knowledge graph experience.
		galaxy.GET("/graph", h.ProxyToBackend)
		galaxy.GET("/nodes", h.ProxyToBackend)
		galaxy.GET("/node/:id", h.ProxyToBackend)
		galaxy.GET("/nodes/:id", h.ProxyToBackend)
		galaxy.GET("/search", h.ProxyToBackend)
		galaxy.GET("/stats", h.ProxyToBackend)
		galaxy.GET("/heatmap", h.ProxyToBackend)
		galaxy.GET("/predict", h.ProxyToBackend)
		galaxy.POST("/predict-next", h.ProxyToBackend)
		galaxy.POST("/node/:id/expansion/candidates", h.ProxyToBackend)
		galaxy.POST("/node/:id/expansion/apply", h.ProxyToBackend)
		galaxy.POST("/node/:id/favorite", h.ProxyToBackend)
		galaxy.POST("/node/:id/decay/pause", h.ProxyToBackend)
		galaxy.POST("/nodes/viewport", h.ProxyToBackend)
		galaxy.POST("/nodes/positions", h.ProxyToBackend)
		if rateLimit != nil {
			galaxy.GET("/events", rateLimit, h.ProxyToBackend) // SSE stream for real-time galaxy updates
			galaxy.POST("/sync", rateLimit, h.ProxyToBackend)
		} else {
			galaxy.GET("/events", h.ProxyToBackend) // SSE stream for real-time galaxy updates
			galaxy.POST("/sync", h.ProxyToBackend)
		}
	}
}

// SparkNode handles POST /galaxy/nodes/:id/spark
// Calls gRPC to update mastery (spark) a node - high performance path.
func (h *GalaxyHandler) SparkNode(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	nodeID := c.Param("id")
	if nodeID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "node_id required"})
		return
	}

	var req struct {
		StudyMinutes int    `json:"study_minutes"`
		TaskID       string `json:"task_id"`
	}
	rawBody, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "failed to read request body"})
		return
	}
	c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
	if len(bytes.TrimSpace(rawBody)) > 0 {
		if err := json.Unmarshal(rawBody, &req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
	}
	if req.StudyMinutes <= 0 {
		req.StudyMinutes = 1
	}

	// Keep spark on the REST path until gRPC has a dedicated study_minutes field/RPC.
	// UpdateNodeMastery expects an absolute mastery score, so sending study_minutes there
	// would overwrite progress with corrupted values.
	c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
	h.ProxyToBackend(c)
}

// UpdateMastery handles POST /galaxy/nodes/:id/mastery
// Direct gRPC call to update mastery.
func (h *GalaxyHandler) UpdateMastery(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	nodeID := c.Param("id")
	if nodeID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "node_id required"})
		return
	}

	var req struct {
		Mastery int    `json:"mastery"`
		Reason  string `json:"reason"`
	}
	rawBody, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "failed to read request body"})
		return
	}
	c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
	if len(bytes.TrimSpace(rawBody)) > 0 {
		if err := json.Unmarshal(rawBody, &req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
	}

	if h.galaxyClient == nil {
		c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
		h.ProxyToBackend(c)
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.UpdateNodeMastery(
		ctx,
		userID,
		nodeID,
		int32(req.Mastery),
		time.Now(),
		req.Reason,
	)
	if err != nil {
		log.Printf("Failed to update mastery via gRPC, falling back to proxy: %v", err)
		c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
		h.ProxyToBackend(c)
		return
	}

	if !resp.Success {
		c.JSON(http.StatusConflict, gin.H{
			"error":            resp.Reason,
			"current_revision": resp.CurrentRevision,
			"node_id":          nodeID,
		})
		return
	}

	h.invalidateGalaxyGraphCache(ctx, userID)

	c.JSON(http.StatusOK, gin.H{
		"success":     true,
		"old_mastery": resp.OldMastery,
		"new_mastery": resp.NewMastery,
		"revision":    resp.CurrentRevision,
		"node_id":     nodeID,
	})
}

func (h *GalaxyHandler) invalidateGalaxyGraphCache(ctx context.Context, userID string) {
	if h.cache == nil || userID == "" {
		return
	}

	if err := h.cache.Del(ctx, "galaxy:graph:"+userID).Err(); err != nil {
		log.Printf("Failed to delete galaxy cache key for user %s: %v", userID, err)
	}

	pattern := "*:view:get_galaxy_graph:" + userID + ":*"
	iter := h.cache.Scan(ctx, 0, pattern, 0).Iterator()
	var keys []string
	for iter.Next(ctx) {
		keys = append(keys, iter.Val())
	}
	if err := iter.Err(); err != nil {
		log.Printf("Failed to scan galaxy cache pattern for user %s: %v", userID, err)
		return
	}
	if len(keys) == 0 {
		return
	}
	if err := h.cache.Del(ctx, keys...).Err(); err != nil {
		log.Printf("Failed to delete galaxy cache pattern for user %s: %v", userID, err)
	}
}

// ProxyToBackend proxies requests to the Python backend.
func (h *GalaxyHandler) ProxyToBackend(c *gin.Context) {
	if h.proxy == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "backend proxy not configured"})
		return
	}

	// Add user context headers for backend
	userID := c.GetString("user_id")
	if userID != "" {
		c.Request.Header.Set("X-User-ID", userID)
	}

	// Preserve auth token - try both stored token and original Authorization header
	if token := c.GetString("auth_token"); token != "" {
		c.Request.Header.Set("Authorization", "Bearer "+token)
	} else if auth := c.GetHeader("Authorization"); auth != "" {
		// Keep original Authorization header if auth_token not set
		c.Request.Header.Set("Authorization", auth)
	}

	h.proxy.ServeHTTP(c.Writer, c.Request)
}
