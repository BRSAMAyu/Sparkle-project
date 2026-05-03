package handler

import (
	"context"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/service"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestBuildExecutionSummaryToolResultPayload(t *testing.T) {
	payload := buildExecutionSummaryToolResultPayload(context.Background(), map[string]interface{}{
		"id":                    "record-1",
		"execution_intent_id":   "intent-1",
		"execution_status":      "succeeded",
		"requires_confirmation": false,
		"result_preview": map[string]interface{}{
			"summary": "workspace clean",
		},
	})

	if payload["tool_name"] != "openclaw.chat_control" {
		t.Fatalf("expected tool_name to be openclaw.chat_control, got %v", payload["tool_name"])
	}
	widgetData, ok := payload["widget_data"].(map[string]interface{})
	if !ok {
		t.Fatal("expected widget_data to be a map")
	}
	if widgetData["tool_result_id"] != "record-1" {
		t.Fatalf("expected tool_result_id to equal record id, got %v", widgetData["tool_result_id"])
	}
	if widgetData["summary"] != "workspace clean" {
		t.Fatalf("expected summary to be derived from result preview, got %v", widgetData["summary"])
	}
}

func TestSaveMessageTruncatedPersistsPartialResponse(t *testing.T) {
	// Regression test for ISSUE-20260503-1511-K2:
	// When gRPC stream breaks mid-response, the fix saves partial text
	// with truncated:true so multi-turn conversation history survives.
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	ch := service.NewChatHistoryService(rdb)
	defer ch.Stop()

	orch := &ChatOrchestrator{chatHistory: ch}
	ctx := context.Background()

	// Simulate the partial save the fix performs when stream breaks.
	orch.saveMessage(ctx, "test-user", "test-session", "assistant",
		"partial response text", map[string]interface{}{
			"trace_id":  "trace-abc",
			"truncated": true,
		})

	// Verify the truncated message was persisted and is retrievable.
	msgs, err := ch.GetMessages(ctx, "test-user", "test-session", 10, 0)
	require.NoError(t, err)
	require.Len(t, msgs, 1)

	assert.Equal(t, "assistant", msgs[0].Role)
	assert.Equal(t, "partial response text", msgs[0].Content)
}

func TestExtractErrorMessage(t *testing.T) {
	message := extractErrorMessage(map[string]interface{}{
		"detail": "pairing required",
	})
	if message != "pairing required" {
		t.Fatalf("expected detail message, got %q", message)
	}
}
