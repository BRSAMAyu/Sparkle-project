package handler

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
	"net/url"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/middleware"
	"go.uber.org/zap"
)

func TestProxyRoutesHandler_RouteRegistration(t *testing.T) {
	// Test that routes are properly registered
	gin.SetMode(gin.TestMode)
	logger := zap.NewNop()

	// Create a dummy proxy
	backendURL, _ := url.Parse("http://backend:8000")
	proxy := httputil.NewSingleHostReverseProxy(backendURL)

	// Create A/B test middleware
	abTestConfig := &middleware.ABTestConfig{
		BackendURL: "http://backend:8000",
		Timeout:    3 * time.Second,
		Enabled:    false,
	}
	abTestMiddleware := middleware.NewABTestMiddleware(abTestConfig)

	// Create handler
	h := NewProxyRoutesHandler(proxy, abTestMiddleware, logger)

	// Verify handler is created
	if h == nil {
		t.Fatal("NewProxyRoutesHandler returned nil")
	}

	if h.proxy == nil {
		t.Error("proxy field is nil")
	}

	if h.abTestMiddleware == nil {
		t.Error("abTestMiddleware field is nil")
	}

	if h.logger == nil {
		t.Error("logger field is nil")
	}
}

func TestProxyRoutesHandler_RegisterProxyRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	logger := zap.NewNop()

	// Create a dummy proxy
	backendURL, _ := url.Parse("http://backend:8000")
	proxy := httputil.NewSingleHostReverseProxy(backendURL)

	// Create A/B test middleware
	abTestConfig := &middleware.ABTestConfig{
		BackendURL: "http://backend:8000",
		Timeout:    3 * time.Second,
		Enabled:    false,
	}
	abTestMiddleware := middleware.NewABTestMiddleware(abTestConfig)

	// Create handler
	h := NewProxyRoutesHandler(proxy, abTestMiddleware, logger)

	// Create router
	router := gin.New()
	api := router.Group("/api/v1")

	// Mock auth middleware
	mockAuthMiddleware := func(c *gin.Context) {
		c.Set("user_id", "test-user-123")
		c.Set("auth_token", "test-token-abc")
		c.Next()
	}

	// Register routes - this should not panic
	h.RegisterProxyRoutes(api, mockAuthMiddleware)

	// Verify routes are registered by checking the router's routes
	routes := router.Routes()

	// Expected route patterns for accountability
	expectedAccountabilityRoutes := []string{
		"POST /api/v1/accountability/request",
		"POST /api/v1/accountability/:id/respond",
		"GET /api/v1/accountability/mine",
		"GET /api/v1/accountability/overview",
		"DELETE /api/v1/accountability/:id",
		"POST /api/v1/accountability/:id/checkin",
		"POST /api/v1/accountability/:id/nudge",
		"GET /api/v1/accountability/:id/dashboard",
		"GET /api/v1/accountability/:id/stats",
	}

	expectedCommunityRoutes := []string{
		"GET /api/v1/community/friends",
		"POST /api/v1/community/friends/recommendations/feedback",
		"GET /api/v1/community/friends/:friend_id/profile",
		"GET /api/v1/community/recommendations/feedback/prompts",
		"GET /api/v1/community/recommendations/feedback/insights",
		"GET /api/v1/community/groups/directory",
	}

	// Expected route patterns for tasks
	expectedTasksRoutes := []string{
		"GET /api/v1/tasks",
		"POST /api/v1/tasks",
		"POST /api/v1/tasks/reorder",
		"POST /api/v1/tasks/suggestions",
		"GET /api/v1/tasks/recommendations/micro",
		"GET /api/v1/tasks/today",
		"GET /api/v1/tasks/:id",
		"GET /api/v1/tasks/:id/resources",
		"PUT /api/v1/tasks/:id",
		"DELETE /api/v1/tasks/:id",
		"POST /api/v1/tasks/:id/resources",
		"DELETE /api/v1/tasks/:id/resources/:resourceId",
		"POST /api/v1/tasks/:id/generate-guide",
		"POST /api/v1/tasks/:id/start",
		"POST /api/v1/tasks/:id/complete",
		"POST /api/v1/tasks/:id/abandon",
		"POST /api/v1/tasks/:id/snooze",
		"POST /api/v1/tasks/:id/too-hard",
		"POST /api/v1/tasks/:id/too_hard",
		"POST /api/v1/tasks/:id/skip",
		"POST /api/v1/tasks/:id/feedback",
		"GET /api/v1/tasks/:id/feedback",
		"GET /api/v1/tasks/feedback/stats",
		"POST /api/v1/tasks/feedback/:feedback_id/reflection",
		"POST /api/v1/tasks/:id/next-action-selection",
	}

	// Expected route patterns for plans (Python uses PATCH, not PUT)
	expectedPlansRoutes := []string{
		"GET /api/v1/plans",
		"POST /api/v1/plans",
		"GET /api/v1/plans/:id",
		"PATCH /api/v1/plans/:id",
		"DELETE /api/v1/plans/:id",
		"POST /api/v1/plans/:id/archive",
	}

	expectedLearningPathRoutes := []string{
		"GET /api/v1/learning-paths/:target_node_id",
		"POST /api/v1/learning-paths/:target_node_id/plan",
		"POST /api/v1/learning-paths/:target_node_id/task-path",
		"POST /api/v1/learning-paths/:target_node_id/full-plan",
	}

	expectedChatRoutes := []string{
		"POST /api/v1/chat",
		"POST /api/v1/chat/stream",
		"POST /api/v1/chat/confirm",
		"POST /api/v1/chat/task/:task_id",
		"GET /api/v1/users/*path",
	}

	expectedTelemetryRoutes := []string{
		"POST /api/v1/client-telemetry/events",
		"POST /api/v1/client-telemetry/events/batch",
		"GET /api/v1/client-telemetry/summary",
	}

	expectedAdditionalRoutes := []string{
		"POST /api/v1/community/shared-resources/:shared_resource_id/adopt",
		"GET /api/v1/theater/predictions/:id",
		"POST /api/v1/theater/predictions/:id/promote-node",
		"GET /api/v1/theater/accuracy/overview",
		"GET /api/v1/visual-elements",
		"GET /api/v1/user/*path",
		"GET /api/v1/achievements/streak/history",
		"GET /api/v1/experiments",
		"GET /api/v1/reviews/*path",
		"GET /api/v1/stats/*path",
		"GET /api/v1/events/*path",
		"GET /api/v1/signals/*path",
		"GET /api/v1/preferences/*path",
		"GET /api/v1/notifications",
		"GET /api/v1/notification-center",
		"GET /api/v1/notification-center/*path",
		"GET /api/v1/devices/*path",
		"GET /api/v1/omnibar/*path",
		"GET /api/v1/prediction/*path",
		"GET /api/v1/growth/*path",
		"POST /api/v1/exam-sprint/intake",
		"GET /api/v1/multi-intent/*path",
		"GET /api/v1/multi-agent/*path",
		"GET /api/v1/subjects",
		"GET /api/v1/focus/*path",
		"GET /api/v1/vocabulary/*path",
		"POST /api/v1/translation/*path",
		"GET /api/v1/decay/*path",
		"GET /api/v1/executions",
		"GET /api/v1/executions/*path",
		"GET /api/v1/admin/executions",
		"GET /api/v1/admin/executions/*path",
	}

	// Verify at least some routes are registered
	routeMap := make(map[string]bool)
	for _, route := range routes {
		routeMap[route.Method+" "+route.Path] = true
	}

	// Check accountability routes
	for _, expected := range expectedAccountabilityRoutes {
		if !routeMap[expected] {
			t.Errorf("Expected route %s not found", expected)
		}
	}

	for _, expected := range expectedCommunityRoutes {
		if !routeMap[expected] {
			t.Errorf("Expected route %s not found", expected)
		}
	}

	// Check tasks routes
	for _, expected := range expectedTasksRoutes {
		if !routeMap[expected] {
			t.Errorf("Expected route %s not found", expected)
		}
	}

	// Check plans routes
	for _, expected := range expectedPlansRoutes {
		if !routeMap[expected] {
			t.Errorf("Expected route %s not found", expected)
		}
	}

	for _, expected := range expectedLearningPathRoutes {
		if !routeMap[expected] {
			t.Errorf("Expected route %s not found", expected)
		}
	}

	for _, expected := range expectedChatRoutes {
		if !routeMap[expected] {
			t.Errorf("Expected route %s not found", expected)
		}
	}

	for _, expected := range expectedTelemetryRoutes {
		if !routeMap[expected] {
			t.Errorf("Expected route %s not found", expected)
		}
	}

	for _, expected := range expectedAdditionalRoutes {
		if !routeMap[expected] {
			t.Errorf("Expected route %s not found", expected)
		}
	}

	// Verify we have routes registered (should be more than 50)
	if len(routes) < 50 {
		t.Errorf("Expected at least 50 routes to be registered, got %d", len(routes))
	}
}

