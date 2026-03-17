// Package handler provides explicit proxy routes for Python Backend APIs
package handler

import (
	"net/http/httputil"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/middleware"
	"go.uber.org/zap"
)

// ProxyRoutesHandler handles explicit proxy routes to Python Backend
// This provides better observability and control compared to NoRoute fallback
type ProxyRoutesHandler struct {
	proxy            *httputil.ReverseProxy
	abTestMiddleware *middleware.ABTestMiddleware
	logger           *zap.Logger
}

// NewProxyRoutesHandler creates a new proxy routes handler
func NewProxyRoutesHandler(
	proxy *httputil.ReverseProxy,
	abTest *middleware.ABTestMiddleware,
	logger *zap.Logger,
) *ProxyRoutesHandler {
	return &ProxyRoutesHandler{
		proxy:            proxy,
		abTestMiddleware: abTest,
		logger:           logger,
	}
}

// RegisterProxyRoutes registers all explicit proxy routes to Python Backend
func (h *ProxyRoutesHandler) RegisterProxyRoutes(
	api *gin.RouterGroup,
	authMiddleware gin.HandlerFunc,
) {
	// ==================== Accountability Routes ====================
	accountability := api.Group("/accountability")
	accountability.Use(authMiddleware)
	{
		accountability.POST("/request", h.proxyWithHeaders)
		accountability.POST("/:id/respond", h.proxyWithHeaders)
		accountability.GET("/mine", h.proxyWithHeaders)
		accountability.DELETE("/:id", h.proxyWithHeaders)
		accountability.POST("/:id/checkin", h.proxyWithHeaders)
		accountability.GET("/:id/stats", h.proxyWithHeaders)
		accountability.GET("/:id/timeline", h.proxyWithHeaders)
		accountability.GET("/:id/heatmap", h.proxyWithHeaders)
		accountability.POST("/checkin/:id/like", h.proxyWithHeaders)
		accountability.POST("/checkin/:id/encourage", h.proxyWithHeaders)
		accountability.GET("/achievements", h.proxyWithHeaders)
		accountability.GET("/:id/achievements", h.proxyWithHeaders)
	}
	h.logger.Info("Registered accountability proxy routes")

	// ==================== Tasks Routes ====================
	tasks := api.Group("/tasks")
	tasks.Use(authMiddleware)
	{
		tasks.GET("", h.proxyWithHeaders)
		tasks.POST("", h.proxyWithHeaders)
		tasks.GET("/today", h.proxyWithHeaders)
		tasks.GET("/recommended", h.proxyWithHeaders)
		tasks.GET("/suggestions", h.proxyWithHeaders)
		tasks.GET("/:id", h.proxyWithHeaders)
		tasks.PUT("/:id", h.proxyWithHeaders)
		tasks.DELETE("/:id", h.proxyWithHeaders)
		tasks.POST("/:id/start", h.proxyWithHeaders)
		tasks.POST("/:id/complete", h.proxyWithHeaders)
		tasks.POST("/:id/abandon", h.proxyWithHeaders)
		tasks.POST("/:id/feedback", h.proxyWithHeaders)
	}
	h.logger.Info("Registered tasks proxy routes")

	// ==================== Plans Routes ====================
	plans := api.Group("/plans")
	plans.Use(authMiddleware)
	{
		plans.GET("", h.proxyWithHeaders)
		plans.POST("", h.proxyWithHeaders)
		plans.GET("/:id", h.proxyWithHeaders)
		plans.PUT("/:id", h.proxyWithHeaders)
		plans.DELETE("/:id", h.proxyWithHeaders)
		plans.POST("/:id/archive", h.proxyWithHeaders)
		plans.POST("/:id/restore", h.proxyWithHeaders)
		plans.GET("/:id/tasks", h.proxyWithHeaders)
	}
	h.logger.Info("Registered plans proxy routes")

	// ==================== Achievements Routes ====================
	achievements := api.Group("/achievements")
	achievements.Use(authMiddleware)
	{
		achievements.GET("", h.proxyWithHeaders)
		achievements.GET("/stats", h.proxyWithHeaders)
		achievements.GET("/map", h.proxyWithHeaders)
		achievements.GET("/streak", h.proxyWithHeaders)
		achievements.GET("/:id", h.proxyWithHeaders)
		achievements.POST("/:id/share", h.proxyWithHeaders)
		achievements.GET("/contracts", h.proxyWithHeaders)
	}
	h.logger.Info("Registered achievements proxy routes")

	// ==================== Calendar Routes ====================
	calendar := api.Group("/calendar")
	calendar.Use(authMiddleware)
	{
		calendar.GET("", h.proxyWithHeaders)
		calendar.POST("", h.proxyWithHeaders)
		calendar.GET("/summary", h.proxyWithHeaders)
		calendar.GET("/:id", h.proxyWithHeaders)
		calendar.PUT("/:id", h.proxyWithHeaders)
		calendar.DELETE("/:id", h.proxyWithHeaders)
		calendar.POST("/batch", h.proxyWithHeaders)
		calendar.POST("/suggest-time", h.proxyWithHeaders)
	}
	h.logger.Info("Registered calendar proxy routes")

	// ==================== Recommendations Routes ====================
	recommendations := api.Group("/recommendations")
	recommendations.Use(authMiddleware)
	{
		recommendations.GET("", h.proxyWithHeaders)
		recommendations.POST("/feedback", h.proxyWithHeaders)
	}
	h.logger.Info("Registered recommendations proxy routes")

	// ==================== Reflections Routes ====================
	reflections := api.Group("/reflections")
	reflections.Use(authMiddleware)
	{
		reflections.GET("", h.proxyWithHeaders)
		reflections.POST("", h.proxyWithHeaders)
		reflections.GET("/:id", h.proxyWithHeaders)
		reflections.PUT("/:id", h.proxyWithHeaders)
		reflections.DELETE("/:id", h.proxyWithHeaders)
	}
	h.logger.Info("Registered reflections proxy routes")

	// ==================== Goals Routes ====================
	goals := api.Group("/goals")
	goals.Use(authMiddleware)
	{
		goals.GET("", h.proxyWithHeaders)
		goals.POST("", h.proxyWithHeaders)
		goals.GET("/:id", h.proxyWithHeaders)
		goals.PUT("/:id", h.proxyWithHeaders)
		goals.DELETE("/:id", h.proxyWithHeaders)
		goals.POST("/:id/checkpoint", h.proxyWithHeaders)
		goals.GET("/:id/progress", h.proxyWithHeaders)
	}
	h.logger.Info("Registered goals proxy routes")
}

// proxyWithHeaders proxies request to Python Backend with user context headers
func (h *ProxyRoutesHandler) proxyWithHeaders(c *gin.Context) {
	// Set user context headers (provided by authMiddleware)
	if userID := c.GetString("user_id"); userID != "" {
		c.Request.Header.Set("X-User-ID", userID)
	}
	if token := c.GetString("auth_token"); token != "" {
		c.Request.Header.Set("Authorization", "Bearer "+token)
	}

	// A/B testing variant assignment
	h.abTestMiddleware.AssignVariant()(c)

	// Log the proxy request
	h.logger.Debug("Proxying explicit route request",
		zap.String("path", c.Request.URL.Path),
		zap.String("method", c.Request.Method))

	// Proxy to Python Backend
	h.proxy.ServeHTTP(c.Writer, c.Request)

	// Record metrics
	h.abTestMiddleware.RecordMetricAfter(c)

	// Log the result
	h.logger.Debug("Explicit route proxy completed",
		zap.String("path", c.Request.URL.Path),
		zap.Int("status", c.Writer.Status()))
}
