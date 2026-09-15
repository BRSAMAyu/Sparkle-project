package handler

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestGalaxyHandlerRegistersFrontendEndpoints(t *testing.T) {
	gin.SetMode(gin.TestMode)

	type capturedRequest struct {
		method string
		path   string
		userID string
	}
	var captured []capturedRequest

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		captured = append(captured, capturedRequest{
			method: r.Method,
			path:   r.URL.Path,
			userID: r.Header.Get("X-User-ID"),
		})
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"ok":true}`))
	}))
	defer backend.Close()

	router := gin.New()
	auth := func(c *gin.Context) {
		c.Set("user_id", "user-123")
		c.Next()
	}
	handler, err := NewGalaxyHandler(nil, nil, nil, backend.URL)
	if err != nil {
		t.Fatalf("NewGalaxyHandler failed: %v", err)
	}
	handler.RegisterRoutes(router.Group("/api/v1"), auth, nil)
	gateway := httptest.NewServer(router)
	defer gateway.Close()

	cases := []struct {
		method string
		path   string
	}{
		{method: http.MethodGet, path: "/api/v1/galaxy/graph"},
		{method: http.MethodGet, path: "/api/v1/galaxy/contribution-stats"},
		{method: http.MethodPost, path: "/api/v1/galaxy/nodes"},
		{method: http.MethodPost, path: "/api/v1/galaxy/search"},
		{method: http.MethodGet, path: "/api/v1/galaxy/node/node-1/history"},
		{method: http.MethodPost, path: "/api/v1/galaxy/node/node-1/expansion/candidates"},
		{method: http.MethodPost, path: "/api/v1/galaxy/node/node-1/expansion/apply"},
		{method: http.MethodPost, path: "/api/v1/galaxy/node/node-1/favorite"},
		{method: http.MethodPost, path: "/api/v1/galaxy/node/node-1/decay/pause"},
		{method: http.MethodPost, path: "/api/v1/galaxy/predict-next"},
		{method: http.MethodPost, path: "/api/v1/galaxy/nodes/viewport"},
		{method: http.MethodPost, path: "/api/v1/galaxy/nodes/positions"},
		{method: http.MethodPost, path: "/api/v1/galaxy/sync/mastery"},
	}

	for index, tc := range cases {
		req, err := http.NewRequest(tc.method, gateway.URL+tc.path, nil)
		if err != nil {
			t.Fatalf("new request: %v", err)
		}
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("%s %s request failed: %v", tc.method, tc.path, err)
		}
		_ = resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Fatalf("%s %s returned %d, want 200", tc.method, tc.path, resp.StatusCode)
		}
		if len(captured) != index+1 {
			t.Fatalf("%s %s was not proxied", tc.method, tc.path)
		}
		got := captured[index]
		if got.method != tc.method || got.path != tc.path {
			t.Fatalf("proxied request = %s %s, want %s %s", got.method, got.path, tc.method, tc.path)
		}
		if got.userID != "user-123" {
			t.Fatalf("X-User-ID = %q, want user-123", got.userID)
		}
	}
}
