package middleware

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/i18n"
	"go.uber.org/zap"
)

const (
	localBlacklistCleanupThreshold = 100
	localBlacklistMaxEntries       = 10000
)

// Local token blacklist cache for Fail-Closed fallback
// When Redis is unavailable and Fail-Closed is enabled, we maintain a local
// cache of revoked tokens to provide some protection
type localBlacklistCache struct {
	mu             sync.RWMutex
	jtiSet         map[string]time.Time // JTI -> expiry time
	jtiAddedAt     map[string]time.Time
	userRevoked    map[string]localRevocation
	cleanupRunning bool // Prevent goroutine leak
}

type localRevocation struct {
	timestamp int64
	expiresAt time.Time
	addedAt   time.Time
}

var globalLocalBlacklist = &localBlacklistCache{
	jtiSet:      make(map[string]time.Time),
	jtiAddedAt:  make(map[string]time.Time),
	userRevoked: make(map[string]localRevocation),
}

// AddJTI adds a JTI to the local blacklist cache
func (c *localBlacklistCache) AddJTI(jti string, ttl time.Duration) {
	c.mu.Lock()
	now := time.Now()
	c.ensureMapsLocked()
	c.jtiSet[jti] = now.Add(ttl)
	c.jtiAddedAt[jti] = now
	c.enforceHardLimitLocked()
	shouldCleanup := c.shouldStartCleanupLocked()
	c.mu.Unlock()

	if shouldCleanup {
		go c.cleanupExpired()
	}
}

// IsJTIBlacklisted checks if JTI is in local cache
func (c *localBlacklistCache) IsJTIBlacklisted(jti string) bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if exp, exists := c.jtiSet[jti]; exists {
		if time.Now().Before(exp) {
			return true
		}
	}
	return false
}

// SetUserRevoked sets user-level revocation timestamp
func (c *localBlacklistCache) SetUserRevoked(userID string, timestamp int64, ttl time.Duration) {
	c.mu.Lock()
	now := time.Now()
	c.ensureMapsLocked()
	expiresAt := now.Add(ttl)
	if ttl <= 0 {
		expiresAt = now.Add(24 * time.Hour)
	}
	c.userRevoked[userID] = localRevocation{
		timestamp: timestamp,
		expiresAt: expiresAt,
		addedAt:   now,
	}
	c.enforceHardLimitLocked()
	shouldCleanup := c.shouldStartCleanupLocked()
	c.mu.Unlock()

	// Only spawn cleanup goroutine if needed and not already running
	if shouldCleanup {
		go c.cleanupExpired()
	}
}

func (c *localBlacklistCache) shouldStartCleanupLocked() bool {
	if c.cleanupRunning {
		return false
	}
	if len(c.jtiSet) <= localBlacklistCleanupThreshold && len(c.userRevoked) <= localBlacklistCleanupThreshold {
		return false
	}
	c.cleanupRunning = true
	return true
}

func (c *localBlacklistCache) ensureMapsLocked() {
	if c.jtiSet == nil {
		c.jtiSet = make(map[string]time.Time)
	}
	if c.jtiAddedAt == nil {
		c.jtiAddedAt = make(map[string]time.Time)
	}
	if c.userRevoked == nil {
		c.userRevoked = make(map[string]localRevocation)
	}
}

func (c *localBlacklistCache) enforceHardLimitLocked() {
	for len(c.jtiSet) > localBlacklistMaxEntries {
		c.evictOldestJTILocked()
	}
	for len(c.userRevoked) > localBlacklistMaxEntries {
		c.evictOldestUserRevocationLocked()
	}
}

func (c *localBlacklistCache) evictOldestJTILocked() {
	oldestKey := ""
	var oldestTime time.Time
	for jti, expiresAt := range c.jtiSet {
		addedAt := c.jtiAddedAt[jti]
		if addedAt.IsZero() {
			addedAt = expiresAt
		}
		if oldestKey == "" || addedAt.Before(oldestTime) {
			oldestKey = jti
			oldestTime = addedAt
		}
	}
	if oldestKey != "" {
		delete(c.jtiSet, oldestKey)
		delete(c.jtiAddedAt, oldestKey)
	}
}

