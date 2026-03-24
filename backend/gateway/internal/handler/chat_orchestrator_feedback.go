package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/trace"
)

type actionStatusSender interface {
	SendActionStatus(actionID, status string, data map[string]interface{})
}

type updateNodeResponder interface {
	SendUpdateNodeError(nodeID, version, message string)
	SendUpdateNodeMasteryAck(nodeID, version string, success bool)
}

type interventionResponder interface {
	SendInterventionAck(requestID, status, message string)
}

type responseFeedbackResponder interface {
	SendResponseFeedbackAck(responseID, status, message string)
}

type planReviewStatusSender interface {
	SendPlanReviewStatus(reviewID, status string, data map[string]interface{})
}

// saveMessage persists a chat message to the database
func (h *ChatOrchestrator) saveMessage(userID, sessionID, role, content string) {
	tracer := otel.Tracer("chat-orchestrator")
	ctx, span := tracer.Start(context.Background(), "redis.save_message")
	defer span.End()

	payload := map[string]string{
		"id":         uuid.New().String(), // Generate stable UUID for message ID
		"session_id": sessionID,
		"user_id":    userID,
		"role":       role,
		"content":    content,
		"timestamp":  fmt.Sprintf("%d", time.Now().Unix()),
	}
	data, _ := json.Marshal(payload)

	// Use the new reliable double-write mechanism
	if err := h.chatHistory.SaveMessage(ctx, sessionID, data); err != nil {
		log.Printf("Failed to save chat message: %v", err)
	}
}

type legacyActionStatusSender struct {
	conn *websocket.Conn
}

func (s legacyActionStatusSender) SendActionStatus(actionID, status string, data map[string]interface{}) {
	statusMsg := map[string]interface{}{
		"type":      "action_status",
		"action_id": actionID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}
	for k, v := range data {
		statusMsg[k] = v
	}
	if err := s.conn.WriteJSON(statusMsg); err != nil {
		log.Printf("Failed to send action status: %v", err)
	} else {
		log.Printf("✅ Action status sent: status=%s, action_id=%s", status, actionID)
	}
}

type legacyUpdateNodeResponder struct {
	conn *websocket.Conn
}

func (s legacyUpdateNodeResponder) SendUpdateNodeError(nodeID, version, message string) {
	s.conn.WriteJSON(map[string]interface{}{
		"type": "error_update_node_mastery",
		"payload": map[string]interface{}{
			"nodeId":  nodeID,
			"version": version,
			"error":   message,
		},
	})
}

func (s legacyUpdateNodeResponder) SendUpdateNodeMasteryAck(nodeID, version string, success bool) {
	s.conn.WriteJSON(map[string]interface{}{
		"type": "ack_update_node_mastery",
		"payload": map[string]interface{}{
			"node_id":   nodeID,
			"version":   version,
			"success":   success,
			"timestamp": time.Now().Unix(),
		},
	})
}

type legacyInterventionResponder struct {
	conn *websocket.Conn
}

func (s legacyInterventionResponder) SendInterventionAck(requestID, status, message string) {
	payload := map[string]interface{}{
		"type":       "intervention_feedback_ack",
		"request_id": requestID,
		"status":     status,
		"timestamp":  time.Now().Unix(),
	}
	if message != "" {
		payload["message"] = message
	}
	if err := s.conn.WriteJSON(payload); err != nil {
		log.Printf("Failed to send intervention feedback ack: %v", err)
	}
}

type legacyResponseFeedbackResponder struct {
	conn *websocket.Conn
}

func (s legacyResponseFeedbackResponder) SendResponseFeedbackAck(responseID, status, message string) {
	payload := map[string]interface{}{
		"type":        "response_feedback_ack",
		"response_id": responseID,
		"status":      status,
		"timestamp":   time.Now().Unix(),
	}
	if message != "" {
		payload["message"] = message
	}
	if err := s.conn.WriteJSON(payload); err != nil {
		log.Printf("Failed to send response feedback ack: %v", err)
	}
}

