package handler

import (
	"bytes"
	"fmt"
	"testing"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/structpb"
)

func TestProtoSerializationChatResponseDeltaRoundTrip(t *testing.T) {
	original := &agentv1.ChatResponse{
		ResponseId:   "resp-1",
		RequestId:    "req-1",
		FinishReason: agentv1.FinishReason_STOP,
		Content: &agentv1.ChatResponse_Delta{
			Delta: "hello",
		},
	}

	wire, err := proto.Marshal(original)
	require.NoError(t, err)

	var restored agentv1.ChatResponse
	require.NoError(t, proto.Unmarshal(wire, &restored))
	assert.Equal(t, "hello", restored.GetDelta())
	assert.Equal(t, agentv1.FinishReason_STOP, restored.GetFinishReason())
}

func TestProtoSerializationChatRequestToolResultOneofRoundTrip(t *testing.T) {
	original := &agentv1.ChatRequest{
		UserId:    "user-1",
		SessionId: "session-1",
		Input: &agentv1.ChatRequest_ToolResult{
			ToolResult: &agentv1.ToolResult{
				ToolCallId: "tool-1",
				ToolName:   "search",
				ResultJson: `{"items":1}`,
			},
		},
	}

	wire, err := proto.Marshal(original)
	require.NoError(t, err)

	var restored agentv1.ChatRequest
	require.NoError(t, proto.Unmarshal(wire, &restored))
	require.NotNil(t, restored.GetToolResult())
	assert.Equal(t, "search", restored.GetToolResult().GetToolName())
	assert.Empty(t, restored.GetMessage())
}

func TestProtoSerializationChatResponseAllFinishReasons(t *testing.T) {
	jsonOptions := protojson.MarshalOptions{
		UseProtoNames: true,
	}
	validFinishReasons := []agentv1.FinishReason{
		agentv1.FinishReason_NULL,
		agentv1.FinishReason_STOP,
		agentv1.FinishReason_LENGTH,
		agentv1.FinishReason_TOOL_CALLS,
		agentv1.FinishReason_CONTENT_FILTER,
		agentv1.FinishReason_ERROR,
		agentv1.FinishReason_CONTINUE,
	}

	for _, reason := range validFinishReasons {
		t.Run(reason.String(), func(t *testing.T) {
			response := &agentv1.ChatResponse{
				ResponseId:   "resp-finish",
				FinishReason: reason,
				Content: &agentv1.ChatResponse_ToolResult{
					ToolResult: &agentv1.ToolResultPayload{
						ToolName:   "search",
						Success:    true,
						Data:       mustStructPB(t, map[string]interface{}{"items": 1}),
						WidgetType: "execution_summary",
					},
				},
			}

			wire, err := proto.Marshal(response)
			require.NoError(t, err)

			var restored agentv1.ChatResponse
			require.NoError(t, proto.Unmarshal(wire, &restored))
			assert.Equal(t, reason, restored.GetFinishReason())

			jsonWire, err := jsonOptions.Marshal(response)
			require.NoError(t, err)
			if reason == agentv1.FinishReason_NULL {
				assert.False(t, bytes.Contains(jsonWire, []byte(`"finish_reason"`)))
				return
			}
			assert.True(t, bytes.Contains(jsonWire, []byte(fmt.Sprintf(`"finish_reason":"%s"`, reason.String()))))
		})
	}
}

func mustStructPB(t *testing.T, data map[string]interface{}) *structpb.Struct {
	t.Helper()
	msg, err := structpb.NewStruct(data)
	require.NoError(t, err)
	return msg
}
