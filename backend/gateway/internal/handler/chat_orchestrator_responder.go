package handler

import (
	"context"
	"encoding/json"
	"log"
	"time"

	"github.com/gorilla/websocket"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	pbws "github.com/sparkle/gateway/gen/ws"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/timestamppb"
)

type envelopeResponder struct {
	conn     *websocket.Conn
	envelope *wsEnvelopeIn
	ctx      context.Context
}

func newEnvelopeResponder(conn *websocket.Conn, env *wsEnvelopeIn, ctx context.Context) *envelopeResponder {
	return &envelopeResponder{
		conn:     conn,
		envelope: env,
		ctx:      ctx,
	}
}

func (r *envelopeResponder) SendAck() {
	traceparent := traceparentFromContext(r.ctx)
	payload := map[string]json.RawMessage{}
	ack := map[string]interface{}{
		"request_id":  r.envelope.RequestID,
		"server_ts":   time.Now().UnixMilli(),
		"traceparent": traceparent,
	}
	raw, err := json.Marshal(ack)
	if err != nil {
		log.Printf("Failed to encode ack: %v", err)
		return
	}
	payload["ack"] = raw
	if err := r.writeEnvelope(payload, traceparent); err != nil {
		log.Printf("Failed to send ack: %v", err)
	}
}

func (r *envelopeResponder) SendError(code, message string, retryable bool) {
	payload := map[string]json.RawMessage{}
	enumCode := parseErrorCode(code)
	errBody := map[string]interface{}{
		"error_code": normalizeErrorCodeString(enumCode),
		"message":    message,
		"retryable":  retryable,
	}
	raw, err := json.Marshal(errBody)
	if err != nil {
		log.Printf("Failed to encode error: %v", err)
		return
	}
	payload["error"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send error: %v", err)
	}
}

func (r *envelopeResponder) SendActionStatus(actionID, status string, data map[string]interface{}) {
	payload := map[string]json.RawMessage{}
	statusMsg := map[string]interface{}{
		"action_id": actionID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}
	for k, v := range data {
		statusMsg[k] = v
	}
	raw, err := json.Marshal(statusMsg)
	if err != nil {
		log.Printf("Failed to encode action status: %v", err)
		return
	}
	payload["action_status"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send action status: %v", err)
	}
}

func (r *envelopeResponder) SendInterventionAck(requestID, status, message string) {
	payload := map[string]json.RawMessage{}
	ack := map[string]interface{}{
		"request_id": requestID,
		"status":     status,
		"timestamp":  time.Now().Unix(),
	}
	if message != "" {
		ack["message"] = message
	}
	raw, err := json.Marshal(ack)
	if err != nil {
		log.Printf("Failed to encode intervention ack: %v", err)
		return
	}
	payload["intervention_feedback_ack"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send intervention ack: %v", err)
	}
}

func (r *envelopeResponder) SendResponseFeedbackAck(responseID, status, message string) {
	payload := map[string]json.RawMessage{}
	ack := map[string]interface{}{
		"response_id": responseID,
		"status":      status,
		"timestamp":   time.Now().Unix(),
	}
	if message != "" {
		ack["message"] = message
	}
	raw, err := json.Marshal(ack)
	if err != nil {
		log.Printf("Failed to encode response feedback ack: %v", err)
		return
	}
	payload["response_feedback_ack"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send response feedback ack: %v", err)
	}
}

func (r *envelopeResponder) SendUpdateNodeMasteryAck(nodeID, version string, success bool) {
	payload := map[string]json.RawMessage{}
	body := map[string]interface{}{
		"node_id":   nodeID,
		"version":   version,
		"success":   success,
		"timestamp": time.Now().Unix(),
	}
	raw, err := json.Marshal(body)
	if err != nil {
		log.Printf("Failed to encode mastery ack: %v", err)
		return
	}
	payload["ack_update_node_mastery"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send mastery ack: %v", err)
	}
}

func (r *envelopeResponder) SendUpdateNodeError(nodeID, version, message string) {
	payload := map[string]json.RawMessage{}
	body := map[string]interface{}{
		"nodeId":  nodeID,
		"version": version,
		"error":   message,
	}
	raw, err := json.Marshal(body)
	if err != nil {
		log.Printf("Failed to encode mastery error: %v", err)
		return
	}
	payload["error_update_node_mastery"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send mastery error: %v", err)
	}
}

func (r *envelopeResponder) SendChatResponse(resp *agentv1.ChatResponse) error {
	raw, err := protojson.Marshal(resp)
	if err != nil {
		return err
	}
	payload := map[string]json.RawMessage{
		"chat_response": raw,
	}
	return r.writeEnvelope(payload, traceparentFromContext(r.ctx))
}

func (r *envelopeResponder) SendMeta(meta map[string]interface{}) error {
	raw, err := json.Marshal(meta)
	if err != nil {
		return err
	}
	payload := map[string]json.RawMessage{
		"meta": raw,
	}
	return r.writeEnvelope(payload, traceparentFromContext(r.ctx))
}

