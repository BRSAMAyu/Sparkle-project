package middleware

import (
	"bytes"
	"log"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/config"
)

// captureStdLog runs fn while capturing the standard library log output.
func captureStdLog(t *testing.T, fn func()) string {
	t.Helper()
	var buf bytes.Buffer
	flags := log.Flags()
	out := log.Writer()
	log.SetOutput(&buf)
	log.SetFlags(0)
	defer func() {
		log.SetOutput(out)
		log.SetFlags(flags)
	}()
	fn()
	return buf.String()
}

// TestInternalIPWhitelist_WarnsWhenProductionWhitelistMissing pins GW-P3-2:
// in production an unset/empty INTERNAL_IP_WHITELIST silently reduces the
// internal API defense to the static key alone; construction of the
// middleware must emit a loud startup warning so operators notice.
func TestInternalIPWhitelist_WarnsWhenProductionWhitelistMissing(t *testing.T) {
	cfg := &config.Config{
		Environment:         "production",
		InternalIPWhitelist: []string{},
	}

	var logs string
	logs = captureStdLog(t, func() {
		_ = InternalIPWhitelistMiddleware(cfg)
	})
	require.Contains(t, logs, "INTERNAL_IP_WHITELIST",
		"production construction with an empty whitelist must log a startup warning")

	// Development stays quiet.
	devCfg := &config.Config{
		Environment:         "development",
		InternalIPWhitelist: []string{},
	}
	logs = captureStdLog(t, func() {
		_ = InternalIPWhitelistMiddleware(devCfg)
	})
	require.False(t, strings.Contains(logs, "INTERNAL_IP_WHITELIST"),
		"development construction must not warn")

	// A configured production whitelist also stays quiet.
	prodCfg := &config.Config{
		Environment:         "production",
		InternalIPWhitelist: []string{"10.0.0.0/8"},
	}
	logs = captureStdLog(t, func() {
		_ = InternalIPWhitelistMiddleware(prodCfg)
	})
	require.False(t, strings.Contains(logs, "INTERNAL_IP_WHITELIST"),
		"configured production whitelist must not warn")
}

// TestInternalIPWhitelist_EmptyWhitelistStillServes pins the intentional
// runtime behavior that accompanies the warning: with no whitelist the layer
// still passes through (static key remains the gate), so the warning must not
// be confused with a behavior change.
func TestInternalIPWhitelist_EmptyWhitelistStillServes(t *testing.T) {
	cfg := &config.Config{
		Environment:         "production",
		InternalIPWhitelist: []string{},
	}
	r := gin.New()
	r.Use(InternalIPWhitelistMiddleware(cfg))
	// route-tier: internal
	r.GET("/internal/test", func(c *gin.Context) { c.Status(http.StatusOK) })

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/internal/test", nil))
	require.Equal(t, http.StatusOK, w.Code)
}
