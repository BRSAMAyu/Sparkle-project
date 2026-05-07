package handler

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	pbws "github.com/sparkle/gateway/gen/ws"
	"github.com/stretchr/testify/require"
	"google.golang.org/protobuf/proto"
)

func readTextEnvelope(t *testing.T, conn *websocket.Conn) map[string]interface{} {
	t.Helper()
	require.NoError(t, conn.SetReadDeadline(time.Now().Add(time.Second)))
	messageType, data, err := conn.ReadMessage()
	require.NoError(t, err)
	require.Equal(t, websocket.TextMessage, messageType)

	var envelope map[string]interface{}
	require.NoError(t, json.Unmarshal(data, &envelope))
	return envelope
}

func TestEnvelopeResponderWritesAllPayloadShapes(t *testing.T) {
	serverConn, clientConn, cleanup := newWSSafeWriterTestPair(t)
	defer cleanup()

	writer := newWSSafeWriter(serverConn, time.Second)
	defer writer.Close()
	responder := newEnvelopeResponder(writer, &wsEnvelopeIn{
		MessageID: "msg-1",
		RequestID: "req-1",
	}, context.Background())

	responder.SendAck()
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "ack")

	responder.SendError("invalid_argument", "bad payload", true)
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "message_nack")

	responder.SendActionStatus("action-1", "confirmed", map[string]interface{}{"widget_type": "plan_card"})
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "action_status")

	responder.SendToolResult(map[string]interface{}{"tool_name": "openclaw.run", "success": true})
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "tool_result")

	responder.SendInterventionAck("intervention-1", "ok", "saved")
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "intervention_feedback_ack")

	responder.SendResponseFeedbackAck("response-1", "ok", "thanks")
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "response_feedback_ack")

	responder.SendUpdateNodeMasteryAck("node-1", "v1", true)
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "ack_update_node_mastery")

	responder.SendUpdateNodeError("node-1", "v1", "stale")
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "error_update_node_mastery")

	require.NoError(t, responder.SendChatResponse(&agentv1.ChatResponse{ResponseId: "resp-1"}))
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "chat_response")

	require.NoError(t, responder.SendMeta(map[string]interface{}{"stream": "ready"}))
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "meta")

	responder.SendPlanReviewStatus("review-1", "approved", map[string]interface{}{"message": "done"})
	require.Contains(t, readTextEnvelope(t, clientConn)["payload"], "plan_review_status")
}

func TestProtobufResponderWritesAllPayloadShapes(t *testing.T) {
	serverConn, clientConn, cleanup := newWSSafeWriterTestPair(t)
	defer cleanup()

	writer := newWSSafeWriter(serverConn, time.Second)
	defer writer.Close()
	responder := newProtobufResponder(writer, &pbws.WebSocketMessage{
		Version:   "2.0",
		Type:      "chat",
		RequestId: "req-1",
		TraceId:   "trace-1",
	}, context.Background())

	readProto := func(wantType string) {
		t.Helper()
		require.NoError(t, clientConn.SetReadDeadline(time.Now().Add(time.Second)))
		messageType, data, err := clientConn.ReadMessage()
		require.NoError(t, err)
		require.Equal(t, websocket.BinaryMessage, messageType)
		var msg pbws.WebSocketMessage
		require.NoError(t, proto.Unmarshal(data, &msg))
		require.Equal(t, wantType, msg.Type)
		require.Equal(t, "req-1", msg.RequestId)
		require.Equal(t, "trace-1", msg.TraceId)
		require.NotNil(t, msg.EventTime)
	}

	responder.SendAck()
	readProto("ack")

	responder.SendError("timeout", "slow", false)
	readProto("message_nack")

	responder.SendActionStatus("action-1", "confirmed", nil)
	readProto("action_status")

	responder.SendToolResult(map[string]interface{}{"success": true})
	readProto("tool_result")

	responder.SendInterventionAck("request-1", "ok", "")
	readProto("intervention_feedback_ack")

	responder.SendResponseFeedbackAck("response-1", "failed", "try again")
	readProto("response_feedback_ack")

	responder.SendUpdateNodeMasteryAck("node-1", "v1", true)
	readProto("ack_update_node_mastery")

	responder.SendUpdateNodeError("node-1", "v1", "bad")
	readProto("error_update_node_mastery")

	require.NoError(t, responder.SendChatResponse(&agentv1.ChatResponse{ResponseId: "resp-1"}))
	readProto("chat_response")

	require.NoError(t, responder.SendMeta(map[string]interface{}{"phase": "test"}))
	readProto("meta")
}