func (r *envelopeResponder) SendPlanReviewStatus(reviewID, status string, data map[string]interface{}) {
	statusMsg := map[string]interface{}{
		"review_id": reviewID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}
	for k, v := range data {
		statusMsg[k] = v
	}
	raw, _ := json.Marshal(statusMsg)
	payload := map[string]json.RawMessage{
		"plan_review_status": raw,
	}
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send plan review status: %v", err)
	} else {
		log.Printf("✅ Plan review status sent: status=%s, review_id=%s", status, reviewID)
	}
}

func (r *envelopeResponder) writeEnvelope(payload map[string]json.RawMessage, traceparent string) error {
	envOut := wsEnvelopeOut{
		Traceparent: traceparent,
		MessageID:   r.envelope.MessageID,
		RequestID:   r.envelope.RequestID,
		Payload:     payload,
	}
	data, err := json.Marshal(envOut)
	if err != nil {
		return err
	}
	return r.conn.WriteMessage(websocket.TextMessage, data)
}

// protobufResponder implements the responder interfaces for Binary/Protobuf protocol
type protobufResponder struct {
	conn *websocket.Conn
	msg  *pbws.WebSocketMessage
	ctx  context.Context
}

func newProtobufResponder(conn *websocket.Conn, msg *pbws.WebSocketMessage, ctx context.Context) *protobufResponder {
	return &protobufResponder{
		conn: conn,
		msg:  msg,
		ctx:  ctx,
	}
}

func (r *protobufResponder) SendAck() {
	// For P2, we can define a dedicated Ack message or just use status
	// Using generic WebSocketMessage for Ack
	// Payload could be empty or a simple status proto
	r.sendProto("ack", nil)
}

func (r *protobufResponder) SendError(code, message string, retryable bool) {
	// TODO: Define Error proto in websocket.proto
	// For now, sending JSON error inside protobuf wrapper to be compatible with clients expecting structured error
	enumCode := parseErrorCode(code)
	errBody := map[string]interface{}{
		"error_code": normalizeErrorCodeString(enumCode),
		"message":    message,
		"retryable":  retryable,
	}
	raw, _ := json.Marshal(errBody)
	r.sendProto("error", raw)
}

func (r *protobufResponder) SendActionStatus(actionID, status string, data map[string]interface{}) {
	statusMsg := map[string]interface{}{
		"action_id": actionID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}
	for k, v := range data {
		statusMsg[k] = v
	}
	raw, _ := json.Marshal(statusMsg)
	r.sendProto("action_status", raw)
}

func (r *protobufResponder) SendInterventionAck(requestID, status, message string) {
	ack := map[string]interface{}{
		"request_id": requestID,
		"status":     status,
		"timestamp":  time.Now().Unix(),
	}
	if message != "" {
		ack["message"] = message
	}
	raw, _ := json.Marshal(ack)
	r.sendProto("intervention_feedback_ack", raw)
}

func (r *protobufResponder) SendResponseFeedbackAck(responseID, status, message string) {
	ack := map[string]interface{}{
		"response_id": responseID,
		"status":      status,
		"timestamp":   time.Now().Unix(),
	}
	if message != "" {
		ack["message"] = message
	}
	raw, _ := json.Marshal(ack)
	r.sendProto("response_feedback_ack", raw)
}

func (r *protobufResponder) SendUpdateNodeMasteryAck(nodeID, version string, success bool) {
	body := map[string]interface{}{
		"node_id":   nodeID,
		"version":   version,
		"success":   success,
		"timestamp": time.Now().Unix(),
	}
	raw, _ := json.Marshal(body)
	r.sendProto("ack_update_node_mastery", raw)
}

func (r *protobufResponder) SendUpdateNodeError(nodeID, version, message string) {
	body := map[string]interface{}{
		"nodeId":  nodeID,
		"version": version,
		"error":   message,
	}
	raw, _ := json.Marshal(body)
	r.sendProto("error_update_node_mastery", raw)
}

func (r *protobufResponder) SendChatResponse(resp *agentv1.ChatResponse) error {
	// Marshal the ChatResponse to bytes
	payload, err := proto.Marshal(resp)
	if err != nil {
		return err
	}
	return r.sendProto("chat_response", payload)
}

func (r *protobufResponder) SendMeta(meta map[string]interface{}) error {
	raw, err := json.Marshal(meta)
	if err != nil {
		return err
	}
	return r.sendProto("meta", raw)
}

func (r *protobufResponder) sendProto(msgType string, payload []byte) error {
	now := time.Now()
	resp := &pbws.WebSocketMessage{
		Version:   "2.0",
		Type:      msgType,
		Payload:   payload,
		TraceId:   r.msg.TraceId,
		RequestId: r.msg.RequestId,
		Timestamp: now.UnixMilli(),
		EventTime: timestamppb.New(now),
	}
	data, err := proto.Marshal(resp)
	if err != nil {
		return err
	}
	return r.conn.WriteMessage(websocket.BinaryMessage, data)
}