type legacyPlanReviewStatusSender struct {
	conn *websocket.Conn
}

func (s legacyPlanReviewStatusSender) SendPlanReviewStatus(reviewID, status string, data map[string]interface{}) {
	statusMsg := map[string]interface{}{
		"type":      "plan_review_status",
		"review_id": reviewID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}
	for k, v := range data {
		statusMsg[k] = v
	}
	if err := s.conn.WriteJSON(statusMsg); err != nil {
		log.Printf("Failed to send plan review status: %v", err)
	} else {
		log.Printf("✅ Plan review status sent: status=%s, review_id=%s", status, reviewID)
	}
}

func (h *ChatOrchestrator) handleActionFeedbackWithResponder(sender actionStatusSender, msgMap map[string]interface{}, userID, authToken string) {
	action, ok := msgMap["action"].(string)
	if !ok {
		log.Printf("Invalid action feedback: missing action field")
		return
	}

	toolResultID, ok := msgMap["tool_result_id"].(string)
	if !ok {
		log.Printf("Invalid action feedback: missing tool_result_id field")
		return
	}

	widgetType, ok := msgMap["widget_type"].(string)
	if !ok {
		log.Printf("Invalid action feedback: missing widget_type field")
		return
	}

	log.Printf("Action feedback from user %s: action=%s, widget_type=%s, tool_result_id=%s",
		userID, action, widgetType, toolResultID)

	// Parse user ID
	userUUID, err := uuid.Parse(userID)
	if err != nil {
		log.Printf("Invalid user ID in action feedback: %v", err)
		return
	}

	// Route feedback to appropriate service handler
	switch widgetType {
	case "task_list", "create_task":
		if action == "confirm" {
			// Handle task list confirmation (tasks were created)
			log.Printf("Task list creation confirmed for user %s, tool_result_id=%s", userID, toolResultID)

			// [P0.1 FIX]: Call TaskCommand to confirm tasks in database
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()

			err := h.taskCommand.ConfirmGeneratedTasks(ctx, userUUID, toolResultID)
			if err != nil {
				log.Printf("❌ Failed to confirm tasks for user %s: %v", userID, err)
				sender.SendActionStatus(toolResultID, "failed", map[string]interface{}{
					"message": "确认失败，请重试",
				})
				return
			}

			// Send confirmation status back to client
			sender.SendActionStatus(toolResultID, "confirmed", map[string]interface{}{
				"message":     "任务已确认",
				"widget_type": widgetType,
			})
		} else if action == "dismiss" {
			// Handle task list dismissal (user rejected generated tasks)
			log.Printf("Task list creation dismissed by user %s", userID)

			// TRACKED(TD-009): In future, could mark tasks as rejected in DB
			// For now, just send status update
			sender.SendActionStatus(toolResultID, "dismissed", map[string]interface{}{
				"message":     "任务已忽略",
				"widget_type": widgetType,
			})
		}

	case "plan_card", "create_plan":
		if action == "confirm" {
			// Handle plan confirmation
			log.Printf("Plan creation confirmed for user %s", userID)

			sender.SendActionStatus(toolResultID, "confirmed", map[string]interface{}{
				"message":     "计划已确认",
				"widget_type": widgetType,
			})
		} else if action == "dismiss" {
			log.Printf("Plan creation dismissed by user %s", userID)

			sender.SendActionStatus(toolResultID, "dismissed", map[string]interface{}{
				"message":     "计划已忽略",
				"widget_type": widgetType,
			})
		}

	case "focus_card":
		if action == "confirm" {
			// Handle focus session start confirmation
			log.Printf("Focus session start confirmed for user %s", userID)

			sender.SendActionStatus(toolResultID, "confirmed", map[string]interface{}{
				"message":     "专注已开始",
				"widget_type": widgetType,
			})
		} else if action == "dismiss" {
			log.Printf("Focus session dismissed by user %s", userID)

			sender.SendActionStatus(toolResultID, "dismissed", map[string]interface{}{
				"message":     "专注已取消",
				"widget_type": widgetType,
			})
		}

	default:
		log.Printf("Unknown widget type in action feedback: %s", widgetType)
	}

	// Persist feedback for analytics/learning (best effort).
	if err := h.persistActionFeedback(authToken, toolResultID, widgetType, action); err != nil {
		log.Printf("Failed to persist action feedback: %v", err)
	}
}

