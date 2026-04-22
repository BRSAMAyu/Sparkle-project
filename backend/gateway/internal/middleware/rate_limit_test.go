package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestShouldBypassGlobalRateLimit(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name   string
		method string
		path   string
		want   bool
	}{
		{
			name:   "telemetry events batch bypasses",
			method: http.MethodPost,
			path:   "/api/v1/client-telemetry/events/batch",
			want:   true,
		},
		{
			name:   "telemetry events bypasses",
			method: http.MethodPost,
			path:   "/api/v1/client-telemetry/events",
			want:   true,
		},
		{
			name:   "telemetry summary stays limited",
			method: http.MethodGet,
			path:   "/api/v1/client-telemetry/summary",
			want:   false,
		},
		{
			name:   "auth guest stays limited",
			method: http.MethodPost,
			path:   "/api/v1/auth/guest",
			want:   false,
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			recorder := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(recorder)
			c.Request = httptest.NewRequest(tc.method, tc.path, nil)

			if got := shouldBypassGlobalRateLimit(c); got != tc.want {
				t.Fatalf("shouldBypassGlobalRateLimit() = %v, want %v", got, tc.want)
			}
		})
	}
}

func TestAdminRateLimitMiddleware(t *testing.T) {
	t.Parallel()

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(AdminRateLimitMiddleware(nil))
	router.GET("/admin/probe", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	blocked := false
	for i := 0; i < 11; i++ {
		recorder := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodGet, "/admin/probe", nil)
		req.RemoteAddr = "127.0.0.1:34567"
		router.ServeHTTP(recorder, req)
		if i < 10 && recorder.Code != http.StatusOK {
			t.Fatalf("request %d should pass, got %d", i+1, recorder.Code)
		}
		if i == 10 {
			blocked = recorder.Code == http.StatusTooManyRequests
		}
	}

	if !blocked {
		t.Fatalf("expected admin rate limiter to reject burst above 10 requests")
	}
}

func TestNormalizeRateLimitRoutePath(t *testing.T) {
	t.Parallel()

	t.Run("uses concrete request path for wildcard routes", func(t *testing.T) {
		t.Parallel()

		recorder := httptest.NewRecorder()
		_, router := gin.CreateTestContext(recorder)
		gotPath := ""
		router.GET("/api/v1/user/*path", func(ctx *gin.Context) {
			gotPath = normalizeRateLimitRoutePath(ctx)
		})

		req := httptest.NewRequest(http.MethodGet, "/api/v1/user/settings/ai-usage", nil)
		router.ServeHTTP(recorder, req)
		if gotPath != "/api/v1/user/settings/ai-usage" {
			t.Fatalf("normalizeRateLimitRoutePath() = %q", gotPath)
		}
	})

	t.Run("keeps static template routes grouped", func(t *testing.T) {
		t.Parallel()

		recorder := httptest.NewRecorder()
		_, router := gin.CreateTestContext(recorder)
		gotPath := ""
		router.GET("/api/v1/calendar/:id", func(ctx *gin.Context) {
			gotPath = normalizeRateLimitRoutePath(ctx)
		})

		req := httptest.NewRequest(http.MethodGet, "/api/v1/calendar/123", nil)
		router.ServeHTTP(recorder, req)
		if gotPath != "/api/v1/calendar/:id" {
			t.Fatalf("normalizeRateLimitRoutePath() = %q", gotPath)
		}
	})
}
