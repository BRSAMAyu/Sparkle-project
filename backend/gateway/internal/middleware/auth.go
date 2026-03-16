package middleware

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/config"
)

func AuthMiddleware(cfg *config.Config, rdb *redis.Client) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get token from Authorization header only.
		tokenString := ""
		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			if strings.HasPrefix(authHeader, "Bearer ") {
				tokenString = strings.TrimPrefix(authHeader, "Bearer ")
			}
		}

		if tokenString == "" {
			log.Printf("Auth failed: missing token")
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authorization token required"})
			return
		}

		userID, isAdmin, err := validateJWT(cfg, rdb, tokenString)
		if err != nil {
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
		// Always require X-Admin-Secret header (including development).
		if cfg.AdminSecret == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Admin secret not configured"})
			return
		}

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

func validateJWT(cfg *config.Config, rdb *redis.Client, tokenString string) (string, bool, error) {
	const jwtClockSkew = 30 * time.Second

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

	// Check token blacklist (Fail Open strategy - allow on Redis errors)
	if rdb != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
		defer cancel()

		// Check JTI blacklist (specific token revoked)
		jti, _ := claims["jti"].(string)
		if jti != "" {
			blacklisted, err := rdb.Exists(ctx, "token_blacklist:"+jti).Result()
			if err != nil {
				// Fail Open: log error but continue
				log.Printf("Redis blacklist check failed for jti, allowing token: %v", err)
			} else if blacklisted > 0 {
				return "", false, fmt.Errorf("token revoked")
			}
		}

		// Check user-level token revocation (all tokens issued before timestamp)
		iatValue, _ := claims["iat"].(float64)
		if iatValue > 0 {
			revokedBefore, err := rdb.Get(ctx, "user_revoked_before:"+userID).Result()
			if err != nil {
				// Fail Open: key not found or Redis error, continue
				if err != redis.Nil {
					log.Printf("Redis user revocation check failed, allowing token: %v", err)
				}
			} else {
				if revokedTs, err := strconv.ParseInt(revokedBefore, 10, 64); err == nil {
					if int64(iatValue) < revokedTs {
						return "", false, fmt.Errorf("token revoked by user")
					}
				}
			}
		}
	}

	expValue, ok := claims["exp"]
	if !ok {
		return "", false, fmt.Errorf("missing exp claim")
	}
	expTime, err := parseNumericDate(expValue)
	if err != nil {
		return "", false, fmt.Errorf("invalid exp claim")
	}
	now := time.Now().UTC()
	if now.After(expTime.Add(jwtClockSkew)) {
		return "", false, fmt.Errorf("token expired")
	}

	if nbfValue, ok := claims["nbf"]; ok {
		nbfTime, err := parseNumericDate(nbfValue)
		if err != nil {
			return "", false, fmt.Errorf("invalid nbf claim")
		}
		if now.Add(-jwtClockSkew).Before(nbfTime) {
			return "", false, fmt.Errorf("token not active")
		}
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

func parseNumericDate(value interface{}) (time.Time, error) {
	switch v := value.(type) {
	case *jwt.NumericDate:
		return v.Time, nil
	case float64:
		return time.Unix(int64(v), 0).UTC(), nil
	case json.Number:
		seconds, err := v.Int64()
		if err == nil {
			return time.Unix(seconds, 0).UTC(), nil
		}
		floatSeconds, err := v.Float64()
		if err != nil {
			return time.Time{}, err
		}
		return time.Unix(int64(floatSeconds), 0).UTC(), nil
	case int64:
		return time.Unix(v, 0).UTC(), nil
	case int:
		return time.Unix(int64(v), 0).UTC(), nil
	default:
		return time.Time{}, fmt.Errorf("unsupported numeric date type")
	}
}