func (c *localBlacklistCache) evictOldestUserRevocationLocked() {
	oldestKey := ""
	var oldestTime time.Time
	for userID, entry := range c.userRevoked {
		addedAt := entry.addedAt
		if addedAt.IsZero() {
			addedAt = entry.expiresAt
		}
		if oldestKey == "" || addedAt.Before(oldestTime) {
			oldestKey = userID
			oldestTime = addedAt
		}
	}
	if oldestKey != "" {
		delete(c.userRevoked, oldestKey)
	}
}

// GetUserRevoked gets user revocation timestamp
func (c *localBlacklistCache) GetUserRevoked(userID string) (int64, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	entry, exists := c.userRevoked[userID]
	if !exists || time.Now().After(entry.expiresAt) {
		return 0, false
	}
	return entry.timestamp, true
}

// cleanupExpired removes expired entries (called in background)
func (c *localBlacklistCache) cleanupExpired() {
	defer func() {
		c.mu.Lock()
		c.cleanupRunning = false
		c.mu.Unlock()
	}()

	// Do multiple cleanup passes with small batches to avoid long lock times
	for i := 0; i < 3; i++ {
		c.mu.Lock()
		now := time.Now()
		removed := 0
		for jti, exp := range c.jtiSet {
			if now.After(exp) {
				delete(c.jtiSet, jti)
				delete(c.jtiAddedAt, jti)
				removed++
				if removed >= 50 { // Limit per-batch removals
					break
				}
			}
		}
		for userID, entry := range c.userRevoked {
			if now.After(entry.expiresAt) {
				delete(c.userRevoked, userID)
				removed++
				if removed >= 50 {
					break
				}
			}
		}
		c.mu.Unlock()

		if removed == 0 {
			break // No more expired entries
		}
		time.Sleep(10 * time.Millisecond) // Yield between batches
	}
}

type apiErrorResponse struct {
	Error     string `json:"error"`
	ErrorCode string `json:"error_code,omitempty"`
	RequestID string `json:"request_id,omitempty"`
}

var middlewareSanitizedErrorsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
	Name: "sparkle_gateway_middleware_errors_total",
	Help: "Total middleware error responses (auth, admin, etc.) sanitized before returning to clients.",
}, []string{"status_code", "code", "category"})

func abortWithAPIError(c *gin.Context, status int, code string, message string) {
	if code == "" {
		code = middlewareErrorCode(status)
	}
	category := middlewareErrorCategory(status)
	middlewareSanitizedErrorsTotal.WithLabelValues(strconv.Itoa(status), code, category).Inc()

	if message != "" {
		fields := []zap.Field{
			zap.Int("status", status),
			zap.String("code", code),
			zap.String("category", category),
			zap.String("internal_message", message),
			zap.String("request_id", requestIDFromContext(c)),
		}
		zap.L().Warn("middleware error response", fields...)
	}

	c.AbortWithStatusJSON(status, apiErrorResponse{
		Error:     middlewareErrorMessage(c, status, message),
		ErrorCode: code,
		RequestID: requestIDFromContext(c),
	})
}

func middlewareErrorCategory(statusCode int) string {
	switch {
	case statusCode >= 500:
		return "server_error"
	case statusCode == http.StatusUnauthorized || statusCode == http.StatusForbidden:
		return "auth_error"
	case statusCode == http.StatusNotFound:
		return "not_found"
	case statusCode >= 400:
		return "client_error"
	default:
		return "unknown"
	}
}

