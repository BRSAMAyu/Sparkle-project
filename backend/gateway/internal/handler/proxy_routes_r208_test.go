package handler

import (
	"net/http/httputil"
	"net/url"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/middleware"
)

// r208TestRouter builds a router with the real proxy route registrations.
func r208TestRouter(t *testing.T) *gin.Engine {
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

	// Galaxy routes are registered on the same api group in production
	// (setup.go); nils are safe because registration never invokes handlers.
	galaxyHandler, err := NewGalaxyHandler(nil, nil, nil, "http://backend:8000")
	require.NoError(t, err)
	galaxyHandler.RegisterRoutes(api, mockAuth, func(c *gin.Context) { c.Next() })
	return router
}

// TestProxyRoutesHandler_DeadRoutesRemoved pins the R2-08 gateway-side P3
// disposition (round2/08-r2-fixes.md §5, 17 archived dead routes): routes the
// engine cannot serve (404/405) are no longer registered on the gateway.
// Methods are part of the key: e.g. POST /tasks/suggestions must exist while
// GET /tasks/suggestions must not.
func TestProxyRoutesHandler_DeadRoutesRemoved(t *testing.T) {
	router := r208TestRouter(t)

	mustNotExist := []string{
		// cards (#4-7): bare GET/POST + PATCH/PUT wildcard method-faces
		"GET /api/v1/cards",
		"POST /api/v1/cards",
		"PUT /api/v1/cards/*path",
		"PATCH /api/v1/cards/*path",
		// tasks (#11, #12)
		// GUARD-DEBT: POST /tasks/:id/reopen moved out of this pin — X-04 gave
		// the engine a real reopen transition (POST /tasks/{task_id}/reopen,
		// tasks.py) and mobile calls it (api_endpoints.dart reopenTask), so the
		// R2-08 #11 "engine has no reopen transition" premise no longer holds.
		// The proxy registration is pinned positively in proxy_routes_test.go
		// (expectedTasksRoutes) and annotated `rule-bm: ignore` in
		// proxy_routes.go. GET /tasks/suggestions stays pinned below.
		"GET /api/v1/tasks/suggestions",
		// goals (#13): PATCH redundant, PUT sibling stays
		"PATCH /api/v1/goals/:id",
		// cqrs (#14)
		"GET /api/v1/cqrs/dlq/stats",
		// community private messages (#15-17)
		"POST /api/v1/community/messages/private",
		"GET /api/v1/community/messages/private/:user_id",
		"DELETE /api/v1/community/messages/private/:msg_id",
		// community posts (#18)
		"PATCH /api/v1/community/posts/:post_id",
		// community groups (#19, #20)
		"DELETE /api/v1/community/groups/:group_id/leave",
		"DELETE /api/v1/community/groups/:group_id/messages/:msg_id",
		// community share old alias (#21)
		"POST /api/v1/community/share/:share_id/adopt",
		// galaxy (#22): engine only serves POST /galaxy/nodes
		"GET /api/v1/galaxy/nodes",
	}

	registered := make(map[string]bool, len(router.Routes()))
	for _, rt := range router.Routes() {
		registered[rt.Method+" "+rt.Path] = true
	}

	for _, key := range mustNotExist {
		require.False(t, registered[key], "dead route must not be registered: %s", key)
	}
}

// TestProxyRoutesHandler_ExamSprintCompletionIsGET pins the R2-08 §2.2 #10
// method correction: the engine only serves GET /completion, so the gateway
// must register GET (the old POST was a guaranteed 405).
func TestProxyRoutesHandler_ExamSprintCompletionIsGET(t *testing.T) {
	router := r208TestRouter(t)

	var haveGET, havePOST bool
	for _, rt := range router.Routes() {
		switch {
		case rt.Method == "GET" && rt.Path == "/api/v1/exam-sprint/completion":
			haveGET = true
		case rt.Method == "POST" && rt.Path == "/api/v1/exam-sprint/completion":
			havePOST = true
		}
	}
	require.True(t, haveGET, "GET /api/v1/exam-sprint/completion must be registered")
	require.False(t, havePOST, "POST /api/v1/exam-sprint/completion must stay removed")
}

// TestProxyRoutesHandler_SurvivingSiblingsIntact guards the deletions against
// over-pruning: the method/path siblings the engine really serves must remain.
func TestProxyRoutesHandler_SurvivingSiblingsIntact(t *testing.T) {
	router := r208TestRouter(t)

	mustExist := []string{
		"GET /api/v1/cards/*path",
		"POST /api/v1/cards/*path",
		"DELETE /api/v1/cards/*path",
		"POST /api/v1/tasks/suggestions",
		"PUT /api/v1/goals/:id",
		"POST /api/v1/community/groups/:group_id/leave",
		"PATCH /api/v1/community/groups/:group_id/messages/:msg_id",
		"POST /api/v1/community/groups/:group_id/messages/:msg_id/revoke",
		"POST /api/v1/community/shared-resources/:shared_resource_id/adopt",
		"POST /api/v1/galaxy/nodes",
		"GET /api/v1/community/friends/:friend_id/messages",
	}

	registered := make(map[string]bool, len(router.Routes()))
	for _, rt := range router.Routes() {
		registered[rt.Method+" "+rt.Path] = true
	}

	for _, key := range mustExist {
		require.True(t, registered[key], "surviving sibling route missing: %s", key)
	}
}
