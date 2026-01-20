package middleware

import (
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

		if tokenString == "" && isWebSocketRequest(c) && cfg.AllowWsQueryToken {
			tokenString = c.Query("token")
		}

		if tokenString == "" {
			log.Printf("Auth failed: missing token")
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authorization token required"})
			return
		}

		if cfg.IsDevelopment() {
			log.Printf("Auth token received: len=%d", len(tokenString))
		}

		userID, isAdmin, err := validateJWT(cfg, tokenString)
		if err != nil {
			if cfg.IsDevelopment() {
				log.Printf("Auth secret debug: len=%d", len(cfg.JWTSecret))
			}
			log.Printf("Auth failed: invalid token (err=%v)", err)
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid or expired token"})
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

		// Set user context
		c.Set("user_id", userID)
		c.Set("is_admin", isAdmin)
		c.Set("auth_token", tokenString)
		c.Next()
	}
}

func claimHasAudience(audClaim interface{}, expected string) bool {
	if audClaim == nil {
		return false
	}
	switch aud := audClaim.(type) {
	case string:
		return aud == expected
	case []interface{}:
		for _, v := range aud {
			if s, ok := v.(string); ok && s == expected {
				return true
			}
		}
	case []string:
		for _, v := range aud {
			if v == expected {
				return true
			}
		}
	}
	return false
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

func validateJWT(cfg *config.Config, tokenString string) (string, bool, error) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if token.Method.Alg() != jwt.SigningMethodHS256.Alg() {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return []byte(cfg.JWTSecret), nil
	})
	if err != nil || !token.Valid {
		return "", false, fmt.Errorf("invalid token")
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", false, fmt.Errorf("invalid token claims")
	}

	userID, ok := claims["sub"].(string)
	if !ok || userID == "" {
		return "", false, fmt.Errorf("invalid user ID")
	}

	tokenType, ok := claims["type"].(string)
	if !ok || tokenType != "access" {
		return "", false, fmt.Errorf("invalid token type")
	}

	if cfg.JWTIssuer != "" {
		issuer, ok := claims["iss"].(string)
		if !ok || issuer != cfg.JWTIssuer {
			return "", false, fmt.Errorf("invalid token issuer")
		}
	}

	if cfg.JWTAudience != "" {
		if !claimHasAudience(claims["aud"], cfg.JWTAudience) {
			return "", false, fmt.Errorf("invalid token audience")
		}
	}

	isAdmin := false
	if adminClaim, exists := claims["is_admin"]; exists {
		if adminBool, ok := adminClaim.(bool); ok {
			isAdmin = adminBool
		}
	}

	return userID, isAdmin, nil
}
