// Core: bridge
// Phase: execute
// Stage: v3 fleet
//
// V3-FIX-169 red→green tests: the gateway semantic-cache query face was dead
// (two unconditional gates in handleChatMessage made shouldSkipCache always
// true). These tests replicate wt469 rev7B probes B and C end to end —
// real WS stack + in-process gRPC mock engine + miniredis-backed services —
// and pin the revived invariants:
//
//   probe B: a pre-seeded cache entry for the same scope+query MUST be served
//            on a first turn that carries a session_id (engine call count 0).
//   probe C: a session first turn writes the cache; a follow-up turn with an
//            EMPTY session_id (the one shape where the query gate must open
//            regardless of history) MUST hit it (engine call count stays 1,
//            marker text proves the engine was not consulted again).
//   guard  : a gateway-detected truncated turn (stream EOF without
//            finish_reason, V3-FIX-155 exit) must never be served from the
//            cache — the write-side exit stays effective now that the read
//            face is alive (guard bit for V3-FIX-168, which it does not fix).

package handler

import (
	"context"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/proto"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/middleware"
	"github.com/sparkle/gateway/internal/service"
)

// cacheGateAgent is an in-process gRPC engine mock with per-call scripts and
// an invocation counter. Scripts repeat their last entry so any unexpected
// extra engine call still produces a distinct observable answer (marker-text
// disambiguation, same technique as the wt469 probes).
type cacheGateAgent struct {
	agentv1.UnimplementedAgentServiceServer

	mu      sync.Mutex
	scripts [][]*agentv1.ChatResponse
	calls   atomic.Int64
}

func (a *cacheGateAgent) script(frames ...*agentv1.ChatResponse) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.scripts = append(a.scripts, frames)
}

func (a *cacheGateAgent) StreamChat(req *agentv1.ChatRequest, stream grpc.ServerStreamingServer[agentv1.ChatResponse]) error {
	n := int(a.calls.Add(1))
	a.mu.Lock()
	idx := n - 1
	if idx >= len(a.scripts) {
		idx = len(a.scripts) - 1
	}
	frames := a.scripts[idx]
	a.mu.Unlock()
	for _, resp := range frames {
		clone := proto.Clone(resp).(*agentv1.ChatResponse)
		clone.RequestId = req.RequestId
		clone.SessionId = req.SessionId
		if err := stream.SendMsg(clone); err != nil {
			return err
		}
	}
	return nil // clean EOF at the gRPC layer
}

type cacheGateHarness struct {
	ts       *httptest.Server
	agent    *cacheGateAgent
	semantic *service.SemanticCacheService
	rdb      *redis.Client
	redis    *miniredis.Miniredis
	jwtRule  func(t *testing.T, sub string) string
}

func newCacheGateHarness(t *testing.T) *cacheGateHarness {
	t.Helper()

	mock := &cacheGateAgent{}
	lis, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	grpcSrv := grpc.NewServer()
	agentv1.RegisterAgentServiceServer(grpcSrv, mock)
	go func() { _ = grpcSrv.Serve(lis) }()
	t.Cleanup(grpcSrv.Stop)

	agentClient, err := agent.NewClient(&config.Config{
		AgentAddress:       lis.Addr().String(),
		InternalAPIKey:     "cache-gate-internal-key",
		GRPCTimeoutSeconds: 10,
	})
	require.NoError(t, err)
	t.Cleanup(func() { agentClient.Close() })

	redisSrv := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: redisSrv.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })

	history := service.NewChatHistoryService(rdb)
	t.Cleanup(history.Stop)
	quota := service.NewQuotaService(rdb)
	semantic := service.NewSemanticCacheService(rdb)

	jwtSecret := "cache-gate-jwt-secret"
	cfg := &config.Config{
		Environment:         "development",
		JWTSecret:           jwtSecret,
		StreamMaxConcurrent: 4,
	}

	orch := NewChatOrchestrator(
		agentClient, nil, nil,
		history, quota,
		semantic,
		nil, // cost calculator
		NewWebSocketFactory(cfg),
		cfg,
		nil, // user context
		nil, // task command
		"http://mock-backend",
		nil, // signal hub
	)

	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/ws/chat", middleware.WsAuthMiddleware(cfg, rdb), orch.HandleWebSocket)
	ts := httptest.NewServer(r)
	t.Cleanup(ts.Close)

	return &cacheGateHarness{
		ts:       ts,
		agent:    mock,
		semantic: semantic,
		rdb:      rdb,
		redis:    redisSrv,
		jwtRule: func(t *testing.T, sub string) string {
			return e2eJWT(t, jwtSecret, sub)
		},
	}
}

