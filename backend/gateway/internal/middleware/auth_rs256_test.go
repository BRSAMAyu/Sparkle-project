package middleware

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"sync"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/config"
)

// rsaTestKeys generates two 2048-bit keys once per test binary — keygen
// dominates this suite's runtime otherwise. First is the active signing key,
// second plays the previous (rotation grace) key.
var rsaTestKeys = sync.OnceValues(func() (*rsa.PrivateKey, *rsa.PrivateKey) {
	gen := func() *rsa.PrivateKey {
		k, err := rsa.GenerateKey(rand.Reader, 2048)
		if err != nil {
			panic(err)
		}
		return k
	}
	return gen(), gen()
})

func marshalPrivatePEM(t testing.TB, key *rsa.PrivateKey) string {
	t.Helper()
	der, err := x509.MarshalPKCS8PrivateKey(key)
	require.NoError(t, err)
	return string(pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: der}))
}

func marshalPublicPEM(t testing.TB, key *rsa.PrivateKey) string {
	t.Helper()
	der, err := x509.MarshalPKIXPublicKey(&key.PublicKey)
	require.NoError(t, err)
	return string(pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: der}))
}

// rs256TestConfig wires an RSA keypair into the config the way the
// JWT_PRIVATE_KEY/JWT_PUBLIC_KEY env would. rotate=true registers the second
// key as the previous (verify-only) rotation key under its own kid.
func rs256TestConfig(t testing.TB, rotate bool) *config.Config {
	active, prev := rsaTestKeys()
	cfg := &config.Config{
		JWTSecret:       "test-secret-key-at-least-32-chars",
		JWTIssuer:       "sparkle-test",
		JWTAudience:     "sparkle-users",
		JWTAlgorithm:    "RS256",
		JWTKid:          "k2-active",
		RedisFailClosed: false,
	}
	cfg.JWTPrivateKeyPEM = marshalPrivatePEM(t, active)
	cfg.JWTPublicKeyPEM = marshalPublicPEM(t, active)
	if rotate {
		cfg.JWTPreviousKid = "k1-previous"
		cfg.JWTPreviousPublicKeyPEM = marshalPublicPEM(t, prev)
	}
	return cfg
}

func rs256Claims(cfg *config.Config) jwt.MapClaims {
	now := time.Now()
	return jwt.MapClaims{
		"sub":  "user-rs256",
		"type": "access",
		"iat":  now.Unix(),
		"exp":  now.Add(30 * time.Minute).Unix(),
		"jti":  "jti-rs256-001",
		"sid":  "sid-rs256-001",
		"iss":  cfg.JWTIssuer,
		"aud":  cfg.JWTAudience,
	}
}

func signRS256(t *testing.T, key *rsa.PrivateKey, kid string, claims jwt.MapClaims) string {
	t.Helper()
	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	if kid != "" {
		token.Header["kid"] = kid
	}
	signed, err := token.SignedString(key)
	require.NoError(t, err)
	return signed
}

func hs256Token(t *testing.T, key []byte, claims jwt.MapClaims) string {
	t.Helper()
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString(key)
	require.NoError(t, err)
	return signed
}

func TestValidateJWT_RS256TokenAccepted(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	active, _ := rsaTestKeys()

	tokenStr := signRS256(t, active, "k2-active", rs256Claims(cfg))
	userID, isAdmin, err := validateJWT(cfg, nil, tokenStr)
	require.NoError(t, err)
	assert.Equal(t, "user-rs256", userID)
	assert.False(t, isAdmin)
}

func TestValidateJWT_RS256WithoutKidAccepted(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	active, _ := rsaTestKeys()

	tokenStr := signRS256(t, active, "", rs256Claims(cfg))
	userID, _, err := validateJWT(cfg, nil, tokenStr)
	require.NoError(t, err)
	assert.Equal(t, "user-rs256", userID)
}

func TestValidateJWT_HS256LegacyTokenAccepted_DualVerify(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	require.True(t, cfg.HS256FallbackEnabled(), "dual-verify must be the default")

	tokenStr := hs256Token(t, []byte(cfg.JWTSecret), rs256Claims(cfg))
	userID, _, err := validateJWT(cfg, nil, tokenStr)
	require.NoError(t, err)
	assert.Equal(t, "user-rs256", userID)
}

