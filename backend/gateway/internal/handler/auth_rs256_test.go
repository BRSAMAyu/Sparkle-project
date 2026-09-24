package handler

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"testing"

	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/config"
)

// signTestRSAKey: 2048-bit keygen per call is acceptable here (3 call sites).
func signTestRSAKey(t *testing.T) *rsa.PrivateKey {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	return key
}

func signTestRS256Config(t *testing.T, withKid bool) (*config.Config, *rsa.PrivateKey) {
	t.Helper()
	key := signTestRSAKey(t)

	privDER, err := x509.MarshalPKCS8PrivateKey(key)
	require.NoError(t, err)
	privPEM := string(pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privDER}))

	pubDER, err := x509.MarshalPKIXPublicKey(&key.PublicKey)
	require.NoError(t, err)
	pubPEM := string(pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: pubDER}))

	cfg := &config.Config{
		JWTSecret:                   "test-secret-key-at-least-32-chars",
		JWTAccessTokenExpireMinutes: 30,
		JWTRefreshTokenExpireDays:   7,
		JWTIssuer:                   "sparkle-test",
		JWTAudience:                 "sparkle-users",
		JWTAlgorithm:                "RS256",
		JWTPrivateKeyPEM:            privPEM,
		JWTPublicKeyPEM:             pubPEM,
	}
	if withKid {
		cfg.JWTKid = "k2-active"
	}
	return cfg, key
}

func parseWithPublicKey(t *testing.T, tokenStr string, pub *rsa.PublicKey) (jwt.MapClaims, map[string]interface{}) {
	t.Helper()
	parsed, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		require.Equal(t, jwt.SigningMethodRS256.Alg(), token.Method.Alg())
		return pub, nil
	}, jwt.WithValidMethods([]string{"RS256"}))
	require.NoError(t, err)
	require.True(t, parsed.Valid)
	claims, ok := parsed.Claims.(jwt.MapClaims)
	require.True(t, ok)
	return claims, parsed.Header
}

func TestCreateAccessToken_RS256_AlgAndKidHeader(t *testing.T) {
	cfg, key := signTestRS256Config(t, true)
	h := &AuthHandler{cfg: cfg}

	tokenStr, err := h.createAccessToken(makeTestUUID(), "session-rs256")
	require.NoError(t, err)

	claims, header := parseWithPublicKey(t, tokenStr, &key.PublicKey)
	assert.Equal(t, "RS256", header["alg"])
	assert.Equal(t, "k2-active", header["kid"], "active kid must be stamped for rotation routing")
	assert.Equal(t, "access", claims["type"])
	assert.Equal(t, "session-rs256", claims["sid"])
}

func TestCreateAccessToken_RS256_NoKidWhenUnset(t *testing.T) {
	cfg, key := signTestRS256Config(t, false)
	h := &AuthHandler{cfg: cfg}

	tokenStr, err := h.createAccessToken(makeTestUUID(), "s1")
	require.NoError(t, err)

	_, header := parseWithPublicKey(t, tokenStr, &key.PublicKey)
	_, hasKid := header["kid"]
	assert.False(t, hasKid, "kid header stays absent when JWT_KID is unset")
}

func TestCreateRefreshToken_RS256_TypeAndAlg(t *testing.T) {
	cfg, key := signTestRS256Config(t, true)
	h := &AuthHandler{cfg: cfg}

	tokenStr, jti, err := h.createRefreshToken(makeTestUUID(), "session-rs256")
	require.NoError(t, err)
	require.NotEmpty(t, jti)

	claims, header := parseWithPublicKey(t, tokenStr, &key.PublicKey)
	assert.Equal(t, "RS256", header["alg"])
	assert.Equal(t, "refresh", claims["type"])
	assert.Equal(t, jti, claims["jti"])
}

func TestCreateAccessToken_HS256_NoKidHeader(t *testing.T) {
	// Legacy path: HS256 tokens are pinned to JWT_SECRET and carry no kid.
	h := testAuthHandler()
	tokenStr, err := h.createAccessToken(makeTestUUID(), "s1")
	require.NoError(t, err)

	parsed, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		require.Equal(t, jwt.SigningMethodHS256.Alg(), token.Method.Alg())
		return []byte(h.cfg.JWTSecret), nil
	}, jwt.WithValidMethods([]string{"HS256"}))
	require.NoError(t, err)
	require.True(t, parsed.Valid)

	_, hasKid := parsed.Header["kid"]
	assert.False(t, hasKid, "HS256 legacy tokens must not carry a kid header")
	assert.Equal(t, "HS256", parsed.Header["alg"])
}
