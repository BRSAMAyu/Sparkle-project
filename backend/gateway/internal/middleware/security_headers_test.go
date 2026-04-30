package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
)

func TestSecurityHeaders_AllPresent(t *testing.T) {
	tests := []struct {
		name         string
		cfg          *config.Config
		expectedHSTS bool
	}{
		{
			name:         "development_mode_no_hsts",
			cfg:          &config.Config{Environment: "development"},
			expectedHSTS: false,
		},
		{
			name:         "production_mode_with_hsts",
			cfg:          &config.Config{Environment: "production"},
			expectedHSTS: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			router := gin.New()
			router.Use(SecurityHeadersMiddleware(tt.cfg))
			router.GET("/test", func(c *gin.Context) {
				c.String(http.StatusOK, "ok")
			})

			w := httptest.NewRecorder()
			req := httptest.NewRequest("GET", "/test", nil)
			router.ServeHTTP(w, req)

			// CSP must be present and strict
			csp := w.Header().Get("Content-Security-Policy")
			assert.NotEmpty(t, csp, "Content-Security-Policy must be present")
			assert.Contains(t, csp, "default-src 'self'", "CSP must have default-src")
			assert.Contains(t, csp, "script-src 'self'", "CSP must restrict scripts")
			assert.NotContains(t, csp, "unsafe-eval", "CSP must not allow unsafe-eval")
			assert.Contains(t, csp, "object-src 'none'", "CSP must block objects")

			// X-Frame-Options must be DENY
			assert.Equal(t, "DENY", w.Header().Get("X-Frame-Options"))

			// X-Content-Type-Options must be nosniff
			assert.Equal(t, "nosniff", w.Header().Get("X-Content-Type-Options"))

			// Referrer-Policy must be strict-origin-when-cross-origin
			assert.Equal(t, "strict-origin-when-cross-origin", w.Header().Get("Referrer-Policy"))

			// Permissions-Policy must restrict features
			pp := w.Header().Get("Permissions-Policy")
			assert.NotEmpty(t, pp, "Permissions-Policy must be present")
			assert.Contains(t, pp, "geolocation=()", "must block geolocation")
			assert.Contains(t, pp, "camera=()", "must block camera")
			assert.Contains(t, pp, "microphone=()", "must block microphone")
			assert.Contains(t, pp, "payment=()", "must block payment")

			// HSTS depends on environment
			hsts := w.Header().Get("Strict-Transport-Security")
			if tt.expectedHSTS {
				assert.Contains(t, hsts, "max-age=31536000", "HSTS must be set in production")
				assert.Contains(t, hsts, "includeSubDomains", "HSTS must include subdomains")
			} else {
				assert.Empty(t, hsts, "HSTS must not be set in development")
			}
		})
	}
}

func TestSecurityHeaders_XSSProtection(t *testing.T) {
	router := gin.New()
	router.Use(SecurityHeadersMiddleware())
	router.GET("/test", func(c *gin.Context) {
		c.String(http.StatusOK, "ok")
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/test", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, "1; mode=block", w.Header().Get("X-XSS-Protection"))
}

func TestSecurityHeaders_AppliesToAllRoutes(t *testing.T) {
	router := gin.New()
	router.Use(SecurityHeadersMiddleware())
	router.GET("/api/v1/users", func(c *gin.Context) { c.String(200, "ok") })
	router.POST("/api/v1/chat", func(c *gin.Context) { c.String(200, "ok") })
	router.GET("/health", func(c *gin.Context) { c.String(200, "ok") })

	for _, path := range []string{"/api/v1/users", "/api/v1/chat", "/health"} {
		t.Run(path, func(t *testing.T) {
			w := httptest.NewRecorder()
			method := "GET"
			if path == "/api/v1/chat" {
				method = "POST"
			}
			req := httptest.NewRequest(method, path, nil)
			router.ServeHTTP(w, req)

			assert.NotEmpty(t, w.Header().Get("Content-Security-Policy"))
			assert.Equal(t, "DENY", w.Header().Get("X-Frame-Options"))
		})
	}
}
