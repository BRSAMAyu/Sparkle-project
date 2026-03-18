package handler

import (
	"context"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/galaxy"
	redisv9 "github.com/redis/go-redis/v9"
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
	if rateLimit != nil {
		galaxy.Use(rateLimit)
	}

	{
		// gRPC direct endpoints (high priority - for performance)
		galaxy.POST("/nodes/:id/spark", h.SparkNode)
		galaxy.POST("/nodes/:id/mastery", h.UpdateMastery)

		// Proxy endpoints (delegated to Python backend for flexibility)
		galaxy.GET("/graph", h.ProxyToBackend)
		galaxy.GET("/nodes", h.ProxyToBackend)
		galaxy.GET("/nodes/:id", h.ProxyToBackend)
		galaxy.GET("/search", h.ProxyToBackend)
		galaxy.GET("/stats", h.ProxyToBackend)
		galaxy.GET("/heatmap", h.ProxyToBackend)
		galaxy.GET("/predict", h.ProxyToBackend)
		galaxy.GET("/events", h.ProxyToBackend) // SSE stream for real-time galaxy updates
		galaxy.POST("/sync", h.ProxyToBackend)
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
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if h.galaxyClient == nil {
		// Fallback to proxy if gRPC client not available
		h.ProxyToBackend(c)
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.UpdateNodeMastery(
		ctx,
		userID,
		nodeID,
		int32(req.StudyMinutes),
		time.Now(),
		"task_complete",
	)
	if err != nil {
		log.Printf("Failed to spark node via gRPC, falling back to proxy: %v", err)
		h.ProxyToBackend(c)
		return
	}

	// Invalidate cache for this user's galaxy graph
	if h.cache != nil {
		cacheKey := "galaxy:graph:" + userID
		_ = h.cache.Del(ctx, cacheKey)
	}

	c.JSON(http.StatusOK, gin.H{
		"success":        true,
		"old_mastery":    resp.OldMastery,
		"new_mastery":    resp.NewMastery,
		"revision":       resp.CurrentRevision,
		"node_id":        nodeID,
	})
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
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if h.galaxyClient == nil {
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
		h.ProxyToBackend(c)
		return
	}

	// Invalidate cache
	if h.cache != nil {
		cacheKey := "galaxy:graph:" + userID
		_ = h.cache.Del(ctx, cacheKey)
	}

	c.JSON(http.StatusOK, gin.H{
		"success":       true,
		"old_mastery":   resp.OldMastery,
		"new_mastery":   resp.NewMastery,
		"revision":      resp.CurrentRevision,
		"node_id":       nodeID,
	})
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
