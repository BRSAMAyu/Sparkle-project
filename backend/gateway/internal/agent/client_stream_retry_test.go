package agent

import (
	"context"
	"io"
	"net"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
)

// ── GW-P1-1 regression: StreamChat reconnect-retry context lifecycle ──────
//
// The retry branch used to build its stream on a context detached from the
// caller (context.Background()) and to `defer retryCancel()` — so the
// returned server-stream was canceled the moment StreamChat returned and
// every retried stream died before its first Recv.

type retryStreamCall struct {
	err error
	ctx context.Context
}

// recordingStreamAPI fails the first StreamChat attempt with a
// reconnect-worthy status and serves the (retry) attempt from a scripted
// result list, recording the ctx each call received.
type recordingStreamAPI struct {
	agentv1.AgentServiceClient

	mu      sync.Mutex
	calls   int
	results []retryStreamCall
}

func (r *recordingStreamAPI) StreamChat(ctx context.Context, in *agentv1.ChatRequest, opts ...grpc.CallOption) (grpc.ServerStreamingClient[agentv1.ChatResponse], error) {
	r.mu.Lock()
	i := r.calls
	r.calls++
	res := r.results[i]
	r.results[i].ctx = ctx
	r.mu.Unlock()
	if res.err != nil {
		return nil, res.err
	}
	return &retryFakeStream{ctx: ctx}, nil
}

func (r *recordingStreamAPI) callCount() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.calls
}

func (r *recordingStreamAPI) retryCtx() context.Context {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.results[1].ctx
}

type retryFakeStream struct {
	grpc.ClientStream
	ctx context.Context
}

func (f *retryFakeStream) Context() context.Context { return f.ctx }
func (f *retryFakeStream) Recv() (*agentv1.ChatResponse, error) {
	return nil, io.EOF
}

// newRetryTestClient wires a Client whose currentAPI is the fake and whose
// currentConn points at a live in-process gRPC server, so reconnect() sees a
// Ready/Idle conn, short-circuits and leaves the injected fake in place.
func newRetryTestClient(t *testing.T, api agentv1.AgentServiceClient) *Client {
	t.Helper()

	lis, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	srv := grpc.NewServer()
	agentv1.RegisterAgentServiceServer(srv, &agentv1.UnimplementedAgentServiceServer{})
	go func() { _ = srv.Serve(lis) }()
	t.Cleanup(srv.Stop)

	conn, err := grpc.NewClient(lis.Addr().String(), grpc.WithTransportCredentials(insecure.NewCredentials()))
	require.NoError(t, err)
	t.Cleanup(func() { _ = conn.Close() })

	// grpc.NewClient starts in Idle; wait until reconnect()'s short-circuit
	// condition (Ready or Idle) is observable.
	deadline := time.Now().Add(2 * time.Second)
	for {
		state := conn.GetState()
		if state == connectivity.Idle || state == connectivity.Ready {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("conn never reached Idle/Ready, state=%v", state)
		}
		time.Sleep(5 * time.Millisecond)
	}

	return &Client{
		conn:            conn,
		api:             api,
		config:          &config.Config{AgentAddress: lis.Addr().String(), InternalAPIKey: "test"},
		dialOptions:     []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())},
		minReconnectGap: time.Millisecond,
	}
}

func retryTestAPI(t *testing.T) *recordingStreamAPI {
	t.Helper()
	return &recordingStreamAPI{results: []retryStreamCall{
		{err: status.Error(codes.Unavailable, "first attempt down")},
		{}, // retry succeeds
	}}
}

// TestStreamChatRetryStreamAliveAfterReturn: the stream returned from the
// retry branch must not be canceled when StreamChat returns — the old
// `defer retryCancel()` killed it before the first Recv.
func TestStreamChatRetryStreamAliveAfterReturn(t *testing.T) {
	api := retryTestAPI(t)
	c := newRetryTestClient(t, api)

	stream, err := c.StreamChat(context.Background(), &agentv1.ChatRequest{UserId: "u-retry"})
	require.NoError(t, err)
	require.NotNil(t, stream)
	require.Equal(t, 2, api.callCount(), "expected initial attempt + retry attempt")

	require.NoError(t, stream.Context().Err(),
		"returned stream context must still be alive after StreamChat returns")
	require.NoError(t, api.retryCtx().Err())
}

// TestStreamChatRetryHonorsCallerCancel: the retry stream must stay attached
// to the caller's context so WS disconnects still propagate — the old branch
// parented it on context.Background(), detaching it from the WS lifecycle.
func TestStreamChatRetryHonorsCallerCancel(t *testing.T) {
	api := retryTestAPI(t)
	c := newRetryTestClient(t, api)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stream, err := c.StreamChat(ctx, &agentv1.ChatRequest{UserId: "u-retry"})
	require.NoError(t, err)
	require.NotNil(t, stream)

	// Guard: the stream must be alive before we cancel the caller — otherwise
	// a canceled-by-defer stream would satisfy the propagation check vacuously
	// (that defer-cancel is exactly the GW-P1-1 defect).
	require.NoError(t, stream.Context().Err(),
		"stream must be alive right after StreamChat returns, before any cancel")

	cancel()
	require.ErrorIs(t, stream.Context().Err(), context.Canceled,
		"canceling the caller ctx must cancel the retried stream")
	require.ErrorIs(t, api.retryCtx().Err(), context.Canceled)
}
