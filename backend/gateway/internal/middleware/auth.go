package middleware

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/sparkle/gateway/internal/config"
)

func AuthMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get token from Authorization header or Query param (for WebSocket)
		tokenString := ""
		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			if strings.HasPrefix(authHeader, "Bearer ") {
				tokenString = strings.TrimPrefix(authHeader, "Bearer ")
			}
		} else {
			tokenString = c.Query("token")
		}

		if tokenString == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authorization token required"})
			return
		}

		// Parse and validate token
		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return []byte(cfg.JWTSecret), nil
		})

		if err != nil || !token.Valid {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid or expired token"})
			return
		}

		claims, ok := token.Claims.(jwt.MapClaims)
		if !ok {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid token claims"})
			return
		}

		// Extract User ID
		userID, ok := claims["sub"].(string)
		if !ok {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid user ID in token"})
			return
		}

		// Extract role information from JWT claims
		isAdmin := false
		if adminClaim, exists := claims["is_admin"]; exists {
			if adminBool, ok := adminClaim.(bool); ok {
				isAdmin = adminBool
			}
		}

		// Set user context
		c.Set("user_id", userID)
		c.Set("is_admin", isAdmin)
		c.Next()
	}
}

// AdminAuthMiddleware validates the X-Admin-Secret header for admin endpoints
func AdminAuthMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		// In development mode, allow admin access without secret
		if cfg.IsDevelopment() {
			c.Next()
			return
		}

		// In production, require X-Admin-Secret header
		secretFromHeader := c.GetHeader("X-Admin-Secret")
		if secretFromHeader == "" || secretFromHeader != cfg.AdminSecret {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid or missing admin secret"})
			return
		}

		c.Next()
	}
}

// RequireAdmin middleware checks if user has admin role
func RequireAdmin(c *gin.Context) {
	isAdmin := c.GetBool("is_admin")
	if !isAdmin {
		c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "Admin access required"})
		return
	}
	c.Next()
}
