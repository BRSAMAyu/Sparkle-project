package middleware

import (
	"github.com/gin-gonic/gin"
)

// SecurityHeadersMiddleware adds security-related headers to every response
func SecurityHeadersMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Content-Security-Policy: restrictive policy
		c.Header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self';")
		
		// X-Frame-Options: prevent clickjacking
		c.Header("X-Frame-Options", "DENY")
		
		// X-Content-Type-Options: prevent MIME-sniffing
		c.Header("X-Content-Type-Options", "nosniff")
		
		// X-XSS-Protection: legacy protection (still useful for older browsers)
		c.Header("X-XSS-Protection", "1; mode=block")
		
		// Strict-Transport-Security: enforce HTTPS (only in production)
		// c.Header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
		
		// Referrer-Policy: control referrer information
		c.Header("Referrer-Policy", "strict-origin-when-cross-origin")
		
		// Permissions-Policy: restrict browser features
		c.Header("Permissions-Policy", "geolocation=(), camera=(), microphone=(), payment=()")

		c.Next()
	}
}