func (h *cacheGateHarness) dial(t *testing.T, sub string) *websocket.Conn {
	t.Helper()
	wsURL := "ws" + strings.TrimPrefix(h.ts.URL, "http") + "/ws/chat"
	conn, resp, err := websocket.DefaultDialer.Dial(wsURL, http.Header{
		"Authorization": []string{"Bearer " + h.jwtRule(t, sub)},
	})
	require.NoError(t, err, "authenticated WS upgrade must succeed")
	if resp != nil {
		_ = resp.Body.Close()
	}
	return conn
}

// cacheGateTurn sends one legacy JSON chat message and collects the turn's
// assembled delta text, every full_text frame, and the terminal meta frame.
func cacheGateTurn(t *testing.T, conn *websocket.Conn, sessionID, message string) (deltas string, fullTexts []string, meta map[string]interface{}) {
	t.Helper()
	require.NoError(t, conn.WriteJSON(map[string]interface{}{
		"message":    message,
		"session_id": sessionID,
	}))

	require.NoError(t, conn.SetReadDeadline(time.Now().Add(5*time.Second)))
	var sb strings.Builder
	for meta == nil {
		var frame map[string]interface{}
		require.NoError(t, conn.ReadJSON(&frame), "reading turn frames")
		switch frame["type"] {
		case "delta":
			d, _ := frame["delta"].(string)
			sb.WriteString(d)
		case "full_text":
			ft, _ := frame["full_text"].(string)
			fullTexts = append(fullTexts, ft)
		case "meta":
			m, _ := frame["meta"].(map[string]interface{})
			meta = m
		}
	}
	// Drain the trailing synthetic done frame (always emitted for non-Aurora
	// streams) so the next turn starts from a clean frame boundary.
	_ = conn.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
	var done map[string]interface{}
	_ = conn.ReadJSON(&done)
	return sb.String(), fullTexts, meta
}

// cacheGateScope mirrors the handler-side semanticCacheScope computation for
// the default no-conversation-settings shape (chatflow.go: input without
// file_ids / active_tools / extra_context / document_filter, mode "standard").
// If the gateway injection or scope contract changes shape, this helper and
// the probe-B seed must be revisited together — the cache key contract is
// pinned, not incidental.
func cacheGateScope(userID, chatMode, query string) string {
	useDocumentContext := defaultUseDocumentContextForMode(normalizeChatMode(chatMode))
	documentFilter := []string(nil)
	extra := map[string]interface{}{
		"use_document_context": useDocumentContext,
		"document_filter":      documentFilter,
		"conversation_settings": map[string]interface{}{
			"use_document_context": useDocumentContext,
			"document_filter":      documentFilter,
		},
	}
	return semanticCacheScope(userID, normalizeChatMode(chatMode), "", nil, false, nil, extra)
}

// waitForCacheKeys polls miniredis until at least one semantic-cache key
// exists (want=true) or the window elapses (used both to await the async
// SetExact and to prove its absence on the truncated-turn guard).
func waitForCacheKeys(t *testing.T, h *cacheGateHarness, want bool, timeout time.Duration) []string {
	t.Helper()
	deadline := time.Now().Add(timeout)
	for {
		keys, err := h.rdb.Keys(context.Background(), "cache:text:*").Result()
		require.NoError(t, err)
		if len(keys) > 0 == want {
			return keys
		}
		if time.Now().After(deadline) {
			return keys
		}
		time.Sleep(25 * time.Millisecond)
	}
}

func stopAnswer(text string) []*agentv1.ChatResponse {
	return []*agentv1.ChatResponse{
		{ResponseId: "resp-delta", Content: &agentv1.ChatResponse_Delta{Delta: text}},
		{ResponseId: "resp-final", Content: &agentv1.ChatResponse_Usage{Usage: &agentv1.Usage{TotalTokens: 7}}, FinishReason: agentv1.FinishReason_STOP},
	}
}

// --- Probe B replica: pre-seeded entry + first turn WITH session → hit ---

func TestChatflowSemanticCache_PreSeedHitOnFirstTurnWithSession(t *testing.T) {
	h := newCacheGateHarness(t)
	const (
		userID = "cache-gate-user-b"
		query  = "what does the semantic cache do"
		seeded = "CACHED SEED ANSWER V3-FIX-169"
	)

	// Pre-seed the exact scope+query the handler will search (wt469 probe B).
	require.NoError(t, h.semantic.SetExact(context.Background(), cacheGateScope(userID, "standard", query), query, seeded))

	// Engine marker: any engine call would surface this text instead of the
	// cached seed, so the assertions below cannot pass by coincidence.
	h.agent.script(stopAnswer("ENGINE CALLED — CACHE MUST HAVE BEEN SERVED INSTEAD")...)

	conn := h.dial(t, userID)
	defer conn.Close()

	_, fullTexts, meta := cacheGateTurn(t, conn, "sess-probe-b", query)

	require.Len(t, fullTexts, 1, "cached turn must answer via a single full_text frame (engine calls so far: %d)", h.agent.calls.Load())
	require.Equal(t, seeded, fullTexts[0], "client must receive the pre-seeded cached answer")
	require.Equal(t, true, meta["is_cache_hit"], "meta must report is_cache_hit=true")
	require.Equal(t, int64(0), h.agent.calls.Load(), "cache hit must skip the engine entirely (calls=0)")
}

