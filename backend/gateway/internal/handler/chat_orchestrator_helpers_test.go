package handler

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgtype"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/service"
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

func TestParseEnvelopeJSONAndPayloadTypeToolResult(t *testing.T) {
	raw := []byte(`{"payload":{"tool_result":{"tool_call_id":"call-1","tool_name":"openclaw.run","result_json":"{\"ok\":true}"}}}`)
	env, ok := parseEnvelopeJSON(raw)
	if !ok {
		t.Fatal("expected tool_result envelope to parse")
	}
	if got := envelopePayloadType(env.Payload); got != "tool_result" {
		t.Fatalf("unexpected payload type: %s", got)
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
		"activeTools":["search","plan"],
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
	if len(input.ActiveTools) != 2 {
		t.Fatalf("unexpected active tools: %#v", input.ActiveTools)
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

func TestDecodeChatRequestEnvelopeToolResultProtoJSON(t *testing.T) {
	var input chatInput
	raw := json.RawMessage(`{
		"sessionId":"session-2",
		"requestId":"req-2",
		"chatMode":"default",
		"toolResult":{
			"toolCallId":"call-2",
			"toolName":"openclaw.run",
			"resultJson":"{\"success\":true}",
			"isError":false,
			"errorMessage":""
		}
	}`)
	if err := decodeChatRequestEnvelope(raw, &input); err != nil {
		t.Fatalf("decodeChatRequestEnvelope returned error: %v", err)
	}
	if !input.IsToolResult {
		t.Fatal("expected tool result input")
	}
	if input.ToolCallID != "call-2" {
		t.Fatalf("unexpected tool call id: %q", input.ToolCallID)
	}
	if input.ToolName != "openclaw.run" {
		t.Fatalf("unexpected tool name: %q", input.ToolName)
	}
	if input.ToolResultJSON != "{\"success\":true}" {
		t.Fatalf("unexpected tool result json: %q", input.ToolResultJSON)
	}
	if input.RequestID != "req-2" {
		t.Fatalf("unexpected request id: %q", input.RequestID)
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
	now := time.Now().UTC().Truncate(time.Millisecond)
	resp := &agentv1.ChatResponse{
		EventTime: timestamppb.New(now),
	}
	got := responseEventTimeMillis(resp)
	if got != now.UnixMilli() {
		t.Fatalf("expected event_time millis %d, got %d", now.UnixMilli(), got)
	}
}

func TestResponseEventTimeMillisReturnsZeroForMissingEventTime(t *testing.T) {
	got := responseEventTimeMillis(&agentv1.ChatResponse{})
	if got != 0 {
		t.Fatalf("expected 0 for missing event_time, got %d", got)
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

func TestBuildAgentUserProfileUsesResolvedSnapshot(t *testing.T) {
	profile := buildAgentUserProfile(
		"input-nickname",
		`{"focus":true}`,
		&service.ChatUserProfileSnapshot{
			Nickname:  "stored-nickname",
			Timezone:  "America/Los_Angeles",
			Language:  "en-US",
			IsPro:     true,
			Level:     6,
			AvatarURL: "https://example.com/avatar.png",
			Preferences: map[string]string{
				"depth_preference":     "0.30",
				"curiosity_preference": "0.80",
				"photon_balance":       "42",
			},
		},
		nil,
	)

	if profile.Nickname != "stored-nickname" {
		t.Fatalf("unexpected nickname: %q", profile.Nickname)
	}
	if profile.Timezone != "America/Los_Angeles" {
		t.Fatalf("unexpected timezone: %q", profile.Timezone)
	}
	if profile.Language != "en-US" {
		t.Fatalf("unexpected language: %q", profile.Language)
	}
	if !profile.IsPro {
		t.Fatal("expected is_pro to be true")
	}
	if profile.Level != 6 {
		t.Fatalf("unexpected level: %d", profile.Level)
	}
	if profile.AvatarUrl != "https://example.com/avatar.png" {
		t.Fatalf("unexpected avatar: %q", profile.AvatarUrl)
	}
	if profile.Preferences["photon_balance"] != "42" {
		t.Fatalf("unexpected preferences: %#v", profile.Preferences)
	}
	if profile.ExtraContext != `{"focus":true}` {
		t.Fatalf("unexpected extra context: %q", profile.ExtraContext)
	}
}

func TestBuildAgentUserProfileFallsBackToResolvedUser(t *testing.T) {
	profile := buildAgentUserProfile(
		"",
		"",
		nil,
		&db.User{
			Username:   "fallback-user",
			Nickname:   pgtype.Text{String: "fallback-nickname", Valid: true},
			AvatarUrl:  pgtype.Text{String: "https://example.com/fallback.png", Valid: true},
			FlameLevel: 4,
		},
	)

	if profile.Nickname != "fallback-nickname" {
		t.Fatalf("unexpected fallback nickname: %q", profile.Nickname)
	}
	if profile.AvatarUrl != "https://example.com/fallback.png" {
		t.Fatalf("unexpected fallback avatar: %q", profile.AvatarUrl)
	}
	if profile.Level != 4 {
		t.Fatalf("unexpected fallback level: %d", profile.Level)
	}
	if !profile.IsPro {
		t.Fatal("expected fallback is_pro to be true")
	}
	if profile.Timezone != "Asia/Shanghai" {
		t.Fatalf("unexpected fallback timezone: %q", profile.Timezone)
	}
}
