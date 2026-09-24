package handler

// R2 deep-audit end-to-end test (reviewer 5): exercises the full chat chain
// with only the engine replaced by an in-process gRPC mock —
//
//	real WS dial (JWT Bearer header)
//	  → real WsAuthMiddleware (HS256 verify + miniredis blacklist)
//	  → real ChatOrchestrator.HandleWebSocket (upgrade, wsSafeWriter, registry)
//	  → real agent.Client (gRPC streaming)
//	  → mock engine StreamChat (deltas + usage + finish)
//	  → streamed JSON back to the WS client
//	  → abrupt disconnect → reconnect → second round-trip
//
// Guards composition-level regressions that per-file tests miss:
// middleware-to-handler identity propagation, streamSem release across a
// full round-trip, registry cleanup on abrupt drop, and reconnect liveness.

import (
	"context"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/middleware"
	"github.com/sparkle/gateway/internal/service"
)

// e2eEchoAgent streams a deterministic two-delta response with usage and an
// upstream finish reason, then ends the server stream (EOF).
type e2eEchoAgent struct {
	agentv1.UnimplementedAgentServiceServer
	mu       sync.Mutex
	sessions []string
}

func (e *e2eEchoAgent) StreamChat(req *agentv1.ChatRequest, stream grpc.ServerStreamingServer[agentv1.ChatResponse]) error {
	e.mu.Lock()
	e.sessions = append(e.sessions, req.SessionId)
	e.mu.Unlock()

	send := func(resp *agentv1.ChatResponse) error {
		return stream.SendMsg(resp)
	}
	if err := send(&agentv1.ChatResponse{
		ResponseId: "resp-e2e-1",
		RequestId:  req.RequestId,
		SessionId:  req.SessionId,
		Content:    &agentv1.ChatResponse_Delta{Delta: "Hello "},
	}); err != nil {
		return err
	}
	if err := send(&agentv1.ChatResponse{
		ResponseId: "resp-e2e-2",
		RequestId:  req.RequestId,
		SessionId:  req.SessionId,
		Content:    &agentv1.ChatResponse_Delta{Delta: "world"},
	}); err != nil {
		return err
	}
	// clean EOF
	return send(&agentv1.ChatResponse{
		ResponseId:   "resp-e2e-final",
		RequestId:    req.RequestId,
		SessionId:    req.SessionId,
		Content:      &agentv1.ChatResponse_Usage{Usage: &agentv1.Usage{TotalTokens: 42}},
		FinishReason: agentv1.FinishReason_STOP,
	})
}

func e2eJWT(t *testing.T, secret, sub string) string {
	t.Helper()
	tok := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":  sub,
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(time.Hour).Unix(),
		"jti":  "jti-e2e-" + sub,
	})
	s, err := tok.SignedString([]byte(secret))
	require.NoError(t, err)
	return s
}

type e2eHarness struct {
	ts        *httptest.Server
	mock      *e2eEchoAgent
	orch      *ChatOrchestrator
	history   *service.ChatHistoryService
	redisSrv  *miniredis.Miniredis
	grpcSrv   *grpc.Server
	jwtSecret string
}

func newE2EHarness(t *testing.T) *e2eHarness {
	return newE2EHarnessCfg(t, nil)
}

func newE2EHarnessCfg(t *testing.T, tune func(*config.Config)) *e2eHarness {
	t.Helper()

	// 1. In-process mock engine.
	mock := &e2eEchoAgent{}
	lis, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	grpcSrv := grpc.NewServer()
	agentv1.RegisterAgentServiceServer(grpcSrv, mock)
	go func() { _ = grpcSrv.Serve(lis) }()
	t.Cleanup(grpcSrv.Stop)

	agentClient, err := agent.NewClient(&config.Config{
		AgentAddress:       lis.Addr().String(),
		InternalAPIKey:     "e2e-internal-key",
		GRPCTimeoutSeconds: 10,
	})
	require.NoError(t, err)
	t.Cleanup(func() { agentClient.Close() })

	// 2. Real Redis-shape backing services (miniredis).
	redisSrv := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: redisSrv.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })

	history := service.NewChatHistoryService(rdb)
	t.Cleanup(history.Stop)
	quota := service.NewQuotaService(rdb)

	jwtSecret := "e2e-jwt-secret"
	cfg := &config.Config{
		Environment:         "development", // native-style empty Origin allowed
		JWTSecret:           jwtSecret,
		StreamMaxConcurrent: 2,
	}
	if tune != nil {
		tune(cfg)
	}

	orch := NewChatOrchestrator(
		agentClient, nil, nil,
		history, quota,
		nil, // semantic cache
		nil, // cost calculator
		NewWebSocketFactory(cfg),
		cfg,
		nil, // user context
		nil, // task command
		"http://mock-backend",
		nil, // signal hub
	)

	// 3. Router with the REAL auth middleware in front of the handler —
	// the composition under test.
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/ws/chat", middleware.WsAuthMiddleware(cfg, rdb), orch.HandleWebSocket)
	ts := httptest.NewServer(r)
	t.Cleanup(ts.Close)

	return &e2eHarness{
		ts: ts, mock: mock, orch: orch, history: history,
		redisSrv: redisSrv, grpcSrv: grpcSrv, jwtSecret: jwtSecret,
	}
}