// --- Probe C replica: session turn writes → empty-session turn hits ---

func TestChatflowSemanticCache_EmptySessionTurnHitsCacheWrittenBySessionTurn(t *testing.T) {
	h := newCacheGateHarness(t)
	const (
		userID  = "cache-gate-user-c"
		query   = "how do probes b and c differ"
		answer1 = "FIRST CALL UNIQUE ANSWER"
		marker  = "SECOND CALL DISTINCT ANSWER"
	)

	h.agent.script(stopAnswer(answer1)...)
	conn := h.dial(t, userID)
	defer conn.Close()

	// Turn 1: first turn of the session — cacheable, answer comes from the
	// engine and is written to the semantic cache (async SetExact).
	deltas1, fullTexts1, meta1 := cacheGateTurn(t, conn, "sess-probe-c", query)
	require.Empty(t, fullTexts1, "engine turn answers via deltas")
	require.Equal(t, answer1, deltas1)
	require.Equal(t, false, meta1["is_cache_hit"], "turn 1 must be a real engine turn")
	require.Equal(t, int64(1), h.agent.calls.Load())

	// Await the async cache write from turn 1.
	keys := waitForCacheKeys(t, h, true, 3*time.Second)
	require.NotEmpty(t, keys, "turn 1 must have written a semantic cache entry")

	// Turn 2: EMPTY session_id — the one shape where the query gate must be
	// open regardless of history. Same user, same scope inputs, same query.
	h.agent.script(stopAnswer(marker)...)
	deltas2, fullTexts2, meta2 := cacheGateTurn(t, conn, "", query)

	require.Empty(t, deltas2, "hit path must not stream deltas (engine calls so far: %d)", h.agent.calls.Load())
	require.Len(t, fullTexts2, 1, "hit path must answer via one full_text frame (engine calls so far: %d)", h.agent.calls.Load())
	require.Equal(t, answer1, fullTexts2[0], "turn 2 must be served from the cache written by turn 1")
	require.NotEqual(t, marker, fullTexts2[0], "marker text proves the engine was NOT consulted again")
	require.Equal(t, true, meta2["is_cache_hit"])
	require.Equal(t, int64(1), h.agent.calls.Load(), "hit turn must skip the engine (calls stays 1)")
}

// --- Guard: gateway-detected truncated turn must never be re-served ---

func TestChatflowSemanticCache_TruncatedTurnNeverServedFromCache(t *testing.T) {
	h := newCacheGateHarness(t)
	const (
		userID   = "cache-gate-user-t"
		query    = "guard me against truncated redelivery"
		truncTxt = "partial truncated answer"
		fresh    = "ENGINE SECOND ANSWER — TURN TWO WAS NOT A CACHE HIT"
	)

	// Turn 1: stream ends with clean EOF but NO finish_reason frame — the
	// V3-FIX-155 gateway-detected truncation shape. Its text must be kept
	// out of the semantic cache.
	h.agent.script([]*agentv1.ChatResponse{
		{ResponseId: "resp-trunc", Content: &agentv1.ChatResponse_Delta{Delta: truncTxt}},
	}...)
	conn := h.dial(t, userID)
	defer conn.Close()

	deltas1, _, meta1 := cacheGateTurn(t, conn, "sess-trunc-a", query)
	require.Equal(t, truncTxt, deltas1)
	require.Equal(t, false, meta1["is_cache_hit"])
	require.Equal(t, int64(1), h.agent.calls.Load())

	// Generous window for a would-be async SetExact to land; it must not.
	keys := waitForCacheKeys(t, h, false, 1500*time.Millisecond)
	require.Empty(t, keys, "truncated turn text must not enter the semantic cache")
	cached, err := h.semantic.SearchExact(context.Background(), cacheGateScope(userID, "standard", query), query)
	require.NoError(t, err)
	require.Empty(t, cached, "SearchExact must not resolve the truncated text")

	// Turn 2: a different session's first turn, same query. With the read
	// face alive, a cache violation would surface as the truncated text.
	h.agent.script(stopAnswer(fresh)...)
	deltas2, fullTexts2, meta2 := cacheGateTurn(t, conn, "sess-trunc-b", query)
	require.Empty(t, fullTexts2)
	require.Equal(t, fresh, deltas2, "turn 2 must get the fresh engine answer, never the truncated text")
	require.Equal(t, false, meta2["is_cache_hit"], "truncated turn must not be a cache hit")
	require.Equal(t, int64(2), h.agent.calls.Load())
}
