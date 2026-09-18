package handler

import (
	"net"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/service"
)

// blockingStreamAgent simulates a long-running upstream StreamChat: it emits
// one delta, then holds the stream open until its context is canceled —
// exactly the shape of an orphaned stream when a WS client vanishes.
type blockingStreamAgent struct {
	agentv1.UnimplementedAgentServiceServer
	enteredOnce sync.Once
	entered     chan struct{}
}

func (b *blockingStreamAgent) StreamChat(req *agentv1.ChatRequest, stream grpc.ServerStreamingServer[agentv1.ChatResponse]) error {
	b.enteredOnce.Do(func() { close(b.entered) })
	if err := stream.SendMsg(&agentv1.ChatResponse{
		ResponseId: "resp-block",
		Content:    &agentv1.ChatResponse_Delta{Delta: "partial"},
	}); err != nil {
		return err
	}
	<-stream.Context().Done()
	return stream.Context().Err()
}

// TestChatOrchestrator_ClientDisconnectReleasesStreamSlot is the regression
// test for GW-P1-2: after the WS upgrade the request context is never
// canceled by net/http, so a client disconnect used to leave the upstream
// gRPC stream running (holding a streamSem slot) until the stream ended
// naturally — enough simultaneous drops exhausted the semaphore and every
// new message got "Server busy". The read pump must cancel the in-flight
// stream as soon as the client disconnects.
func TestChatOrchestrator_ClientDisconnectReleasesStreamSlot(t *testing.T) {
	// 1. In-process gRPC agent mock whose stream blocks until canceled.
	mock := &blockingStreamAgent{entered: make(chan struct{})}
	lis, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	grpcSrv := grpc.NewServer()
	agentv1.RegisterAgentServiceServer(grpcSrv, mock)
	go func() { _ = grpcSrv.Serve(lis) }()
	defer grpcSrv.Stop()

	// 2. Real agent client pointing at the mock (lazy dial).
	agentClient, err := agent.NewClient(&config.Config{
		AgentAddress:       lis.Addr().String(),
		InternalAPIKey:     "test-key",
		GRPCTimeoutSeconds: 5,
	})
	require.NoError(t, err)
	defer agentClient.Close()

	// 3. Orchestrator with a single stream slot: any leak is immediately
	// observable as a stuck semaphore.
	s := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	defer rdb.Close()

	cfg := &config.Config{
		Environment:         "development",
		AllowedOrigins:      []string{"*"},
		StreamMaxConcurrent: 1,
	}
	orchestrator := NewChatOrchestrator(
		agentClient,
		nil, // galaxy
		nil, // userIdentity
		service.NewChatHistoryService(rdb),
		nil, // quota
		nil, // semantic cache
		nil, // billing
		NewWebSocketFactory(cfg),
		cfg,
		nil, // userContext
		nil, // taskCommand
		"http://mock-backend",
		nil, // signalHub
	)

	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/ws/chat", func(c *gin.Context) {
		c.Set("user_id", "disconnect-user")
		c.Set("auth_token", "mock-token")
		orchestrator.HandleWebSocket(c)
	})
	ts := httptest.NewServer(r)
	defer ts.Close()

	// 4. Client connects and kicks off one streaming chat request.
	client, _, err := websocket.DefaultDialer.Dial(
		"ws"+strings.TrimPrefix(ts.URL, "http")+"/ws/chat", nil)
	require.NoError(t, err)

	err = client.WriteJSON(map[string]interface{}{
		"message":    "hello",
		"session_id": "sess-disconnect",
	})
	require.NoError(t, err)

	// Wait until the upstream stream is in flight and holds the only slot.
	select {
	case <-mock.entered:
	case <-time.After(5 * time.Second):
		t.Fatal("upstream stream never started")
	}
	require.Eventually(t, func() bool {
		return len(orchestrator.streamSem) == 1
	}, 2*time.Second, 5*time.Millisecond, "stream slot should be occupied while streaming")

	// Drain the server's writes (message_ack + streamed delta) so the
	// disconnect happens while the handler is parked in stream.Recv() with
	// NO pending write — otherwise a write failure could release the slot
	// even without disconnect propagation, masking the bug.
	_ = client.SetReadDeadline(time.Now().Add(5 * time.Second))
	for i := 0; i < 2; i++ {
		if _, _, err := client.ReadMessage(); err != nil {
			t.Fatalf("expected ack + streamed delta from server: %v", err)
		}
	}

	// 5. Client vanishes without a close frame (weak mobile network).
	require.NoError(t, client.Close())

	// 6. The read pump must cancel the upstream stream and release the slot.
	//    Pre-fix the stream stayed orphaned and this never became true.
	require.Eventually(t, func() bool {
		return len(orchestrator.streamSem) == 0
	}, 5*time.Second, 10*time.Millisecond,
		"stream slot must be released after the client disconnects")
}
