package handler

import (
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
		"GET /api/v1/community/friends/:friendId/profile",
	}

	// Expected route patterns for tasks
	expectedTasksRoutes := []string{
		"GET /api/v1/tasks",
		"POST /api/v1/tasks",
		"GET /api/v1/tasks/today",
		"GET /api/v1/tasks/:id",
		"GET /api/v1/tasks/:id/resources",
		"PUT /api/v1/tasks/:id",
		"DELETE /api/v1/tasks/:id",
		"POST /api/v1/tasks/:id/resources",
		"DELETE /api/v1/tasks/:id/resources/:resourceId",
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

	// Verify we have routes registered (should be more than 50)
	if len(routes) < 50 {
		t.Errorf("Expected at least 50 routes to be registered, got %d", len(routes))
	}
}