func middlewareErrorMessage(c *gin.Context, status int, message string) string {
	message = strings.TrimSpace(message)
	if isDevelopmentModeForMiddlewareErrors() && message != "" {
		return message
	}

	ctx := context.Background()
	if c != nil && c.Request != nil {
		ctx = c.Request.Context()
	}
	switch status {
	case http.StatusBadRequest:
		return i18n.T(ctx, "errors.bad_request")
	case http.StatusUnauthorized:
		return i18n.T(ctx, "errors.unauthorized")
	case http.StatusForbidden:
		return i18n.T(ctx, "errors.forbidden")
	case http.StatusNotFound:
		return i18n.T(ctx, "errors.not_found")
	case http.StatusBadGateway, http.StatusServiceUnavailable, http.StatusGatewayTimeout:
		return i18n.T(ctx, "errors.upstream")
	default:
		return i18n.T(ctx, "errors.generic")
	}
}

func isDevelopmentModeForMiddlewareErrors() bool {
	env := strings.ToLower(os.Getenv("ENVIRONMENT"))
	return env == "" || env == "dev" || env == "development"
}

func middlewareErrorCode(status int) string {
	switch status {
	case http.StatusBadRequest:
		return "bad_request"
	case http.StatusUnauthorized:
		return "unauthorized"
	case http.StatusForbidden:
		return "forbidden"
	case http.StatusNotFound:
		return "not_found"
	case http.StatusServiceUnavailable:
		return "service_unavailable"
	default:
		if status >= 500 {
			return "internal_error"
		}
		if status >= 400 {
			return "request_failed"
		}
	}
	return "operation_failed"
}

func requestIDFromContext(c *gin.Context) string {
	if c == nil {
		return ""
	}
	if requestID := c.GetString("request_id"); requestID != "" {
		return requestID
	}
	if c.Request != nil {
		return c.GetHeader("X-Request-ID")
	}
	return ""
}

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
			abortWithAPIError(c, http.StatusUnauthorized, "authorization_token_required", "Authorization token required")
			return
		}

		userID, isAdmin, err := validateJWT(cfg, rdb, tokenString)
		if err != nil {
			log.Printf("Auth failed: invalid token (err=%v)", err)
			abortWithAPIError(c, http.StatusUnauthorized, "invalid_or_expired_token", "Invalid or expired token")
			return
		}

		// Optional query user_id is for backward compatibility but must match token identity
		queryUserID := c.Query("user_id")
		if queryUserID != "" && queryUserID != userID {
			abortWithAPIError(c, http.StatusForbidden, "user_id_mismatch", "user_id mismatch")
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
			abortWithAPIError(c, http.StatusUnauthorized, "admin_secret_not_configured", "Admin secret not configured")
			return
		}

		secretFromHeader := c.GetHeader("X-Admin-Secret")
		if secretFromHeader == "" || subtle.ConstantTimeCompare([]byte(secretFromHeader), []byte(cfg.AdminSecret)) != 1 {
			abortWithAPIError(c, http.StatusUnauthorized, "invalid_or_missing_admin_secret", "Invalid or missing admin secret")
			return
		}

		c.Next()
	}
}

