package handler

// WSQ-3 (WS-TICKET-DESIGN §WSQ-3) regression: /ws/stt must echo the client's
// chosen Sec-WebSocket-Protocol subprotocol in the 101 handshake response —
// some client libraries fail the handshake unless the server selects one of
// the offered values. The echo must follow the same single-segment convention
// wt286 pinned for WsAuth ticket extraction ("ticket=<uuid>" / "ticket:<uuid>"
// parse; "ticket,<uuid>" never does), so the echoed value is exactly the
// segment the ticket was extracted from.

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
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/middleware"
)

const sttEchoTestTicket = "a1b2c3d4-1111-2222-3333-444455556666"
const sttEchoTestPayload = `{"user_id":"stt-ticket-user","token":"ticket-bearer-token"}`

// newSTTHandlerServer spins an httptest server exposing /ws/stt, optionally
// behind the real WsAuthMiddleware (auth != nil).
func newSTTHandlerServer(t *testing.T, cfg *config.Config, auth gin.HandlerFunc) *httptest.Server {
	t.Helper()
	gin.SetMode(gin.TestMode)
	r := gin.New()
	h := NewSTTHandler("ws://127.0.0.1:1/ws", zap.NewNop(), cfg) // port 1: dial fails fast
	handlers := make([]gin.HandlerFunc, 0, 2)
	if auth != nil { // a nil entry in the chain panics inside gin.Context.Next
		handlers = append(handlers, auth)
	}
	handlers = append(handlers, h.HandleWebSocket)
	r.GET("/ws/stt", handlers...)
	ts := httptest.NewServer(r)
	t.Cleanup(ts.Close)
	return ts
}

// dialSTT performs a real WS dial and returns the connection plus the echoed
// Sec-WebSocket-Protocol header; the handshake response body is consumed and
// closed here so it never escapes to callers.
func dialSTT(t *testing.T, ts *httptest.Server, header http.Header) (*websocket.Conn, string) {
	t.Helper()
	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/stt"
	dialer := websocket.Dialer{HandshakeTimeout: 5 * time.Second}
	conn, resp, err := dialer.Dial(wsURL, header)
	require.NoError(t, err, "STT WS upgrade must succeed")
	echo := ""
	if resp != nil {
		echo = resp.Header.Get("Sec-WebSocket-Protocol")
		_ = resp.Body.Close()
	}
	t.Cleanup(func() { _ = conn.Close() })
	return conn, echo
}

// (a) Handshake WITH a subprotocol offer must echo the offered value back.
func TestSTTHandler_EchoesOfferedSubprotocol(t *testing.T) {
	cfg := &config.Config{Environment: "development"}
	ts := newSTTHandlerServer(t, cfg, nil)

	conn, echo := dialSTT(t, ts, http.Header{
		"Sec-WebSocket-Protocol": []string{"ticket=" + sttEchoTestTicket},
	})

	const want = "ticket=" + sttEchoTestTicket
	assert.Equal(t, want, echo,
		"101 response must select the offered subprotocol")
	assert.Equal(t, want, conn.Subprotocol(),
		"negotiated subprotocol must be the offered value")

	// Handler is reachable without auth middleware: the first frame is the
	// missing-user-context error, proving the upgraded conn is live.
	require.NoError(t, conn.SetReadDeadline(time.Now().Add(5*time.Second)))
	var frame map[string]string
	require.NoError(t, conn.ReadJSON(&frame))
	assert.Equal(t, "error", frame["type"])
	assert.Contains(t, frame["content"], "Unauthorized")
}

// (b) Handshake WITHOUT any subprotocol offer must stay untouched: no
// Sec-WebSocket-Protocol in the response, upgrade still succeeds.
func TestSTTHandler_NoOffer_NoEcho(t *testing.T) {
	cfg := &config.Config{Environment: "development"}
	ts := newSTTHandlerServer(t, cfg, nil)

	conn, echo := dialSTT(t, ts, nil)

	assert.Empty(t, echo,
		"no offer must produce no echo header")
	assert.Empty(t, conn.Subprotocol())

	require.NoError(t, conn.SetReadDeadline(time.Now().Add(5*time.Second)))
	var frame map[string]string
	require.NoError(t, conn.ReadJSON(&frame), "connection must be usable with no subprotocol")
	assert.Equal(t, "error", frame["type"])
}

// (c) End-to-end with the WSQ-2 ticket channel: the REAL WsAuthMiddleware
// extracts the ticket from the same single segment the handler echoes, the
// ticket is consumed (GETDEL), user_id propagates, and the echoed value is
// byte-identical to the extracted segment. Query channels are pinned shut to
// prove the subprotocol channel alone carries the credentials.
func TestSTTHandler_TicketSubprotocol_ExtractAndEchoAgree(t *testing.T) {
	cfg := &config.Config{
		Environment:        "development",
		AllowWsQueryToken:  false,
		AllowWsQueryTicket: false,
	}
	mr := miniredis.RunT(t)
	require.NoError(t, mr.Set("ws:ticket:"+sttEchoTestTicket, sttEchoTestPayload))
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })

	ts := newSTTHandlerServer(t, cfg, middleware.WsAuthMiddleware(cfg, rdb))

	// Single-segment offer (wt286 convention).
	conn, echo := dialSTT(t, ts, http.Header{
		"Sec-WebSocket-Protocol": []string{"ticket=" + sttEchoTestTicket},
	})
	const want = "ticket=" + sttEchoTestTicket
	assert.Equal(t, want, echo)
	assert.Equal(t, want, conn.Subprotocol())

	// Extraction proof: the middleware consumed exactly this ticket.
	assert.False(t, mr.Exists("ws:ticket:"+sttEchoTestTicket),
		"auth must extract and GETDEL the ticket from the echoed segment")

	// Identity proof: first server frame is the upstream dial failure, not
	// the unauthorized error — user_id came from the ticket payload.
	require.NoError(t, conn.SetReadDeadline(time.Now().Add(5*time.Second)))
	var frame map[string]string
	require.NoError(t, conn.ReadJSON(&frame))
	require.Equal(t, "error", frame["type"])
	assert.Equal(t, "STT service unavailable", frame["content"],
		"ticket-authed identity must reach the handler (not the unauthorized branch)")

	// Multi-offer consistency: prefix candidates win over first-part fallback,
	// and the middleware extracts from that same segment.
	const ticket2 = "b2c3d4e5-7777-8888-9999-000000000001"
	require.NoError(t, mr.Set("ws:ticket:"+ticket2, sttEchoTestPayload))
	conn2, echo2 := dialSTT(t, ts, http.Header{
		"Sec-WebSocket-Protocol": []string{"chat, ticket=" + ticket2},
	})
	const want2 = "ticket=" + ticket2
	assert.Equal(t, want2, echo2,
		"echo must select the ticket-prefixed offer, not the first part")
	assert.Equal(t, want2, conn2.Subprotocol())
	assert.False(t, mr.Exists("ws:ticket:"+ticket2),
		"extraction must use the same prefix segment the echo selected")
}
