package handler

import (
	"os"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestPlanReviewE2E tests the complete plan review workflow:
// 1. User creates a plan via chat
// 2. AI agent triggers plan review
// 3. Review result sent via WebSocket with metadata
// 4. User submits feedback via gRPC SubmitPlanReview
// 5. System updates plan based on feedback

func TestPlanReviewE2E(t *testing.T) {
	// Skip if running in short mode
	if testing.Short() {
		t.Skip("Skipping E2E test in short mode")
	}
	requireE2EEnabled(t)

	// Setup test environment
	// This requires:
	// - Running Python gRPC server
	// - Running PostgreSQL
	// - Running Redis

	t.Run("CompletePlanReviewWorkflow", func(t *testing.T) {
		// Step 1: Establish WebSocket connection
		wsURL := setupWebSocketTestServer(t)
		wsConn, resp, err := websocket.DefaultDialer.Dial(wsURL+"?token=test-token", nil)
		require.NoError(t, err)
		require.Equal(t, 101, resp.StatusCode)
		defer wsConn.Close()

		// Step 2: Send message requesting plan creation
		planRequest := map[string]interface{}{
			"type":      "message",
			"content":   "帮我制定一个学习Python的四周计划",
			"sessionId": "test-plan-review-session",
			"userId":    "test-user-123",
		}

		err = wsConn.WriteJSON(planRequest)
		require.NoError(t, err)

		// Step 3: Listen for plan creation response
		var planID string
		responses := collectWebSocketResponses(wsConn, 30*time.Second)

		// Should receive streaming responses
		assert.Greater(t, len(responses), 0, "Should receive responses")

		// Check for plan creation in metadata
		for _, resp := range responses {
			if metadata, ok := resp["metadata"].(map[string]interface{}); ok {
				if planIDVal, ok := metadata["plan_id"].(string); ok {
					planID = planIDVal
				}
			}
		}

		t.Log("Plan created with ID:", planID)

		// Step 4: Send message requesting plan review
		reviewRequest := map[string]interface{}{
			"type":      "message",
			"content":   "请评审这个学习计划",
			"sessionId": "test-plan-review-session",
			"userId":    "test-user-123",
			"metadata": map[string]interface{}{
				"plan_id": planID,
			},
		}

		err = wsConn.WriteJSON(reviewRequest)
		require.NoError(t, err)

		// Step 5: Listen for plan review event
		var reviewReceived bool
		var reviewData map[string]interface{}

		responses = collectWebSocketResponses(wsConn, 30*time.Second)

		for _, resp := range responses {
			if metadata, ok := resp["metadata"].(map[string]interface{}); ok {
				if requiresReview, ok := metadata["requires_review"].(bool); ok && requiresReview {
					reviewReceived = true
					reviewData = metadata["review_data"].(map[string]interface{})
					break
				}
			}
		}

		// Note: Plan review may not always trigger depending on AI logic
		// This test mainly validates the event structure when it does occur
		if reviewReceived {
			t.Log("Plan review received:", reviewData)

			// Verify review data structure
			assert.Contains(t, reviewData, "plan_id")
			assert.Contains(t, reviewData, "review_id")
			assert.Contains(t, reviewData, "overall_score")

			// Step 6: Submit feedback via gRPC (would require gRPC client)
			// For now, we simulate via WebSocket
			feedbackRequest := map[string]interface{}{
				"type":      "plan_review_feedback",
				"planId":    planID,
				"reviewId":  reviewData["review_id"],
				"decision":  "approve",
				"sessionId": "test-plan-review-session",
				"userId":    "test-user-123",
			}

			err = wsConn.WriteJSON(feedbackRequest)
			require.NoError(t, err)

			// Step 7: Verify plan update
			responses = collectWebSocketResponses(wsConn, 10*time.Second)
			assert.Greater(t, len(responses), 0, "Should receive feedback confirmation")
		} else {
			t.Log("Plan review was not triggered (AI decision)")
		}
	})

	t.Run("PlanReviewWithIssues", func(t *testing.T) {
		// Test plan review that identifies issues
		wsConn := setupWebSocketConnection(t, "test-token")
		defer wsConn.Close()

		// Create a problematic plan
		problematicRequest := map[string]interface{}{
			"type":      "message",
			"content":   "制定一个一天学会所有编程语言的计划",
			"sessionId": "test-problematic-plan",
			"userId":    "test-user-456",
		}

		err := wsConn.WriteJSON(problematicRequest)
		require.NoError(t, err)

		// Listen for review with issues
		responses := collectWebSocketResponses(wsConn, 30*time.Second)

		for _, resp := range responses {
			if metadata, ok := resp["metadata"].(map[string]interface{}); ok {
				if requiresReview, ok := metadata["requires_review"].(bool); ok && requiresReview {
					reviewData := metadata["review_data"].(map[string]interface{})

					// Check for issues
					if issues, ok := reviewData["issues"].([]interface{}); ok {
						t.Logf("Plan has %d issues identified", len(issues))
						assert.Greater(t, len(issues), 0, "Should identify issues")
					}
				}
			}
		}
	})

	t.Run("PlanReviewModificationFlow", func(t *testing.T) {
		// Test user modifying plan after review
		wsConn := setupWebSocketConnection(t, "test-token")
		defer wsConn.Close()

		// Create plan
		planRequest := map[string]interface{}{
			"type":      "message",
			"content":   "制定一个学习Go的计划",
			"sessionId": "test-modification-flow",
			"userId":    "test-user-789",
		}

		err := wsConn.WriteJSON(planRequest)
		require.NoError(t, err)

		collectWebSocketResponses(wsConn, 20*time.Second)

		// Request review
		reviewRequest := map[string]interface{}{
			"type":      "message",
			"content":   "评审这个计划",
			"sessionId": "test-modification-flow",
			"userId":    "test-user-789",
		}

		err = wsConn.WriteJSON(reviewRequest)
		require.NoError(t, err)

		responses := collectWebSocketResponses(wsConn, 20*time.Second)

		// Look for review event
		var reviewID string
		for _, resp := range responses {
			if metadata, ok := resp["metadata"].(map[string]interface{}); ok {
				if requiresReview, ok := metadata["requires_review"].(bool); ok && requiresReview {
					reviewData := metadata["review_data"].(map[string]interface{})
					reviewID = reviewData["review_id"].(string)
				}
			}
		}

		if reviewID != "" {
			// Submit modification request
			modificationRequest := map[string]interface{}{
				"type":       "message",
				"content":    "请把学习周期延长到8周",
				"sessionId":  "test-modification-flow",
				"userId":     "test-user-789",
				"reviewId":   reviewID,
				"actionType": "modify",
			}

			err = wsConn.WriteJSON(modificationRequest)
			require.NoError(t, err)

			// Verify modification processed
			responses = collectWebSocketResponses(wsConn, 20*time.Second)
			assert.Greater(t, len(responses), 0)
		}
	})
}

func TestPlanReviewRejectionFlow(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping E2E test in short mode")
	}
	requireE2EEnabled(t)

	t.Run("RejectPlanReview", func(t *testing.T) {
		wsConn := setupWebSocketConnection(t, "test-token")
		defer wsConn.Close()

		// Create and review plan
		planRequest := map[string]interface{}{
			"type":      "message",
			"content":   "制定一个学习Rust的计划",
			"sessionId": "test-rejection-flow",
			"userId":    "test-user-reject",
		}

		err := wsConn.WriteJSON(planRequest)
		require.NoError(t, err)

		collectWebSocketResponses(wsConn, 20*time.Second)

		// Request review
		reviewRequest := map[string]interface{}{
			"type":      "message",
			"content":   "评审这个计划",
			"sessionId": "test-rejection-flow",
			"userId":    "test-user-reject",
		}

		err = wsConn.WriteJSON(reviewRequest)
		require.NoError(t, err)

		responses := collectWebSocketResponses(wsConn, 20*time.Second)

		var reviewID string
		for _, resp := range responses {
			if metadata, ok := resp["metadata"].(map[string]interface{}); ok {
				if requiresReview, ok := metadata["requires_review"].(bool); ok && requiresReview {
					reviewData := metadata["review_data"].(map[string]interface{})
					reviewID = reviewData["review_id"].(string)
				}
			}
		}

		if reviewID != "" {
			// Reject the review
			rejectionRequest := map[string]interface{}{
				"type":       "plan_review_feedback",
				"reviewId":   reviewID,
				"decision":   "reject",
				"reason":     "计划不符合我的需求",
				"sessionId":  "test-rejection-flow",
				"userId":     "test-user-reject",
			}

			err = wsConn.WriteJSON(rejectionRequest)
			require.NoError(t, err)

			// Verify rejection processed
			responses = collectWebSocketResponses(wsConn, 10*time.Second)

			// Should receive confirmation
			rejectionConfirmed := false
			for _, resp := range responses {
				if msgType, ok := resp["type"].(string); ok {
					if msgType == "plan_review_rejection_confirmed" {
						rejectionConfirmed = true
					}
				}
			}

			assert.True(t, rejectionConfirmed, "Should confirm rejection")
		}
	})
}

