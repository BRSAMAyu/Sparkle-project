package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/google/uuid"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	pbws "github.com/sparkle/gateway/gen/ws"
	wsmetrics "github.com/sparkle/gateway/internal/metrics"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/timestamppb"
)

// jsonMetadataKeys lists metadata keys whose values are JSON-serialized objects.
// Proto map<string,string> forces all values to strings; these are decoded back
// to structured objects so Flutter receives them as Maps.
var jsonMetadataKeys = map[string]bool{
	"collaboration_timeline": true,
	"review_data":            true,
	"state_change_event":     true,
	"visualization":          true,
	"selected_experts":       true,
	"answer_experts":         true,
	"routing_strategy":       true,
	"fallback_reason":        true,
	"route_confidence":       true,
	"expert_entry_source":    true,
	"ux_turn":                true,
	"ux_progress":            true,
	"ux_result":              true,
	"ux_followthrough":       true,
	"ux_sources":             true,
	"ux_evolution":           true,
	"execution_progress":     true,
	"continuity_banner":      true,
	"mode_explanation":       true,
	"collaboration_summary":  true,
}

// convertResponseToJSON converts protobuf ChatResponse to JSON-serializable map
func convertResponseToJSON(resp *agentv1.ChatResponse) map[string]interface{} {
	metadata := map[string]interface{}{}
	for key, value := range resp.Metadata {
		if jsonMetadataKeys[key] {
			trimmed := strings.TrimSpace(value)
			if trimmed == "" {
				metadata[key] = value
				continue
			}
			if !strings.HasPrefix(trimmed, "{") && !strings.HasPrefix(trimmed, "[") {
				metadata[key] = value
				continue
			}
			var decoded interface{}
			if err := json.Unmarshal([]byte(value), &decoded); err == nil {
				metadata[key] = decoded
			} else {
				log.Printf("Failed to decode metadata key %s: %v", key, err)
				metadata[key] = value
			}
			continue
		}
		metadata[key] = value
	}

	result := map[string]interface{}{
		"response_id":    resp.ResponseId,
		"created_at":     resp.CreatedAt,
		"request_id":     resp.RequestId,
		"trace_id":       resp.TraceId,
		"workflow_id":    resp.WorkflowId,
		"prompt_version": resp.PromptVersion,
		"session_id":     resp.SessionId, // Use proto field directly
		"metadata":       metadata,
	}
	if ts := responseEventTimeMillis(resp); ts > 0 {
		result["event_time"] = ts
		wsmetrics.ProtoFieldReadTotal.WithLabelValues("chat_response.event_time", "new").Inc()
	}

	// Handle oneof content field
	switch content := resp.Content.(type) {
	case *agentv1.ChatResponse_Delta:
		result["type"] = "delta"
		result["delta"] = sanitizer.Sanitize(content.Delta)
	case *agentv1.ChatResponse_ToolCall:
		result["type"] = "tool_call"
		result["tool_call"] = map[string]interface{}{
			"id":        content.ToolCall.Id,
			"name":      content.ToolCall.Name,
			"arguments": content.ToolCall.Arguments,
		}
	case *agentv1.ChatResponse_StatusUpdate:
		result["type"] = "status_update"
		if _, ok := metadata["ux_progress"]; !ok {
			metadata["ux_progress"] = deriveUXProgress(content.StatusUpdate.State.String(), sanitizer.Sanitize(content.StatusUpdate.Details))
		}
		result["status"] = map[string]interface{}{
			"state":              content.StatusUpdate.State.String(),
			"details":            sanitizer.Sanitize(content.StatusUpdate.Details),
			"current_agent_name": sanitizer.Sanitize(content.StatusUpdate.CurrentAgentName),
			"active_agent":       content.StatusUpdate.ActiveAgent.String(),
		}
	case *agentv1.ChatResponse_FullText:
		result["type"] = "full_text"
		result["full_text"] = sanitizer.Sanitize(content.FullText)
	case *agentv1.ChatResponse_Error:
		result["type"] = "error"
		enumCode := normalizeErrorCodeString(content.Error.ErrorCode)
		if enumCode == "" {
			wsmetrics.ProtoErrorCodeFallbackTotal.WithLabelValues("enum_missing").Inc()
		}
		errorBody := map[string]interface{}{
			"error_code": enumCode,
			"message":    content.Error.Message,
			"retryable":  content.Error.Retryable,
		}
		result["error"] = errorBody
	case *agentv1.ChatResponse_Usage:
		result["type"] = "usage"
		result["usage"] = map[string]interface{}{
			"prompt_tokens":     content.Usage.PromptTokens,
			"completion_tokens": content.Usage.CompletionTokens,
			"total_tokens":      content.Usage.TotalTokens,
			"cost_micro_usd":    content.Usage.CostMicroUsd,
		}
	case *agentv1.ChatResponse_Citations:
		result["type"] = "citations"
		citations := make([]map[string]interface{}, len(content.Citations.Citations))
		for i, c := range content.Citations.Citations {
			citations[i] = map[string]interface{}{
				"id":            c.Id,
				"title":         c.Title,
				"content":       c.Content,
				"source_type":   c.SourceType,
				"score":         c.Score,
				"url":           c.Url,
				"file_id":       c.FileId,
				"page_number":   c.PageNumber,
				"chunk_index":   c.ChunkIndex,
				"section_title": c.SectionTitle,
			}
		}
		result["citations"] = citations
		if _, ok := metadata["ux_sources"]; !ok {
			metadata["ux_sources"] = buildSourceSummary(citations)
		}
	case *agentv1.ChatResponse_ToolResult:
		result["type"] = "tool_result"
		tool := content.ToolResult
		data := map[string]interface{}{}
		if tool.Data != nil {
			data = tool.Data.AsMap()
		}
		widgetData := map[string]interface{}{}
		if tool.WidgetData != nil {
			widgetData = tool.WidgetData.AsMap()
		}
		widgetType := tool.WidgetType
		if widgetType == "" {
			widgetType = "execution_summary"
		}
		if len(widgetData) == 0 {
			widgetData = buildExecutionSummaryWidget(tool.ToolName, tool.Success, data, tool.ErrorMessage, tool.Suggestion, tool.ToolCallId)
		} else if widgetType == "execution_summary" {
			merged := buildExecutionSummaryWidget(tool.ToolName, tool.Success, data, tool.ErrorMessage, tool.Suggestion, tool.ToolCallId)
			for k, v := range widgetData {
				merged[k] = v
			}
			widgetData = merged
		}
		result["tool_result"] = map[string]interface{}{
			"tool_name":     tool.ToolName,
			"success":       tool.Success,
			"data":          data,
			"error_message": tool.ErrorMessage,
			"suggestion":    tool.Suggestion,
			"widget_type":   widgetType,
			"widget_data":   widgetData,
			"tool_call_id":  tool.ToolCallId,
		}
	case *agentv1.ChatResponse_Intervention:
		result["type"] = "intervention"
		payload := content.Intervention
		req := payload.GetRequest()
		intervention := map[string]interface{}{}
		if req != nil {
			reason := map[string]interface{}{}
			if req.Reason != nil {
				evidence := make([]map[string]interface{}, 0, len(req.Reason.EvidenceRefs))
				for _, ref := range req.Reason.EvidenceRefs {
					evidence = append(evidence, map[string]interface{}{
						"type":           ref.Type,
						"id":             ref.Id,
						"schema_version": ref.SchemaVersion,
						"user_deleted":   ref.UserDeleted,
					})
				}
				reason = map[string]interface{}{
					"trigger_event_id": req.Reason.TriggerEventId,
					"explanation_text": req.Reason.ExplanationText,
					"confidence":       req.Reason.Confidence,
					"evidence_refs":    evidence,
					"decision_trace":   req.Reason.DecisionTrace,
				}
			}
			contentMap := map[string]interface{}{}
			if req.Content != nil {
				contentMap = req.Content.AsMap()
			}
			cooldown := map[string]interface{}{}
			if req.OnReject != nil {
				cooldown = map[string]interface{}{
					"policy":   req.OnReject.Policy,
					"until_ms": req.OnReject.UntilMs,
				}
			}
			intervention = map[string]interface{}{
				"id":                  req.Id,
				"dedupe_key":          req.DedupeKey,
				"topic":               req.Topic,
				"created_at_ms":       req.CreatedAtMs,
				"expires_at_ms":       req.ExpiresAtMs,
				"is_retractable":      req.IsRetractable,
				"supersedes_id":       req.SupersedesId,
				"schema_version":      req.SchemaVersion,
				"policy_version":      req.PolicyVersion,
				"model_version":       req.ModelVersion,
				"reason":              reason,
				"level":               req.Level.String(),
				"on_reject":           cooldown,
				"content":             contentMap,
				"user_visible_reason": reason["explanation_text"],
				"reversible":          req.IsRetractable,
				"primary_action":      contentMap["primary_action"],
				"secondary_action":    contentMap["secondary_action"],
			}
		}
		result["intervention"] = intervention
	default:
		// Finish-only responses are terminal stream markers for WebSocket clients.
		if resp.FinishReason != agentv1.FinishReason_NULL {
			result["type"] = "done"
		} else if _, hasType := result["type"]; !hasType {
			// If no content field is set, add type "metadata" for responses with only metadata
			result["type"] = "metadata"
		}
	}

	if resp.FinishReason != agentv1.FinishReason_NULL {
		result["finish_reason"] = resp.FinishReason.String()
		metadata["done"] = true
	}

	return result
}

