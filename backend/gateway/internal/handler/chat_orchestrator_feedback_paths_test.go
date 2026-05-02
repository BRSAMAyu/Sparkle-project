package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

type recordingFeedbackSender struct {
	actionStatuses []recordedStatus
	toolResults    []map[string]interface{}
	nodeErrors     []recordedNodeError
	nodeAcks       []recordedNodeAck
	interventions  []recordedAck
	responses      []recordedAck
	plans          []recordedStatus
}

type recordedStatus struct {
	id     string
	status string
	data   map[string]interface{}
}

type recordedNodeError struct {
	nodeID  string
	version string
	message string
}

type recordedNodeAck struct {
	nodeID  string
	version string
	success bool
}

type recordedAck struct {
	id      string
	status  string
	message string
}

func (s *recordingFeedbackSender) SendActionStatus(actionID, status string, data map[string]interface{}) {
	s.actionStatuses = append(s.actionStatuses, recordedStatus{id: actionID, status: status, data: data})
}

func (s *recordingFeedbackSender) SendToolResult(payload map[string]interface{}) {
	s.toolResults = append(s.toolResults, payload)
}

func (s *recordingFeedbackSender) SendUpdateNodeError(nodeID, version, message string) {
	s.nodeErrors = append(s.nodeErrors, recordedNodeError{nodeID: nodeID, version: version, message: message})
}

func (s *recordingFeedbackSender) SendUpdateNodeMasteryAck(nodeID, version string, success bool) {
	s.nodeAcks = append(s.nodeAcks, recordedNodeAck{nodeID: nodeID, version: version, success: success})
}

func (s *recordingFeedbackSender) SendInterventionAck(requestID, status, message string) {
	s.interventions = append(s.interventions, recordedAck{id: requestID, status: status, message: message})
}

func (s *recordingFeedbackSender) SendResponseFeedbackAck(responseID, status, message string) {
	s.responses = append(s.responses, recordedAck{id: responseID, status: status, message: message})
}

func (s *recordingFeedbackSender) SendPlanReviewStatus(reviewID, status string, data map[string]interface{}) {
	s.plans = append(s.plans, recordedStatus{id: reviewID, status: status, data: data})
}

func TestChatOrchestratorFeedbackValidationPaths(t *testing.T) {
	ctx := context.Background()
	h := &ChatOrchestrator{httpClient: http.DefaultClient}
	sender := &recordingFeedbackSender{}
	userID := "11111111-2222-3333-4444-555555555555"

	h.handleActionFeedbackWithResponder(ctx, sender, map[string]interface{}{}, userID, "")
	require.Empty(t, sender.actionStatuses)

	h.handleActionFeedbackWithResponder(ctx, sender, map[string]interface{}{
		"action":         "dismiss",
		"tool_result_id": "tool-1",
		"widget_type":    "plan_card",
	}, userID, "")
	require.Len(t, sender.actionStatuses, 1)
	require.Equal(t, "dismissed", sender.actionStatuses[0].status)

	h.handleExecutionSummaryActionWithResponder(ctx, sender, "record-1", "confirm", "execution_summary", "")
	require.Equal(t, "failed", sender.actionStatuses[1].status)

	h.handleInterventionFeedbackWithResponder(sender, map[string]interface{}{}, userID, "")
	require.Equal(t, "failed", sender.interventions[0].status)

	h.handleInterventionFeedbackWithResponder(sender, map[string]interface{}{"request_id": "req-1"}, userID, "")
	require.Equal(t, "failed", sender.interventions[1].status)

	h.handleResponseFeedbackWithResponder(ctx, sender, map[string]interface{}{}, userID)
	require.Equal(t, "failed", sender.responses[0].status)

	h.handleResponseFeedbackWithResponder(ctx, sender, map[string]interface{}{
		"response_id":   "resp-1",
		"feedback_type": "sideways",
	}, userID)
	require.Equal(t, "failed", sender.responses[1].status)

	h.handleResponseFeedbackWithResponder(ctx, sender, map[string]interface{}{
		"response_id":   "resp-1",
		"feedback_type": "down",
		"reasons":       []interface{}{"inaccurate", "too_easy"},
		"meta":          map[string]interface{}{"screen": "chat"},
	}, userID)
	require.Equal(t, "failed", sender.responses[2].status)

	h.handlePlanReviewFeedbackWithResponder(ctx, sender, map[string]interface{}{}, userID)
	require.Empty(t, sender.plans)

	h.handlePlanReviewFeedbackWithResponder(ctx, sender, map[string]interface{}{
		"review_id":     "review-1",
		"user_decision": "modify",
		"meta":          map[string]interface{}{"reason": "scope"},
	}, userID)
	require.Len(t, sender.plans, 1)
	require.Equal(t, "failed", sender.plans[0].status)

	h.handleUpdateNodeMasteryWithResponder(ctx, sender, map[string]interface{}{}, userID)
	require.Empty(t, sender.nodeErrors)

	h.handleUpdateNodeMasteryWithResponder(ctx, sender, map[string]interface{}{
		"payload": map[string]interface{}{"nodeId": "", "version": ""},
	}, userID)
	require.Equal(t, "Invalid payload", sender.nodeErrors[0].message)

	h.handleUpdateNodeMasteryWithResponder(ctx, sender, map[string]interface{}{
		"payload": map[string]interface{}{"nodeId": "node-1", "version": "bad"},
	}, userID)
	require.Equal(t, "Invalid timestamp format", sender.nodeErrors[1].message)

	h.handleUpdateNodeMasteryWithResponder(ctx, sender, map[string]interface{}{
		"payload": map[string]interface{}{"nodeId": "node-1", "version": time.Now().UTC().Format(time.RFC3339Nano)},
	}, userID)
	require.Equal(t, "Internal service error", sender.nodeErrors[2].message)
}

