package handler

import (
	"context"
	"testing"
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

func TestExtractErrorMessage(t *testing.T) {
	message := extractErrorMessage(map[string]interface{}{
		"detail": "pairing required",
	})
	if message != "pairing required" {
		t.Fatalf("expected detail message, got %q", message)
	}
}