func TestProxyRoutesHandler_ClientTelemetryAuthBoundary(t *testing.T) {
	gin.SetMode(gin.TestMode)
	logger := zap.NewNop()

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	backendURL, err := url.Parse(backend.URL)
	if err != nil {
		t.Fatalf("failed to parse backend url: %v", err)
	}
	proxy := httputil.NewSingleHostReverseProxy(backendURL)

	abTestConfig := &middleware.ABTestConfig{
		BackendURL: backend.URL,
		Timeout:    3 * time.Second,
		Enabled:    false,
	}
	abTestMiddleware := middleware.NewABTestMiddleware(abTestConfig)
	h := NewProxyRoutesHandler(proxy, abTestMiddleware, logger)

	router := gin.New()
	api := router.Group("/api/v1")

	authCalls := 0
	mockAuthMiddleware := func(c *gin.Context) {
		authCalls++
		c.Set("user_id", "test-user-123")
		c.Set("auth_token", "test-token-abc")
		c.Next()
	}

	h.RegisterProxyRoutes(api, mockAuthMiddleware)

	server := httptest.NewServer(router)
	defer server.Close()
	postResp, err := http.Post(
		server.URL+"/api/v1/client-telemetry/events/batch",
		"application/json",
		bytes.NewBufferString(`{"events":[{"event_type":"screen_view"}]}`),
	)
	if err != nil {
		t.Fatalf("failed to post anonymous telemetry ingest: %v", err)
	}
	defer postResp.Body.Close()

	if postResp.StatusCode != http.StatusOK {
		t.Fatalf("expected anonymous telemetry ingest to proxy successfully, got %d", postResp.StatusCode)
	}
	if authCalls != 0 {
		t.Fatalf("expected anonymous telemetry ingest to bypass auth middleware, got %d calls", authCalls)
	}

	summaryResp, err := http.Get(server.URL + "/api/v1/client-telemetry/summary")
	if err != nil {
		t.Fatalf("failed to get telemetry summary: %v", err)
	}
	defer summaryResp.Body.Close()

	if summaryResp.StatusCode != http.StatusOK {
		t.Fatalf("expected telemetry summary to proxy successfully, got %d", summaryResp.StatusCode)
	}
	if authCalls != 1 {
		t.Fatalf("expected telemetry summary to invoke auth middleware once, got %d calls", authCalls)
	}
}

