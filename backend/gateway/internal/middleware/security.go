package middleware

import (
	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
)

// SecurityHeadersMiddleware adds security-related headers to every response
func SecurityHeadersMiddleware(cfg ...*config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Content-Security-Policy: 更严格的策略
		// 注意: 移除了 script-src 的 'unsafe-inline' 和 'unsafe-eval'
		// 如果前端需要内联脚本，需要使用 nonce 或 hash 机制
		// style-src 保留 'unsafe-inline' 因为很多 CSS 框架需要
		c.Header("Content-Security-Policy",
			"default-src 'self'; "+
				"script-src 'self'; "+
				"style-src 'self' 'unsafe-inline'; "+
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