func deriveUXProgress(state string, details string) map[string]interface{} {
	stage := "understanding"
	headline := "我先理解你的问题"
	blocked := false

	switch state {
	case "THINKING":
		stage = "planning"
		headline = "我在整理你的目标和思路"
	case "SEARCHING":
		stage = "retrieving"
		headline = "我在查找相关依据和上下文"
	case "EXECUTING_TOOL":
		stage = "executing"
		headline = "我在替你执行需要的步骤"
	case "GENERATING":
		stage = "answering"
		headline = "我在组织最终回答"
	case "IDLE":
		stage = "answering"
		headline = "这轮处理已经完成"
	}

	if strings.Contains(details, "等待") || strings.Contains(details, "确认") || strings.Contains(details, "补充") {
		blocked = true
	}

	return map[string]interface{}{
		"stage":      stage,
		"headline":   headline,
		"detail":     details,
		"is_blocked": blocked,
	}
}

func buildExecutionSummaryWidget(toolName string, success bool, data map[string]interface{}, errorMessage string, suggestion string, toolCallID string) map[string]interface{} {
	state := "success"
	headline := fmt.Sprintf("%s 已执行", toolName)
	impact := "已更新相关结果。"
	if !success {
		state = "failed"
		headline = fmt.Sprintf("%s 执行失败", toolName)
		impact = "这一步没有成功完成，结果可能部分受影响。"
	} else if len(data) == 0 {
		state = "partial"
		impact = "执行已完成，但暂时没有返回可展示的详细对象。"
	}

	affected := make([]string, 0, minInt(3, len(data)))
	for key := range data {
		affected = append(affected, key)
		if len(affected) >= 3 {
			break
		}
	}

	nextAction := "继续查看最终回答"
	if !success {
		nextAction = "补充信息后重试，或换一种方式继续"
	} else if suggestion != "" {
		nextAction = suggestion
	}

	return map[string]interface{}{
		"title":            headline,
		"tool_name":        toolName,
		"status":           state,
		"impact_summary":   impact,
		"affected_objects": affected,
		"next_action":      nextAction,
		"error_message":    errorMessage,
		"execution_id":     toolCallID,
		"reversible":       false,
	}
}

