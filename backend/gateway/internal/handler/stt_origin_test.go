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

// GW-P2-2 regression: /ws/stt used to carry a local checkOrigin that allowed
// empty Origin headers unconditionally — the only WS entry accepting them in
// production. It must follow the WebSocketFactory policy: empty Origin
// rejected in production, allowed in development; listed origins allowed;
// unlisted origins rejected.
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

	t.Run("production_rejects_empty_origin", func(t *testing.T) {
		h := NewSTTHandler("ws://stt:50052", zap.NewNop(), prodCfg)
		assert.False(t, h.upgrader.CheckOrigin(req("")),
			"empty Origin must be rejected in production")
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
		assert.False(t, h.upgrader.CheckOrigin(req("https://evil.example.com")))
	})
}
