package handler

// V13 regression: citations streamed by the engine (ChatResponse_Citations)
// power the live "source summary" UI, but the gateway never persisted them
// with the assistant turn — so chat history replay rendered the source
// summary badge with NO source cards (B-04: chat_citation_expanded_no_cards).
//
// This file guards the full chain:
//
//	real WS dial → real ChatOrchestrator chatflow
//	  → mock engine StreamChat (delta + citations + finish)
//	  → live citations frame forwarded to the WS client (red line: unchanged)
//	  → completed turn persisted WITH citations
//	  → GetConversationHistory JSON shape the mobile model parses
//	    (meta.citations + widgets[source_summary].data.citations)

import (
	"context"
	"encoding/json"
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

// citeEchoAgent streams one delta, one citations block, then usage+finish.
type citeEchoAgent struct {
	agentv1.UnimplementedAgentServiceServer
	mu       sync.Mutex
	sessions []string
}

func (c *citeEchoAgent) StreamChat(req *agentv1.ChatRequest, stream grpc.ServerStreamingServer[agentv1.ChatResponse]) error {
	c.mu.Lock()
	c.sessions = append(c.sessions, req.SessionId)
	c.mu.Unlock()

	if err := stream.SendMsg(&agentv1.ChatResponse{
		ResponseId: "resp-cite-1",
		RequestId:  req.RequestId,
		SessionId:  req.SessionId,
		Content:    &agentv1.ChatResponse_Delta{Delta: "根据文档，答案是 42。"},
	}); err != nil {
		return err
	}
	if err := stream.SendMsg(&agentv1.ChatResponse{
		ResponseId: "resp-cite-2",
		RequestId:  req.RequestId,
		SessionId:  req.SessionId,
		Content: &agentv1.ChatResponse_Citations{Citations: &agentv1.CitationBlock{
			Citations: []*agentv1.Citation{
				{
					Id:           "chunk-1",
					Title:        "学习科学导论.pdf - 第2章 遗忘曲线",
					Content:      "艾宾浩斯遗忘曲线表明，记忆在最初 24 小时内衰退最快……",
					SourceType:   "document",
					Score:        0.91,
					FileId:       "file-abc",
					PageNumber:   12,
					ChunkIndex:   3,
					SectionTitle: "第2章 遗忘曲线",
				},
			},
		}},
	}); err != nil {
		return err
	}
	return stream.SendMsg(&agentv1.ChatResponse{
		ResponseId:   "resp-cite-final",
		RequestId:    req.RequestId,
		SessionId:    req.SessionId,
		Content:      &agentv1.ChatResponse_Usage{Usage: &agentv1.Usage{TotalTokens: 7}},
		FinishReason: agentv1.FinishReason_STOP,
	})
}

type citeHarness struct {
	ts        *httptest.Server
	history   *service.ChatHistoryService
	jwtSecret string
}

func newCiteHarness(t *testing.T) *citeHarness {
	t.Helper()

	mock := &citeEchoAgent{}
	lis, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	grpcSrv := grpc.NewServer()
	agentv1.RegisterAgentServiceServer(grpcSrv, mock)
	go func() { _ = grpcSrv.Serve(lis) }()
	t.Cleanup(grpcSrv.Stop)

	agentClient, err := agent.NewClient(&config.Config{
		AgentAddress:       lis.Addr().String(),
		InternalAPIKey:     "cite-internal-key",
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

	jwtSecret := "cite-jwt-secret"
	cfg := &config.Config{
		Environment:         "development",
		JWTSecret:           jwtSecret,
		StreamMaxConcurrent: 2,
	}

	orch := NewChatOrchestrator(
		agentClient, nil, nil,
		history, quota,
		nil, nil,
		NewWebSocketFactory(cfg),
		cfg,
		nil, nil,
		"http://mock-backend",
		nil,
	)

	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/ws/chat", middleware.WsAuthMiddleware(cfg, rdb), orch.HandleWebSocket)
	// route-tier: authed
	r.GET("/history/:conversation_id", func(c *gin.Context) {
		c.Set("user_id", citeUserID)
		NewChatHistoryHandler(history).GetConversationHistory(c)
	})
	ts := httptest.NewServer(r)
	t.Cleanup(ts.Close)

	return &citeHarness{ts: ts, history: history, jwtSecret: jwtSecret}
}

const citeUserID = "cite-user"

func (h *citeHarness) dial(t *testing.T) *websocket.Conn {
	t.Helper()
	tok := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":  citeUserID,
		"type": "access",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(time.Hour).Unix(),
		"jti":  "jti-cite-1",
	})
	signed, err := tok.SignedString([]byte(h.jwtSecret))
	require.NoError(t, err)

	wsURL := "ws" + strings.TrimPrefix(h.ts.URL, "http") + "/ws/chat"
	conn, resp, err := websocket.DefaultDialer.Dial(wsURL, http.Header{
		"Authorization": []string{"Bearer " + signed},
	})
	require.NoError(t, err)
	if resp != nil {
		_ = resp.Body.Close()
	}
	return conn
}

// TestChatOrchestrator_CitationsPersistedForHistoryReplay is the V13 red
// test: the engine streams citations during a normal chat turn; after the
// turn completes, the persisted assistant message must carry the citation
// payloads so history replay can render the source cards.
func TestChatOrchestrator_CitationsPersistedForHistoryReplay(t *testing.T) {
	h := newCiteHarness(t)
	conn := h.dial(t)
	defer func() { _ = conn.Close() }()

	require.NoError(t, conn.WriteJSON(map[string]interface{}{
		"message":    "为什么会遗忘？",
		"session_id": "sess-cite",
	}))

	// Red line: the live citations frame must still reach the client.
	sawLiveCitations := false
	require.NoError(t, conn.SetReadDeadline(time.Now().Add(5*time.Second)))
	for !sawLiveCitations {
		var frame map[string]interface{}
		require.NoError(t, conn.ReadJSON(&frame))
		if frame["type"] == "citations" {
			list, ok := frame["citations"].([]interface{})
			require.Truef(t, ok, "live citations frame must carry the citations list, got %v", frame)
			require.NotEmpty(t, list)
			sawLiveCitations = true
		}
		if frame["type"] == "meta" {
			break
		}
	}
	require.True(t, sawLiveCitations, "live citations frame must be forwarded before terminal meta")

	// The completed assistant turn must be persisted with citations.
	var assistant map[string]interface{}
	require.Eventually(t, func() bool {
		msgs, err := h.history.GetMessages(context.Background(), citeUserID, "sess-cite", 10, 0)
		if err != nil {
			return false
		}
		for _, m := range msgs {
			if m.Role != "assistant" {
				continue
			}
			if len(m.Widgets) > 0 {
				raw, err := json.Marshal(m)
				require.NoError(t, err)
				require.NoError(t, json.Unmarshal(raw, &assistant))
				return true
			}
		}
		return false
	}, 5*time.Second, 20*time.Millisecond, "assistant turn must be persisted with widgets")

	require.NotNil(t, assistant, "assistant message missing from history")

	// Contract A: meta.citations — the key the mobile model reads as
	// rawMetadata['citations'] to build the citation strip.
	meta, ok := assistant["meta"].(map[string]interface{})
	require.Truef(t, ok, "assistant meta must be an object, got %v", assistant["meta"])
	metaCitations, ok := meta["citations"].([]interface{})
	require.Truef(t, ok, "assistant meta.citations must be persisted for replay, got %v", meta["citations"])
	require.NotEmpty(t, metaCitations)
	first, ok := metaCitations[0].(map[string]interface{})
	require.Truef(t, ok, "citation entry must be an object, got %v", metaCitations[0])
	require.Equal(t, "chunk-1", first["id"])
	require.Equal(t, "file-abc", first["file_id"])

	// Contract B: widgets[source_summary].data.citations — the key the
	// mobile metadata tray expands into the source cards.
	widgets, ok := assistant["widgets"].([]interface{})
	require.Truef(t, ok, "assistant widgets must be persisted for replay, got %v", assistant["widgets"])
	require.NotEmpty(t, widgets)
	var sourceSummary map[string]interface{}
	for _, w := range widgets {
		if wm, ok := w.(map[string]interface{}); ok && wm["type"] == "source_summary" {
			sourceSummary = wm
			break
		}
	}
	require.NotNil(t, sourceSummary, "persisted widgets must contain a source_summary entry")
	data, ok := sourceSummary["data"].(map[string]interface{})
	require.Truef(t, ok, "source_summary widget must carry data, got %v", sourceSummary)
	require.Equal(t, true, data["citations_available"])
	dataCitations, ok := data["citations"].([]interface{})
	require.Truef(t, ok, "source_summary data.citations must be a list, got %v", data["citations"])
	require.NotEmpty(t, dataCitations)
	firstWidgetCitation, ok := dataCitations[0].(map[string]interface{})
	require.Truef(t, ok, "widget citation entry must be an object, got %v", dataCitations[0])
	require.Equal(t, "学习科学导论.pdf - 第2章 遗忘曲线", firstWidgetCitation["title"])
	require.NotEmpty(t, firstWidgetCitation["content"], "citation excerpt (content) must survive persistence")
}

// TestGetConversationHistory_ServesCitationsToMobile locks the HTTP shape the
// mobile parser consumes on replay: meta.citations and
// widgets[source_summary].data.citations must survive the handler DTO.
func TestGetConversationHistory_ServesCitationsToMobile(t *testing.T) {
	gin.SetMode(gin.TestMode)
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := service.NewChatHistoryService(rdb)
	handler := NewChatHistoryHandler(svc)

	citation := map[string]interface{}{
		"id":            "chunk-9",
		"title":         "认知心理学.pdf - 第3章",
		"content":       "提取练习能显著增强长期记忆……",
		"source_type":   "document",
		"score":         0.87,
		"file_id":       "file-xyz",
		"page_number":   7,
		"chunk_index":   1,
		"section_title": "第3章 提取练习",
	}
	payload := map[string]interface{}{
		"id":         "msg-cite",
		"session_id": "session-cite",
		"user_id":    citeUserID,
		"role":       "assistant",
		"content":    "答案是……",
		"timestamp":  "1710000009",
		"meta": map[string]interface{}{
			"latency_ms": 42,
			"citations":  []interface{}{citation},
		},
		"widgets": []interface{}{
			map[string]interface{}{
				"type": "source_summary",
				"data": map[string]interface{}{
					"citations_available": true,
					"reference_scope":     "file_only",
					"evidence_summary":    "回答基于 1 个来源",
					"citations":           []interface{}{citation},
				},
			},
		},
	}
	raw, err := json.Marshal(payload)
	require.NoError(t, err)
	require.NoError(t, svc.SaveMessage(context.Background(), "session-cite", raw))

	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("user_id", citeUserID)
		c.Next()
	})
	// route-tier: authed
	router.GET("/history/:conversation_id", handler.GetConversationHistory)

	req := httptest.NewRequest(http.MethodGet, "/history/session-cite", nil)
	resp := httptest.NewRecorder()
	router.ServeHTTP(resp, req)

	require.Equal(t, http.StatusOK, resp.Code)
	var body []map[string]interface{}
	require.NoError(t, json.Unmarshal(resp.Body.Bytes(), &body))
	require.Len(t, body, 1)
	msg := body[0]

	meta, ok := msg["meta"].(map[string]interface{})
	require.True(t, ok)
	_, hasCitations := meta["citations"].([]interface{})
	require.Truef(t, hasCitations, "meta.citations must survive the history DTO, got %v", meta)

	widgets, ok := msg["widgets"].([]interface{})
	require.Truef(t, ok, "widgets must survive the history DTO, got %v", msg["widgets"])
	require.NotEmpty(t, widgets)
}
