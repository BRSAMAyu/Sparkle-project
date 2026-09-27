package handler

// V3-FIX-334: a gateway dedup-window hit must resolve into the engine's
// recorded outcome instead of bouncing unconditionally. These tests pin the
// pure bridge-level decision (dedupHitDecision) and the replay frame builder
// (buildReplayChatResponse) that the handleChatMessage dedup branch relies on.

import (
	"errors"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
)

func TestDedupHitDecisionTriState(t *testing.T) {
	completed := &agentv1.GetRequestResultResponse{
		Status:  agentv1.RequestResultStatus_REQUEST_RESULT_COMPLETED,
		Message: "已完成的回答",
	}
	running := &agentv1.GetRequestResultResponse{
		Status: agentv1.RequestResultStatus_REQUEST_RESULT_RUNNING,
	}
	unknown := &agentv1.GetRequestResultResponse{
		Status: agentv1.RequestResultStatus_REQUEST_RESULT_UNKNOWN,
	}
	completedNoBody := &agentv1.GetRequestResultResponse{
		Status: agentv1.RequestResultStatus_REQUEST_RESULT_COMPLETED,
	}

	tests := []struct {
		name         string
		resp         *agentv1.GetRequestResultResponse
		err          error
		wantAction   dedupHitAction
		wantReplayTx string
	}{
		{
			name:       "engine error falls back to duplicate_request",
			resp:       completed,
			err:        errors.New("unavailable"),
			wantAction: dedupFallbackDuplicate,
		},
		{
			name:       "nil response falls back to duplicate_request",
			wantAction: dedupFallbackDuplicate,
		},
		{
			name:       "unknown status falls back to duplicate_request",
			resp:       unknown,
			wantAction: dedupFallbackDuplicate,
		},
		{
			name:         "completed replays recorded message",
			resp:         completed,
			wantAction:   dedupReplayResult,
			wantReplayTx: "已完成的回答",
		},
		{
			name:       "completed without a replayable body falls back honestly",
			resp:       completedNoBody,
			wantAction: dedupFallbackDuplicate,
		},
		{
			name:       "running keeps the client waiting on the ack",
			resp:       running,
			wantAction: dedupAckRunning,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			action, replayText := dedupHitDecision(tc.resp, tc.err)
			assert.Equal(t, tc.wantAction, action)
			assert.Equal(t, tc.wantReplayTx, replayText)
		})
	}
}

func TestDedupHitDecisionNeverReplaysBlankMessage(t *testing.T) {
	resp := &agentv1.GetRequestResultResponse{
		Status:  agentv1.RequestResultStatus_REQUEST_RESULT_COMPLETED,
		Message: "   \n  ",
	}
	action, replayText := dedupHitDecision(resp, nil)
	assert.Equal(t, dedupFallbackDuplicate, action, "whitespace-only body must not be replayed as a real answer")
	assert.Empty(t, replayText)
}

func TestBuildReplayChatResponsePayload(t *testing.T) {
	resp := buildReplayChatResponse("req-123", "session-abc", "trace-xyz", "最终回答全文")

	require.NotNil(t, resp.GetFullText())
	assert.Equal(t, "最终回答全文", resp.GetFullText(), "replay must carry the recorded answer verbatim as full_text")
	assert.Equal(t, "req-123", resp.GetRequestId(), "replay must reuse the original request_id")
	assert.Equal(t, "session-abc", resp.GetSessionId())
	assert.Equal(t, "trace-xyz", resp.GetTraceId())
	assert.Equal(t, agentv1.FinishReason_STOP, resp.GetFinishReason())
	assert.NotEmpty(t, resp.GetResponseId())
	assert.Positive(t, resp.GetCreatedAt())
	assert.Equal(t, "true", resp.GetMetadata()["is_replay"], "replay frames must be marked so clients/metrics can tell them apart")
	assert.True(t, resp.EventTime.IsValid())
}

func TestBuildReplayChatResponseNeverWrapsSanitizedPlaceholders(t *testing.T) {
	message := strings.Repeat("长回答", 500)
	resp := buildReplayChatResponse("req-1", "sess-1", "", message)
	assert.Len(t, resp.GetFullText(), len(message), "replay must not mutate the recorded body")
}
