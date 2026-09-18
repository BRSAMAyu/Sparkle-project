package handler

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/metrics"
	"github.com/sparkle/gateway/internal/service"
)

// newQuotaFallbackTestOrchestrator spins up the minimal production-shaped
// chat orchestrator used by the GW-P2-4 fallback tests: a prod WebSocket
// factory pinned to the exact test origin, a real QuotaService on miniredis,
// and a nil agent client (admitted requests terminate with the
// service_unavailable message_nack, which is enough to prove admission).
func newQuotaFallbackTestOrchestrator(t *testing.T) (wsURL, origin string, mr *miniredis.Miniredis) {
	t.Helper()

	mr = miniredis.RunT(t)
	// Fail fast against a closed miniredis: the default pool retries would
	// add ~1s of dial latency to every degraded request in these tests.
	rdb := redis.NewClient(&redis.Options{
		Addr:         mr.Addr(),
		MaxRetries:   -1,
		DialTimeout:  100 * time.Millisecond,
		ReadTimeout:  500 * time.Millisecond,
		MinIdleConns: 0,
	})
	t.Cleanup(func() { _ = rdb.Close() })

	quotaSvc := service.NewQuotaService(rdb)
	historySvc := service.NewChatHistoryService(rdb)
	t.Cleanup(historySvc.Stop)

	gin.SetMode(gin.TestMode)
	r := gin.New()
	ts := httptest.NewServer(r)
	t.Cleanup(ts.Close)
	origin = "http://" + ts.Listener.Addr().String()

	wsFactory := NewWebSocketFactory(&config.Config{
		Environment:    "prod",
		AllowedOrigins: []string{origin},
	})
	cfg := &config.Config{
		Environment:    "prod",
		AllowedOrigins: []string{origin},
	}

	orchestrator := NewChatOrchestrator(
		nil,        // agentClient: admitted requests fail fast with service_unavailable
		nil,        // galaxyClient
		nil,        // userIdentity
		historySvc, // chatHistory
		quotaSvc,
		nil, // semantic cache
		nil, // cost
		wsFactory,
		cfg,
		nil, // userContext
		nil, // taskCommand
		"http://mock-backend",
		nil, // signalHub
	)
	r.GET("/ws/chat", func(c *gin.Context) {
		c.Set("user_id", "user_quota_fallback")
		c.Set("auth_token", "mock_token")
		orchestrator.HandleWebSocket(c)
	})

	wsURL = "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"
	return wsURL, origin, mr
}

func dialQuotaFallbackWS(t *testing.T, wsURL, origin string) *websocket.Conn {
	t.Helper()
	conn, resp, err := websocket.DefaultDialer.Dial(wsURL, http.Header{
		"Origin": []string{origin},
	})
	require.NoError(t, err, "upgrade with the whitelisted origin must succeed")
	if resp != nil {
		defer resp.Body.Close()
	}
	t.Cleanup(func() { _ = conn.Close() })
	return conn
}

// sendChatMessageAndWaitForNack sends one legacy chat message and drains frames
// until a terminal error frame arrives (bounded so a regression cannot hang
// the suite). It returns the error_code carried by that frame.
func sendChatMessageAndWaitForNack(t *testing.T, conn *websocket.Conn) string {
	t.Helper()
	require.NoError(t, conn.WriteJSON(map[string]interface{}{
		"message":    "hello",
		"session_id": "sess_quota_fallback",
	}))

	var frame map[string]interface{}
	var err error
	for i := 0; i < 6; i++ {
		if err = conn.ReadJSON(&frame); err != nil {
			t.Fatalf("read frame %d: %v", i, err)
		}
		if frame["type"] == "message_nack" || frame["type"] == "error" {
			code, _ := frame["error_code"].(string)
			return code
		}
	}
	t.Fatalf("no terminal error frame within 6 frames; last=%v", frame)
	return ""
}

// TestChatOrchestrator_QuotaLocalFallbackRejects51stRequest is the red-green
// proof of the GW-P2-4 product decision (2026-09-18): when Redis is down and
// the daily usage snapshot cannot be loaded, the gateway must not silently
// fail open forever. It degrades to a local instance-level approximate daily
// hard cap (default 50 per instance per UTC day) and rejects the first request
// over that cap with an explicit quota error.
func TestChatOrchestrator_QuotaLocalFallbackRejects51stRequest(t *testing.T) {
	wsURL, origin, mr := newQuotaFallbackTestOrchestrator(t)

	// Inject the Redis fault before any request: every GetDailyUsage /
	// RecordUsageSegment call now fails (connection refused), which is the
	// degraded regime GW-P2-4 covers.
	mr.Close()

	const fallbackLimit = 50 // DefaultQuotaLocalFallbackDailyLimit
	for i := 1; i <= fallbackLimit; i++ {
		conn := dialQuotaFallbackWS(t, wsURL, origin)
		code := sendChatMessageAndWaitForNack(t, conn)
		assert.NotEqual(t, "quota_exceeded", code,
			"request %d must still be admitted while under the fallback cap", i)
	}

	// The request right after the cap must be rejected with an explicit
	// quota error instead of being admitted unbounded (old fail-open).
	conn := dialQuotaFallbackWS(t, wsURL, origin)
	code := sendChatMessageAndWaitForNack(t, conn)
	require.Equal(t, "quota_exceeded", code,
		"the first request over the local fallback cap must be rejected with quota_exceeded")
}

// TestChatOrchestrator_QuotaLocalFallbackGauge pins the gauge contract of the
// bounded degradation: active while Redis daily-usage loads fail, disarmed as
// soon as one load succeeds again (Redis recovered).
func TestChatOrchestrator_QuotaLocalFallbackGauge(t *testing.T) {
	wsURL, origin, mr := newQuotaFallbackTestOrchestrator(t)

	mr.Close()
	conn := dialQuotaFallbackWS(t, wsURL, origin)
	code := sendChatMessageAndWaitForNack(t, conn)
	assert.Equal(t, "service_unavailable", code)
	require.Equal(t, 1.0, metrics.QuotaLocalFallbackActiveGaugeValue(),
		"fallback gauge must be active while Redis loads fail")

	// Recover Redis: the next request's usage load succeeds, disarming the
	// fallback gauge.
	require.NoError(t, mr.Restart())
	conn2 := dialQuotaFallbackWS(t, wsURL, origin)
	code = sendChatMessageAndWaitForNack(t, conn2)
	assert.Equal(t, "service_unavailable", code)
	require.Equal(t, 0.0, metrics.QuotaLocalFallbackActiveGaugeValue(),
		"fallback gauge must disarm once a daily usage load succeeds")
}