func (h *e2eHarness) dial(t *testing.T, token string) *websocket.Conn {
	t.Helper()
	wsURL := "ws" + strings.TrimPrefix(h.ts.URL, "http") + "/ws/chat"
	conn, resp, err := websocket.DefaultDialer.Dial(wsURL, http.Header{
		"Authorization": []string{"Bearer " + token},
	})
	require.NoError(t, err, "authenticated WS upgrade must succeed")
	if resp != nil {
		_ = resp.Body.Close()
	}
	return conn
}

// readUntil consumes server frames until pred matches; returns the matching frame.
func readUntil(t *testing.T, conn *websocket.Conn, pred func(map[string]interface{}) bool) map[string]interface{} {
	t.Helper()
	require.NoError(t, conn.SetReadDeadline(time.Now().Add(5*time.Second)))
	for i := 0; i < 50; i++ {
		var frame map[string]interface{}
		require.NoError(t, conn.ReadJSON(&frame), "reading server frame")
		if pred(frame) {
			return frame
		}
	}
	t.Fatal("expected frame never arrived")
	return nil
}

// runChatRound sends one legacy JSON chat message and returns the assembled
// delta text and the terminal meta frame.
func runChatRound(t *testing.T, conn *websocket.Conn, sessionID, message string) (string, map[string]interface{}) {
	t.Helper()
	require.NoError(t, conn.WriteJSON(map[string]interface{}{
		"message":    message,
		"session_id": sessionID,
	}))

	ack := readUntil(t, conn, func(f map[string]interface{}) bool {
		return f["type"] == "ack"
	})
	require.NotNil(t, ack, "accepted ack must arrive before stream frames")

	var sb strings.Builder
	var meta map[string]interface{}
	require.NoError(t, conn.SetReadDeadline(time.Now().Add(5*time.Second)))
	for meta == nil {
		var frame map[string]interface{}
		require.NoError(t, conn.ReadJSON(&frame))
		switch frame["type"] {
		case "delta":
			d, _ := frame["delta"].(string)
			sb.WriteString(d)
		case "meta":
			meta = frame
		}
	}
	return sb.String(), meta
}