func TestValidateJWT_HS256Rejected_WhenFallbackTightened(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	fallbackOff := false
	cfg.JWTHS256Fallback = &fallbackOff

	legacy := hs256Token(t, []byte(cfg.JWTSecret), rs256Claims(cfg))
	_, _, err := validateJWT(cfg, nil, legacy)
	require.Error(t, err, "HS256 tokens must be rejected once JWT_HS256_FALLBACK=false")

	// RS256 path must stay open after tightening.
	active, _ := rsaTestKeys()
	rs := signRS256(t, active, "k2-active", rs256Claims(cfg))
	userID, _, err := validateJWT(cfg, nil, rs)
	require.NoError(t, err)
	assert.Equal(t, "user-rs256", userID)
}

func TestValidateJWT_AlgNoneRejected_UnderRS256Config(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	token := jwt.NewWithClaims(jwt.SigningMethodNone, rs256Claims(cfg))
	tokenStr, err := token.SignedString(jwt.UnsafeAllowNoneSignatureType)
	require.NoError(t, err)

	_, _, err = validateJWT(cfg, nil, tokenStr)
	require.Error(t, err, "alg=none must never verify")
}

func TestValidateJWT_HS256WithPublicKeyAsHMACSecretRejected(t *testing.T) {
	// Classic algorithm-confusion attack: attacker signs with alg=HS256
	// using the (public!) RSA public key as the HMAC secret. The verifier
	// must only ever accept HS256 against the server-side JWT_SECRET, so
	// both the PEM text and the raw DER forms must fail.
	cfg := rs256TestConfig(t, false)
	claims := rs256Claims(cfg)

	pubPEM := cfg.JWTPublicKeyPEM
	_, _, err := validateJWT(cfg, nil, hs256Token(t, []byte(pubPEM), claims))
	require.Error(t, err, "HS256 with public-key PEM as HMAC secret must be rejected")

	block, _ := pem.Decode([]byte(pubPEM))
	require.NotNil(t, block)
	_, _, err = validateJWT(cfg, nil, hs256Token(t, block.Bytes, claims))
	require.Error(t, err, "HS256 with public-key DER as HMAC secret must be rejected")
}

func TestValidateJWT_RS256TamperedSignatureRejected(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	active, _ := rsaTestKeys()
	tokenStr := signRS256(t, active, "k2-active", rs256Claims(cfg))

	runes := []rune(tokenStr)
	runes[len(runes)-1] ^= 0x01
	_, _, err := validateJWT(cfg, nil, string(runes))
	require.Error(t, err, "tampered signature must be rejected")
}

func TestValidateJWT_RS256ExpiredRejected(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	active, _ := rsaTestKeys()
	claims := rs256Claims(cfg)
	claims["exp"] = time.Now().Add(-time.Hour).Unix()
	tokenStr := signRS256(t, active, "k2-active", claims)

	_, _, err := validateJWT(cfg, nil, tokenStr)
	require.Error(t, err, "expired RS256 token must be rejected")
}

func TestValidateJWT_RS256SignedByUnregisteredKeyRejected(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	unregistered, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)

	tokenStr := signRS256(t, unregistered, "k2-active", rs256Claims(cfg))
	_, _, err = validateJWT(cfg, nil, tokenStr)
	require.Error(t, err, "signature from a key outside the trust set must be rejected")
}

func TestValidateJWT_RS256Rotation_PreviousKidVerifiesWithPreviousKey(t *testing.T) {
	cfg := rs256TestConfig(t, true)
	_, prev := rsaTestKeys()

	// Old key still signs during the rotation grace: kid=k1 routes the
	// signature to the previous public key.
	tokenStr := signRS256(t, prev, cfg.JWTPreviousKid, rs256Claims(cfg))
	userID, _, err := validateJWT(cfg, nil, tokenStr)
	require.NoError(t, err)
	assert.Equal(t, "user-rs256", userID)
}

func TestValidateJWT_RS256UnknownKidCannotBypassSignature(t *testing.T) {
	cfg := rs256TestConfig(t, true)
	_, prev := rsaTestKeys()

	// Attacker-controlled kid pointing at an unregistered key id: the
	// keyfunc falls back to the active pubkey, which cannot verify a
	// previous-key signature.
	tokenStr := signRS256(t, prev, "k99-attacker", rs256Claims(cfg))
	_, _, err := validateJWT(cfg, nil, tokenStr)
	require.Error(t, err, "unknown kid must not bypass the active-key signature check")
}

func TestValidateJWT_RS256RefreshTokenTypeRejected(t *testing.T) {
	cfg := rs256TestConfig(t, false)
	active, _ := rsaTestKeys()
	claims := rs256Claims(cfg)
	claims["type"] = "refresh"
	tokenStr := signRS256(t, active, "k2-active", claims)

	_, _, err := validateJWT(cfg, nil, tokenStr)
	require.Error(t, err, "refresh tokens must not authenticate as access tokens")
}
