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
		accountability.GET("/overview", h.proxyWithHeaders)
		accountability.DELETE("/:id", h.proxyWithHeaders)
		accountability.POST("/:id/checkin", h.proxyWithHeaders)
		accountability.POST("/:id/nudge", h.proxyWithHeaders)
		accountability.GET("/:id/dashboard", h.proxyWithHeaders)
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
		tasks.GET("/:id/resources", h.proxyWithHeaders)
		tasks.PUT("/:id", h.proxyWithHeaders)
		tasks.DELETE("/:id", h.proxyWithHeaders)
		tasks.POST("/:id/resources", h.proxyWithHeaders)
		tasks.DELETE("/:id/resources/:resourceId", h.proxyWithHeaders)
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
		plans.PUT("/:id", h.proxyWithHeaders)
		plans.PATCH("/:id", h.proxyWithHeaders) // Python uses PATCH (not PUT)
		plans.DELETE("/:id", h.proxyWithHeaders)
		plans.POST("/:id/archive", h.proxyWithHeaders)
		plans.POST("/:id/restore", h.proxyWithHeaders)
		plans.POST("/:id/generate-tasks", h.proxyWithHeaders)
		plans.GET("/:id/progress", h.proxyWithHeaders)
		plans.PATCH("/:id/priority", h.proxyWithHeaders)
		plans.GET("/:id/learning-path-progress", h.proxyWithHeaders)
	}
	h.logger.Info("Registered plans proxy routes")

	// ==================== Learning Paths Routes ====================
	learningPaths := api.Group("/learning-paths")
	learningPaths.Use(authMiddleware)
	{
		learningPaths.GET("/:target_node_id", h.proxyWithHeaders)
		learningPaths.POST("/:target_node_id/plan", h.proxyWithHeaders)
		learningPaths.POST("/:target_node_id/full-plan", h.proxyWithHeaders)
	}
	h.logger.Info("Registered learning paths proxy routes")

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

	// ==================== Suggestions Routes ====================
	suggestions := api.Group("/suggestions")
	suggestions.Use(authMiddleware)
	{
		suggestions.GET("", h.proxyWithHeaders)
	}
	h.logger.Info("Registered suggestions proxy routes")

	// ==================== Agent Stats Routes ====================
	agentStats := api.Group("/agent-stats")
	agentStats.Use(authMiddleware)
	{
		agentStats.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered agent-stats proxy routes")

	// ==================== Assets Routes ====================
	assets := api.Group("/assets")
	assets.Use(authMiddleware)
	{
		assets.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered assets proxy routes")

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
		seedLibs.GET("/my-subscriptions", h.proxyWithHeaders)
		seedLibs.GET("/subscriptions/me", h.proxyWithHeaders)
		seedLibs.GET("/query/few-shot", h.proxyWithHeaders)
		seedLibs.GET("/examples/few-shot", h.proxyWithHeaders)
		seedLibs.POST("/query", h.proxyWithHeaders)
		seedLibs.POST("/:id/subscribe", h.proxyWithHeaders)
		seedLibs.DELETE("/:id/unsubscribe", h.proxyWithHeaders)
		seedLibs.POST("/subscribe/:id", h.proxyWithHeaders)
		seedLibs.DELETE("/subscribe/:id", h.proxyWithHeaders)
		seedLibs.GET("/:id", h.proxyWithHeaders)
		seedLibs.PUT("/:id", h.proxyWithHeaders)
		seedLibs.DELETE("/:id", h.proxyWithHeaders)
		seedLibs.POST("/:id/items/import", h.proxyWithHeaders)
		seedLibs.POST("/:id/items", h.proxyWithHeaders)
		seedLibs.GET("/:id/items", h.proxyWithHeaders)
		seedLibs.PUT("/:id/items/:itemId", h.proxyWithHeaders)
		seedLibs.DELETE("/:id/items/:itemId", h.proxyWithHeaders)
	}
	h.logger.Info("Registered seed-libraries proxy routes")

	// ==================== Community Routes ====================
	community := api.Group("/community")
	community.Use(authMiddleware)
	{
		// Friend System
		community.POST("/friends/request", h.proxyWithHeaders)
		community.POST("/friends/respond", h.proxyWithHeaders)
		community.GET("/friends", h.proxyWithHeaders)
		community.GET("/friends/pending", h.proxyWithHeaders)
		community.GET("/friends/recommendations", h.proxyWithHeaders)
		community.POST("/friends/recommendations/feedback", h.proxyWithHeaders)
		community.GET("/friends/:friend_id/profile", h.proxyWithHeaders)
		community.GET("/recommendations/feedback/prompts", h.proxyWithHeaders)
		community.GET("/recommendations/feedback/insights", h.proxyWithHeaders)
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
		community.GET("/groups/directory", h.proxyWithHeaders)
		community.GET("/groups/search", h.proxyWithHeaders)
		// Group System
		community.POST("/groups", h.proxyWithHeaders)
		community.GET("/groups", h.proxyWithHeaders)
		community.GET("/groups/recommendations", h.proxyWithHeaders)
		community.POST("/groups/recommendations/feedback", h.proxyWithHeaders)
		community.GET("/groups/:group_id", h.proxyWithHeaders)
		community.DELETE("/groups/:group_id", h.proxyWithHeaders)
		community.POST("/groups/:group_id/join", h.proxyWithHeaders)
		community.POST("/groups/:group_id/leave", h.proxyWithHeaders)
		community.DELETE("/groups/:group_id/leave", h.proxyWithHeaders)
		community.POST("/groups/:group_id/transfer", h.proxyWithHeaders)
		community.GET("/groups/:group_id/members", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/kick", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/promote", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/demote", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/transfer-ownership", h.proxyWithHeaders)
		// Group Messages
		community.GET("/groups/:group_id/messages", h.proxyWithHeaders)
		community.POST("/groups/:group_id/messages", h.proxyWithHeaders)
		community.DELETE("/groups/:group_id/messages/:msg_id", h.proxyWithHeaders)
		community.PATCH("/groups/:group_id/messages/:msg_id", h.proxyWithHeaders)
		community.POST("/groups/:group_id/messages/:msg_id/revoke", h.proxyWithHeaders)
		community.POST("/groups/:group_id/messages/:msg_id/reactions", h.proxyWithHeaders)
		community.POST("/groups/:group_id/messages/read", h.proxyWithHeaders)
		community.GET("/groups/:group_id/threads/:thread_root_id", h.proxyWithHeaders)
		community.GET("/groups/:group_id/messages/search", h.proxyWithHeaders)
		community.POST("/groups/:group_id/messages/search/advanced", h.proxyWithHeaders)
		community.GET("/groups/:group_id/topics", h.proxyWithHeaders)
		// Group Files
		community.POST("/groups/:group_id/files/:file_id/share", h.proxyWithHeaders)
		community.GET("/groups/:group_id/files", h.proxyWithHeaders)
		community.PUT("/groups/:group_id/files/:file_id/permissions", h.proxyWithHeaders)
		community.GET("/groups/:group_id/files/categories", h.proxyWithHeaders)
		// Group Tasks
		community.POST("/groups/:group_id/tasks", h.proxyWithHeaders)
		community.GET("/groups/:group_id/tasks", h.proxyWithHeaders)
		community.POST("/tasks/:task_id/claim", h.proxyWithHeaders)
		// Group Flame
		community.GET("/groups/:group_id/flame", h.proxyWithHeaders)
		// Group Management
		community.PUT("/groups/:group_id/announcement", h.proxyWithHeaders)
		community.PUT("/groups/:group_id/moderation", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/mute", h.proxyWithHeaders)
		community.DELETE("/groups/:group_id/members/:user_id/mute", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/warn", h.proxyWithHeaders)
		community.GET("/groups/:group_id/reports", h.proxyWithHeaders)
		community.GET("/groups/:group_id/resources", h.proxyWithHeaders)
		// Private Messages
		community.POST("/messages", h.proxyWithHeaders)
		community.POST("/messages/private", h.proxyWithHeaders)
		community.GET("/messages/private/:user_id", h.proxyWithHeaders)
		community.DELETE("/messages/private/:msg_id", h.proxyWithHeaders)
		community.PATCH("/messages/:message_id", h.proxyWithHeaders)
		community.POST("/messages/:message_id/revoke", h.proxyWithHeaders)
		community.POST("/messages/:message_id/reactions", h.proxyWithHeaders)
		community.GET("/friends/:friend_id/messages", h.proxyWithHeaders)
		community.GET("/friends/:friend_id/messages/search", h.proxyWithHeaders)
		// Feed & Posts
		community.GET("/feed", h.proxyWithHeaders)
		community.POST("/posts", h.proxyWithHeaders)
		community.POST("/posts/:post_id/like", h.proxyWithHeaders)
		// Check-in
		community.POST("/checkin", h.proxyWithHeaders)
		// User Status
		community.PUT("/status", h.proxyWithHeaders)
		// Share Resources
		community.POST("/share", h.proxyWithHeaders)
		community.POST("/share/:share_id/adopt", h.proxyWithHeaders)
		// Encryption
		community.POST("/encryption/keys", h.proxyWithHeaders)
		community.GET("/encryption/keys/:user_id", h.proxyWithHeaders)
		community.DELETE("/encryption/keys/:key_id", h.proxyWithHeaders)
		// Reports
		community.POST("/reports", h.proxyWithHeaders)
		community.PUT("/reports/:report_id", h.proxyWithHeaders)
		// Favorites
		community.POST("/favorites", h.proxyWithHeaders)
		community.GET("/favorites", h.proxyWithHeaders)
		community.DELETE("/favorites/:favorite_id", h.proxyWithHeaders)
		// Forward
		community.POST("/forward", h.proxyWithHeaders)
		// Broadcast
		community.POST("/broadcast", h.proxyWithHeaders)
		// Offline Messages
		community.GET("/offline/pending", h.proxyWithHeaders)
		community.GET("/offline/failed", h.proxyWithHeaders)
		community.POST("/offline/retry", h.proxyWithHeaders)
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

	// ==================== Background Tasks Routes ====================
	backgroundTasks := api.Group("/background-tasks")
	backgroundTasks.Use(authMiddleware)
	{
		backgroundTasks.GET("", h.proxyWithHeaders)
		backgroundTasks.GET("/stats/summary", h.proxyWithHeaders)
		backgroundTasks.GET("/:task_id", h.proxyWithHeaders)
		backgroundTasks.POST("/:task_id/retry", h.proxyWithHeaders)
		backgroundTasks.POST("/:task_id/cancel", h.proxyWithHeaders)
	}
	h.logger.Info("Registered background-tasks proxy routes")

	// ==================== Predictive Routes ====================
	predictive := api.Group("/predictive")
	predictive.Use(authMiddleware)
	{
		predictive.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered predictive proxy routes")

	// ==================== Ingestion / Documents Routes ====================
	ingestion := api.Group("/ingestion")
	ingestion.Use(authMiddleware)
	{
		ingestion.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered ingestion proxy routes")

	documents := api.Group("/documents")
	documents.Use(authMiddleware)
	{
		documents.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered documents proxy routes")

	// ==================== STT Batch Transcription ====================
	stt := api.Group("/stt")
	stt.Use(authMiddleware)
	{
		stt.POST("/transcribe", h.proxyWithHeaders)
	}
	h.logger.Info("Registered STT proxy routes")

	// ==================== WebSocket Monitoring Routes ====================
	ws := api.Group("/ws")
	ws.Use(authMiddleware)
	{
		ws.GET("/health", h.proxyWithHeaders)
		ws.GET("/stats", h.proxyWithHeaders)
		ws.GET("/metrics", h.proxyWithHeaders)
	}
	h.logger.Info("Registered websocket monitoring proxy routes")

	// ==================== Leaderboards Routes ====================
	leaderboards := api.Group("/leaderboards")
	leaderboards.Use(authMiddleware)
	{
		leaderboards.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered leaderboards proxy routes")

	// ==================== Notification Center Routes ====================
	notifCenter := api.Group("/notification-center")
	notifCenter.Use(authMiddleware)
	{
		notifCenter.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered notification-center proxy routes")

	// ==================== Notifications Routes ====================
	notifications := api.Group("/notifications")
	notifications.Use(authMiddleware)
	{
		notifications.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered notifications proxy routes")

	// ==================== Cognitive Routes ====================
	cognitive := api.Group("/cognitive")
	cognitive.Use(authMiddleware)
	{
		cognitive.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered cognitive proxy routes")

	// ==================== Memory Routes ====================
	memory := api.Group("/memory")
	memory.Use(authMiddleware)
	{
		memory.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered memory proxy routes")

	// ==================== Visual Elements Routes ====================
	visualElements := api.Group("/visual-elements")
	visualElements.Use(authMiddleware)
	{
		visualElements.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered visual-elements proxy routes")

	// ==================== Profile Transparency Routes ====================
	profileTransparency := api.Group("/profile")
	profileTransparency.Use(authMiddleware)
	{
		profileTransparency.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered profile-transparency proxy routes")

	// ==================== Observability Routes ====================
	observability := api.Group("/observability")
	observability.Use(authMiddleware)
	{
		observability.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered observability proxy routes")

	// ==================== Knowledge Theater Routes ====================
	theater := api.Group("/theater")
	theater.Use(authMiddleware)
	{
		theater.POST("/predictions/generate", h.proxyWithHeaders)
		theater.POST("/predictions/what-if", h.proxyWithHeaders)
		theater.POST("/predictions/:id/adopt", h.proxyWithHeaders)
		theater.POST("/predictions/:id/actuals", h.proxyWithHeaders)
		theater.GET("/predictions/:id/accuracy", h.proxyWithHeaders)
		theater.POST("/snapshots", h.proxyWithHeaders)
	}
	h.logger.Info("Registered theater proxy routes")

	// ==================== Simulation Routes ====================
	simulation := api.Group("/simulation")
	simulation.Use(authMiddleware)
	{
		simulation.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered simulation proxy routes")

	// ==================== Learning Reports Routes ====================
	learningReports := api.Group("/learning-reports")
	learningReports.Use(authMiddleware)
	{
		learningReports.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered learning-reports proxy routes")

	// ==================== Shop, Photons, Inventory Routes ====================
	shop := api.Group("/shop")
	shop.Use(authMiddleware)
	{
		shop.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered shop proxy routes")

	photons := api.Group("/photons")
	photons.Use(authMiddleware)
	{
		photons.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered photons proxy routes")

	inventory := api.Group("/inventory")
	inventory.Use(authMiddleware)
	{
		inventory.Any("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered inventory proxy routes")
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
