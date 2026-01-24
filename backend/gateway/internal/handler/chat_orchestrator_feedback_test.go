package handler

import (
	"context"
	"testing"
)

type responseFeedbackAckRecorder struct {
	responseID string
	status     string
	message    string
}

func (r *responseFeedbackAckRecorder) SendResponseFeedbackAck(responseID, status, message string) {
	r.responseID = responseID
	r.status = status
	r.message = message
}

func TestHandleResponseFeedbackMissingResponseID(t *testing.T) {
	h := &ChatOrchestrator{}
	recorder := &responseFeedbackAckRecorder{}
	msg := map[string]interface{}{
		"feedback_type": "up",
	}

	h.handleResponseFeedbackWithResponder(context.Background(), recorder, msg, "user-123")

	if recorder.status != "failed" {
		t.Fatalf("expected failed status, got %q", recorder.status)
	}
}

func TestHandleResponseFeedbackInvalidFeedbackType(t *testing.T) {
	h := &ChatOrchestrator{}
	recorder := &responseFeedbackAckRecorder{}
	msg := map[string]interface{}{
		"response_id":   "resp-123",
		"feedback_type": "unknown",
	}

	h.handleResponseFeedbackWithResponder(context.Background(), recorder, msg, "user-123")

	if recorder.status != "failed" {
		t.Fatalf("expected failed status, got %q", recorder.status)
	}
}
