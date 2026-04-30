package handler

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestReader(s string) io.Reader { return strings.NewReader(s) }

func makeTestUUID() pgtype.UUID {
	id := uuid.New()
	var pgID pgtype.UUID
	copy(pgID.Bytes[:], id[:])
	pgID.Valid = true
	return pgID
}

func testAuthHandler() *AuthHandler {
	return &AuthHandler{
		cfg: &config.Config{
			JWTSecret:                   "test-secret-key-at-least-32-chars",
			JWTAccessTokenExpireMinutes: 30,
			JWTRefreshTokenExpireDays:   7,
			JWTIssuer:                   "sparkle-test",
			JWTAudience:                 "sparkle-users",
		},
	}
}

func TestCreateAccessToken_Structure(t *testing.T) {
	h := testAuthHandler()
	userID := makeTestUUID()
	tokenStr, err := h.createAccessToken(userID, "session-abc")
	require.NoError(t, err)
	require.NotEmpty(t, tokenStr)

	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return []byte(h.cfg.JWTSecret), nil
	})
	require.NoError(t, err)
	require.True(t, token.Valid)

	claims, ok := token.Claims.(jwt.MapClaims)
	require.True(t, ok)

	assert.Equal(t, "access", claims["type"])
	assert.Equal(t, "session-abc", claims["sid"])
	assert.Equal(t, "sparkle-test", claims["iss"])
	assert.Equal(t, "sparkle-users", claims["aud"])
	assert.Contains(t, claims, "sub")
	assert.Contains(t, claims, "exp")
	assert.Contains(t, claims, "iat")
	assert.Contains(t, claims, "jti")

	expFloat := claims["exp"].(float64)
	iatFloat := claims["iat"].(float64)
	assert.InDelta(t, 1800, expFloat-iatFloat, 5) // 30 min
}

func TestCreateRefreshToken_Structure(t *testing.T) {
	h := testAuthHandler()
	userID := makeTestUUID()
	tokenStr, jti, err := h.createRefreshToken(userID, "session-xyz")
	require.NoError(t, err)
	require.NotEmpty(t, tokenStr)
	require.NotEmpty(t, jti)

	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return []byte(h.cfg.JWTSecret), nil
	})
	require.NoError(t, err)
	require.True(t, token.Valid)

	claims, ok := token.Claims.(jwt.MapClaims)
	require.True(t, ok)

	assert.Equal(t, "refresh", claims["type"])
	assert.Equal(t, "session-xyz", claims["sid"])
	assert.Equal(t, jti, claims["jti"])
	assert.Equal(t, "sparkle-test", claims["iss"])

	expFloat := claims["exp"].(float64)
	iatFloat := claims["iat"].(float64)
	assert.InDelta(t, 7*24*3600, expFloat-iatFloat, 5) // 7 days
}

func TestCreateAccessToken_DefaultExpiration(t *testing.T) {
	h := &AuthHandler{
		cfg: &config.Config{
			JWTSecret:                   "test-secret-key-at-least-32-chars",
			JWTAccessTokenExpireMinutes: 0,
		},
	}
	tokenStr, err := h.createAccessToken(makeTestUUID(), "s1")
	require.NoError(t, err)

	token, _ := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return []byte(h.cfg.JWTSecret), nil
	})
	claims := token.Claims.(jwt.MapClaims)
	expFloat := claims["exp"].(float64)
	iatFloat := claims["iat"].(float64)
	assert.InDelta(t, 1800, expFloat-iatFloat, 5) // defaults to 30 min
}

func TestCreateRefreshToken_DefaultExpiration(t *testing.T) {
	h := &AuthHandler{
		cfg: &config.Config{JWTSecret: "test-secret-key-at-least-32-chars"},
	}
	tokenStr, _, err := h.createRefreshToken(makeTestUUID(), "s1")
	require.NoError(t, err)

	token, _ := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return []byte(h.cfg.JWTSecret), nil
	})
	claims := token.Claims.(jwt.MapClaims)
	expFloat := claims["exp"].(float64)
	iatFloat := claims["iat"].(float64)
	assert.InDelta(t, 7*24*3600, expFloat-iatFloat, 5) // defaults to 7 days
}

func TestCreateAccessToken_HS256(t *testing.T) {
	h := testAuthHandler()
	tokenStr, err := h.createAccessToken(makeTestUUID(), "s1")
	require.NoError(t, err)

	token, _ := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		assert.Equal(t, jwt.SigningMethodHS256, token.Method)
		return []byte(h.cfg.JWTSecret), nil
	})
	assert.True(t, token.Valid)
}

