package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	dto "github.com/prometheus/client_model/go"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/metrics"
)

func keyAuthFailureCount(mechanism, reason string) float64 {
	var m dto.Metric
	if err := metrics.KeyAuthFailures.WithLabelValues(mechanism, reason).Write(&m); err != nil {
		return 0
	}
	return m.GetCounter().GetValue()
}

// serveKeyAuth runs a request through a middleware constructor func and
// returns the response recorder.
func serveKeyAuth(mw gin.HandlerFunc, headers map[string]string) *httptest.ResponseRecorder {
	r := gin.New()
	r.Use(mw)
	r.GET("/probe", func(c *gin.Context) { c.Status(http.StatusOK) })
	req := httptest.NewRequest(http.MethodGet, "/probe", nil)
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	return w
}

// TestKeyAuthFailuresCounted pins the GW-9 fix: static-key rejections on the
// admin and internal API surfaces increment sparkle_key_auth_failures_total.
// These requests are aborted before rate limiting sees them, so the counter
// is the only non-log signal of brute-force probing.
func TestKeyAuthFailuresCounted(t *testing.T) {
	// Admin secret: missing and invalid are counted separately.
	beforeMissing := keyAuthFailureCount("admin_secret", "missing")
	w := serveKeyAuth(AdminAuthMiddleware(&config.Config{AdminSecret: "real-secret"}), nil)
	require.Equal(t, http.StatusUnauthorized, w.Code)
	require.Greater(t, keyAuthFailureCount("admin_secret", "missing"), beforeMissing)

	beforeInvalid := keyAuthFailureCount("admin_secret", "invalid")
	w = serveKeyAuth(AdminAuthMiddleware(&config.Config{AdminSecret: "real-secret"}), map[string]string{"X-Admin-Secret": "wrong"})
	require.Equal(t, http.StatusUnauthorized, w.Code)
	require.Greater(t, keyAuthFailureCount("admin_secret", "invalid"), beforeInvalid)

	// Valid secret is NOT counted as a failure.
	beforeValid := keyAuthFailureCount("admin_secret", "invalid")
	w = serveKeyAuth(AdminAuthMiddleware(&config.Config{AdminSecret: "real-secret"}), map[string]string{"X-Admin-Secret": "real-secret"})
	require.Equal(t, http.StatusOK, w.Code)
	require.Equal(t, beforeValid, keyAuthFailureCount("admin_secret", "invalid"))

	// Internal API key: missing and invalid.
	beforeMissingKey := keyAuthFailureCount("internal_api_key", "missing")
	w = serveKeyAuth(InternalAPIKeyMiddleware(&config.Config{InternalAPIKey: "internal-key"}), nil)
	require.Equal(t, http.StatusUnauthorized, w.Code)
	require.Greater(t, keyAuthFailureCount("internal_api_key", "missing"), beforeMissingKey)

	beforeInvalidKey := keyAuthFailureCount("internal_api_key", "invalid")
	w = serveKeyAuth(InternalAPIKeyMiddleware(&config.Config{InternalAPIKey: "internal-key"}), map[string]string{"X-Internal-API-Key": "wrong"})
	require.Equal(t, http.StatusUnauthorized, w.Code)
	require.Greater(t, keyAuthFailureCount("internal_api_key", "invalid"), beforeInvalidKey)
}