func buildSourceSummary(citations []map[string]interface{}) map[string]interface{} {
	scope := "mixed"
	if len(citations) == 0 {
		scope = "none"
	}
	if len(citations) > 0 {
		fileOnly := true
		for _, cite := range citations {
			if cite["file_id"] == "" || cite["file_id"] == nil {
				fileOnly = false
				break
			}
		}
		if fileOnly {
			scope = "file_only"
		}
	}

	summary := "本轮回答带有可展开的依据来源。"
	if len(citations) == 0 {
		summary = "本轮回答没有附带可展开的引用来源。"
	}

	return map[string]interface{}{
		"citations_available": len(citations) > 0,
		"reference_scope":     scope,
		"evidence_summary":    summary,
		"citations":           citations,
	}
}

func minInt(a int, b int) int {
	if a < b {
		return a
	}
	return b
}

func parseEnvelopeJSON(msg []byte) (*wsEnvelopeIn, bool) {
	raw := map[string]json.RawMessage{}
	if err := json.Unmarshal(msg, &raw); err != nil {
		return nil, false
	}
	payloadRaw, ok := raw["payload"]
	if !ok {
		return nil, false
	}
	payload := map[string]json.RawMessage{}
	if err := json.Unmarshal(payloadRaw, &payload); err != nil {
		return nil, false
	}
	if len(payload) == 0 {
		return nil, false
	}
	env := &wsEnvelopeIn{}
	if err := json.Unmarshal(msg, env); err != nil {
		return nil, false
	}
	env.Payload = payload
	env.Raw = raw
	return env, true
}