// RequireAdmin middleware checks if user has admin role
func RequireAdmin(c *gin.Context) {
	isAdmin := c.GetBool("is_admin")
	if !isAdmin {
		abortWithAPIError(c, http.StatusForbidden, "admin_access_required", "Admin access required")
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

	// Get token timing info for blacklist checks
	jti, _ := claims["jti"].(string)
	iatValue, _ := claims["iat"].(float64)

	// Calculate TTL for local cache based on token expiry
	var tokenTTL time.Duration
	if rawExp, ok := claims["exp"]; ok {
		if expTime, err := parseNumericDate(rawExp); err == nil {
			ttl := time.Until(expTime)
			if ttl > 0 {
				tokenTTL = ttl
			} else {
				tokenTTL = 5 * time.Minute // Fallback TTL
			}
		} else {
			tokenTTL = 5 * time.Minute // Fallback TTL
		}
	} else {
		tokenTTL = 5 * time.Minute // Fallback TTL
	}

	// Check token blacklist with Fail-Closed strategy
	// When cfg.RedisFailClosed is true:
	// - Redis errors cause token rejection (secure default for production)
	// - Local cache is used as fallback when available
	// When cfg.RedisFailClosed is false (development):
	// - Redis errors are logged but token is allowed (for easier debugging)
	if rdb != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
		defer cancel()

		redisAvailable := true

		// Check JTI blacklist (specific token revoked)
		if jti != "" {
			// First check local cache
			if globalLocalBlacklist.IsJTIBlacklisted(jti) {
				return "", false, fmt.Errorf("token revoked")
			}

			blacklisted, err := rdb.Exists(ctx, "token_blacklist:"+jti).Result()
			if err != nil {
				redisAvailable = false
				if cfg.RedisFailClosed {
					// Fail-Closed: reject token when Redis is unavailable
					log.Printf("[SECURITY] Redis unavailable with Fail-Closed mode, rejecting token for user %s: %v", userID, err)
					return "", false, fmt.Errorf("token validation unavailable")
				}
				// Fail-Open (development): log warning but continue
				log.Printf("[SECURITY WARNING] Redis blacklist check failed for jti, allowing token (Fail-Open mode): %v", err)
			} else if blacklisted > 0 {
				// Update local cache for future requests
				globalLocalBlacklist.AddJTI(jti, tokenTTL)
				return "", false, fmt.Errorf("token revoked")
			}
		}

		// Check user-level token revocation (all tokens issued before timestamp)
		if iatValue > 0 {
			// First check local cache
			if localTs, exists := globalLocalBlacklist.GetUserRevoked(userID); exists {
				if int64(iatValue) < localTs {
					return "", false, fmt.Errorf("token revoked by user")
				}
			}

			revokedBefore, err := rdb.Get(ctx, "user_revoked_before:"+userID).Result()
			if err != nil {
				if !redisAvailable && cfg.RedisFailClosed {
					// Already logged above, don't log again
					return "", false, fmt.Errorf("token validation unavailable")
				}
				if err != redis.Nil {
					if cfg.RedisFailClosed {
						log.Printf("[SECURITY] Redis user revocation check failed with Fail-Closed mode, rejecting token for user %s: %v", userID, err)
						return "", false, fmt.Errorf("token validation unavailable")
					}
					log.Printf("[SECURITY WARNING] Redis user revocation check failed, allowing token (Fail-Open mode): %v", err)
				}
			} else {
				if revokedTs, parseErr := strconv.ParseInt(revokedBefore, 10, 64); parseErr == nil {
					// Update local cache
					globalLocalBlacklist.SetUserRevoked(userID, revokedTs, tokenTTL)
					if int64(iatValue) < revokedTs {
						return "", false, fmt.Errorf("token revoked by user")
					}
				}
			}
		}

		// Check session-level revocation (device logout)
		if sid, ok := claims["sid"].(string); ok && sid != "" {
			sessionRevoked, err := rdb.Exists(ctx, "session_revoked:"+sid).Result()
			if err != nil {
				if !redisAvailable && cfg.RedisFailClosed {
					log.Printf("[SECURITY] Redis session revocation check failed with Fail-Closed mode, rejecting token for user %s: %v", userID, err)
					return "", false, fmt.Errorf("token validation unavailable")
				}
				if err != redis.Nil {
					if cfg.RedisFailClosed {
						log.Printf("[SECURITY] Redis session revocation check failed with Fail-Closed mode, rejecting token for user %s: %v", userID, err)
						return "", false, fmt.Errorf("token validation unavailable")
					}
					log.Printf("[SECURITY WARNING] Redis session revocation check failed, allowing token (Fail-Open mode): %v", err)
				}
			} else if sessionRevoked > 0 {
				return "", false, fmt.Errorf("session revoked")
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