func normalizeActionFeedbackType(action string) string {
	switch strings.ToLower(action) {
	case "confirm":
		return "accept"
	case "dismiss":
		return "dismiss"
	default:
		return "ignore"
	}
}

func normalizeActionType(widgetType string) string {
	switch strings.ToLower(widgetType) {
	case "focus_card":
		return "break"
	case "task_list", "create_task", "plan_card", "create_plan":
		return "plan_split"
	default:
		return "review"
	}
}

func (h *ChatOrchestrator) persistActionFeedback(authToken, toolResultID, widgetType, action string) error {
	if h.backendURL == "" || authToken == "" || toolResultID == "" {
		return nil
	}

	payload := map[string]interface{}{
		"candidate_id":  toolResultID,
		"action_type":   normalizeActionType(widgetType),
		"feedback_type": normalizeActionFeedbackType(action),
		"executed":      strings.EqualFold(action, "confirm"),
		"context_snapshot": map[string]interface{}{
			"widget_type": widgetType,
			"source":      "chat_orchestrator.action_feedback",
		},
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	endpoint := fmt.Sprintf("%s/api/v1/signals/feedback", h.backendURL)
	req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+authToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := h.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("feedback API returned status=%d", resp.StatusCode)
	}
	return nil
}

func (h *ChatOrchestrator) handleUpdateNodeMasteryWithResponder(responder updateNodeResponder, msgMap map[string]interface{}, userID string) {
	payload, ok := msgMap["payload"].(map[string]interface{})
	if !ok {
		log.Printf("Invalid update_node_mastery: missing payload")
		return
	}

	nodeID, _ := payload["nodeId"].(string)
	mastery := int32(0)
	if v, ok := payload["mastery"].(float64); ok {
		mastery = int32(v)
	}
	versionStr, _ := payload["version"].(string)

	if nodeID == "" || versionStr == "" {
		log.Printf("Invalid update_node_mastery: missing fields")
		responder.SendUpdateNodeError(nodeID, versionStr, "Invalid payload")
		return
	}

	// Support flexible ISO8601 parsing (Dart toIso8601String format)
	var version time.Time
	var err error

	// Try multiple formats to be safe
	formats := []string{
		time.RFC3339Nano,
		"2006-01-02T15:04:05.999999999Z",
		"2006-01-02T15:04:05.999999",
		time.RFC3339,
	}

	for _, f := range formats {
		version, err = time.Parse(f, versionStr)
		if err == nil {
			break
		}
	}

	if err != nil {
		log.Printf("Invalid version format: %s", versionStr)
		responder.SendUpdateNodeError(nodeID, versionStr, "Invalid timestamp format")
		return
	}

	log.Printf("Received mastery update for user %s, node %s, mastery %d, version %s", userID, nodeID, mastery, versionStr)

	// Call Python Backend via gRPC
	if h.galaxyClient == nil {
		log.Printf("Galaxy gRPC client not initialized")
		responder.SendUpdateNodeError(nodeID, versionStr, "Internal service error")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.UpdateNodeMastery(ctx, userID, nodeID, mastery, version, "offline_sync")

	if err != nil {
		log.Printf("gRPC mastery update failed: %v", err)
		responder.SendUpdateNodeError(nodeID, versionStr, "Sync service unavailable")
		return
	}

	if resp.Success {
		responder.SendUpdateNodeMasteryAck(nodeID, versionStr, true)
	} else {
		responder.SendUpdateNodeError(nodeID, versionStr, resp.Reason)
	}
}

func (h *ChatOrchestrator) handleInterventionFeedbackWithResponder(responder interventionResponder, msgMap map[string]interface{}, userID, authToken string) {
	requestID, ok := msgMap["request_id"].(string)
	if !ok || requestID == "" {
		log.Printf("Invalid intervention_feedback: missing request_id")
		responder.SendInterventionAck("", "failed", "missing request_id")
		return
	}

	feedbackType, ok := msgMap["feedback_type"].(string)
	if !ok || feedbackType == "" {
		log.Printf("Invalid intervention_feedback: missing feedback_type")
		responder.SendInterventionAck(requestID, "failed", "missing feedback_type")
		return
	}

	extraData := map[string]interface{}{}
	if raw, ok := msgMap["extra_data"].(map[string]interface{}); ok {
		extraData = raw
	}

	if h.backendURL == "" || authToken == "" {
		log.Printf("Intervention feedback rejected: backendURL or auth token missing")
		responder.SendInterventionAck(requestID, "failed", "backend unavailable")
		return
	}

	payload := map[string]interface{}{
		"feedback_type": feedbackType,
		"extra_data":    extraData,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Failed to marshal intervention feedback: %v", err)
		responder.SendInterventionAck(requestID, "failed", "invalid payload")
		return
	}

	endpoint := fmt.Sprintf("%s/api/v1/interventions/requests/%s/feedback", h.backendURL, requestID)
	req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		log.Printf("Failed to build intervention feedback request: %v", err)
		responder.SendInterventionAck(requestID, "failed", "request error")
		return
	}
	req.Header.Set("Authorization", "Bearer "+authToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := h.httpClient.Do(req)
	if err != nil {
		log.Printf("Failed to send intervention feedback: %v", err)
		responder.SendInterventionAck(requestID, "failed", "network error")
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		log.Printf("Intervention feedback rejected: status=%d", resp.StatusCode)
		responder.SendInterventionAck(requestID, "failed", "backend rejected")
		return
	}

	responder.SendInterventionAck(requestID, "ok", "")
}

func (h *ChatOrchestrator) handleResponseFeedbackWithResponder(ctx context.Context, responder responseFeedbackResponder, msgMap map[string]interface{}, userID string) {
	responseID, ok := msgMap["response_id"].(string)
	if !ok || responseID == "" {
		log.Printf("Invalid response_feedback: missing response_id")
		responder.SendResponseFeedbackAck("", "failed", "missing response_id")
		return
	}

	feedbackTypeRaw, ok := msgMap["feedback_type"].(string)
	if !ok || feedbackTypeRaw == "" {
		log.Printf("Invalid response_feedback: missing feedback_type")
		responder.SendResponseFeedbackAck(responseID, "failed", "missing feedback_type")
		return
	}

	feedbackType := agentv1.FeedbackType_FEEDBACK_TYPE_UP
	switch strings.ToLower(feedbackTypeRaw) {
	case "up", "thumbs_up", "like":
		feedbackType = agentv1.FeedbackType_FEEDBACK_TYPE_UP
	case "down", "thumbs_down", "dislike":
		feedbackType = agentv1.FeedbackType_FEEDBACK_TYPE_DOWN
	default:
		log.Printf("Invalid response_feedback: unknown feedback_type=%s", feedbackTypeRaw)
		responder.SendResponseFeedbackAck(responseID, "failed", "invalid feedback_type")
		return
	}

	traceID, _ := msgMap["trace_id"].(string)
	if traceID == "" {
		if span := trace.SpanFromContext(ctx); span.SpanContext().IsValid() {
			traceID = span.SpanContext().TraceID().String()
		}
	}

	reasonMap := map[string]agentv1.FeedbackReason{
		"inaccurate":    agentv1.FeedbackReason_FEEDBACK_REASON_INACCURATE,
		"incomplete":    agentv1.FeedbackReason_FEEDBACK_REASON_INCOMPLETE,
		"verbose":       agentv1.FeedbackReason_FEEDBACK_REASON_VERBOSE,
		"formatting":    agentv1.FeedbackReason_FEEDBACK_REASON_FORMATTING,
		"misaligned":    agentv1.FeedbackReason_FEEDBACK_REASON_MISALIGNED,
		"too_hard":      agentv1.FeedbackReason_FEEDBACK_REASON_TOO_HARD,
		"too_simple":    agentv1.FeedbackReason_FEEDBACK_REASON_TOO_SIMPLE,
		"unspecified":   agentv1.FeedbackReason_FEEDBACK_REASON_UNSPECIFIED,
		"format":        agentv1.FeedbackReason_FEEDBACK_REASON_FORMATTING,
		"not_aligned":   agentv1.FeedbackReason_FEEDBACK_REASON_MISALIGNED,
		"not_accurate":  agentv1.FeedbackReason_FEEDBACK_REASON_INACCURATE,
		"not_complete":  agentv1.FeedbackReason_FEEDBACK_REASON_INCOMPLETE,
		"too_verbose":   agentv1.FeedbackReason_FEEDBACK_REASON_VERBOSE,
		"too_difficult": agentv1.FeedbackReason_FEEDBACK_REASON_TOO_HARD,
		"too_easy":      agentv1.FeedbackReason_FEEDBACK_REASON_TOO_SIMPLE,
	}

	reasons := []agentv1.FeedbackReason{}
	if raw, ok := msgMap["reasons"].([]interface{}); ok {
		for _, item := range raw {
			if text, ok := item.(string); ok {
				if reason, ok := reasonMap[strings.ToLower(text)]; ok {
					reasons = append(reasons, reason)
				}
			}
		}
	}

	freeText, _ := msgMap["free_text"].(string)
	workflowID, _ := msgMap["workflow_id"].(string)
	promptVersion, _ := msgMap["prompt_version"].(string)

	meta := map[string]string{}
	if raw, ok := msgMap["meta"].(map[string]interface{}); ok {
		for key, val := range raw {
			meta[key] = fmt.Sprint(val)
		}
	}

	if h.agentClient == nil {
		log.Printf("Agent client not initialized for response feedback")
		responder.SendResponseFeedbackAck(responseID, "failed", "service unavailable")
		return
	}

	log.Printf("Response feedback from user %s: response_id=%s trace_id=%s", userID, responseID, traceID)

	req := &agentv1.ResponseFeedbackRequest{
		UserId:        userID,
		ResponseId:    responseID,
		TraceId:       traceID,
		FeedbackType:  feedbackType,
		Reasons:       reasons,
		FreeText:      freeText,
		WorkflowId:    workflowID,
		PromptVersion: promptVersion,
		Meta:          meta,
	}

	feedbackCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	resp, err := h.agentClient.SubmitResponseFeedback(feedbackCtx, req)
	if err != nil || resp == nil || !resp.Success {
		log.Printf("Failed to submit response feedback: %v", err)
		responder.SendResponseFeedbackAck(responseID, "failed", "submit failed")
		return
	}

	responder.SendResponseFeedbackAck(responseID, "ok", "")
}

// handleActionFeedback processes action confirmation/dismissal feedback from user
func (h *ChatOrchestrator) handleActionFeedback(conn *websocket.Conn, msgMap map[string]interface{}, userID, authToken string) {
	h.handleActionFeedbackWithResponder(legacyActionStatusSender{conn: conn}, msgMap, userID, authToken)
}

// sendActionStatus sends action confirmation/dismissal status back to the client via WebSocket
func (h *ChatOrchestrator) sendActionStatus(conn *websocket.Conn, actionID, status string, data map[string]interface{}) {
	// Build status message
	statusMsg := map[string]interface{}{
		"type":      "action_status",
		"action_id": actionID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}

	// Merge additional data
	for k, v := range data {
		statusMsg[k] = v
	}

	// Send message to client
	if err := conn.WriteJSON(statusMsg); err != nil {
		log.Printf("Failed to send action status: %v", err)
	} else {
		log.Printf("✅ Action status sent: status=%s, action_id=%s", status, actionID)
	}
}

func (h *ChatOrchestrator) handleInterventionFeedback(conn *websocket.Conn, msgMap map[string]interface{}, userID, authToken string) {
	h.handleInterventionFeedbackWithResponder(legacyInterventionResponder{conn: conn}, msgMap, userID, authToken)
}

func (h *ChatOrchestrator) sendInterventionAck(conn *websocket.Conn, requestID, status, message string) {
	payload := map[string]interface{}{
		"type":       "intervention_feedback_ack",
		"request_id": requestID,
		"status":     status,
		"timestamp":  time.Now().Unix(),
	}
	if message != "" {
		payload["message"] = message
	}
	if err := conn.WriteJSON(payload); err != nil {
		log.Printf("Failed to send intervention feedback ack: %v", err)
	}
}

func (h *ChatOrchestrator) handleResponseFeedback(conn *websocket.Conn, msgMap map[string]interface{}, userID string, ctx context.Context) {
	h.handleResponseFeedbackWithResponder(ctx, legacyResponseFeedbackResponder{conn: conn}, msgMap, userID)
}

// handlePlanReviewFeedback processes user feedback on plan reviews (legacy wrapper)
func (h *ChatOrchestrator) handlePlanReviewFeedback(conn *websocket.Conn, msgMap map[string]interface{}, userID string, ctx context.Context) {
	h.handlePlanReviewFeedbackWithResponder(ctx, legacyPlanReviewStatusSender{conn: conn}, msgMap, userID)
}

// handlePlanReviewFeedbackWithResponder processes user feedback on plan reviews
// and forwards the decision to the Python engine via gRPC.
func (h *ChatOrchestrator) handlePlanReviewFeedbackWithResponder(ctx context.Context, sender planReviewStatusSender, msgMap map[string]interface{}, userID string) {
	reviewID, ok := msgMap["review_id"].(string)
	if !ok {
		log.Printf("Invalid plan review feedback: missing review_id field")
		return
	}

	userDecision, ok := msgMap["user_decision"].(string)
	if !ok {
		log.Printf("Invalid plan review feedback: missing user_decision field")
		return
	}

	planID, _ := msgMap["plan_id"].(string)
	userComment, _ := msgMap["user_comment"].(string)

	log.Printf("Plan review feedback from user %s: review_id=%s, plan_id=%s, decision=%s, comment=%s",
		userID, reviewID, planID, userDecision, userComment)

	// Map string decision to proto enum
	var decision agentv1.PlanReviewDecision
	var status, message string

	switch userDecision {
	case "approve":
		decision = agentv1.PlanReviewDecision_APPROVE
		status = "approved"
		message = "计划已批准，正在执行..."
	case "reject":
		decision = agentv1.PlanReviewDecision_REJECT
		status = "rejected"
		message = "计划已取消"
	case "modify":
		decision = agentv1.PlanReviewDecision_MODIFY
		status = "modify_requested"
		message = "请提供修改要求..."
	default:
		decision = agentv1.PlanReviewDecision_ACKNOWLEDGE
		status = "acknowledged"
		message = "已确认"
	}

	// Extract optional meta fields
	meta := map[string]string{}
	if raw, ok := msgMap["meta"].(map[string]interface{}); ok {
		for key, val := range raw {
			meta[key] = fmt.Sprint(val)
		}
	}

	if h.agentClient == nil {
		log.Printf("Agent client not initialized for plan review feedback")
		sender.SendPlanReviewStatus(reviewID, "failed", map[string]interface{}{
			"message":   "service unavailable",
			"timestamp": time.Now().Unix(),
		})
		return
	}

	req := &agentv1.PlanReviewRequest{
		UserId:      userID,
		PlanId:      planID,
		ReviewId:    reviewID,
		Decision:    decision,
		UserComment: userComment,
		Meta:        meta,
	}

	reviewCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	resp, err := h.agentClient.SubmitPlanReview(reviewCtx, req)
	if err != nil || resp == nil || !resp.Success {
		log.Printf("Failed to submit plan review to agent: %v", err)
		sender.SendPlanReviewStatus(reviewID, "failed", map[string]interface{}{
			"message":       message,
			"user_decision": userDecision,
			"timestamp":     time.Now().Unix(),
		})
		return
	}

	// Use backend-returned message if available, otherwise use local default
	if resp.Message != "" {
		message = resp.Message
	}

	sender.SendPlanReviewStatus(reviewID, status, map[string]interface{}{
		"message":       message,
		"user_decision": userDecision,
		"timestamp":     time.Now().Unix(),
	})
}

// handleFocusCompleted processes focus session completion events
func (h *ChatOrchestrator) handleFocusCompleted(msgMap map[string]interface{}, userID, authToken string) {
	sessionID, ok := msgMap["session_id"].(string)
	if !ok {
		log.Printf("Invalid focus_completed event: missing session_id field")
		return
	}

	actualDuration, ok := msgMap["actual_duration"].(float64)
	if !ok {
		log.Printf("Invalid focus_completed event: missing actual_duration field")
		return
	}

	var completedTaskIDs []string
	if tasks, ok := msgMap["tasks_completed"].([]interface{}); ok {
		for _, t := range tasks {
			if taskID, ok := t.(string); ok {
				completedTaskIDs = append(completedTaskIDs, taskID)
			}
		}
	}

	log.Printf("Focus session completed: user=%s, session_id=%s, duration=%d minutes, completed_tasks=%d",
		userID, sessionID, int(actualDuration), len(completedTaskIDs))

	if h.backendURL == "" || authToken == "" {
		log.Printf("Focus completion not persisted: backendURL or auth token missing")
		return
	}

	duration := int(actualDuration)
	if duration <= 0 {
		log.Printf("Focus completion not persisted: invalid duration=%d", duration)
		return
	}

	endTime := time.Now().UTC()
	startTime := endTime.Add(-time.Duration(duration) * time.Minute)

	payload := map[string]interface{}{
		"start_time":       startTime.Format(time.RFC3339),
		"end_time":         endTime.Format(time.RFC3339),
		"duration_minutes": duration,
		"focus_type":       "pomodoro",
		"status":           "completed",
	}
	if rawType, ok := msgMap["focus_type"].(string); ok && rawType != "" {
		payload["focus_type"] = rawType
	}

	for _, taskID := range completedTaskIDs {
		if _, err := uuid.Parse(taskID); err == nil {
			payload["task_id"] = taskID
			break
		}
	}

	body, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Failed to marshal focus_completed payload: %v", err)
		return
	}

	endpoint := fmt.Sprintf("%s/api/v1/focus/sessions", h.backendURL)
	req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		log.Printf("Failed to build focus_completed request: %v", err)
		return
	}
	req.Header.Set("Authorization", "Bearer "+authToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := h.httpClient.Do(req)
	if err != nil {
		log.Printf("Failed to persist focus_completed: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		log.Printf("Focus completion rejected by backend: status=%d", resp.StatusCode)
		return
	}

	log.Printf("Focus completion persisted: session_id=%s", sessionID)
}

// handleUpdateNodeMastery forwards mastery updates to Python backend via gRPC and sends ACK
func (h *ChatOrchestrator) handleUpdateNodeMastery(conn *websocket.Conn, msgMap map[string]interface{}, userID string) {
	h.handleUpdateNodeMasteryWithResponder(legacyUpdateNodeResponder{conn: conn}, msgMap, userID)
}

func (h *ChatOrchestrator) sendError(conn *websocket.Conn, opType, nodeID, version, message string) {
	conn.WriteJSON(map[string]interface{}{
		"type": fmt.Sprintf("error_%s", opType),
		"payload": map[string]interface{}{
			"nodeId":  nodeID,
			"version": version,
			"error":   message,
		},
	})
}