func TestCreateAccessToken_NoIssuerWhenEmpty(t *testing.T) {
	h := &AuthHandler{
		cfg: &config.Config{
			JWTSecret:                   "test-secret-key-at-least-32-chars",
			JWTAccessTokenExpireMinutes: 30,
		},
	}
	tokenStr, _ := h.createAccessToken(makeTestUUID(), "s1")
	token, _ := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return []byte(h.cfg.JWTSecret), nil
	})
	claims := token.Claims.(jwt.MapClaims)
	_, hasISS := claims["iss"]
	_, hasAud := claims["aud"]
	assert.False(t, hasISS)
	assert.False(t, hasAud)
}

func TestCreateAccessToken_DifferentSessions(t *testing.T) {
	h := testAuthHandler()
	userID := makeTestUUID()

	t1, _ := h.createAccessToken(userID, "session-A")
	t2, _ := h.createAccessToken(userID, "session-B")

	parsed1, _ := jwt.Parse(t1, func(token *jwt.Token) (interface{}, error) { return []byte(h.cfg.JWTSecret), nil })
	parsed2, _ := jwt.Parse(t2, func(token *jwt.Token) (interface{}, error) { return []byte(h.cfg.JWTSecret), nil })

	c1 := parsed1.Claims.(jwt.MapClaims)
	c2 := parsed2.Claims.(jwt.MapClaims)

	assert.Equal(t, "session-A", c1["sid"])
	assert.Equal(t, "session-B", c2["sid"])
	assert.NotEqual(t, c1["jti"], c2["jti"]) // Each token gets unique JTI
}

func TestRandomString_Length(t *testing.T) {
	h := &AuthHandler{cfg: &config.Config{}}
	for _, n := range []int{8, 16, 32} {
		s := h.randomString(n)
		assert.Equal(t, n, len(s))
	}
}

func TestRandomString_Uniqueness(t *testing.T) {
	h := &AuthHandler{cfg: &config.Config{}}
	seen := make(map[string]bool)
	for i := 0; i < 100; i++ {
		s := h.randomString(16)
		assert.False(t, seen[s])
		seen[s] = true
	}
}

func TestRandomString_HexFormat(t *testing.T) {
	h := &AuthHandler{cfg: &config.Config{}}
	s := h.randomString(16)
	for _, c := range s {
		assert.True(t, (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'),
			"randomString should be hex, got: %c", c)
	}
}

func TestUuidToString(t *testing.T) {
	h := &AuthHandler{cfg: &config.Config{}}
	id := makeTestUUID()
	s := h.uuidToString(id)
	parsed, err := uuid.Parse(s)
	assert.NoError(t, err)
	assert.Equal(t, id.Bytes[:], parsed[:])
}

func TestUuidToString_Consistency(t *testing.T) {
	h := &AuthHandler{cfg: &config.Config{}}
	id := makeTestUUID()
	s1 := h.uuidToString(id)
	s2 := h.uuidToString(id)
	assert.Equal(t, s1, s2)
}

func TestAppleLogin_MissingProvider(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := testAuthHandler()
	r := gin.New()
	r.POST("/auth/apple", h.AppleLogin)

	body := `{"token": "abc"}`
	req := httptest.NewRequest(http.MethodPost, "/auth/apple", newTestReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestAppleLogin_UnsupportedProvider(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := testAuthHandler()
	r := gin.New()
	r.POST("/auth/apple", h.AppleLogin)

	body := `{"provider": "google", "token": "abc"}`
	req := httptest.NewRequest(http.MethodPost, "/auth/apple", newTestReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.NotNil(t, resp["error"]) // Error message returned (i18n may vary)
}

func TestAppleLogin_InvalidJSON(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := testAuthHandler()
	r := gin.New()
	r.POST("/auth/apple", h.AppleLogin)

	req := httptest.NewRequest(http.MethodPost, "/auth/apple", newTestReader(`{invalid`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestAppleLogin_MissingToken(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := testAuthHandler()
	r := gin.New()
	r.POST("/auth/apple", h.AppleLogin)

	body := `{"provider": "apple"}`
	req := httptest.NewRequest(http.MethodPost, "/auth/apple", newTestReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}
