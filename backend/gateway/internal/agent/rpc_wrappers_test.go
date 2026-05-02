package agent

import (
	"context"
	"net"
	"testing"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/test/bufconn"
)

type wrapperAgentServer struct {
	agentv1.UnimplementedAgentServiceServer
	seenMetadata metadata.MD
}

func (s *wrapperAgentServer) remember(ctx context.Context) {
	md, _ := metadata.FromIncomingContext(ctx)
	s.seenMetadata = md
}

func (s *wrapperAgentServer) StreamChat(req *agentv1.ChatRequest, stream grpc.ServerStreamingServer[agentv1.ChatResponse]) error {
	s.remember(stream.Context())
	return stream.Send(&agentv1.ChatResponse{ResponseId: "resp-1", RequestId: req.RequestId})
}

func (s *wrapperAgentServer) RetrieveMemory(ctx context.Context, req *agentv1.MemoryQuery) (*agentv1.MemoryResult, error) {
	s.remember(ctx)
	return &agentv1.MemoryResult{}, nil
}

func (s *wrapperAgentServer) GetUserProfile(ctx context.Context, req *agentv1.ProfileRequest) (*agentv1.UserProfile, error) {
	s.remember(ctx)
	return &agentv1.UserProfile{Nickname: "tester"}, nil
}

func (s *wrapperAgentServer) GetWeeklyReport(ctx context.Context, req *agentv1.WeeklyReportRequest) (*agentv1.WeeklyReport, error) {
	s.remember(ctx)
	return &agentv1.WeeklyReport{Summary: "done"}, nil
}

func (s *wrapperAgentServer) SubmitResponseFeedback(ctx context.Context, req *agentv1.ResponseFeedbackRequest) (*agentv1.ResponseFeedbackResponse, error) {
	s.remember(ctx)
	return &agentv1.ResponseFeedbackResponse{Success: true}, nil
}

func (s *wrapperAgentServer) SubmitPlanReview(ctx context.Context, req *agentv1.PlanReviewRequest) (*agentv1.PlanReviewResponse, error) {
	s.remember(ctx)
	return &agentv1.PlanReviewResponse{Success: true}, nil
}

func (s *wrapperAgentServer) SubmitContentReviewFeedback(ctx context.Context, req *agentv1.ContentReviewFeedbackRequest) (*agentv1.ContentReviewFeedbackResponse, error) {
	s.remember(ctx)
	return &agentv1.ContentReviewFeedbackResponse{}, nil
}

func (s *wrapperAgentServer) SubmitReviewOverride(ctx context.Context, req *agentv1.ReviewOverrideRequest) (*agentv1.ReviewOverrideResponse, error) {
	s.remember(ctx)
	return &agentv1.ReviewOverrideResponse{}, nil
}

func (s *wrapperAgentServer) SubmitReviewAppeal(ctx context.Context, req *agentv1.ReviewAppealRequest) (*agentv1.ReviewAppealResponse, error) {
	s.remember(ctx)
	return &agentv1.ReviewAppealResponse{}, nil
}

func (s *wrapperAgentServer) GetAppealStatus(ctx context.Context, req *agentv1.AppealStatusRequest) (*agentv1.AppealStatusResponse, error) {
	s.remember(ctx)
	return &agentv1.AppealStatusResponse{}, nil
}

func (s *wrapperAgentServer) SubmitReviewFeedback(ctx context.Context, req *agentv1.ReviewFeedbackRequest) (*agentv1.ReviewFeedbackResponse, error) {
	s.remember(ctx)
	return &agentv1.ReviewFeedbackResponse{}, nil
}

func (s *wrapperAgentServer) RequestRegeneration(ctx context.Context, req *agentv1.RegenerationRequest) (*agentv1.RegenerationResponse, error) {
	s.remember(ctx)
	return &agentv1.RegenerationResponse{}, nil
}

func (s *wrapperAgentServer) GetFeedbackStatistics(ctx context.Context, req *agentv1.FeedbackStatisticsRequest) (*agentv1.FeedbackStatisticsResponse, error) {
	s.remember(ctx)
	return &agentv1.FeedbackStatisticsResponse{}, nil
}

func (s *wrapperAgentServer) GetArbitrationQueue(ctx context.Context, req *agentv1.GetArbitrationQueueRequest) (*agentv1.GetArbitrationQueueResponse, error) {
	s.remember(ctx)
	return &agentv1.GetArbitrationQueueResponse{}, nil
}

func (s *wrapperAgentServer) AssignArbitrationCase(ctx context.Context, req *agentv1.AssignArbitrationCaseRequest) (*agentv1.AssignArbitrationCaseResponse, error) {
	s.remember(ctx)
	return &agentv1.AssignArbitrationCaseResponse{}, nil
}

