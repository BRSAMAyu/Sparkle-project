package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
)

func makeTestJWT(cfg *config.Config, claims jwt.MapClaims) string {
	if claims == nil {
		claims = jwt.MapClaims{
			"sub":  "user-123",
			"type": "access",
			"iat":  time.Now().Unix(),
			"exp":  time.Now().Add(30 * time.Minute).Unix(),
			"jti":  "test-jti-001",
			"sid":  "session-001",
			"iss":  cfg.JWTIssuer,
			"aud":  cfg.JWTAudience,
		}
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	s, _ := token.SignedString([]byte(cfg.JWTSecret))
	return s
}

func testAuthConfig() *config.Config {
	return &config.Config{
		JWTSecret:      "test-secret-key-at-least-32-chars",
		JWTIssuer:      "sparkle-test",
		JWTAudience:    "sparkle-users",
		RedisFailClosed: false,
	}
}

func TestAuthMiddleware_MissingToken(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) { c.JSON(200, gin.H{"ok": true}) })

	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAuthMiddleware_InvalidToken(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) { c.JSON(200, gin.H{"ok": true}) })

	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", "Bearer invalid-token")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAuthMiddleware_ValidToken(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) {
		userID, _ := c.Get("user_id")
		c.JSON(200, gin.H{"user_id": userID})
	})

	token := makeTestJWT(cfg, nil)
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestAuthMiddleware_SetsUserContext(t *testing.T) {
	cfg := testAuthConfig()
	var capturedUserID, capturedToken string
	var capturedIsAdmin bool

	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/test", func(c *gin.Context) {
		capturedUserID = c.GetString("user_id")
		capturedToken = c.GetString("auth_token")
		capturedIsAdmin = c.GetBool("is_admin")
		c.Status(200)
	})

	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":      "user-abc",
		"type":     "access",
		"iat":      time.Now().Unix(),
		"exp":      time.Now().Add(30 * time.Minute).Unix(),
		"jti":      "jti-001",
		"sid":      "sid-001",
		"is_admin": true,
		"iss":      cfg.JWTIssuer,
		"aud":      cfg.JWTAudience,
	})
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "user-abc", capturedUserID)
	assert.Equal(t, token, capturedToken)
	assert.True(t, capturedIsAdmin)
}

func TestAuthMiddleware_ExpiredToken(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) { c.Status(200) })

	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "user-123",
		"type": "access",
		"iat":  time.Now().Add(-2 * time.Hour).Unix(),
		"exp":  time.Now().Add(-1 * time.Hour).Unix(),
		"jti":  "expired-jti",
		"sid":  "expired-sid",
	})
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAuthMiddleware_RefreshTokenRejected(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) { c.Status(200) })

	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "user-123",
		"type": "refresh", // Wrong type
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(7 * 24 * time.Hour).Unix(),
	})
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAuthMiddleware_UserIDMismatch(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) { c.Status(200) })

	token := makeTestJWT(cfg, nil)
	req := httptest.NewRequest(http.MethodGet, "/protected?user_id=different-user", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusForbidden, w.Code)
}

