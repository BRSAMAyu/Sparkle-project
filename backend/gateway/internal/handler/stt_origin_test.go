package handler

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/config"
)

// GW-P2-2 regression (updated by R2-GW-8): /ws/stt must follow the
// WebSocketFactory origin policy. That policy changed with R2-GW-8 — empty
// Origin is now allowed in every environment because the request has already
// passed WsAuth (JWT/ticket) and native mobile clients never send an Origin;
// the previous empty-Origin rejection made production mobile STT unusable.
// Non-empty origins still go through the configured whitelist in production,
// and development keeps its local-host allowances.
func TestSTTUpgrader_OriginPolicyMatchesFactory(t *testing.T) {
	prodCfg := &config.Config{Environment: "prod", AllowedOrigins: []string{"https://app.example.com"}}
	devCfg := &config.Config{Environment: "development", AllowedOrigins: []string{"https://app.example.com"}}

	req := func(origin string) *http.Request {
		r := httptest.NewRequest(http.MethodGet, "/ws/stt", nil)
		if origin != "" {
			r.Header.Set("Origin", origin)
		}
		return r
	}

	t.Run("production_allows_empty_origin_after_wsauth", func(t *testing.T) {
		h := NewSTTHandler("ws://stt:50052", zap.NewNop(), prodCfg)
		assert.True(t, h.upgrader.CheckOrigin(req("")),
			"empty Origin must be allowed in production: native clients never send one and auth already happened")
	})

	t.Run("development_allows_empty_origin", func(t *testing.T) {
		h := NewSTTHandler("ws://stt:50052", zap.NewNop(), devCfg)
		assert.True(t, h.upgrader.CheckOrigin(req("")),
			"empty Origin must be allowed in development")
	})

	t.Run("allowed_origin_accepted", func(t *testing.T) {
		h := NewSTTHandler("ws://stt:50052", zap.NewNop(), prodCfg)
		require.True(t, h.upgrader.CheckOrigin(req("https://app.example.com")))
	})

	t.Run("unlisted_origin_rejected", func(t *testing.T) {
		h := NewSTTHandler("ws://stt:50052", zap.NewNop(), prodCfg)
		assert.False(t, h.upgrader.CheckOrigin(req("https://evil.example.com")),
			"non-empty unlisted origins must still be rejected in production")
	})
}
