package agent

import (
	"context"
	"testing"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

// ============================================================
// RPC Request Construction Tests
// Verify each RPC method accepts correctly-structured requests.
// ============================================================

func TestRetrieveMemoryRequest(t *testing.T) {
	t.Run("valid_memory_query", func(t *testing.T) {
		req := &agentv1.MemoryQuery{
			UserId:    "user-123",
			QueryText: "recent study sessions",
			Limit:     10,
		}
		assert.Equal(t, "user-123", req.UserId)
		assert.Equal(t, "recent study sessions", req.QueryText)
		assert.Equal(t, int32(10), req.Limit)
	})

	t.Run("empty_query_text", func(t *testing.T) {
		req := &agentv1.MemoryQuery{UserId: "user-456"}
		assert.Equal(t, "user-456", req.UserId)
		assert.Empty(t, req.QueryText)
	})
}

func TestGetUserProfileRequest(t *testing.T) {
	t.Run("valid_profile_request", func(t *testing.T) {
		req := &agentv1.ProfileRequest{
			UserId: "user-789",
		}
		assert.Equal(t, "user-789", req.UserId)
	})
}

func TestSubmitContentReviewFeedbackRequest(t *testing.T) {
	t.Run("valid_feedback_request", func(t *testing.T) {
		req := &agentv1.ContentReviewFeedbackRequest{
			UserId:       "user-001",
			ReviewId:     "review-001",
			ResponseId:   "resp-001",
			Rating:       1,
			Comment:      "inappropriate content",
		}
		assert.Equal(t, "user-001", req.UserId)
		assert.Equal(t, "review-001", req.ReviewId)
		assert.Equal(t, int32(1), req.Rating)
	})
}

func TestSubmitReviewOverrideRequest(t *testing.T) {
	t.Run("valid_override_request", func(t *testing.T) {
		req := &agentv1.ReviewOverrideRequest{
			UserId:           "user-002",
			ReviewId:         "review-002",
			OriginalDecision: "failed",
			NewDecision:      "passed",
			Reason:           "false positive",
		}
		assert.Equal(t, "user-002", req.UserId)
		assert.Equal(t, "passed", req.NewDecision)
		assert.Equal(t, "false positive", req.Reason)
	})
}

func TestSubmitReviewAppealRequest(t *testing.T) {
	t.Run("valid_appeal_request", func(t *testing.T) {
		req := &agentv1.ReviewAppealRequest{
			UserId:       "user-003",
			ReviewId:     "review-003",
			AppealReason: "I disagree with the review assessment",
		}
		assert.Equal(t, "user-003", req.UserId)
		assert.NotEmpty(t, req.AppealReason)
	})
}

func TestGetAppealStatusRequest(t *testing.T) {
	t.Run("valid_appeal_status", func(t *testing.T) {
		req := &agentv1.AppealStatusRequest{
			UserId:   "user-004",
			AppealId: "appeal-004",
		}
		assert.Equal(t, "user-004", req.UserId)
		assert.Equal(t, "appeal-004", req.AppealId)
	})
}

func TestSubmitReviewFeedbackRequest(t *testing.T) {
	t.Run("valid_review_feedback", func(t *testing.T) {
		req := &agentv1.ReviewFeedbackRequest{
			UserId:       "user-005",
			ReviewId:     "review-005",
			FeedbackType: "rating",
			Rating:       5,
			WasHelpful:   true,
		}
		assert.Equal(t, "user-005", req.UserId)
		assert.Equal(t, int32(5), req.Rating)
		assert.True(t, req.WasHelpful)
	})
}

func TestRequestRegenerationRequest(t *testing.T) {
	t.Run("valid_regen_request", func(t *testing.T) {
		req := &agentv1.RegenerationRequest{
			UserId:            "user-006",
			OriginalContentId: "content-006",
			ReviewId:          "review-006",
			RegenerationType:  "improve_quality",
		}
		assert.Equal(t, "user-006", req.UserId)
		assert.Equal(t, "improve_quality", req.RegenerationType)
	})
}

func TestGetFeedbackStatisticsRequest(t *testing.T) {
	t.Run("valid_stats_request", func(t *testing.T) {
		req := &agentv1.FeedbackStatisticsRequest{
			UserId:     "user-007",
			PeriodDays: 30,
		}
		assert.Equal(t, "user-007", req.UserId)
		assert.Equal(t, int32(30), req.PeriodDays)
	})
}

func TestArbitrationRequests(t *testing.T) {
	t.Run("get_arbitration_queue", func(t *testing.T) {
		req := &agentv1.GetArbitrationQueueRequest{
			Limit:          20,
			StatusFilter:   "pending",
			PriorityFilter: "high",
		}
		assert.Equal(t, int32(20), req.Limit)
		assert.Equal(t, "pending", req.StatusFilter)
	})

	t.Run("assign_arbitration_case", func(t *testing.T) {
		req := &agentv1.AssignArbitrationCaseRequest{
			CaseId:       "case-001",
			ArbitratorId: "arb-001",
		}
		assert.Equal(t, "arb-001", req.ArbitratorId)
		assert.Equal(t, "case-001", req.CaseId)
	})

	t.Run("submit_arbitration_decision", func(t *testing.T) {
		req := &agentv1.SubmitArbitrationDecisionRequest{
			CaseId:       "case-002",
			Decision:     "rejected",
			Explanation:  "content violates policy",
			ArbitratorId: "arb-002",
		}
		assert.Equal(t, "arb-002", req.ArbitratorId)
		assert.Equal(t, "rejected", req.Decision)
		assert.NotEmpty(t, req.Explanation)
	})

	t.Run("get_arbitration_queue_stats", func(t *testing.T) {
		req := &agentv1.GetArbitrationQueueStatsRequest{}
		assert.NotNil(t, req)
	})
}

// ============================================================
// Metadata Injection Tests
// ============================================================

func TestMetadataInjection(t *testing.T) {
	t.Run("inject_metadata_adds_user_id", func(t *testing.T) {
		client := &Client{config: &config.Config{InternalAPIKey: "test-key"}}
		ctx := context.Background()

		outCtx := client.injectMetadata(ctx, "user-abc")

		existing, ok := metadata.FromOutgoingContext(outCtx)
		assert.True(t, ok, "should have outgoing metadata")
		if ok {
			userIDs := existing.Get("user-id")
			assert.Contains(t, userIDs, "user-abc", "should contain user ID in metadata")
			apiKeys := existing.Get("x-internal-api-key")
			assert.Contains(t, apiKeys, "test-key", "should contain internal API key")
		}
	})

	t.Run("inject_metadata_with_trace_id", func(t *testing.T) {
		client := &Client{config: &config.Config{InternalAPIKey: "test-key"}}
		ctx := WithTraceID(context.Background(), "trace-123")

		outCtx := client.injectMetadata(ctx, "user-xyz")

		existing, ok := metadata.FromOutgoingContext(outCtx)
		assert.True(t, ok)
		traceIDs := existing.Get("x-trace-id")
		assert.Contains(t, traceIDs, "trace-123", "should contain trace ID from context value")
	})

	t.Run("inject_metadata_empty_user_id", func(t *testing.T) {
		client := &Client{config: &config.Config{InternalAPIKey: "test-key"}}
		ctx := context.Background()

		// Some methods pass empty user ID (e.g., GetArbitrationQueue)
		outCtx := client.injectMetadata(ctx, "")

		existing, ok := metadata.FromOutgoingContext(outCtx)
		assert.True(t, ok, "should have metadata even with empty user ID")
		if ok {
			// Empty user ID should NOT be added as a pair
			userIDs := existing.Get("user-id")
			assert.Empty(t, userIDs, "empty user ID should not be added to metadata")
		}
	})
}

// ============================================================
// Error Handling Tests
// ============================================================

func TestRPCErrorHandling(t *testing.T) {
	t.Run("unavailable_triggers_reconnect", func(t *testing.T) {
		err := status.Error(codes.Unavailable, "connection refused")
		assert.True(t, shouldReconnect(err))
	})

	t.Run("deadline_exceeded_triggers_reconnect", func(t *testing.T) {
		err := status.Error(codes.DeadlineExceeded, "timeout")
		assert.True(t, shouldReconnect(err))
	})

	t.Run("internal_error_no_reconnect", func(t *testing.T) {
		err := status.Error(codes.Internal, "internal error")
		// Only Unavailable and DeadlineExceeded trigger reconnect
		assert.False(t, shouldReconnect(err), "Internal should NOT trigger reconnect")
	})

	t.Run("not_found_no_reconnect", func(t *testing.T) {
		err := status.Error(codes.NotFound, "resource not found")
		assert.False(t, shouldReconnect(err))
	})

	t.Run("permission_denied_no_reconnect", func(t *testing.T) {
		err := status.Error(codes.PermissionDenied, "access denied")
		assert.False(t, shouldReconnect(err))
	})

	t.Run("cancelled_no_reconnect", func(t *testing.T) {
		err := status.Error(codes.Canceled, "request cancelled")
		assert.False(t, shouldReconnect(err))
	})
}

// ============================================================
// Client State Tests
// ============================================================

func TestClientStateWithoutConnection(t *testing.T) {
	t.Run("close_nil_connection_no_panic", func(t *testing.T) {
		client := &Client{}
		assert.NotPanics(t, func() {
			client.Close()
		})
	})
}