func TestAuthMiddleware_UserIDMatch(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) { c.Status(200) })

	token := makeTestJWT(cfg, nil)
	req := httptest.NewRequest(http.MethodGet, "/protected?user_id=user-123", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestAuthMiddleware_MissingBearerPrefix(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) { c.Status(200) })

	token := makeTestJWT(cfg, nil)
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", token) // Missing "Bearer " prefix
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAuthMiddleware_WrongSigningMethod(t *testing.T) {
	cfg := testAuthConfig()
	r := gin.New()
	r.Use(AuthMiddleware(cfg, nil))
		// route-tier: internal
	r.GET("/protected", func(c *gin.Context) { c.Status(200) })

	// Create token with wrong signing method
	token := jwt.NewWithClaims(jwt.SigningMethodNone, jwt.MapClaims{
		"sub":  "user-123",
		"type": "access",
		"exp":  time.Now().Add(30 * time.Minute).Unix(),
	})
	tokenStr, _ := token.SignedString(jwt.UnsafeAllowNoneSignatureType)

	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", "Bearer "+tokenStr)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAdminAuthMiddleware_ValidSecret(t *testing.T) {
	cfg := &config.Config{AdminSecret: "admin-secret-123"}
	r := gin.New()
	r.Use(AdminAuthMiddleware(cfg))
		// route-tier: internal
	r.GET("/admin", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	req.Header.Set("X-Admin-Secret", "admin-secret-123")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestAdminAuthMiddleware_InvalidSecret(t *testing.T) {
	cfg := &config.Config{AdminSecret: "admin-secret-123"}
	r := gin.New()
	r.Use(AdminAuthMiddleware(cfg))
		// route-tier: internal
	r.GET("/admin", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	req.Header.Set("X-Admin-Secret", "wrong-secret")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAdminAuthMiddleware_MissingSecret(t *testing.T) {
	cfg := &config.Config{AdminSecret: ""}
	r := gin.New()
	r.Use(AdminAuthMiddleware(cfg))
		// route-tier: internal
	r.GET("/admin", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAdminAuthMiddleware_MissingHeader(t *testing.T) {
	cfg := &config.Config{AdminSecret: "admin-secret-123"}
	r := gin.New()
	r.Use(AdminAuthMiddleware(cfg))
		// route-tier: internal
	r.GET("/admin", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	// No X-Admin-Secret header
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestRequireAdmin_IsAdmin(t *testing.T) {
	r := gin.New()
	r.Use(func(c *gin.Context) { c.Set("is_admin", true); c.Next() })
	r.Use(RequireAdmin)
		// route-tier: internal
	r.GET("/admin", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestRequireAdmin_NotAdmin(t *testing.T) {
	r := gin.New()
	r.Use(func(c *gin.Context) { c.Set("is_admin", false); c.Next() })
	r.Use(RequireAdmin)
		// route-tier: internal
	r.GET("/admin", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusForbidden, w.Code)
}

func TestClaimHasAudience(t *testing.T) {
	assert.True(t, claimHasAudience("sparkle-users", "sparkle-users"))
	assert.False(t, claimHasAudience("other", "sparkle-users"))
	assert.False(t, claimHasAudience(nil, "sparkle-users"))
	assert.True(t, claimHasAudience([]interface{}{"sparkle-users", "other"}, "sparkle-users"))
	assert.False(t, claimHasAudience([]interface{}{"other"}, "sparkle-users"))
	assert.True(t, claimHasAudience([]string{"sparkle-users"}, "sparkle-users"))
}

func TestLocalBlacklistCache_JTI(t *testing.T) {
	cache := &localBlacklistCache{
		jtiSet:      make(map[string]time.Time),
		userRevoked: make(map[string]localRevocation),
	}

	assert.False(t, cache.IsJTIBlacklisted("jti-1"))

	cache.AddJTI("jti-1", 5*time.Minute)
	assert.True(t, cache.IsJTIBlacklisted("jti-1"))
	assert.False(t, cache.IsJTIBlacklisted("jti-2"))
}

func TestLocalBlacklistCache_UserRevocation(t *testing.T) {
	cache := &localBlacklistCache{
		jtiSet:      make(map[string]time.Time),
		userRevoked: make(map[string]localRevocation),
	}

	_, exists := cache.GetUserRevoked("user-1")
	assert.False(t, exists)

	cache.SetUserRevoked("user-1", 1700000000, 5*time.Minute)
	ts, exists := cache.GetUserRevoked("user-1")
	assert.True(t, exists)
	assert.Equal(t, int64(1700000000), ts)
}

func TestLocalBlacklistCache_ExpiredEntry(t *testing.T) {
	cache := &localBlacklistCache{
		jtiSet:      make(map[string]time.Time),
		userRevoked: make(map[string]localRevocation),
	}

	cache.AddJTI("expired-jti", -1*time.Second)
	assert.False(t, cache.IsJTIBlacklisted("expired-jti"))
}

func TestIsWebSocketRequest(t *testing.T) {
	r := gin.New()
		// route-tier: internal
	r.GET("/ws", func(c *gin.Context) {
		assert.True(t, isWebSocketRequest(c))
		c.Status(200)
	})
		// route-tier: internal
	r.GET("/http", func(c *gin.Context) {
		assert.False(t, isWebSocketRequest(c))
		c.Status(200)
	})

	wsReq := httptest.NewRequest(http.MethodGet, "/ws", nil)
	wsReq.Header.Set("Upgrade", "websocket")
	wsReq.Header.Set("Connection", "Upgrade")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, wsReq)

	httpReq := httptest.NewRequest(http.MethodGet, "/http", nil)
	w2 := httptest.NewRecorder()
	r.ServeHTTP(w2, httpReq)
}

func TestValidateJWT_IssuerCheck(t *testing.T) {
	cfg := &config.Config{
		JWTSecret:       "test-secret-key-at-least-32-chars",
		JWTIssuer:       "expected-issuer",
		RedisFailClosed: false,
	}

	// Wrong issuer
	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "user-1",
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(30 * time.Minute).Unix(),
		"iss":  "wrong-issuer",
	})
	_, _, err := validateJWT(cfg, nil, token)
	assert.Error(t, err)

	// Correct issuer
	token2 := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "user-1",
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(30 * time.Minute).Unix(),
		"iss":  "expected-issuer",
	})
	userID, _, err := validateJWT(cfg, nil, token2)
	assert.NoError(t, err)
	assert.Equal(t, "user-1", userID)
}

func TestValidateJWT_AudienceCheck(t *testing.T) {
	cfg := &config.Config{
		JWTSecret:       "test-secret-key-at-least-32-chars",
		JWTAudience:     "expected-aud",
		RedisFailClosed: false,
	}

	// Wrong audience
	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "user-1",
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(30 * time.Minute).Unix(),
		"aud":  "wrong-aud",
	})
	_, _, err := validateJWT(cfg, nil, token)
	assert.Error(t, err)

	// Correct audience
	token2 := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "user-1",
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(30 * time.Minute).Unix(),
		"aud":  "expected-aud",
	})
	userID, _, err := validateJWT(cfg, nil, token2)
	assert.NoError(t, err)
	assert.Equal(t, "user-1", userID)
}

func TestParseNumericDate(t *testing.T) {
	expected := time.Unix(1700000000, 0).UTC()

	result, err := parseNumericDate(float64(1700000000))
	assert.NoError(t, err)
	assert.Equal(t, expected, result)

	result, err = parseNumericDate(int64(1700000000))
	assert.NoError(t, err)
	assert.Equal(t, expected, result)

	result, err = parseNumericDate(1700000000)
	assert.NoError(t, err)
	assert.Equal(t, expected, result)

	_, err = parseNumericDate("invalid")
	assert.Error(t, err)
}