// Helper functions

func setupWebSocketTestServer(t *testing.T) string {
	// In real implementation, this would start a test server
	// For now, return the actual server URL
	return "ws://localhost:8080/ws/chat"
}

func requireE2EEnabled(t *testing.T) {
	if os.Getenv("SPARKLE_E2E_WS") != "1" {
		t.Skip("Skipping WebSocket E2E test; set SPARKLE_E2E_WS=1 to enable")
	}
}

func setupWebSocketConnection(t *testing.T, token string) *websocket.Conn {
	wsURL := setupWebSocketTestServer(t)
	wsConn, resp, err := websocket.DefaultDialer.Dial(wsURL+"?token="+token, nil)
	require.NoError(t, err)
	require.Equal(t, 101, resp.StatusCode)
	return wsConn
}

func collectWebSocketResponses(conn *websocket.Conn, timeout time.Duration) []map[string]interface{} {
	var responses []map[string]interface{}
	deadline := time.Now().Add(timeout)

	for time.Now().Before(deadline) {
		// Set read deadline
		conn.SetReadDeadline(time.Now().Add(1 * time.Second))

		var msg map[string]interface{}
		err := conn.ReadJSON(&msg)
		if err != nil {
			// Timeout is expected, break
			break
		}

		responses = append(responses, msg)

		// Check for completion signal
		if metadata, ok := msg["metadata"].(map[string]interface{}); ok {
			if done, ok := metadata["done"].(bool); ok && done {
				break
			}
		}
	}

	return responses
}

