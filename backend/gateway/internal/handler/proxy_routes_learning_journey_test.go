package handler

import (
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
	"net/url"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/middleware"
)

// learningJourneyTestRouter builds a router with the real proxy route
// registrations (same wiring as production setup).
func learningJourneyTestRouter(t *testing.T) *gin.Engine {
	t.Helper()
	gin.SetMode(gin.TestMode)

	backendURL, _ := url.Parse("http://backend:8000")
	proxy := httputil.NewSingleHostReverseProxy(backendURL)
	abTestMiddleware := middleware.NewABTestMiddleware(&middleware.ABTestConfig{
		BackendURL: "http://backend:8000",
		Timeout:    3 * time.Second,
		Enabled:    false,
	})
	h := NewProxyRoutesHandler(proxy, abTestMiddleware, zap.NewNop())

	router := gin.New()
	api := router.Group("/api/v1")
	mockAuth := func(c *gin.Context) {
		c.Set("user_id", "test-user-123")
		c.Set("auth_token", "test-token-abc")
		c.Next()
	}
	h.RegisterProxyRoutes(api, mockAuth)
	return router
}

// TestProxyRoutesHandler_LearningJourneyRegistered pins the V4-U10
// 资料→错题→练习→检验旅程 proxy faces: the gateway must expose the
// learning-journey read model and both check faces to the mobile client
// (registerREST wildcard covers subpaths).
func TestProxyRoutesHandler_LearningJourneyRegistered(t *testing.T) {
	router := learningJourneyTestRouter(t)

	routeMap := map[string]bool{}
	for _, route := range router.Routes() {
		routeMap[route.Method+" "+route.Path] = true
	}

	expected := []string{
		"GET /api/v1/learning-journey/*path",
		"POST /api/v1/learning-journey/*path",
		"GET /api/v1/learning-journey",
		"POST /api/v1/learning-journey",
	}
	for _, route := range expected {
		require.Truef(t, routeMap[route], "expected learning-journey route %s not registered", route)
	}
}

// TestProxyRoutesHandler_LearningJourneyProxiedAndAuthed verifies the group
// passes requests through to the reverse proxy and rejects unauthenticated
// calls before proxying (route-tier: authed).
func TestProxyRoutesHandler_LearningJourneyProxiedAndAuthed(t *testing.T) {
	gin.SetMode(gin.TestMode)

	var backendCalled bool
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		backendCalled = true
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	backendURL, _ := url.Parse(backend.URL)
	proxy := httputil.NewSingleHostReverseProxy(backendURL)
	abTestMiddleware := middleware.NewABTestMiddleware(&middleware.ABTestConfig{
		BackendURL: backend.URL,
		Timeout:    3 * time.Second,
		Enabled:    false,
	})
	h := NewProxyRoutesHandler(proxy, abTestMiddleware, zap.NewNop())

	router := gin.New()
	api := router.Group("/api/v1")
	// Deny-all auth: requests must never reach the backend without a valid session.
	denyAuth := func(c *gin.Context) {
		c.AbortWithStatus(http.StatusUnauthorized)
	}
	h.RegisterProxyRoutes(api, denyAuth)

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/api/v1/learning-journey/tasks/00000000-0000-0000-0000-000000000001", nil)
	router.ServeHTTP(recorder, request)

	require.Equal(t, http.StatusUnauthorized, recorder.Code)
	require.False(t, backendCalled, "unauthenticated request must not reach the backend")
}