func (s *wrapperAgentServer) SubmitArbitrationDecision(ctx context.Context, req *agentv1.SubmitArbitrationDecisionRequest) (*agentv1.SubmitArbitrationDecisionResponse, error) {
	s.remember(ctx)
	return &agentv1.SubmitArbitrationDecisionResponse{}, nil
}

func (s *wrapperAgentServer) GetArbitrationQueueStats(ctx context.Context, req *agentv1.GetArbitrationQueueStatsRequest) (*agentv1.GetArbitrationQueueStatsResponse, error) {
	s.remember(ctx)
	return &agentv1.GetArbitrationQueueStatsResponse{}, nil
}

func newWrapperClient(t *testing.T) (*Client, *wrapperAgentServer, func()) {
	t.Helper()
	listener := bufconn.Listen(1024 * 1024)
	grpcServer := grpc.NewServer()
	service := &wrapperAgentServer{}
	agentv1.RegisterAgentServiceServer(grpcServer, service)

	go func() {
		_ = grpcServer.Serve(listener)
	}()

	ctx := context.Background()
	conn, err := grpc.DialContext(ctx, "bufnet",
		grpc.WithContextDialer(func(context.Context, string) (net.Conn, error) {
			return listener.Dial()
		}),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	require.NoError(t, err)

	client := &Client{
		conn: conn,
		api:  agentv1.NewAgentServiceClient(conn),
		config: &config.Config{
			InternalAPIKey: "internal-secret",
		},
		minReconnectGap: 1,
	}

	cleanup := func() {
		client.Close()
		grpcServer.Stop()
		_ = listener.Close()
	}
	return client, service, cleanup
}

func TestClientRPCWrappersUseCurrentAPI(t *testing.T) {
	client, service, cleanup := newWrapperClient(t)
	defer cleanup()

	ctx := WithTraceID(context.Background(), "trace-123")
	stream, err := client.StreamChat(ctx, &agentv1.ChatRequest{
		UserId:    "user-1",
		SessionId: "session-1",
		RequestId: "req-1",
	})
	require.NoError(t, err)
	resp, err := stream.Recv()
	require.NoError(t, err)
	require.Equal(t, "resp-1", resp.ResponseId)

	_, err = client.RetrieveMemory(ctx, &agentv1.MemoryQuery{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.GetUserProfile(ctx, &agentv1.ProfileRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.GetWeeklyReport(ctx, &agentv1.WeeklyReportRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.SubmitResponseFeedback(ctx, &agentv1.ResponseFeedbackRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.SubmitPlanReview(ctx, &agentv1.PlanReviewRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.SubmitContentReviewFeedback(ctx, &agentv1.ContentReviewFeedbackRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.SubmitReviewOverride(ctx, &agentv1.ReviewOverrideRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.SubmitReviewAppeal(ctx, &agentv1.ReviewAppealRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.GetAppealStatus(ctx, &agentv1.AppealStatusRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.SubmitReviewFeedback(ctx, &agentv1.ReviewFeedbackRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.RequestRegeneration(ctx, &agentv1.RegenerationRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.GetFeedbackStatistics(ctx, &agentv1.FeedbackStatisticsRequest{UserId: "user-1"})
	require.NoError(t, err)
	_, err = client.GetArbitrationQueue(ctx, &agentv1.GetArbitrationQueueRequest{})
	require.NoError(t, err)
	_, err = client.AssignArbitrationCase(ctx, &agentv1.AssignArbitrationCaseRequest{ArbitratorId: "arb-1"})
	require.NoError(t, err)
	_, err = client.SubmitArbitrationDecision(ctx, &agentv1.SubmitArbitrationDecisionRequest{ArbitratorId: "arb-1"})
	require.NoError(t, err)
	_, err = client.GetArbitrationQueueStats(ctx, &agentv1.GetArbitrationQueueStatsRequest{})
	require.NoError(t, err)

	require.Contains(t, service.seenMetadata.Get("x-internal-api-key"), "internal-secret")
}

func TestStreamChatWithFallbackRecordsSuccessfulResult(t *testing.T) {
	client, _, cleanup := newWrapperClient(t)
	defer cleanup()

	checker := NewAgentHealthChecker(client, time.Hour, time.Second, DefaultCircuitBreakerConfig())
	client.healthChecker = checker

	stream, err := client.StreamChatWithFallback(context.Background(), &agentv1.ChatRequest{
		UserId:    "user-1",
		RequestId: "req-1",
	})
	require.NoError(t, err)
	_, err = stream.Recv()
	require.NoError(t, err)
	require.True(t, client.IsHealthy())
}
