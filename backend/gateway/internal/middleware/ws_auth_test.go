package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newWsAuthTestRouter(cfg *config.Config, rdb *redis.Client) *gin.Engine {
	router := gin.New()
	router.Use(WsAuthMiddleware(cfg, rdb))
	router.GET("/ws", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"user_id":        c.GetString("user_id"),
			"is_admin":       c.GetBool("is_admin"),
			"auth_token":     c.GetString("auth_token"),
			"ws_auth_method": c.GetString("ws_auth_method"),
		})
	})
	return router
}

func performWsAuthRequest(router *gin.Engine, target string, token string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodGet, target, nil)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, req)
	return recorder
}

func TestWsAuthMiddleware_ValidHeaderToken(t *testing.T) {
	cfg := testAuthConfig()
	router := newWsAuthTestRouter(cfg, nil)
	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":      "ws-user-1",
		"type":     "access",
		"iat":      time.Now().Unix(),
		"exp":      time.Now().Add(30 * time.Minute).Unix(),
		"jti":      "ws-jti-header",
		"sid":      "ws-session-header",
		"is_admin": true,
		"iss":      cfg.JWTIssuer,
		"aud":      cfg.JWTAudience,
	})

	recorder := performWsAuthRequest(router, "/ws", token)

	require.Equal(t, http.StatusOK, recorder.Code)
	assert.JSONEq(t, `{
		"user_id":"ws-user-1",
		"is_admin":true,
		"auth_token":"`+token+`",
		"ws_auth_method":"jwt_header"
	}`, recorder.Body.String())
}

func TestWsAuthMiddleware_InvalidHeaderToken(t *testing.T) {
	cfg := testAuthConfig()
	router := newWsAuthTestRouter(cfg, nil)

	recorder := performWsAuthRequest(router, "/ws", "not-a-valid-jwt")

	assert.Equal(t, http.StatusUnauthorized, recorder.Code)
	assert.Contains(t, recorder.Body.String(), "Invalid or expired token")
}

func TestWsAuthMiddleware_MissingToken(t *testing.T) {
	cfg := testAuthConfig()
	router := newWsAuthTestRouter(cfg, nil)

	recorder := performWsAuthRequest(router, "/ws", "")

	assert.Equal(t, http.StatusUnauthorized, recorder.Code)
	assert.Contains(t, recorder.Body.String(), "Authorization token required")
}

func TestWsAuthMiddleware_QueryTokenPolicy(t *testing.T) {
	cfg := testAuthConfig()
	token := makeTestJWT(cfg, jwt.MapClaims{
		"sub":  "ws-query-user",
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(30 * time.Minute).Unix(),
		"jti":  "ws-jti-query",
		"sid":  "ws-session-query",
		"iss":  cfg.JWTIssuer,
		"aud":  cfg.JWTAudience,
	})

	cfg.AllowWsQueryToken = false
	disallowedRouter := newWsAuthTestRouter(cfg, nil)
	disallowed := performWsAuthRequest(disallowedRouter, "/ws?token="+token, "")
	require.Equal(t, http.StatusUnauthorized, disallowed.Code)
	assert.Contains(t, disallowed.Body.String(), "Authorization token required")

	cfg.AllowWsQueryToken = true
	allowedRouter := newWsAuthTestRouter(cfg, nil)
	allowed := performWsAuthRequest(allowedRouter, "/ws?token="+token, "")
	require.Equal(t, http.StatusOK, allowed.Code)
	assert.Contains(t, allowed.Body.String(), `"user_id":"ws-query-user"`)
	assert.Contains(t, allowed.Body.String(), `"ws_auth_method":"jwt_query"`)
}
