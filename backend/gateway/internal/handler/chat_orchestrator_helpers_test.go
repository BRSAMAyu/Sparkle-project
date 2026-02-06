package handler

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"google.golang.org/protobuf/types/known/timestamppb"
)

func TestParseEnvelopeJSONAndPayloadType(t *testing.T) {
	raw := []byte(`{"traceparent":"00-abc-def-01","payload":{"chat_request":{"session_id":"s1","message":"hi"}}}`)
	env, ok := parseEnvelopeJSON(raw)
	if !ok {
		t.Fatal("expected envelope to parse")
	}
	if env == nil || env.Payload == nil {
		t.Fatal("expected payload map")
	}
	msgType := envelopePayloadType(env.Payload)
	if msgType != "chat_request" {
		t.Fatalf("unexpected payload type: %s", msgType)
	}
}

func TestDecodePayloadMap(t *testing.T) {
	valid := json.RawMessage(`{"action_id":"a1","status":"ok"}`)
	msgMap, err := decodePayloadMap(valid)
	if err != nil {
		t.Fatalf("decodePayloadMap returned error: %v", err)
	}
	if msgMap["action_id"] != "a1" {
		t.Fatalf("unexpected action_id: %#v", msgMap["action_id"])
	}

	invalid := json.RawMessage(`{"action_id":`)
	if _, err := decodePayloadMap(invalid); err == nil {
		t.Fatal("expected error for invalid JSON payload")
	}
}

func TestEnvelopePayloadTypePlanReviewFeedback(t *testing.T) {
	raw := []byte(`{"payload":{"plan_review_feedback":{"review_id":"r1","user_decision":"approved"}}}`)
	env, ok := parseEnvelopeJSON(raw)
	if !ok {
		t.Fatal("expected envelope to parse")
	}
	if got := envelopePayloadType(env.Payload); got != "plan_review_feedback" {
		t.Fatalf("unexpected payload type: %s", got)
	}
}

func TestDecodeChatRequestEnvelopeProtoJSON(t *testing.T) {
	var input chatInput
	raw := json.RawMessage(`{
		"sessionId":"session-1",
		"chatMode":"default",
		"includeReferences":true,
		"fileIds":["f1","f2"],
		"userProfile":{"nickname":"tester"},
		"message":"hello world",
		"extraContext":{"plan_id":"p1"}
	}`)
	if err := decodeChatRequestEnvelope(raw, &input); err != nil {
		t.Fatalf("decodeChatRequestEnvelope returned error: %v", err)
	}
	if input.Message != "hello world" {
		t.Fatalf("unexpected message: %q", input.Message)
	}
	if input.SessionID != "session-1" {
		t.Fatalf("unexpected session id: %q", input.SessionID)
	}
	if input.Nickname != "tester" {
		t.Fatalf("unexpected nickname: %q", input.Nickname)
	}
	if len(input.FileIds) != 2 {
		t.Fatalf("unexpected file ids: %#v", input.FileIds)
	}
	if !input.IncludeReferences {
		t.Fatal("expected include references to be true")
	}
	if got := input.ExtraContext["plan_id"]; got != "p1" {
		t.Fatalf("unexpected extra context plan_id: %#v", got)
	}
}

func TestDecodeChatRequestEnvelopeRejectsInvalidShape(t *testing.T) {
	var input chatInput
	raw := json.RawMessage(`{"message":{"text":"bad-shape"}}`)
	if err := decodeChatRequestEnvelope(raw, &input); err == nil {
		t.Fatal("expected error for invalid chat_request payload shape")
	}
}

func TestGetEnvInt64FallbackAndParse(t *testing.T) {
	t.Setenv("TEST_STREAM_SEGMENT", "256")
	if got := getEnvInt64("TEST_STREAM_SEGMENT", 123); got != 256 {
		t.Fatalf("unexpected parsed value: %d", got)
	}

	t.Setenv("TEST_STREAM_SEGMENT", "bad")
	if got := getEnvInt64("TEST_STREAM_SEGMENT", 123); got != 123 {
		t.Fatalf("expected fallback for invalid value, got: %d", got)
	}

	t.Setenv("TEST_STREAM_SEGMENT", "")
	if got := getEnvInt64("TEST_STREAM_SEGMENT", 123); got != 123 {
		t.Fatalf("expected fallback for empty value, got: %d", got)
	}
}

func TestExtractTraceContextFromEnvelopeRejectsOversizedTraceparent(t *testing.T) {
	env := &wsEnvelopeIn{
		Traceparent: "00-" + strings.Repeat("a", maxTraceparentLen+1) + "-01",
	}
	ctx := context.WithValue(context.Background(), "sentinel", "ok")
	got := extractTraceContextFromEnvelope(ctx, env)
	if got == nil {
		t.Fatal("expected non-nil context")
	}
	if got.Value("sentinel") != "ok" {
		t.Fatal("expected original context to remain unchanged")
	}
}

func TestResponseEventTimeMillisPrefersEventTime(t *testing.T) {
	t.Setenv("PROTO_READ_NEW_FIRST", "true")
	now := time.Now().UTC().Truncate(time.Millisecond)
	resp := &agentv1.ChatResponse{
		Timestamp: 123,
		EventTime: timestamppb.New(now),
	}
	got := responseEventTimeMillis(resp)
	if got != now.UnixMilli() {
		t.Fatalf("expected event_time millis %d, got %d", now.UnixMilli(), got)
	}
}

func TestResponseEventTimeMillisCanPreferLegacyTimestamp(t *testing.T) {
	t.Setenv("PROTO_READ_NEW_FIRST", "false")
	now := time.Now().UTC().Truncate(time.Millisecond)
	resp := &agentv1.ChatResponse{
		Timestamp: 456,
		EventTime: timestamppb.New(now),
	}
	got := responseEventTimeMillis(resp)
	if got != 456 {
		t.Fatalf("expected legacy timestamp 456, got %d", got)
	}
}

func TestParseErrorCode(t *testing.T) {
	if got := parseErrorCode("resource_exhausted"); got != agentv1.ErrorCode_ERROR_CODE_RATE_LIMITED {
		t.Fatalf("unexpected mapped error code: %v", got)
	}
	if got := parseErrorCode("INTERNAL_ERROR"); got != agentv1.ErrorCode_ERROR_CODE_INTERNAL {
		t.Fatalf("unexpected mapped error code: %v", got)
	}
	if got := parseErrorCode("non_standard"); got != agentv1.ErrorCode_ERROR_CODE_UNSPECIFIED {
		t.Fatalf("unexpected mapped error code: %v", got)
	}
}