func TestProxyRoutesHandler_AdminExecutionsRequireAdmin(t *testing.T) {
	gin.SetMode(gin.TestMode)
	logger := zap.NewNop()

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	backendURL, err := url.Parse(backend.URL)
	if err != nil {
		t.Fatalf("failed to parse backend url: %v", err)
	}
	proxy := httputil.NewSingleHostReverseProxy(backendURL)

	abTestConfig := &middleware.ABTestConfig{
		BackendURL: backend.URL,
		Timeout:    3 * time.Second,
		Enabled:    false,
	}
	abTestMiddleware := middleware.NewABTestMiddleware(abTestConfig)
	h := NewProxyRoutesHandler(proxy, abTestMiddleware, logger)

	newRouter := func(isAdmin bool) *gin.Engine {
		router := gin.New()
		// route-tier: authed
		api := router.Group("/api/v1")
		mockAuthMiddleware := func(c *gin.Context) {
			c.Set("user_id", "test-user-123")
			c.Set("auth_token", "test-token-abc")
			c.Set("is_admin", isAdmin)
			c.Next()
		}
		h.RegisterProxyRoutes(api, mockAuthMiddleware)
		return router
	}

	notAdminResp := httptest.NewRecorder()
	newRouter(false).ServeHTTP(
		notAdminResp,
		httptest.NewRequest(http.MethodGet, "/api/v1/admin/executions", nil),
	)
	if notAdminResp.Code != http.StatusForbidden {
		t.Fatalf("expected non-admin request to be forbidden, got %d", notAdminResp.Code)
	}

	adminServer := httptest.NewServer(newRouter(true))
	defer adminServer.Close()

	adminResp, err := http.Get(adminServer.URL + "/api/v1/admin/executions")
	if err != nil {
		t.Fatalf("expected admin request to proxy successfully: %v", err)
	}
	defer adminResp.Body.Close()
	if adminResp.StatusCode != http.StatusOK {
		t.Fatalf("expected admin request to proxy successfully, got %d", adminResp.StatusCode)
	}
}