// TestPlanReviewIntegrationWithGRPC tests the gRPC SubmitPlanReview endpoint
func TestPlanReviewIntegrationWithGRPC(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}
	requireE2EEnabled(t)

	t.Run("SubmitPlanReviewViaGRPC", func(t *testing.T) {
		// This test requires a running gRPC server
		// and would use the generated gRPC client

		// Pseudo-code:
		// 1. Connect to gRPC server at localhost:50051
		// 2. Call SubmitPlanReview RPC
		// 3. Verify response

		// For now, we'll skip the actual gRPC call
		// as it requires the server to be running
		t.Skip("Requires running gRPC server")

		/*
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()

			conn, err := grpc.DialContext(ctx, "localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
			require.NoError(t, err)
			defer conn.Close()

			client := agent_v1.NewAgentServiceClient(conn)

			req := &agent_v1.PlanReviewRequest{
				UserId:       "test-user-123",
				PlanId:       "plan-456",
				ReviewId:     "review-789",
				Decision:     agent_v1.ReviewDecision_APPROVE,
				Feedback:     "Looks good!",
				ModifiedPlan: nil,
			}

			resp, err := client.SubmitPlanReview(ctx, req)
			require.NoError(t, err)
			assert.NotNil(t, resp)
			assert.True(t, resp.Success)
		*/
	})
}

// BenchmarkPlanReviewWorkflow benchmarks the plan review workflow
func BenchmarkPlanReviewWorkflow(b *testing.B) {
	// Setup connection
	wsConn := setupWebSocketConnection(&testing.T{}, "test-token")
	defer wsConn.Close()

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		// Create plan
		planRequest := map[string]interface{}{
			"type":      "message",
			"content":   "制定一个学习计划",
			"sessionId": "bench-session",
			"userId":    "bench-user",
		}

		wsConn.WriteJSON(planRequest)

		// Collect responses
		responses := collectWebSocketResponses(wsConn, 30*time.Second)
		_ = responses
	}
}