func TestChatOrchestratorFeedbackHTTPCallbacks(t *testing.T) {
	ctx := context.Background()
	seen := map[string]int{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen[r.URL.Path]++
		require.Equal(t, "Bearer token-1", r.Header.Get("Authorization"))

		switch r.URL.Path {
		case "/api/v1/executions/records/record-1/confirm":
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"id":                    "record-1",
				"execution_intent_id":   "intent-1",
				"execution_status":      "succeeded",
				"requires_confirmation": false,
				"result_preview":        map[string]interface{}{"summary": "done"},
			})
		case "/api/v1/executions/records/record-2/reject":
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"id":                    "record-2",
				"execution_intent_id":   "intent-2",
				"execution_status":      "rejected",
				"requires_confirmation": false,
				"result_preview":        map[string]interface{}{"text": "not now"},
			})
		case "/api/v1/interventions/requests/request-1/feedback":
			w.WriteHeader(http.StatusNoContent)
		case "/api/v1/focus/sessions":
			var payload map[string]interface{}
			require.NoError(t, json.NewDecoder(r.Body).Decode(&payload))
			require.Equal(t, "deep_work", payload["focus_type"])
			w.WriteHeader(http.StatusCreated)
		case "/api/v1/signals/feedback":
			w.WriteHeader(http.StatusOK)
		default:
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
	}))
	defer server.Close()

	h := &ChatOrchestrator{
		backendURL: server.URL,
		httpClient: server.Client(),
	}
	sender := &recordingFeedbackSender{}

	h.handleExecutionSummaryActionWithResponder(ctx, sender, "record-1", "confirm", "execution_summary", "token-1")
	require.Equal(t, "confirmed", sender.actionStatuses[0].status)
	require.Len(t, sender.toolResults, 1)

	h.handleExecutionSummaryActionWithResponder(ctx, sender, "record-2", "dismiss", "execution_summary", "token-1")
	require.Equal(t, "dismissed", sender.actionStatuses[1].status)

	h.handleInterventionFeedbackWithResponder(sender, map[string]interface{}{
		"request_id":    "request-1",
		"feedback_type": "accepted",
		"extra_data":    map[string]interface{}{"source": "test"},
	}, "user-1", "token-1")
	require.Equal(t, "ok", sender.interventions[0].status)

	h.handleFocusCompleted(map[string]interface{}{
		"session_id":      "focus-1",
		"actual_duration": 25.0,
		"focus_type":      "deep_work",
		"tasks_completed": []interface{}{"not-a-uuid", "11111111-2222-3333-4444-555555555555"},
	}, "user-1", "token-1")

	require.NoError(t, h.persistActionFeedback("token-1", "tool-1", "focus_card", "confirm"))
	require.Equal(t, 1, seen["/api/v1/executions/records/record-1/confirm"])
	require.Equal(t, 1, seen["/api/v1/executions/records/record-2/reject"])
	require.Equal(t, 1, seen["/api/v1/interventions/requests/request-1/feedback"])
	require.Equal(t, 1, seen["/api/v1/focus/sessions"])
	require.Equal(t, 1, seen["/api/v1/signals/feedback"])
}

func TestFocusCompletedEarlyReturns(t *testing.T) {
	h := &ChatOrchestrator{}

	require.NotPanics(t, func() {
		h.handleFocusCompleted(map[string]interface{}{}, "user-1", "")
		h.handleFocusCompleted(map[string]interface{}{"session_id": "focus-1"}, "user-1", "")
		h.handleFocusCompleted(map[string]interface{}{
			"session_id":      "focus-1",
			"actual_duration": 25.0,
		}, "user-1", "")
		h.handleFocusCompleted(map[string]interface{}{
			"session_id":      "focus-1",
			"actual_duration": 0.0,
		}, "user-1", "token")
	})
}