func envelopePayloadType(payload map[string]json.RawMessage) string {
	switch {
	case payload["chat_request"] != nil:
		return "chat_request"
	case payload["tool_result"] != nil:
		return "tool_result"
	case payload["action_feedback"] != nil:
		return "action_feedback"
	case payload["focus_completed"] != nil:
		return "focus_completed"
	case payload["update_node_mastery"] != nil:
		return "update_node_mastery"
	case payload["intervention_feedback"] != nil:
		return "intervention_feedback"
	case payload["response_feedback"] != nil:
		return "response_feedback"
	case payload["plan_review_feedback"] != nil:
		return "plan_review_feedback"
	default:
		return ""
	}
}

func decodePayloadMap(raw json.RawMessage) (map[string]interface{}, error) {
	msgMap := make(map[string]interface{})
	if err := json.Unmarshal(raw, &msgMap); err != nil {
		return nil, err
	}
	return msgMap, nil
}

func decodeChatRequestEnvelope(raw json.RawMessage, input *chatInput) error {
	var req agentv1.ChatRequest
	if err := protojson.Unmarshal(raw, &req); err != nil {
		return err
	}
	switch content := req.GetInput().(type) {
	case *agentv1.ChatRequest_Message:
		input.Message = content.Message
	case *agentv1.ChatRequest_ToolResult:
		if content.ToolResult != nil {
			tr := content.ToolResult
			input.IsToolResult = true
			input.ToolCallID = tr.GetToolCallId()
			input.ToolName = tr.GetToolName()
			input.ToolResultJSON = tr.GetResultJson()
			input.ToolIsError = tr.GetIsError()
			input.ToolErrorMsg = tr.GetErrorMessage()
		}
	default:
		return fmt.Errorf("unsupported chat_request input")
	}
	input.SessionID = req.GetSessionId()
	input.RequestID = req.GetRequestId()
	input.ChatMode = req.GetChatMode()
	input.Nickname = req.GetUserProfile().GetNickname()
	input.FileIds = req.GetFileIds()
	input.IncludeReferences = req.GetIncludeReferences()
	if extra := req.GetExtraContext(); extra != nil {
		input.ExtraContext = extra.AsMap()
	}
	return nil
}

func extractTraceContextFromEnvelope(ctx context.Context, env *wsEnvelopeIn) context.Context {
	if env.Traceparent == "" {
		return ctx
	}
	if len(env.Traceparent) > maxTraceparentLen || len(env.Tracestate) > maxTracestateLen {
		return ctx
	}
	carrier := propagation.MapCarrier{
		"traceparent": env.Traceparent,
	}
	if env.Tracestate != "" {
		carrier["tracestate"] = env.Tracestate
	}
	return otel.GetTextMapPropagator().Extract(ctx, carrier)
}

func traceparentFromContext(ctx context.Context) string {
	carrier := propagation.MapCarrier{}
	otel.GetTextMapPropagator().Inject(ctx, carrier)
	return carrier["traceparent"]
}

func generateMessageID() string {
	id := uuid.New()
	return "msg_" + strings.ReplaceAll(id.String(), "-", "")
}

func generateRequestID() string {
	id := uuid.New()
	return "req_" + strings.ReplaceAll(id.String(), "-", "")
}

func (h *ChatOrchestrator) handleProtobufMessage(writer *wsSafeWriter, msg []byte, userID string, tracer trace.Tracer, baseCtx context.Context) {
	wsMsg := &pbws.WebSocketMessage{}
	if err := proto.Unmarshal(msg, wsMsg); err != nil {
		log.Printf("Failed to unmarshal protobuf message: %v", err)
		return
	}

	// Extract trace context
	// TRACKED(TD-009): Map TraceId from proto to OpenTelemetry context if it's a valid traceparent
	ctx := baseCtx
	ctx, span := tracer.Start(ctx, "HandleMessage.Proto")
	span.SetAttributes(
		attribute.String("user_id", userID),
		attribute.String("message_id", wsMsg.RequestId), // using RequestId as ID for now
		attribute.String("type", wsMsg.Type),
	)
	defer span.End()

	responder := newProtobufResponder(writer, wsMsg, ctx)

	switch wsMsg.Type {
	case "chat":
		chatMsg := &pbws.ChatMessage{}
		if err := proto.Unmarshal(wsMsg.Payload, chatMsg); err != nil {
			log.Printf("Failed to unmarshal ChatMessage: %v", err)
			responder.SendError("invalid_argument", "Invalid ChatMessage payload", false)
			return
		}

		input := chatInputPool.Get().(*chatInput)
		input.Reset()
		defer func() {
			input.Reset()
			chatInputPool.Put(input)
		}()

		input.Message = chatMsg.Message
		input.SessionID = chatMsg.SessionId
		// Map other fields if ChatMessage has them (e.g. UserProfile)

		h.handleChatMessage(ctx, responder, userID, input, wsMsg.RequestId)

	case "update_node_mastery":
		req := &pbws.UpdateNodeMasteryRequest{}
		if err := proto.Unmarshal(wsMsg.Payload, req); err != nil {
			log.Printf("Failed to unmarshal UpdateNodeMasteryRequest: %v", err)
			responder.SendError("invalid_argument", "Invalid UpdateNodeMastery payload", false)
			return
		}
		h.handleUpdateNodeMasteryProto(ctx, responder, req, userID)

	default:
		log.Printf("Unknown protobuf message type: %s", wsMsg.Type)
		responder.SendError("invalid_argument", "Unknown message type", false)
	}
}

