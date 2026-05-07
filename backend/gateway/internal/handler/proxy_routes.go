/*
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
*/

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

// registerREST registers GET, POST, PUT, PATCH, DELETE for the given relative path.
// This avoids Any() which would also allow CONNECT, TRACE, HEAD, OPTIONS.
func (h *ProxyRoutesHandler) registerREST(rg *gin.RouterGroup, relativePath string) {
	rg.GET(relativePath, h.proxyWithHeaders)
	rg.POST(relativePath, h.proxyWithHeaders)
	rg.PUT(relativePath, h.proxyWithHeaders)
	rg.PATCH(relativePath, h.proxyWithHeaders)
	rg.DELETE(relativePath, h.proxyWithHeaders)
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
		accountability.POST("/struggle-alerts/:notificationId/encourage", h.proxyWithHeaders)
		accountability.POST("/hints/:notificationId/dismiss", h.proxyWithHeaders)
	}
	h.logger.Info("Registered accountability proxy routes")

	// ==================== Tasks Routes ====================
	tasks := api.Group("/tasks")
	tasks.Use(authMiddleware)
	{
		tasks.GET("", h.proxyWithHeaders)
		tasks.POST("", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/reorder", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/suggestions", h.proxyWithHeaders)
		// route-tier: authed
		tasks.GET("/recommendations/micro", h.proxyWithHeaders)
		// route-tier: authed
		tasks.GET("/today", h.proxyWithHeaders)
		// route-tier: authed
		tasks.GET("/recommended", h.proxyWithHeaders)
		tasks.GET("/suggestions", h.proxyWithHeaders)
		// route-tier: authed
		tasks.GET("/feedback/stats", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/feedback/:feedback_id/reflection", h.proxyWithHeaders)
		tasks.GET("/:id", h.proxyWithHeaders)
		// route-tier: authed
		tasks.GET("/:id/resources", h.proxyWithHeaders)
		tasks.PUT("/:id", h.proxyWithHeaders)
		// route-tier: authed
		tasks.DELETE("/:id", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/:id/resources", h.proxyWithHeaders)
		tasks.DELETE("/:id/resources/:resourceId", h.proxyWithHeaders)
		// route-tier: authed
		tasks.GET("/:id/card-protocol", h.proxyWithHeaders)
		tasks.GET("/:id/priority-reasoning", h.proxyWithHeaders)
		// route-tier: authed
	}

	// ==================== Error Book Extended Routes ====================
	errors := api.Group("/errors")
	errors.Use(authMiddleware)
	{
		errors.GET("/remediable-patterns", h.proxyWithHeaders)
		errors.POST("/patterns/:pattern_id/generate-template", h.proxyWithHeaders)
		errors.POST("/patterns/:pattern_id/accept-template", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/:id/generate-guide", h.proxyWithHeaders)
		tasks.POST("/:id/start", h.proxyWithHeaders)
		tasks.POST("/:id/complete", h.proxyWithHeaders)
		tasks.POST("/:id/abandon", h.proxyWithHeaders)
		tasks.POST("/:id/pause", h.proxyWithHeaders)
		tasks.POST("/:id/resume", h.proxyWithHeaders)
		tasks.POST("/:id/stuck", h.proxyWithHeaders)
		tasks.GET("/:id/guidance", h.proxyWithHeaders)
		tasks.POST("/:id/guidance", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/:id/snooze", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/:id/too-hard", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/:id/too_hard", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/:id/skip", h.proxyWithHeaders)
		tasks.POST("/:id/feedback", h.proxyWithHeaders)
		// route-tier: authed
		tasks.GET("/:id/feedback", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/:id/next-action-selection", h.proxyWithHeaders)
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
		// route-tier: authed
		plans.GET("/:id", h.proxyWithHeaders)
		// PUT remains accepted for legacy full-update clients; PATCH is the preferred
		// partial-update method used by the Python plans service.
		plans.PUT("/:id", h.proxyWithHeaders)
		// route-tier: authed
		plans.PATCH("/:id", h.proxyWithHeaders) // Python uses PATCH (not PUT)
		// route-tier: authed
		plans.DELETE("/:id", h.proxyWithHeaders)
		plans.POST("/:id/archive", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/:id/restore", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/:id/generate-tasks", h.proxyWithHeaders)
		// route-tier: authed
		plans.GET("/:id/progress", h.proxyWithHeaders)
		// route-tier: authed
		plans.PATCH("/:id/priority", h.proxyWithHeaders)
		// route-tier: authed
		plans.GET("/:id/learning-path-progress", h.proxyWithHeaders)
			// Plan Phases
			// route-tier: authed
			plans.GET("/:id/phases", h.proxyWithHeaders)
			// route-tier: authed
			plans.POST("/:id/phases/reorder", h.proxyWithHeaders)
			// route-tier: authed
			plans.POST("/phases/:phaseCardId/activate", h.proxyWithHeaders)
	}
	h.logger.Info("Registered plans proxy routes")

	// ==================== Cards Routes ====================
	// route-tier: authed
	cards := api.Group("/cards")
	cards.Use(authMiddleware)
	{
		// Explicit methods rather than Any() to respect HTTP semantics and
		// prevent unintended method exposure (HEAD/CONNECT/TRACE).
		// route-tier: authed
		cards.GET("", h.proxyWithHeaders)
		// route-tier: authed
		cards.POST("", h.proxyWithHeaders)
		// route-tier: authed
		cards.GET("/*path", h.proxyWithHeaders)
		// route-tier: authed
		cards.POST("/*path", h.proxyWithHeaders)
		// route-tier: authed
		cards.PUT("/*path", h.proxyWithHeaders)
		// route-tier: authed
		cards.PATCH("/*path", h.proxyWithHeaders)
		// route-tier: authed
		cards.DELETE("/*path", h.proxyWithHeaders)
	}
	h.logger.Info("Registered cards proxy routes")

	// ==================== Learning Paths Routes ====================
	learningPaths := api.Group("/learning-paths")
	learningPaths.Use(authMiddleware)
	{
		learningPaths.GET("/:target_node_id", h.proxyWithHeaders)
		learningPaths.POST("/:target_node_id/plan", h.proxyWithHeaders)
		learningPaths.POST("/:target_node_id/task-path", h.proxyWithHeaders)
		learningPaths.POST("/:target_node_id/full-plan", h.proxyWithHeaders)
	}
	h.logger.Info("Registered learning paths proxy routes")

	// ==================== Chat Routes ====================
	chat := api.Group("/chat")
	chat.Use(authMiddleware)
	{
		chat.POST("", h.proxyWithHeaders)
		chat.POST("/stream", h.proxyWithHeaders)
		chat.POST("/confirm", h.proxyWithHeaders)
		chat.POST("/task/:task_id", h.proxyWithHeaders)
	}
	h.logger.Info("Registered chat proxy routes")

	// ==================== Users Routes ====================
	users := api.Group("/users")
	users.Use(authMiddleware)
	{
		h.registerREST(users, "/*path")
	}
	h.logger.Info("Registered users proxy routes")

	// ==================== User Settings Routes ====================
	user := api.Group("/user")
	user.Use(authMiddleware)
	{
		h.registerREST(user, "/*path")
	}
	h.logger.Info("Registered user proxy routes")

	// ==================== Achievements Routes ====================
	achievements := api.Group("/achievements")
	achievements.Use(authMiddleware)
	{
		achievements.GET("", h.proxyWithHeaders)
		achievements.GET("/stats", h.proxyWithHeaders)
		achievements.GET("/map", h.proxyWithHeaders)
		achievements.GET("/streak", h.proxyWithHeaders)
		achievements.GET("/streak/history", h.proxyWithHeaders)
		achievements.GET("/:id", h.proxyWithHeaders)
		achievements.POST("/:id/share", h.proxyWithHeaders)
		achievements.GET("/contracts", h.proxyWithHeaders)
		achievements.POST("/:id/pin", h.proxyWithHeaders)
		achievements.POST("/contracts", h.proxyWithHeaders)
		achievements.DELETE("/contracts", h.proxyWithHeaders)
		achievements.GET("/skins", h.proxyWithHeaders)
		achievements.POST("/skins/:skinId/equip", h.proxyWithHeaders)
		achievements.GET("/titles", h.proxyWithHeaders)
		achievements.POST("/titles/:titleId/equip", h.proxyWithHeaders)
		achievements.GET("/close-to-unlock", h.proxyWithHeaders)
		achievements.GET("/share-templates", h.proxyWithHeaders)
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

	// ==================== Experiments Routes ====================
	experiments := api.Group("/experiments")
	experiments.Use(authMiddleware)
	{
		h.registerREST(experiments, "/*path")
		h.registerREST(experiments, "")
	}
	h.logger.Info("Registered experiments proxy routes")

	// ==================== Agent Stats Routes ====================
	agentStats := api.Group("/agent-stats")
	agentStats.Use(authMiddleware)
	{
		h.registerREST(agentStats, "/*path")
	}
	h.logger.Info("Registered agent-stats proxy routes")

	// ==================== Assets Routes ====================
	assets := api.Group("/assets")
	assets.Use(authMiddleware)
	{
		h.registerREST(assets, "/*path")
	}
	h.logger.Info("Registered assets proxy routes")

	// ==================== Multi-Agent Routes ====================
	multiAgent := api.Group("/multi-agent")
	multiAgent.Use(authMiddleware)
	{
		h.registerREST(multiAgent, "/*path")
	}
	h.logger.Info("Registered multi-agent proxy routes")

	// ==================== Goals Routes ====================
	goals := api.Group("/goals")
	goals.Use(authMiddleware)
	{
		goals.GET("/", h.proxyWithHeaders)
		goals.POST("/", h.proxyWithHeaders)
		goals.POST("/decompose-preview", h.proxyWithHeaders)
		goals.GET("/:id", h.proxyWithHeaders)
		goals.PUT("/:id", h.proxyWithHeaders)
		goals.DELETE("/:id", h.proxyWithHeaders)
	}

	// ==================== Insights Routes ====================
	insights := api.Group("/insights")
	insights.Use(authMiddleware)
	{
		insights.GET("/recent-directives", h.proxyWithHeaders)
	}

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

	// ==================== Marketplace Routes ====================
	marketplace := api.Group("/marketplace")
	marketplace.Use(authMiddleware)
	{
		marketplace.GET("/skills", h.proxyWithHeaders)
		marketplace.GET("/skills/:skillId", h.proxyWithHeaders)
		marketplace.GET("/skills/:skillId/preview", h.proxyWithHeaders)
		marketplace.POST("/skills/:skillId/adopt", h.proxyWithHeaders)
		marketplace.GET("/packs", h.proxyWithHeaders)
		marketplace.GET("/packs/:packId", h.proxyWithHeaders)
		marketplace.GET("/packs/:packId/preview", h.proxyWithHeaders)
		marketplace.POST("/packs/:packId/adopt", h.proxyWithHeaders)
		marketplace.POST("/adoptions/:adoptionId/revoke", h.proxyWithHeaders)
		marketplace.GET("/adoptions/:adoptionId/impact", h.proxyWithHeaders)
		marketplace.POST("/adoptions/:adoptionId/impact", h.proxyWithHeaders)
	}
	h.logger.Info("Registered marketplace proxy routes")

	// ==================== Tool History Routes ====================
	toolHistory := api.Group("/tool-history")
	toolHistory.Use(authMiddleware)
	{
		toolHistory.POST("/client-events", h.proxyWithHeaders)
		toolHistory.DELETE("/client-events/:historyId", h.proxyWithHeaders)
	}
	h.logger.Info("Registered tool-history proxy routes")

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
		community.DELETE("/posts/:post_id", h.proxyWithHeaders)
		community.PATCH("/posts/:post_id", h.proxyWithHeaders)
		community.GET("/posts/:post_id/comments", h.proxyWithHeaders)
		community.POST("/posts/:post_id/comments", h.proxyWithHeaders)
		community.DELETE("/posts/:post_id/comments/:comment_id", h.proxyWithHeaders)
		// Check-in
		community.POST("/checkin", h.proxyWithHeaders)
		// User Status
		community.PUT("/status", h.proxyWithHeaders)
		// Share Resources
		community.POST("/share", h.proxyWithHeaders)
		community.POST("/share/:share_id/adopt", h.proxyWithHeaders)
		community.POST("/shared-resources/:shared_resource_id/adopt", h.proxyWithHeaders)
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
		// route-tier: authed
		community.DELETE("/favorites/:favorite_id", h.proxyWithHeaders)
		// Forward
		// route-tier: authed
		community.POST("/forward", h.proxyWithHeaders)
		// Broadcast
		// route-tier: authed
		community.POST("/broadcast", h.proxyWithHeaders)
		// Offline Messages
		// route-tier: authed
		community.GET("/offline/pending", h.proxyWithHeaders)
		// route-tier: authed
		community.GET("/offline/failed", h.proxyWithHeaders)
		// route-tier: authed
		community.POST("/offline/retry", h.proxyWithHeaders)
	}
	h.logger.Info("Registered community proxy routes")

	// ==================== Interventions Routes ====================
	// route-tier: authed
	interventions := api.Group("/interventions")
	interventions.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(interventions, "/*path")
	}
	h.logger.Info("Registered interventions proxy routes")

	// ==================== Dashboard Routes ====================
	dashboard := api.Group("/dashboard")
	dashboard.Use(authMiddleware)
	{
		h.registerREST(dashboard, "/*path")
	}
	h.logger.Info("Registered dashboard proxy routes")

	// ==================== Growth Routes ====================
	// route-tier: authed
	growth := api.Group("/growth")
	growth.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(growth, "/*path")
	}
	h.logger.Info("Registered growth proxy routes")

	// ==================== Exam Sprint Routes ====================
	// route-tier: authed
	examSprint := api.Group("/exam-sprint")
	examSprint.Use(authMiddleware)
	{
		// route-tier: authed
		examSprint.POST("/intake", h.proxyWithHeaders)
		// route-tier: authed
		examSprint.POST("/completion", h.proxyWithHeaders)
		// route-tier: authed
		examSprint.POST("/post-exam-review", h.proxyWithHeaders)
		// route-tier: authed
		examSprint.GET("/portfolio", h.proxyWithHeaders)
	}
	h.logger.Info("Registered exam sprint proxy routes")

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

	// ==================== Reviews Routes ====================
	reviews := api.Group("/reviews")
	reviews.Use(authMiddleware)
	{
		h.registerREST(reviews, "/*path")
	}
	h.logger.Info("Registered reviews proxy routes")

	// ==================== Statistics Routes ====================
	stats := api.Group("/stats")
	stats.Use(authMiddleware)
	{
		h.registerREST(stats, "/*path")
	}
	h.logger.Info("Registered statistics proxy routes")

	// ==================== Events Routes ====================
	events := api.Group("/events")
	events.Use(authMiddleware)
	{
		h.registerREST(events, "/*path")
	}
	h.logger.Info("Registered events proxy routes")

	// ==================== Signals Routes ====================
	signals := api.Group("/signals")
	signals.Use(authMiddleware)
	{
		h.registerREST(signals, "/*path")
	}
	h.logger.Info("Registered signals proxy routes")

	// ==================== Preferences Routes ====================
	preferences := api.Group("/preferences")
	preferences.Use(authMiddleware)
	{
		h.registerREST(preferences, "/*path")
	}
	h.logger.Info("Registered preferences proxy routes")

	// ==================== Notifications Routes ====================
	notifications := api.Group("/notifications")
	notifications.Use(authMiddleware)
	{
		h.registerREST(notifications, "")
		h.registerREST(notifications, "/*path")
	}
	h.logger.Info("Registered notifications proxy routes")

	// ==================== Notification Center Routes ====================
	notificationCenter := api.Group("/notification-center")
	notificationCenter.Use(authMiddleware)
	{
		h.registerREST(notificationCenter, "")
		h.registerREST(notificationCenter, "/*path")
	}
	h.logger.Info("Registered notification-center proxy routes")

	// ==================== Devices Routes ====================
	devices := api.Group("/devices")
	devices.Use(authMiddleware)
	{
		h.registerREST(devices, "/*path")
	}
	h.logger.Info("Registered devices proxy routes")

	// ==================== OmniBar Routes ====================
	omnibar := api.Group("/omnibar")
	omnibar.Use(authMiddleware)
	{
		h.registerREST(omnibar, "/*path")
	}
	h.logger.Info("Registered omnibar proxy routes")

	// ==================== Prediction Routes ====================
	prediction := api.Group("/prediction")
	prediction.Use(authMiddleware)
	{
		h.registerREST(prediction, "/*path")
	}
	h.logger.Info("Registered prediction proxy routes")

	// ==================== Multi-Intent Routes ====================
	multiIntent := api.Group("/multi-intent")
	multiIntent.Use(authMiddleware)
	{
		h.registerREST(multiIntent, "/*path")
	}
	h.logger.Info("Registered multi-intent proxy routes")

	// ==================== Subjects Routes ====================
	subjects := api.Group("/subjects")
	subjects.Use(authMiddleware)
	{
		h.registerREST(subjects, "")
		h.registerREST(subjects, "/*path")
	}
	h.logger.Info("Registered subjects proxy routes")

	// ==================== Client Telemetry Routes ====================
	clientTelemetry := api.Group("/client-telemetry")
	clientTelemetry.Use(authMiddleware)
	{
		clientTelemetry.POST("/events", h.proxyWithHeaders)
		clientTelemetry.POST("/events/batch", h.proxyWithHeaders)
		clientTelemetry.GET("/summary", h.proxyWithHeaders)
	}
	h.logger.Info("Registered client-telemetry proxy routes")

	// ==================== Predictive Routes ====================
	predictive := api.Group("/predictive")
	predictive.Use(authMiddleware)
	{
		h.registerREST(predictive, "/*path")
	}
	h.logger.Info("Registered predictive proxy routes")

	// ==================== Ingestion / Documents Routes ====================
	ingestion := api.Group("/ingestion")
	ingestion.Use(authMiddleware)
	{
		h.registerREST(ingestion, "/*path")
	}
	h.logger.Info("Registered ingestion proxy routes")

	documents := api.Group("/documents")
	documents.Use(authMiddleware)
	{
		h.registerREST(documents, "/*path")
	}
	h.logger.Info("Registered documents proxy routes")

	// route-tier: authed
	sources := api.Group("/sources")
	sources.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(sources, "/*path")
	}
	h.logger.Info("Registered sources proxy routes")

	// ==================== STT Batch Transcription ====================
	stt := api.Group("/stt")
	stt.Use(authMiddleware)
	{
		stt.POST("/transcribe", h.proxyWithHeaders)
	}
	h.logger.Info("Registered STT proxy routes")

	// ==================== Focus Routes ====================
	focus := api.Group("/focus")
	focus.Use(authMiddleware)
	{
		h.registerREST(focus, "/*path")
	}
	h.logger.Info("Registered focus proxy routes")

	// ==================== Vocabulary Routes ====================
	vocabulary := api.Group("/vocabulary")
	vocabulary.Use(authMiddleware)
	{
		h.registerREST(vocabulary, "/*path")
	}
	h.logger.Info("Registered vocabulary proxy routes")

	// ==================== Translation Routes ====================
	translation := api.Group("/translation")
	translation.Use(authMiddleware)
	{
		h.registerREST(translation, "/*path")
	}
	h.logger.Info("Registered translation proxy routes")

	// ==================== Decay TimeMachine Routes ====================
	decay := api.Group("/decay")
	decay.Use(authMiddleware)
	{
		h.registerREST(decay, "/*path")
	}
	h.logger.Info("Registered decay proxy routes")

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
		h.registerREST(leaderboards, "/*path")
	}
	h.logger.Info("Registered leaderboards proxy routes")

	// ==================== Cognitive Routes ====================
	cognitive := api.Group("/cognitive")
	cognitive.Use(authMiddleware)
	{
		h.registerREST(cognitive, "/*path")
	}
	h.logger.Info("Registered cognitive proxy routes")

	// ==================== Memory Routes ====================
	memory := api.Group("/memory")
	memory.Use(authMiddleware)
	{
		h.registerREST(memory, "/*path")
	}
	h.logger.Info("Registered memory proxy routes")

	// ==================== Visual Elements Routes ====================
	visualElements := api.Group("/visual-elements")
	visualElements.Use(authMiddleware)
	{
		h.registerREST(visualElements, "")
		h.registerREST(visualElements, "/*path")
	}
	h.logger.Info("Registered visual-elements proxy routes")

	// ==================== Profile Transparency Routes ====================
	// route-tier: authed
	profileTransparency := api.Group("/profile")
	profileTransparency.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(profileTransparency, "/*path")
	}
	h.logger.Info("Registered profile-transparency proxy routes")

	// ==================== Experience Routes ====================
	experience := api.Group("/experience")
	experience.Use(authMiddleware)
	{
		h.registerREST(experience, "/*path")
	}
	h.logger.Info("Registered experience proxy routes")

	// ==================== Observability Routes ====================
	// route-tier: authed
	observability := api.Group("/observability")
	observability.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(observability, "/*path")
	}
	h.logger.Info("Registered observability proxy routes")

	// ==================== Knowledge Theater Routes ====================
	// route-tier: authed
	theater := api.Group("/theater")
	theater.Use(authMiddleware)
	{
		// route-tier: authed
		theater.POST("/predictions/generate", h.proxyWithHeaders)
		theater.POST("/predictions/what-if", h.proxyWithHeaders)
		// route-tier: authed
		theater.GET("/predictions/:id", h.proxyWithHeaders)
		// route-tier: authed
		theater.POST("/predictions/:id/adopt", h.proxyWithHeaders)
		theater.POST("/predictions/:id/actuals", h.proxyWithHeaders)
		// route-tier: authed
		theater.POST("/predictions/:id/promote-node", h.proxyWithHeaders)
		theater.GET("/predictions/:id/accuracy", h.proxyWithHeaders)
		// route-tier: authed
		theater.GET("/accuracy/overview", h.proxyWithHeaders)
		// route-tier: authed
		theater.POST("/snapshots", h.proxyWithHeaders)
	}
	h.logger.Info("Registered theater proxy routes")

	// ==================== Simulation Routes ====================
	// route-tier: authed
	simulation := api.Group("/simulation")
	simulation.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(simulation, "/*path")
	}
	h.logger.Info("Registered simulation proxy routes")

	// ==================== Executions / OpenClaw Routes ====================
	// route-tier: authed
	executions := api.Group("/executions")
	executions.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(executions, "")
		// route-tier: authed
		h.registerREST(executions, "/*path")
	}
	h.logger.Info("Registered executions proxy routes")

	// ==================== Admin Executions / OpenClaw Routes ====================
	// route-tier: internal
	adminExecutions := api.Group("/admin/executions")
	adminExecutions.Use(authMiddleware, middleware.RequireAdmin)
	{
		// route-tier: authed
		h.registerREST(adminExecutions, "")
		// route-tier: authed
		h.registerREST(adminExecutions, "/*path")
	}
	h.logger.Info("Registered admin executions proxy routes")

	// ==================== Learning Reports Routes ====================
	learningReports := api.Group("/learning-reports")
	learningReports.Use(authMiddleware)
	{
		h.registerREST(learningReports, "/*path")
	}
	h.logger.Info("Registered learning-reports proxy routes")

	// ==================== Shop, Photons, Inventory Routes ====================
	shop := api.Group("/shop")
	shop.Use(authMiddleware)
	{
		h.registerREST(shop, "/*path")
	}
	h.logger.Info("Registered shop proxy routes")

	photons := api.Group("/photons")
	photons.Use(authMiddleware)
	{
		h.registerREST(photons, "/*path")
	}
	h.logger.Info("Registered photons proxy routes")

	inventory := api.Group("/inventory")
	inventory.Use(authMiddleware)
	{
		h.registerREST(inventory, "/*path")
	}
	h.logger.Info("Registered inventory proxy routes")

	// ==================== Aurora Routes ====================
	aurora := api.Group("/aurora")
	aurora.Use(authMiddleware)
	{
		h.registerREST(aurora, "/*path")
	}
	h.logger.Info("Registered aurora proxy routes (catch-all)")

		// ==================== Missing Proxy Routes ====================

		for _, r := range []struct {
			prefix string
			name   string
		}{
			{"/analytics", "analytics"},
			{"/error-book", "error-book"},
			{"/safe-experiments", "safe-experiments"},
			{"/skills", "skills"},
			{"/scenario-packs", "scenario-packs"},
			{"/subtasks", "subtasks"},
		} {
			rg := api.Group(r.prefix)
			rg.Use(authMiddleware)
			h.registerREST(rg, "/*path")
			h.logger.Info("Registered " + r.name + " proxy routes")
		}

	// Health routes are handled locally by the gateway (setup.go) — do not proxy
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
