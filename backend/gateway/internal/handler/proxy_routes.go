/*
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
*/

// Package handler provides explicit proxy routes for Python Backend APIs
package handler

import (
	"net/http/httputil"
	"strings"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/middleware"
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
//
// For wildcard groups ("/*path") it additionally:
//  1. registers the bare collection path ("") — gin's httprouter does NOT match
//     "/group" against "/group/*path", so without this the bare request is met
//     by gin's RedirectTrailingSlash 301 → "/group/", which the FastAPI engine
//     (redirect_slashes) bounces back with a 307 whose Location is an absolute
//     internal URL (http://127.0.0.1:8000/...), producing the 301↔307 redirect
//     loop + intranet address leak observed on /api/v1/leaderboards and
//     /api/v1/inventory (gamification-eval P1-2); and
//  2. trims trailing slashes on wildcard-matched paths before proxying, since
//     FastAPI canonicalizes to non-slash routes and its 307 Location would leak
//     the internal topology to clients.
func (h *ProxyRoutesHandler) registerREST(rg *gin.RouterGroup, relativePath string) {
	handler := h.proxyWithHeaders
	if relativePath == "/*path" {
		// Bare collection path ("/api/v1/<group>") must proxy directly.
		rg.GET("", handler)
		rg.POST("", handler)
		rg.PUT("", handler)
		rg.PATCH("", handler)
		rg.DELETE("", handler)
		handler = h.proxyWithHeadersTrailingSlashTrimmed
	}
	rg.GET(relativePath, handler)
	rg.POST(relativePath, handler)
	rg.PUT(relativePath, handler)
	rg.PATCH(relativePath, handler)
	rg.DELETE(relativePath, handler)
}

// RegisterProxyRoutes registers all explicit proxy routes to Python Backend
func (h *ProxyRoutesHandler) RegisterProxyRoutes(
	api *gin.RouterGroup,
	authMiddleware gin.HandlerFunc,
) {
	// ==================== Billing Routes (D-REDEEM) ====================
	// route-tier: authed
	billing := api.Group("/billing")
	billing.Use(authMiddleware)
	{
		// 用户核销兑换码；admin 批量生成面按 marketplace/seed-libraries
		// admin 先例 engine-side only。
		// route-tier: authed
		billing.POST("/redeem", h.proxyWithHeaders)
	}
	h.logger.Info("Registered billing proxy routes")

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
		// R2-08 §2.2 #12: GET /suggestions removed — the engine only serves
		// POST /suggestions (the surviving sibling above).
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
		tasks.GET("/:id/documents", h.proxyWithHeaders)
		tasks.POST("/:id/documents", h.proxyWithHeaders)
		tasks.DELETE("/:id/documents", h.proxyWithHeaders)
		tasks.GET("/:id/card-protocol", h.proxyWithHeaders)
		tasks.GET("/:id/priority-reasoning", h.proxyWithHeaders)
		// route-tier: authed
	}

	// ==================== Tasks Action Routes ====================
	// Task state-transition and action routes registered on the tasks group,
	// not inside the errors group — they belong to the tasks resource.
	{
		// route-tier: authed
		tasks.POST("/:id/generate-guide", h.proxyWithHeaders)
		tasks.POST("/:id/start", h.proxyWithHeaders)
		tasks.POST("/:id/complete", h.proxyWithHeaders)
		tasks.POST("/:id/abandon", h.proxyWithHeaders)
		tasks.POST("/:id/pause", h.proxyWithHeaders)
		tasks.POST("/:id/resume", h.proxyWithHeaders)
		// R2-08 §2.2 #11 removed POST /:id/reopen ("engine has no reopen
		// transition") — superseded by X-04: the engine now serves
		// POST /tasks/{task_id}/reopen and mobile calls it
		// (api_endpoints.dart reopenTask). GUARD-DEBT restored the proxy.
		// route-tier: authed
		tasks.POST("/:id/reopen", h.proxyWithHeaders) // rule-bm: ignore engine gained this reopen surface post-R2-08 (X-04)
		// X-04 rescope (engine POST /tasks/{task_id}/rescope; mobile rescopeTask).
		// route-tier: authed
		tasks.POST("/:id/rescope", h.proxyWithHeaders)
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
		tasks.POST("/confirm-batch/:toolResultId", h.proxyWithHeaders)
		tasks.POST("/:id/feedback", h.proxyWithHeaders)
		// route-tier: authed
		tasks.GET("/:id/feedback", h.proxyWithHeaders)
		// route-tier: authed
		tasks.POST("/:id/next-action-selection", h.proxyWithHeaders)
	}

	// ==================== Error Book Extended Routes ====================
	errors := api.Group("/errors")
	errors.Use(authMiddleware)
	{
		errors.GET("/remediable-patterns", h.proxyWithHeaders)
		errors.POST("/patterns/:pattern_id/generate-template", h.proxyWithHeaders)
		errors.POST("/patterns/:pattern_id/accept-template", h.proxyWithHeaders)
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
		// R2-08-03: /plans/active 为移动端首页活跃消费端点（home_growth_provider）。
		plans.GET("/active", h.proxyWithHeaders)
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
		// R2-08-03: 新版计划阶段/探索管线（引擎 18 条路由此前从移动端不可达）。
		// Phase cards（activate 兄弟路由；complete/feedback/schedule-regenerate
		// 为移动端 api_endpoints.dart 既有常量）
		// route-tier: authed
		plans.POST("/phases/:phaseCardId/complete", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/phases/:phaseCardId/design-tasks", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/phases/:phaseCardId/feedback", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/phases/:phaseCardId/feedback-gate/start", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/phases/:phaseCardId/schedule/regenerate", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/phases/feedback-gate/:sessionId/respond", h.proxyWithHeaders)
		// Discovery 探索管线
		// route-tier: authed
		plans.POST("/discovery/start", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/discovery/:sessionId/turn", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/discovery/:sessionId/finalize", h.proxyWithHeaders)
		// Compass 评审管线
		// route-tier: authed
		plans.POST("/compass/:artifactId/approve", h.proxyWithHeaders)
		// route-tier: authed
		plans.GET("/:id/compass/review", h.proxyWithHeaders)
		// Phase sketch + 计划执行状态机
		// route-tier: authed
		plans.POST("/:id/phase-sketch/generate", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/:id/phase-sketch/:artifactId/materialize", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/:id/advance-phase", h.proxyWithHeaders)
		// route-tier: authed
		plans.GET("/:id/planning-context", h.proxyWithHeaders)
		// route-tier: authed
		// R2 fix (schema-route-tail): method drift corrected POST -> GET; the
		// engine only serves GET /plans/{plan_id}/today (api/v1/plans.py:851),
		// engine is source of truth — POST here proxied to 405/404.
		plans.GET("/:id/today", h.proxyWithHeaders)
		// route-tier: authed
		plans.POST("/:id/phases", h.proxyWithHeaders)
	}
	h.logger.Info("Registered plans proxy routes")

	// ==================== Cards Routes ====================
	// route-tier: authed
	cards := api.Group("/cards")
	cards.Use(authMiddleware)
	{
		// Explicit methods rather than Any() to respect HTTP semantics and
		// prevent unintended method exposure (HEAD/CONNECT/TRACE).
		// R2-08 §2.2 #4-7: bare GET/POST /cards and the PATCH/PUT wildcard
		// method-faces are dead (the engine has no such surface) — removed.
		// route-tier: authed
		cards.GET("/*path", h.proxyWithHeaders)
		// route-tier: authed
		cards.POST("/*path", h.proxyWithHeaders)
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
		// route-tier: authed
		calendar.GET("", h.proxyWithHeaders)
		// route-tier: authed
		calendar.POST("", h.proxyWithHeaders)
		// route-tier: authed
		calendar.GET("/summary", h.proxyWithHeaders)
		// route-tier: authed
		calendar.GET("/:id", h.proxyWithHeaders)
		// route-tier: authed
		calendar.PUT("/:id", h.proxyWithHeaders)
		// route-tier: authed
		calendar.DELETE("/:id", h.proxyWithHeaders)
		calendar.POST("/batch", h.proxyWithHeaders)
		calendar.POST("/suggest-time", h.proxyWithHeaders)
	}
	h.logger.Info("Registered calendar proxy routes")

	// ==================== Recommendations Routes ====================
	// R2-08-04: 引擎无 bare GET /recommendations 与 POST /feedback（两条死路由
	// 已删）；改为注册引擎真实挂载的 6 条（移动端 api_endpoints.dart 全量消费）。
	recommendations := api.Group("/recommendations")
	recommendations.Use(authMiddleware)
	{
		// route-tier: authed
		recommendations.GET("/collaborative", h.proxyWithHeaders)
		// route-tier: authed
		recommendations.GET("/similar-users", h.proxyWithHeaders)
		// route-tier: authed
		recommendations.GET("/similar-items", h.proxyWithHeaders)
		// route-tier: authed
		recommendations.GET("/my-interactions", h.proxyWithHeaders)
		// route-tier: authed
		recommendations.POST("/record-interaction", h.proxyWithHeaders)
		// route-tier: authed
		recommendations.GET("/stats", h.proxyWithHeaders)
	}
	h.logger.Info("Registered recommendations proxy routes")

	// ==================== Reflections Routes ====================
	reflections := api.Group("/reflections")
	reflections.Use(authMiddleware)
	{
		reflections.GET("/summary", h.proxyWithHeaders)
	}
	h.logger.Info("Registered reflections proxy routes")

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
		// R2 fix (schema-route-tail): GET /:id removed — the engine has no
		// GET-by-id on goals (only PUT/DELETE /{goal_id}); the GET face here
		// proxied to engine 404. Mobile reads goal detail from list payloads.
		goals.PUT("/:id", h.proxyWithHeaders)
		// R2-08 §2.2 #13: PATCH /:id removed — the engine only serves
		// PUT /goals/{goal_id}; the PUT sibling above stays.
		goals.DELETE("/:id", h.proxyWithHeaders)
	}

	// ==================== Insights Routes ====================
	insights := api.Group("/insights")
	insights.Use(authMiddleware)
	{
		insights.GET("/recent-directives", h.proxyWithHeaders)
		// route-tier: authed — 数据飞轮：理解深度每日基线趋势（user-id 由网关注入）
		insights.GET("/understanding-depth", h.proxyWithHeaders)
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
		// R2-08 §2.2 #19: DELETE leave removed — the engine only serves
		// POST leave.
		community.POST("/groups/:group_id/transfer", h.proxyWithHeaders)
		community.GET("/groups/:group_id/members", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/kick", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/promote", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/demote", h.proxyWithHeaders)
		community.POST("/groups/:group_id/members/:user_id/transfer-ownership", h.proxyWithHeaders)
		// Group Messages
		community.GET("/groups/:group_id/messages", h.proxyWithHeaders)
		community.POST("/groups/:group_id/messages", h.proxyWithHeaders)
		// R2-08 §2.2 #20: DELETE group message removed — the engine only
		// serves PATCH edit + POST revoke (below).
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
		// R2-08 §2.2 #15-17: the /messages/private trio is removed — the
		// engine has no private-message surface; DMs live under
		// /friends/{id}/messages (below).
		community.POST("/messages", h.proxyWithHeaders)
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
		// R2-08 §2.2 #18: PATCH /posts/{id} removed — the engine has no
		// post edit surface.
		community.GET("/posts/:post_id/comments", h.proxyWithHeaders)
		community.POST("/posts/:post_id/comments", h.proxyWithHeaders)
		community.DELETE("/posts/:post_id/comments/:comment_id", h.proxyWithHeaders)
		// Check-in
		community.POST("/checkin", h.proxyWithHeaders)
		// User Status
		community.PUT("/status", h.proxyWithHeaders)
		// Share Resources
		community.POST("/share", h.proxyWithHeaders)
		// R2-08 §2.2 #21: the /share/{id}/adopt old alias is removed —
		// adoption lives at /shared-resources/{id}/adopt (below).
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
		// R2 fix (M-5): engine also serves GET /dashboard, POST /diagnose/generate,
		// POST /diagnose/grade and GET /sprint-summary; without them the gateway
		// answers 404 while the engine route exists (engine is source of truth).
		examSprint.GET("/dashboard", h.proxyWithHeaders)
		// route-tier: authed
		examSprint.POST("/diagnose/generate", h.proxyWithHeaders)
		// route-tier: authed
		examSprint.POST("/diagnose/grade", h.proxyWithHeaders)
		// route-tier: authed
		examSprint.GET("/sprint-summary", h.proxyWithHeaders)
		// route-tier: authed
		// R2-08 §2.2 #10: method corrected POST -> GET; the engine only
		// serves GET /completion (plan_id query param).
		examSprint.GET("/completion", h.proxyWithHeaders)
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
		h.registerREST(notifications, "/*path")
	}
	h.logger.Info("Registered notifications proxy routes")

	// ==================== Notification Center Routes ====================
	notificationCenter := api.Group("/notification-center")
	notificationCenter.Use(authMiddleware)
	{
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
	// route-tier: authed
	prediction := api.Group("/prediction")
	prediction.Use(authMiddleware)
	{
		h.registerREST(prediction, "/*path")
	}
	h.logger.Info("Registered prediction proxy routes")

	// ==================== Multi-Intent Routes ====================
	// route-tier: authed
	multiIntent := api.Group("/multi-intent")
	multiIntent.Use(authMiddleware)
	{
		h.registerREST(multiIntent, "/*path")
	}
	h.logger.Info("Registered multi-intent proxy routes")

	// ==================== Subjects Routes ====================
	// route-tier: authed
	subjects := api.Group("/subjects")
	subjects.Use(authMiddleware)
	{
		h.registerREST(subjects, "/*path")
	}
	h.logger.Info("Registered subjects proxy routes")

	// ==================== Client Telemetry Routes ====================
	clientTelemetry := api.Group("/client-telemetry")
	{
		// Anonymous ingest: pre-login telemetry batches must reach the
		// backend without auth (contract:
		// TestProxyRoutesHandler_ClientTelemetryAuthBoundary).
		// route-tier: public
		clientTelemetry.POST("/events", h.proxyWithHeaders)
		// route-tier: public
		clientTelemetry.POST("/events/batch", h.proxyWithHeaders)

		// Aggregated summaries stay behind auth.
		// route-tier: authed
		authedTelemetry := clientTelemetry.Group("")
		authedTelemetry.Use(authMiddleware)
		// route-tier: authed
		authedTelemetry.GET("/summary", h.proxyWithHeaders)
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

	// files 组已有 Go 本地实现（file_handler.go：upload/:file_id/download/thumbnail），
	// 这里只补 Python 侧两条：POST /files/process（触发 Celery 处理）与
	// GET /files/{file_id}/status（处理状态轮询）——上传链路演示依赖（2026-09-20 盘点补）
	files := api.Group("/files")
	files.Use(authMiddleware)
	{
		files.POST("/process", h.proxyWithHeaders)
		files.GET("/:file_id/status", h.proxyWithHeaders)
	}
	h.logger.Info("Registered files proxy routes")

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

	// ==================== TTS Synthesis（百炼 qwen3-tts，服务端合成） ====================
	tts := api.Group("/tts")
	tts.Use(authMiddleware)
	{
		tts.POST("/synthesize", h.proxyWithHeaders)
	}
	h.logger.Info("Registered TTS proxy routes")

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
	// R2-08-10: /api/v1/observability/* 整组死代理已移除。引擎真身挂载在
	// /api/v1/admin/observability/*（observability.py prefix），由下方
	// /admin catch-all 组（RequireAdmin）代理，此处重复注册只会 404。

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
		h.registerREST(executions, "/*path")
	}
	h.logger.Info("Registered executions proxy routes")

	// ==================== Agent Runs Routes (X-05 unified run state) ====================
	// route-tier: authed
	runs := api.Group("/runs")
	runs.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(runs, "/*path")
	}
	h.logger.Info("Registered agent runs proxy routes")

	// ==================== Action Proposals Routes (X-03 unified command path) ====================
	// route-tier: authed
	actionProposals := api.Group("/action-proposals")
	actionProposals.Use(authMiddleware)
	{
		// route-tier: authed
		h.registerREST(actionProposals, "/*path")
	}
	h.logger.Info("Registered action proposals proxy routes")

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

	// route-tier: authed
	inventory := api.Group("/inventory")
	inventory.Use(authMiddleware)
	{
		h.registerREST(inventory, "/*path")
	}
	h.logger.Info("Registered inventory proxy routes")

	// ==================== Aurora Routes ====================
	// route-tier: authed
	aurora := api.Group("/aurora")
	aurora.Use(authMiddleware)
	{
		h.registerREST(aurora, "/*path")
	}
	h.logger.Info("Registered aurora proxy routes (catch-all)")

	// ==================== Galaxy Routes ====================
	// Note: galaxy_handler.RegisterRoutes() already registers specific routes.
	// A catch-all /*path would conflict with those concrete routes.
	// Unmatched galaxy paths fall through to NoRoute proxy.
	h.logger.Info("Skipped galaxy proxy catch-all (handled by galaxy_handler)")

	// ==================== Missing Proxy Routes ====================

	for _, r := range []struct {
		prefix string
		name   string
	}{
		{"/analytics", "analytics"},
		{"/audit", "audit"},
		{"/counterfactual", "counterfactual"},
		{"/error-book", "error-book"},
		// R2-08-10: "/event-bus" 死代理已移除——引擎真身在
		// /api/v1/admin/event-bus/*（event_bus_health.py, prefix=/admin），
		// 由 /admin catch-all 组（RequireAdmin）覆盖，本组只会 404。
		// Engine mounts /api/v1/release_approvals (underscore); the path must match or every proxied request 404s.
		{"/release_approvals", "release_approvals"},
		{"/research", "research"},
		{"/safe-experiments", "safe-experiments"},
		{"/scenario-packs", "scenario-packs"},
		{"/skills", "skills"},
		{"/subtasks", "subtasks"},
	} {
		rg := api.Group(r.prefix)
		rg.Use(authMiddleware)
		h.registerREST(rg, "/*path")
		h.logger.Info("Registered " + r.name + " proxy routes")
	}
	// R2-08 §2.2 #14: the GET /cqrs/dlq/stats proxy group is removed — the
	// engine has no /api/v1/cqrs/* surface (DLQ truth lives under /dlq/* and
	// the /admin catch-all below).

	// ==================== DLQ Admin Routes ====================
	dlq := api.Group("/dlq")
	dlq.Use(authMiddleware, middleware.RequireAdmin)
	{
		dlq.GET("/", h.proxyWithHeaders)
		dlq.GET("/main-events", h.proxyWithHeaders)
		dlq.POST("/replay", h.proxyWithHeaders)
	}
	h.logger.Info("Registered DLQ admin proxy routes")

	// ==================== Admin Catch-All Routes ====================
	admin := api.Group("/admin")
	admin.Use(authMiddleware, middleware.RequireAdmin)
	{
		h.registerREST(admin, "/*path")
	}
	h.logger.Info("Registered admin proxy routes (catch-all)")

	// Health routes are handled locally by the gateway (setup.go) — do not proxy
}

// proxyWithHeadersTrailingSlashTrimmed proxies the request like proxyWithHeaders
// but trims trailing slashes from the path first. FastAPI (engine) responds to a
// trailing-slash request with a 307 whose Location is an absolute internal URL
// (e.g. http://127.0.0.1:8000/api/v1/...), leaking intranet topology to the
// client and bouncing Dio's redirect limit. The engine's canonical routes never
// require a trailing slash, so trimming is always safe.
func (h *ProxyRoutesHandler) proxyWithHeadersTrailingSlashTrimmed(c *gin.Context) {
	p := c.Request.URL.Path
	if trimmed := strings.TrimRight(p, "/"); trimmed != p && trimmed != "" {
		c.Request.URL.Path = trimmed
		c.Request.URL.RawPath = ""
	}
	h.proxyWithHeaders(c)
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
