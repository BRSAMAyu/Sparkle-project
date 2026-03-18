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
		plans.GET("/stats/summary", h.proxyWithHeaders)
		plans.GET("/quota/status", h.proxyWithHeaders)
		plans.GET("/primary", h.proxyWithHeaders)
		plans.POST("/primary", h.proxyWithHeaders)
		plans.GET("/archived", h.proxyWithHeaders)
		plans.GET("/:id", h.proxyWithHeaders)
		plans.PATCH("/:id", h.proxyWithHeaders) // Python uses PATCH (not PUT)
		plans.DELETE("/:id", h.proxyWithHeaders)
		plans.POST("/:id/archive", h.proxyWithHeaders)
		plans.POST("/:id/restore", h.proxyWithHeaders)
		plans.GET("/:id/progress", h.proxyWithHeaders)
		plans.PATCH("/:id/priority", h.proxyWithHeaders)
		plans.GET("/:id/learning-path-progress", h.proxyWithHeaders)
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

	// NOTE: /goals and /reflections routes are intentionally omitted —
	// no Python backend implementation exists yet. Add here when implemented.

	// ==================== Capsules Routes ====================
	capsules := api.Group("/capsules")
	capsules.Use(authMiddleware)
	{
		capsules.GET("/today", h.proxyWithHeaders)
		capsules.POST("/:id/read", h.proxyWithHeaders)
		capsules.POST("/generate", h.proxyWithHeaders)
		capsules.GET("/favorites", h.proxyWithHeaders)
		capsules.POST("/:id/favorite", h.proxyWithHeaders)
		capsules.POST("/:id/feedback", h.proxyWithHeaders)
		capsules.POST("/:id/share", h.proxyWithHeaders)
		capsules.GET("/generation/jobs", h.proxyWithHeaders)
		capsules.POST("/generate/batch", h.proxyWithHeaders)
		capsules.GET("/stats", h.proxyWithHeaders)
		capsules.GET("/list/all", h.proxyWithHeaders)
		capsules.GET("/:id", h.proxyWithHeaders)
	}
	h.logger.Info("Registered capsules proxy routes")

	// ==================== Seed Libraries Routes ====================
	seedLibs := api.Group("/seed-libraries")
	seedLibs.Use(authMiddleware)
	{
		seedLibs.GET("", h.proxyWithHeaders)
		seedLibs.POST("", h.proxyWithHeaders)
		seedLibs.GET("/subscriptions/me", h.proxyWithHeaders)
		seedLibs.GET("/examples/few-shot", h.proxyWithHeaders)
		seedLibs.POST("/query", h.proxyWithHeaders)
		seedLibs.POST("/subscribe/:id", h.proxyWithHeaders)
		seedLibs.DELETE("/subscribe/:id", h.proxyWithHeaders)
		seedLibs.GET("/:id", h.proxyWithHeaders)
		seedLibs.PUT("/:id", h.proxyWithHeaders)
		seedLibs.DELETE("/:id", h.proxyWithHeaders)
		seedLibs.POST("/:id/items", h.proxyWithHeaders)
		seedLibs.GET("/:id/items", h.proxyWithHeaders)
	}
	h.logger.Info("Registered seed-libraries proxy routes")

	// ==================== Community Routes ====================
	community := api.Group("/community")
	community.Use(authMiddleware)
	{
		// Friend System
		community.POST("/friends/request", h.proxyWithHeaders)
		community.POST("/friends/respond", h.proxyWithHeaders) // Python: POST /friends/respond with friendship_id in body
		community.GET("/friends", h.proxyWithHeaders)
		community.GET("/friends/pending", h.proxyWithHeaders)
		community.DELETE("/friends/:friendshipId", h.proxyWithHeaders)
		// Block System
		community.POST("/users/block", h.proxyWithHeaders)
		community.DELETE("/users/block/:userId", h.proxyWithHeaders)
		community.GET("/users/blocked", h.proxyWithHeaders)
		// Privacy
		community.PUT("/users/privacy", h.proxyWithHeaders)
		community.GET("/users/privacy", h.proxyWithHeaders)
		// Search
		community.GET("/users/search", h.proxyWithHeaders)
		community.GET("/groups/search", h.proxyWithHeaders)
		// Group System
		community.POST("/groups", h.proxyWithHeaders)
		community.GET("/groups", h.proxyWithHeaders)
		community.GET("/groups/:group_id", h.proxyWithHeaders)
		community.POST("/groups/:group_id/join", h.proxyWithHeaders)
		community.DELETE("/groups/:group_id/leave", h.proxyWithHeaders)
		community.GET("/groups/:group_id/members", h.proxyWithHeaders)
		community.GET("/groups/:group_id/messages", h.proxyWithHeaders)
		community.POST("/groups/:group_id/messages", h.proxyWithHeaders)
		community.DELETE("/groups/:group_id/messages/:msg_id", h.proxyWithHeaders)
		community.POST("/groups/:group_id/messages/read", h.proxyWithHeaders)
		// Private Messages
		community.POST("/messages/private", h.proxyWithHeaders)
		community.GET("/messages/private/:user_id", h.proxyWithHeaders)
		community.DELETE("/messages/private/:msg_id", h.proxyWithHeaders)
		// Feed & Posts
		community.POST("/posts", h.proxyWithHeaders)
		community.POST("/posts/:post_id/like", h.proxyWithHeaders)
		community.GET("/feed", h.proxyWithHeaders)
		// Check-in
		community.POST("/checkin", h.proxyWithHeaders)
	}
	h.logger.Info("Registered community proxy routes")

	// ==================== Interventions Routes ====================
	interventions := api.Group("/interventions")
	interventions.Use(authMiddleware)
	{
		interventions.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered interventions proxy routes")

	// ==================== Dashboard Routes ====================
	dashboard := api.Group("/dashboard")
	dashboard.Use(authMiddleware)
	{
		dashboard.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered dashboard proxy routes")

	// ==================== Predictive Routes ====================
	predictive := api.Group("/predictive")
	predictive.Use(authMiddleware)
	{
		predictive.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered predictive proxy routes")

	// ==================== STT Batch Transcription ====================
	stt := api.Group("/stt")
	stt.Use(authMiddleware)
	{
		stt.POST("/transcribe", h.proxyWithHeaders)
	}
	h.logger.Info("Registered STT proxy routes")
}

// proxyWithHeaders proxies request to Python Backend with user context headers
func (h *ProxyRoutesHandler) proxyWithHeaders(c *gin.Context) {
	SetProxyUserContextHeaders(c)

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

// SetProxyUserContextHeaders sets X-User-ID and Authorization headers
// from gin context values populated by AuthMiddleware.
// Used by both ProxyRoutesHandler and NoRoute fallback.
func SetProxyUserContextHeaders(c *gin.Context) {
	if userID := c.GetString("user_id"); userID != "" {
		c.Request.Header.Set("X-User-ID", userID)
	}
	if token := c.GetString("auth_token"); token != "" {
		c.Request.Header.Set("Authorization", "Bearer "+token)
	}
}
