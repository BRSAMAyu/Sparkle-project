package config

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func jwtTestRSAKey(t *testing.T) *rsa.PrivateKey {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	return key
}

func jwtTestPrivatePEM(t *testing.T, key *rsa.PrivateKey) string {
	t.Helper()
	der, err := x509.MarshalPKCS8PrivateKey(key)
	require.NoError(t, err)
	return string(pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: der}))
}

func jwtTestPublicPEM(t *testing.T, key *rsa.PrivateKey) string {
	t.Helper()
	der, err := x509.MarshalPKIXPublicKey(&key.PublicKey)
	require.NoError(t, err)
	return string(pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: der}))
}

func TestParseJWTKeyPair_RoundTrip(t *testing.T) {
	key := jwtTestRSAKey(t)
	cfg := &Config{
		JWTPrivateKeyPEM: jwtTestPrivatePEM(t, key),
		JWTPublicKeyPEM:  jwtTestPublicPEM(t, key),
	}

	priv, err := cfg.ParseJWTPrivateKey()
	require.NoError(t, err)
	assert.Equal(t, key.N, priv.N, "private key must round-trip through PEM")

	pub, err := cfg.ParseJWTPublicKey()
	require.NoError(t, err)
	assert.Equal(t, key.PublicKey.N, pub.N, "public key must round-trip through PEM")
}

func TestParseJWTKeys_InvalidPEMRejected(t *testing.T) {
	cfg := &Config{JWTPrivateKeyPEM: "not-a-pem", JWTPublicKeyPEM: "not-a-pem"}
	_, err := cfg.ParseJWTPrivateKey()
	require.Error(t, err)
	_, err = cfg.ParseJWTPublicKey()
	require.Error(t, err)
}

func TestParseJWTPreviousPublicKey_RoundTripAndInvalid(t *testing.T) {
	key := jwtTestRSAKey(t)
	cfg := &Config{JWTPreviousPublicKeyPEM: jwtTestPublicPEM(t, key)}

	prev, err := cfg.ParseJWTPreviousPublicKey()
	require.NoError(t, err)
	assert.Equal(t, key.PublicKey.N, prev.N)

	cfg.JWTPreviousPublicKeyPEM = "garbage"
	_, err = cfg.ParseJWTPreviousPublicKey()
	require.Error(t, err)
}

func TestLoadJWTKeyFiles_FromFiles(t *testing.T) {
	key := jwtTestRSAKey(t)
	dir := t.TempDir()
	privPath := filepath.Join(dir, "jwt_private.pem")
	pubPath := filepath.Join(dir, "jwt_public.pem")
	prevPath := filepath.Join(dir, "jwt_previous_public.pem")
	require.NoError(t, os.WriteFile(privPath, []byte(jwtTestPrivatePEM(t, key)), 0o600))
	require.NoError(t, os.WriteFile(pubPath, []byte(jwtTestPublicPEM(t, key)), 0o600))
	require.NoError(t, os.WriteFile(prevPath, []byte(jwtTestPublicPEM(t, key)), 0o600))

	cfg := &Config{
		JWTPrivateKeyFile:        privPath,
		JWTPublicKeyFile:         pubPath,
		JWTPreviousPublicKeyFile: prevPath,
		JWTPrivateKeyPEM:         "",
		JWTPublicKeyPEM:          "",
		JWTPreviousPublicKeyPEM:  "",
	}
	require.NoError(t, cfg.loadJWTKeyFiles())

	_, err := cfg.ParseJWTPrivateKey()
	require.NoError(t, err)
	_, err = cfg.ParseJWTPublicKey()
	require.NoError(t, err)
	_, err = cfg.ParseJWTPreviousPublicKey()
	require.NoError(t, err)
}

func TestLoadJWTKeyFiles_InlinePEMTakesPrecedence(t *testing.T) {
	key := jwtTestRSAKey(t)
	dir := t.TempDir()
	filePath := filepath.Join(dir, "jwt_public.pem")
	require.NoError(t, os.WriteFile(filePath, []byte(jwtTestPublicPEM(t, key)), 0o600))

	inline := jwtTestPublicPEM(t, jwtTestRSAKey(t))
	cfg := &Config{JWTPublicKeyFile: filePath, JWTPublicKeyPEM: inline}
	require.NoError(t, cfg.loadJWTKeyFiles())
	assert.Equal(t, inline, cfg.JWTPublicKeyPEM, "inline PEM must win over the *_FILE mount")
}

func TestLoadJWTKeyFiles_MissingFileFails(t *testing.T) {
	cfg := &Config{JWTPrivateKeyFile: filepath.Join(t.TempDir(), "absent.pem")}
	err := cfg.loadJWTKeyFiles()
	require.Error(t, err, "a half-loaded key pair must never reach the signing path")
}

func TestHS256FallbackEnabled_Defaults(t *testing.T) {
	// nil (env unset / hand-built configs) keeps the dual-verify window open.
	assert.True(t, (&Config{}).HS256FallbackEnabled())

	on := true
	assert.True(t, (&Config{JWTHS256Fallback: &on}).HS256FallbackEnabled())

	off := false
	assert.False(t, (&Config{JWTHS256Fallback: &off}).HS256FallbackEnabled(),
		"JWT_HS256_FALLBACK=false must tighten verification to RS256-only")
}
