package middleware

import (
	"crypto/sha256"
	"crypto/subtle"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/sparkle/gateway/internal/config"
)

func AuthMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get token from Authorization header or Query param (WebSocket upgrade only)
		tokenString := ""
		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			if strings.HasPrefix(authHeader, "Bearer ") {
				tokenString = strings.TrimPrefix(authHeader, "Bearer ")
			}
		}

		if tokenString == "" && isWebSocketRequest(c) {
			tokenString = c.Query("token")
		}

		if tokenString == "" {
			tokenString = c.Query("token")
		}

		if tokenString == "" {
			log.Printf("Auth failed: missing token")
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authorization token required"})
			return
		}

		if cfg.IsDevelopment() {
			if len(tokenString) >= 16 {
				log.Printf("Auth token received: len=%d prefix=%s suffix=%s", len(tokenString), tokenString[:8], tokenString[len(tokenString)-8:])
			} else {
				log.Printf("Auth token received: len=%d", len(tokenString))
			}
		}

		// Parse and validate token
		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return []byte(cfg.JWTSecret), nil
		})

		if err != nil || !token.Valid {
			if cfg.IsDevelopment() {
				secretHash := sha256.Sum256([]byte(cfg.JWTSecret))
				log.Printf("Auth secret debug: len=%d sha256=%x", len(cfg.JWTSecret), secretHash)
			}
			log.Printf("Auth failed: invalid token (err=%v, valid=%v)", err, token != nil && token.Valid)
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

		// Optional query user_id is for backward compatibility but must match token identity
		queryUserID := c.Query("user_id")
		if queryUserID != "" && queryUserID != userID {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{
				"error": "user_id mismatch",
				"code":  "USER_ID_MISMATCH",
			})
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
		c.Set("auth_token", tokenString)
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
		if secretFromHeader == "" || subtle.ConstantTimeCompare([]byte(secretFromHeader), []byte(cfg.AdminSecret)) != 1 {
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

func isWebSocketRequest(c *gin.Context) bool {
	upgrade := strings.ToLower(c.GetHeader("Upgrade"))
	connection := strings.ToLower(c.GetHeader("Connection"))
	return upgrade == "websocket" && strings.Contains(connection, "upgrade")
}
