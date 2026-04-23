package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestHybridRateLimitMiddleware_ClientTelemetryIsRateLimited(t *testing.T) {
	t.Parallel()

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(HybridRateLimitMiddlewareSimple(nil, 1, 1))
	router.POST("/api/v1/client-telemetry/events", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	for i := 0; i < 2; i++ {
		recorder := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodPost, "/api/v1/client-telemetry/events", nil)
		req.RemoteAddr = "127.0.0.1:34567"
		router.ServeHTTP(recorder, req)

		if i == 0 && recorder.Code != http.StatusOK {
			t.Fatalf("first telemetry request should pass, got %d", recorder.Code)
		}
		if i == 1 && recorder.Code != http.StatusTooManyRequests {
			t.Fatalf("second telemetry request should be rate limited, got %d", recorder.Code)
		}
	}
}

func TestAdminRateLimitMiddleware(t *testing.T) {
	t.Parallel()

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(AdminRateLimitMiddleware(nil))
	// route-tier: authed
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

func TestInternalRateLimitMiddleware(t *testing.T) {
	t.Parallel()

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(InternalRateLimitMiddleware(nil))
	router.GET("/internal/probe", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	blocked := false
	for i := 0; i < 121; i++ {
		recorder := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodGet, "/internal/probe", nil)
		req.RemoteAddr = "127.0.0.1:34567"
		router.ServeHTTP(recorder, req)
		if i < 120 && recorder.Code != http.StatusOK {
			t.Fatalf("request %d should pass, got %d", i+1, recorder.Code)
		}
		if i == 120 {
			blocked = recorder.Code == http.StatusTooManyRequests
		}
	}

	if !blocked {
		t.Fatalf("expected internal rate limiter to reject burst above 120 requests")
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
