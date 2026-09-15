package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
)

// DefaultMaxBodyBytes is the default maximum request body size (10 MB).
const DefaultMaxBodyBytes = 10 << 20 // 10 MB

// MaxBodySizeMiddleware rejects requests whose body exceeds maxBytes.
// This prevents OOM attacks from oversized payloads on proxy routes.
func MaxBodySizeMiddleware(maxBytes int64) gin.HandlerFunc {
	return func(c *gin.Context) {
		if c.Request.Body != nil {
			c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, maxBytes)
		}
		c.Next()
	}
}

// SecurityHeadersMiddleware adds security-related headers to every response
func SecurityHeadersMiddleware(cfg ...*config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Content-Security-Policy: strict CSP without unsafe-inline
		c.Header("Content-Security-Policy",
			"default-src 'self'; "+
				"script-src 'self'; "+
				"style-src 'self'; "+
				"img-src 'self' data: https:; "+
				"connect-src 'self' wss: https:; "+
				"font-src 'self'; "+
				"frame-src 'none'; "+
				"object-src 'none'; "+
				"base-uri 'self'; "+
				"form-action 'self'")

		// X-Frame-Options: prevent clickjacking
		c.Header("X-Frame-Options", "DENY")

		// X-Content-Type-Options: prevent MIME-sniffing
		c.Header("X-Content-Type-Options", "nosniff")

		// X-XSS-Protection: legacy protection (still useful for older browsers)
		c.Header("X-XSS-Protection", "1; mode=block")

		// Strict-Transport-Security: enforce HTTPS (only in production)
		if len(cfg) > 0 && cfg[0] != nil && cfg[0].IsProduction() {
			c.Header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
		}

		// Referrer-Policy: control referrer information
		c.Header("Referrer-Policy", "strict-origin-when-cross-origin")

		// Permissions-Policy: restrict browser features
		c.Header("Permissions-Policy", "geolocation=(), camera=(), microphone=(), payment=()")

		// Cross-Origin isolation: prevent cross-origin information leaks
		c.Header("Cross-Origin-Opener-Policy", "same-origin")
		c.Header("Cross-Origin-Resource-Policy", "same-origin")

		c.Next()
	}
}