func TestChatOrchestrator_WSFullChainE2E(t *testing.T) {
	h := newE2EHarness(t)
	token := e2eJWT(t, h.jwtSecret, "e2e-user")

	t.Run("unauthenticated upgrade is rejected before handler", func(t *testing.T) {
		wsURL := "ws" + strings.TrimPrefix(h.ts.URL, "http") + "/ws/chat"
		_, resp, err := websocket.DefaultDialer.Dial(wsURL, http.Header{
			"Authorization": []string{"Bearer not-a-valid-token"},
		})
		require.Error(t, err, "invalid JWT must fail the upgrade")
		if resp == nil {
			t.Fatal("expected handshake response on rejected upgrade")
		}
		require.Equal(t, http.StatusUnauthorized, resp.StatusCode)
		_ = resp.Body.Close()
		require.Zero(t, h.orch.Registry().Count(), "rejected upgrade must not register a connection")
	})

	t.Run("client close immediately after meta loses assistant turn", func(t *testing.T) {
		// R2-GW-1 regression (hard assertion): the server persists the
		// completed assistant turn AFTER sending the terminal meta frame. The
		// save used to ride streamCtx, which the read pump cancels the moment
		// the client disconnects — a client that closes right after meta
		// (normal for mobile: answer received, app backgrounded) raced the
		// save and lost the turn entirely. The save now runs on a detached
		// ctx, so the turn must ALWAYS reach the history store.
		conn := h.dial(t, token)
		runChatRound(t, conn, "sess-race", "question that gets answered")
		// Close IMMEDIATELY — no intermediate assertions.
		require.NoError(t, conn.Close())

		require.Eventually(t, func() bool {
			return h.orch.Registry().Count() == 0
		}, 5*time.Second, 10*time.Millisecond)

		var roles []string
		require.Eventually(t, func() bool {
			msgs, err := h.history.GetMessages(context.Background(), "e2e-user", "sess-race", 10, 0)
			if err != nil {
				return false
			}
			roles = roles[:0]
			hasAssistant := false
			for _, m := range msgs {
				roles = append(roles, m.Role)
				if m.Role == "assistant" {
					hasAssistant = true
				}
			}
			return hasAssistant
		}, 5*time.Second, 20*time.Millisecond, "completed assistant turn must survive the disconnect race (R2-GW-1); got roles=%v", roles)
	})

	t.Run("stream round-trip then abrupt drop then reconnect", func(t *testing.T) {
		// --- Round 1: full streaming round-trip. ---
		conn1 := h.dial(t, token)
		text1, meta1 := runChatRound(t, conn1, "sess-e2e", "first question")
		require.Equal(t, "Hello world", text1, "streamed deltas must reach the client in order")
		require.NotNil(t, meta1["meta"], "terminal meta frame must arrive")

		require.Equal(t, 1, h.orch.Registry().Count(), "live connection must be registered")

		// Persistence: the user turn must be visible in the history store.
		require.Eventually(t, func() bool {
			msgs, err := h.history.GetMessages(context.Background(), "e2e-user", "sess-e2e", 10, 0)
			return err == nil && len(msgs) >= 1
		}, 3*time.Second, 50*time.Millisecond, "user message must be persisted to chat history")

		// Quota: usage recorded against the daily counter key.
		require.Eventually(t, func() bool {
			found := false
			for _, k := range h.redisSrv.Keys() {
				if strings.HasPrefix(k, "llm_tokens:e2e-user:") {
					found = true
				}
			}
			return found
		}, 3*time.Second, 50*time.Millisecond, "token usage must be recorded")

		// --- Abrupt disconnect (no close frame). ---
		require.NoError(t, conn1.Close())
		require.Eventually(t, func() bool {
			return h.orch.Registry().Count() == 0
		}, 5*time.Second, 20*time.Millisecond, "registry entry must be cleaned up after abrupt drop")
		require.Eventually(t, func() bool {
			return len(h.orch.streamSem) == 0
		}, 5*time.Second, 20*time.Millisecond, "stream slot must be free between rounds")

		// --- Round 2: reconnect and stream again. ---
		conn2 := h.dial(t, token)
		text2, _ := runChatRound(t, conn2, "sess-e2e", "second question")
		require.Equal(t, "Hello world", text2, "reconnected client must get a full stream")

		h.mock.mu.Lock()
		e2eRounds := 0
		for _, s := range h.mock.sessions {
			if s == "sess-e2e" {
				e2eRounds++
			}
		}
		h.mock.mu.Unlock()
		require.Equal(t, 2, e2eRounds, "engine must have received exactly two StreamChat calls for sess-e2e")

		require.NoError(t, conn2.Close())
	})
}

// TestChatOrchestrator_WSE2E_IdleTimeout exercises the idle-timer leg of the
// connection lifecycle: a connected client that never sends a message must be
// closed by the server within the configured idle window (and release all
// lifecycle state), without any traffic from the client side.
func TestChatOrchestrator_WSE2E_IdleTimeout(t *testing.T) {
	h := newE2EHarnessCfg(t, func(c *config.Config) {
		c.WSIdleTimeoutSeconds = 1
	})
	token := e2eJWT(t, h.jwtSecret, "e2e-idle-user")

	conn := h.dial(t, token)
	// Dial only guarantees the 101 upgrade was written; the server handler
	// reaches registerConnection only after logging/metrics/timer setup, so
	// registration is asynchronous from the client's point of view. Poll
	// instead of asserting inline — a fixed assert raced CI (-race, slow
	// runners) and local runs alike (observed 1-in-5 failure).
	require.Eventually(t, func() bool {
		return h.orch.Registry().Count() == 1
	}, 5*time.Second, 10*time.Millisecond, "dial must register exactly one connection")

	// Never send anything; expect the server-side idle timer to close us.
	require.NoError(t, conn.SetReadDeadline(time.Now().Add(5*time.Second)))
	_, _, err := conn.ReadMessage()
	require.Error(t, err, "idle connection must be closed by the server")

	require.Eventually(t, func() bool {
		return h.orch.Registry().Count() == 0
	}, 5*time.Second, 20*time.Millisecond, "idle-closed connection must release registry state")
}