func (h *ChatOrchestrator) handleUpdateNodeMasteryProto(ctx context.Context, responder *protobufResponder, req *pbws.UpdateNodeMasteryRequest, userID string) {
	log.Printf("Received mastery update (proto) for user %s, node %s, mastery %d", userID, req.NodeId, req.Mastery)

	if h.galaxyClient == nil {
		log.Printf("Galaxy gRPC client not initialized")
		responder.SendUpdateNodeError(req.NodeId, req.RequestId, "Internal service error")
		return
	}

	version := requestEventTime(req.EventTime)
	versionToken := fmt.Sprintf("%d", version.UnixMilli())

	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.UpdateNodeMastery(ctx, userID, req.NodeId, req.Mastery, version, "offline_sync_proto")

	if err != nil {
		log.Printf("gRPC mastery update failed: %v", err)
		responder.SendUpdateNodeError(req.NodeId, versionToken, "Sync service unavailable")
		return
	}

	if resp.Success {
		responder.SendUpdateNodeMasteryAck(req.NodeId, versionToken, true)
	} else {
		responder.SendUpdateNodeError(req.NodeId, versionToken, resp.Reason)
	}
}

func getEnvInt64(key string, fallback int64) int64 {
	raw := strings.TrimSpace(os.Getenv(key))
	if raw == "" {
		return fallback
	}
	val, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		return fallback
	}
	return val
}

func requestEventTime(eventTime *timestamppb.Timestamp) time.Time {
	if eventTime != nil && eventTime.IsValid() {
		wsmetrics.ProtoFieldReadTotal.WithLabelValues("request.event_time", "new").Inc()
		return eventTime.AsTime()
	}
	return time.Now()
}

func responseEventTimeMillis(resp *agentv1.ChatResponse) int64 {
	if resp == nil {
		return 0
	}
	if resp.EventTime != nil && resp.EventTime.IsValid() {
		wsmetrics.ProtoFieldReadTotal.WithLabelValues("chat_response.event_time", "new").Inc()
		return resp.EventTime.AsTime().UnixMilli()
	}
	return 0
}

func normalizeErrorCodeString(code agentv1.ErrorCode) string {
	raw := strings.TrimPrefix(code.String(), "ERROR_CODE_")
	if raw == "" || raw == "UNSPECIFIED" {
		return ""
	}
	return strings.ToLower(raw)
}

func parseErrorCode(code string) agentv1.ErrorCode {
	switch strings.ToLower(strings.TrimSpace(code)) {
	case "invalid_argument", "validation_error":
		return agentv1.ErrorCode_ERROR_CODE_INVALID_ARGUMENT
	case "unauthorized":
		return agentv1.ErrorCode_ERROR_CODE_UNAUTHORIZED
	case "forbidden":
		return agentv1.ErrorCode_ERROR_CODE_FORBIDDEN
	case "not_found":
		return agentv1.ErrorCode_ERROR_CODE_NOT_FOUND
	case "conflict", "duplicate_request":
		return agentv1.ErrorCode_ERROR_CODE_CONFLICT
	case "rate_limited", "rate_limit", "resource_exhausted":
		return agentv1.ErrorCode_ERROR_CODE_RATE_LIMITED
	case "unavailable", "circuit_breaker_open":
		return agentv1.ErrorCode_ERROR_CODE_UNAVAILABLE
	case "timeout", "deadline_exceeded":
		return agentv1.ErrorCode_ERROR_CODE_TIMEOUT
	case "internal", "internal_error", "multi_agent_error":
		return agentv1.ErrorCode_ERROR_CODE_INTERNAL
	case "unknown":
		return agentv1.ErrorCode_ERROR_CODE_UNKNOWN
	default:
		wsmetrics.ProtoErrorCodeFallbackTotal.WithLabelValues("unknown_legacy_string").Inc()
		return agentv1.ErrorCode_ERROR_CODE_UNSPECIFIED
	}
}
