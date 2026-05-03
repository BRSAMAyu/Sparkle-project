package handler

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/db"
	wsmetrics "github.com/sparkle/gateway/internal/metrics"
	"github.com/sparkle/gateway/internal/service"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc/codes"
	grpcstatus "google.golang.org/grpc/status"
	"google.golang.org/protobuf/types/known/structpb"
	"google.golang.org/protobuf/types/known/timestamppb"
)

const (
	defaultChatMode = "standard"
	expertModeAuto  = "expert_auto"
	expertModePref  = "expert::"
	teamModePref    = "team::"
)

func defaultUseDocumentContextForMode(chatMode string) bool {
	return normalizeChatMode(chatMode) == "study_plan"
}

func ensureChatExtraContext(input *chatInput) map[string]interface{} {
	if input.ExtraContext == nil {
		input.ExtraContext = map[string]interface{}{}
	}
	return input.ExtraContext
}

func shortHash(parts ...string) string {
	h := sha256.New()
	for _, part := range parts {
		if _, err := h.Write([]byte(part)); err != nil {
			return "hash_error"
		}
		if _, err := h.Write([]byte{0}); err != nil {
			return "hash_error"
		}
	}
	return hex.EncodeToString(h.Sum(nil))[:12]
}

func semanticCacheScope(userID, chatMode, userContextJSON string, fileIDs []string, includeReferences bool, activeTools []string, extraContext map[string]interface{}) string {
	sortedFileIDs := append([]string(nil), fileIDs...)
	sort.Strings(sortedFileIDs)

	sortedActiveTools := append([]string(nil), activeTools...)
	sort.Strings(sortedActiveTools)

	referencesFlag := "refs_off"
	if includeReferences {
		referencesFlag = "refs_on"
	}

	contextHash := shortHash(userContextJSON)
	fileHash := shortHash(strings.Join(sortedFileIDs, ","))
	toolsHash := shortHash(strings.Join(sortedActiveTools, ","))

	extraCtxJSON, _ := json.Marshal(extraContext)
	extraHash := shortHash(string(extraCtxJSON))

	return fmt.Sprintf(
		"user:%s|mode:%s|ctx:%s|files:%s|tools:%s|extra:%s|%s",
		userID,
		normalizeChatMode(chatMode),
		contextHash,
		fileHash,
		toolsHash,
		extraHash,
		referencesFlag,
	)
}

func normalizeChatMode(mode string) string {
	trimmed := strings.TrimSpace(mode)
	if trimmed == "" {
		return defaultChatMode
	}
	if strings.HasPrefix(trimmed, expertModePref) || strings.HasPrefix(trimmed, teamModePref) {
		return trimmed
	}
	switch trimmed {
	case defaultChatMode, "deep_analysis", "study_plan", "error_diagnosis", expertModeAuto:
		return trimmed
	default:
		return defaultChatMode
	}
}

func writeLegacyJSON(writer *wsSafeWriter, payload interface{}) error {
	return writer.WriteJSON(payload)
}

func logWebSocketWriteError(operation string, err error) {
	if err != nil {
		log.Printf("Failed to write WebSocket %s: %v", operation, err)
	}
}

func writeLegacyJSONLogged(writer *wsSafeWriter, operation string, payload interface{}) bool {
	if err := writeLegacyJSON(writer, payload); err != nil {
		logWebSocketWriteError(operation, err)
		return false
	}
	return true
}

func writeWSJSONLogged(writer *wsSafeWriter, operation string, payload interface{}) bool {
	if err := writer.WriteJSON(payload); err != nil {
		logWebSocketWriteError(operation, err)
		return false
	}
	return true
}

func writeWSMessageLogged(writer *wsSafeWriter, operation string, messageType int, data []byte) bool {
	if err := writer.WriteMessage(messageType, data); err != nil {
		logWebSocketWriteError(operation, err)
		return false
	}
	return true
}

func sendChatAccepted(responder interface{}, requestID string) bool {
	if strings.TrimSpace(requestID) == "" {
		return true
	}
	switch r := responder.(type) {
	case *envelopeResponder:
		// Envelope frames are ACKed immediately when the frame is decoded.
		return true
	case *protobufResponder:
		r.SendAck()
		return true
	case *wsSafeWriter:
		return writeLegacyJSONLogged(r, "legacy message ack", gin.H{
			"type":       "message_ack",
			"message_id": requestID,
			"request_id": requestID,
			"status":     "received",
			"timestamp":  time.Now().UnixMilli(),
		})
	default:
		return true
	}
}

func workflowIDForChatMode(mode string) string {
	normalized := normalizeChatMode(mode)
	switch normalized {
	case defaultChatMode:
		return "standard_chat"
	case "deep_analysis":
		return "deep_analysis_workflow"
	case "study_plan":
		return "study_plan_workflow"
	case "error_diagnosis":
		return "error_diagnosis_workflow"
	case expertModeAuto:
		return "expert_auto_workflow"
	default:
		if strings.HasPrefix(normalized, expertModePref) {
			expertID := strings.TrimSpace(strings.TrimPrefix(normalized, expertModePref))
			if expertID == "" {
				expertID = "unknown"
			}
			return "expert_" + expertID + "_workflow"
		}
		if strings.HasPrefix(normalized, teamModePref) {
			return "expert_team_workflow"
		}
		return "standard_chat"
	}
}

func (h *ChatOrchestrator) resolveUserIdentity(ctx context.Context, userID string) (uuid.UUID, string, *db.User, error) {
	if parsed, err := uuid.Parse(userID); err == nil {
		if h.userIdentity == nil {
			return parsed, userID, nil, nil
		}
		user, err := h.userIdentity.GetUserByUUID(ctx, parsed)
		if err != nil {
			return parsed, userID, nil, nil
		}
		return parsed, userID, &user, nil
	}

	if h.userIdentity == nil {
		return uuid.Nil, userID, nil, nil
	}

	user, err := h.userIdentity.GetUserByEmail(ctx, userID)
	if err != nil {
		return uuid.Nil, userID, nil, nil
	}
	if !user.ID.Valid {
		return uuid.Nil, userID, nil, nil
	}

	parsed, err := uuid.FromBytes(user.ID.Bytes[:])
	if err != nil {
		return uuid.Nil, userID, nil, nil
	}
	return parsed, parsed.String(), &user, nil
}

func buildAgentUserProfile(inputNickname, userContextJSON string, snapshot *service.ChatUserProfileSnapshot, fallbackUser *db.User) *agentv1.UserProfile {
	profile := &agentv1.UserProfile{
		Nickname:     inputNickname,
		Timezone:     "Asia/Shanghai",
		Language:     "zh-CN",
		ExtraContext: userContextJSON,
	}

	if snapshot != nil {
		if snapshot.Nickname != "" {
			profile.Nickname = snapshot.Nickname
		}
		if snapshot.Timezone != "" {
			profile.Timezone = snapshot.Timezone
		}
		if snapshot.Language != "" {
			profile.Language = snapshot.Language
		}
		profile.IsPro = snapshot.IsPro
		profile.Level = snapshot.Level
		if snapshot.AvatarURL != "" {
			profile.AvatarUrl = snapshot.AvatarURL
		}
		profile.Preferences = snapshot.Preferences
	}

	if fallbackUser != nil {
		if profile.Nickname == "" {
			if fallbackUser.Nickname.Valid && fallbackUser.Nickname.String != "" {
				profile.Nickname = fallbackUser.Nickname.String
			} else {
				profile.Nickname = fallbackUser.Username
			}
		}
		if profile.AvatarUrl == "" && fallbackUser.AvatarUrl.Valid {
			profile.AvatarUrl = fallbackUser.AvatarUrl.String
		}
		if profile.Level == 0 {
			profile.Level = fallbackUser.FlameLevel
		}
		if !profile.IsPro {
			profile.IsPro = fallbackUser.FlameLevel >= 3
		}
	}

	return profile
}

func (h *ChatOrchestrator) handleChatMessage(ctx context.Context, responder interface{}, userID string, input *chatInput, requestID string) bool {
	tracer := otel.Tracer("chat-orchestrator")
	span := trace.SpanFromContext(ctx)
	span.SetAttributes(
		attribute.String("session_id", input.SessionID),
	)

	// Set timeout for the entire chat message processing.
	// Streaming multi-agent/team conversations can legitimately run longer than
	// short unary-style gRPC calls, so we keep a more generous floor here.
	timeoutSeconds := 300
	if h.cfg != nil && h.cfg.GRPCTimeoutSeconds > 0 {
		timeoutSeconds = h.cfg.GRPCTimeoutSeconds
		if timeoutSeconds < 300 {
			timeoutSeconds = 300
		}
	}
	ctx, cancel := context.WithTimeout(ctx, time.Duration(timeoutSeconds)*time.Second)
	defer cancel()

	// Admission control: block until a stream slot is available.
	// This prevents unbounded concurrent gRPC streams from exhausting resources.
	select {
	case h.streamSem <- struct{}{}:
		defer func() { <-h.streamSem }()
	default:
		// All stream slots occupied — reject immediately.
		switch r := responder.(type) {
		case *envelopeResponder:
			r.SendError("resource_exhausted", "Server busy, please retry", true)
		case *protobufResponder:
			r.SendError("resource_exhausted", "Server busy, please retry", true)
		case *wsSafeWriter:
			writeLegacyJSONLogged(r, "resource exhausted error", legacyStreamErrorPayload("resource_exhausted", "Server busy, please retry", true))
		}
		return false
	}

	// Sanitize Input (Security Hygiene) - reuse global sanitizer
	input.Message = sanitizer.Sanitize(input.Message)

	// Canonicalize the authenticated identity before any session history write/read.
	// WS auth may provide an email or legacy subject, while chat history ownership
	// and downstream AI context should consistently use the resolved UUID.
	userUUID, resolvedUserID, resolvedUser, _ := h.resolveUserIdentity(ctx, userID)
	if resolvedUserID != "" {
		userID = resolvedUserID
	}

	reqID := requestID
	if reqID == "" {
		reqID = fmt.Sprintf("req_%s", uuid.New().String())
	}
	if h.chatHistory != nil {
		accepted, err := h.chatHistory.TryAcceptRealtimeRequest(ctx, userID, reqID, time.Hour)
		if err != nil {
			log.Printf("Failed to record realtime request id user=%s request_id=%s: %v", hashUserIDForLog(userID), reqID, err)
		} else if !accepted {
			log.Printf("Duplicate realtime request ignored user=%s request_id=%s", hashUserIDForLog(userID), reqID)
			if !sendChatAccepted(responder, reqID) {
				return true
			}
			switch r := responder.(type) {
			case *envelopeResponder:
				r.SendError("duplicate_request", "Request already accepted; refresh conversation if the response is missing.", false)
			case *protobufResponder:
				r.SendError("duplicate_request", "Request already accepted; refresh conversation if the response is missing.", false)
			case *wsSafeWriter:
				writeLegacyJSONLogged(r, "duplicate request error", legacyStreamErrorPayload("duplicate_request", "Request already accepted; refresh conversation if the response is missing.", false))
			}
			return false
		}
	}
	if !sendChatAccepted(responder, reqID) {
		return true
	}

	// Persist user message to Redis history for context pruning
	if input.SessionID != "" {
		sessionID := input.SessionID
		message := input.Message
		h.saveMessage(ctx, userID, sessionID, "user", message, nil)
	}

	startTime := time.Now()
	isCacheHit := false
	traceID := ""
	if span := trace.SpanFromContext(ctx); span.SpanContext().IsValid() {
		traceID = span.SpanContext().TraceID().String()
	}

	var profileSnapshot *service.ChatUserProfileSnapshot
	if h.userContext != nil && userUUID != uuid.Nil {
		if snapshot, err := h.userContext.GetChatUserProfileSnapshot(ctx, userUUID); err != nil {
			log.Printf("Failed to fetch chat user profile for user=%s: %v", hashUserIDForLog(userID), err)
		} else {
			profileSnapshot = snapshot
		}
	}

	// P0: Fetch user context (pending tasks, active plans, focus stats, recent progress)
	userContextJSON := ""
	var contextFetchLatency time.Duration
	if h.userContext != nil && userUUID != uuid.Nil {
		ucCtx, ucSpan := tracer.Start(ctx, "user_context.fetch")
		contextFetchStart := time.Now()
		contextData, err := h.userContext.GetUserContextData(ucCtx, userUUID)
		contextFetchLatency = time.Since(contextFetchStart)
		ucSpan.End()

		if err != nil {
			log.Printf("[CONTEXT] Failed to fetch user context for user=%s, latency=%dms, error=%v",
				hashUserIDForLog(userID), contextFetchLatency.Milliseconds(), err)
			// Non-fatal: continue with empty context
		} else {
			userContextJSON = contextData
			// P0.4: Enhanced logging for context injection validation
			var contextMap map[string]interface{}
			if jsonErr := json.Unmarshal([]byte(userContextJSON), &contextMap); jsonErr == nil {
				pendingTasksCount := 0
				activePlansCount := 0
				focusMinutes := 0
				recentProgressCount := 0

				if tasks, ok := contextMap["pending_tasks"].([]interface{}); ok {
					pendingTasksCount = len(tasks)
				}
				if plans, ok := contextMap["active_plans"].([]interface{}); ok {
					activePlansCount = len(plans)
				}
				if stats, ok := contextMap["focus_stats"].(map[string]interface{}); ok {
					if mins, ok := stats["total_minutes_today"].(float64); ok {
						focusMinutes = int(mins)
					}
				}
				if progress, ok := contextMap["recent_progress"].([]interface{}); ok {
					recentProgressCount = len(progress)
				}

				log.Printf("[CONTEXT] User=%s, PendingTasks=%d, ActivePlans=%d, FocusMinutes=%dm, RecentProgress=%d, Size=%dB, Latency=%dms",
					hashUserIDForLog(userID), pendingTasksCount, activePlansCount, focusMinutes, recentProgressCount,
					len(userContextJSON), contextFetchLatency.Milliseconds())
			} else {
				log.Printf("[CONTEXT] User=%s, Size=%dB, Latency=%dms (JSON parse error: %v)",
					hashUserIDForLog(userID), len(userContextJSON), contextFetchLatency.Milliseconds(), jsonErr)
			}
		}
	}

	if traceID != "" {
		log.Printf("Chat request trace_id=%s user_id=%s session_id=%s request_id=%s", traceID, hashUserIDForLog(userID), input.SessionID, reqID)
	}

	// P0: Semantic Cache Check (scoped by user + mode, after context resolution)
	normalizedChatMode := normalizeChatMode(input.ChatMode)
	useDocumentContext := defaultUseDocumentContextForMode(normalizedChatMode)
	documentFilter := append([]string(nil), input.DocumentFilter...)
	if h.chatHistory != nil && input.SessionID != "" {
		if stored, ok, err := h.chatHistory.GetConversationSettings(ctx, userID, input.SessionID); err != nil {
			log.Printf("Failed to load conversation settings for session=%s: %v", input.SessionID, err)
		} else if ok && stored != nil {
			useDocumentContext = stored.UseDocumentContext
			if len(input.DocumentFilter) == 0 {
				documentFilter = append([]string(nil), stored.DocumentFilter...)
			}
		}
		if input.UseDocumentContext != nil {
			useDocumentContext = *input.UseDocumentContext
		}
		if input.UseDocumentContext != nil || len(input.DocumentFilter) > 0 {
			updated, err := h.chatHistory.UpdateConversationSettings(ctx, userID, input.SessionID, service.ConversationSettings{
				UseDocumentContext: useDocumentContext,
				DocumentFilter:     documentFilter,
			})
			if err != nil {
				log.Printf("Failed to update conversation settings for session=%s: %v", input.SessionID, err)
			} else if updated != nil {
				useDocumentContext = updated.UseDocumentContext
				documentFilter = append([]string(nil), updated.DocumentFilter...)
			}
		}
	} else if input.UseDocumentContext != nil {
		useDocumentContext = *input.UseDocumentContext
	}
	if input.UseDocumentContext != nil && (h.chatHistory == nil || input.SessionID == "") {
		useDocumentContext = *input.UseDocumentContext
	}
	extraContext := ensureChatExtraContext(input)
	extraContext["use_document_context"] = useDocumentContext
	extraContext["document_filter"] = documentFilter
	extraContext["conversation_settings"] = map[string]interface{}{
		"use_document_context": useDocumentContext,
		"document_filter":      documentFilter,
	}
	if len(documentFilter) > 0 {
		extraContext["selected_document_ids"] = documentFilter
	}

	// Load conversation history from Redis for session context restoration.
	// This is critical for WS reconnects: without it, Python receives empty
	// history and treats the request as a new conversation.
	var historyMessages []*agentv1.ChatMessage
	sessionHasHistory := false
	if input.SessionID != "" && h.chatHistory != nil {
		msgs, histErr := h.chatHistory.GetMessages(ctx, userID, input.SessionID, 20, 0)
		if histErr == nil {
			for _, m := range msgs {
				historyMessages = append(historyMessages, &agentv1.ChatMessage{
					Role:    m.Role,
					Content: m.Content,
				})
			}
			sessionHasHistory = len(historyMessages) > 0
		} else {
			log.Printf("[chatflow] history load failed for session=%s user=%s: %v", input.SessionID, hashUserIDForLog(userID), histErr)
		}
	}

	cacheScope := semanticCacheScope(
		userID,
		normalizedChatMode,
		userContextJSON,
		input.FileIds,
		input.IncludeReferences,
		input.ActiveTools,
		input.ExtraContext,
	)
	// Skip cache when request carries orchestration-bearing fields
	// (active_tools, tool results, or extra_context) — these must hit
	// the Python orchestrator to preserve graph/tool/HITL behavior.
	// Also skip when session has existing history: in a multi-turn
	// conversation, the same words mean different things depending on
	// what was said before, so cached responses from earlier turns are
	// stale and incorrect.
	shouldSkipCache := len(input.ActiveTools) > 0 || input.IsToolResult || len(input.ExtraContext) > 0 || sessionHasHistory
	if h.semantic != nil && !shouldSkipCache {
		cacheCtx, cacheSpan := tracer.Start(ctx, "semantic_cache.search")
		cachedResp, err := h.semantic.SearchExact(cacheCtx, cacheScope, input.Message)
		cacheSpan.End()

		if err == nil && cachedResp != "" {
			isCacheHit = true
			log.Printf("Semantic cache hit for user=%s scope=%s", hashUserIDForLog(userID), cacheScope)

			// Construct cached response
			now := time.Now()
			resp := &agentv1.ChatResponse{
				ResponseId:    uuid.New().String(),
				CreatedAt:     now.Unix(),
				RequestId:     reqID,
				TraceId:       traceID,
				WorkflowId:    workflowIDForChatMode(normalizedChatMode),
				PromptVersion: "v1",
				Content:       &agentv1.ChatResponse_FullText{FullText: cachedResp},
				FinishReason:  agentv1.FinishReason_STOP,
				EventTime:     timestamppb.New(now),
			}

			// Send response
			switch r := responder.(type) {
			case *envelopeResponder:
				if err := r.SendChatResponse(resp); err != nil {
					logWebSocketWriteError("cached envelope chat response", err)
					return true
				}
				if err := r.SendMeta(map[string]interface{}{
					"latency_ms":   time.Since(startTime).Milliseconds(),
					"is_cache_hit": true,
				}); err != nil {
					logWebSocketWriteError("cached envelope metadata", err)
					return true
				}
			case *protobufResponder:
				if err := r.SendChatResponse(resp); err != nil {
					logWebSocketWriteError("cached protobuf chat response", err)
					return true
				}
				if err := r.SendMeta(map[string]interface{}{
					"latency_ms":   time.Since(startTime).Milliseconds(),
					"is_cache_hit": true,
				}); err != nil {
					logWebSocketWriteError("cached protobuf metadata", err)
					return true
				}
			case *wsSafeWriter:
				if !writeLegacyJSONLogged(r, "cached legacy chat response", convertResponseToJSON(ctx, resp)) {
					return true
				}
				if !writeLegacyJSONLogged(r, "cached legacy metadata", gin.H{
					"type": "meta",
					"meta": map[string]interface{}{
						"latency_ms":   time.Since(startTime).Milliseconds(),
						"is_cache_hit": true,
					},
				}) {
					return true
				}
			}

			return false
		}
	}

	var dailyLimit int64
	var dailyUsageStart int64
	if h.quota != nil {
		dailyLimit = cachedDailyQuota()
		if dailyLimit > 0 && !isDevelopmentEnv() {
			if usage, err := h.quota.GetDailyUsage(ctx, userID); err == nil {
				dailyUsageStart = usage
			} else {
				log.Printf("Failed to load daily usage: %v", err)
			}
		}
	}

	sessionID := input.SessionID
	if sessionID == "" {
		sessionID = uuid.New().String()
		log.Printf("Generated new session_id=%s for user=%s (client sent empty)", sessionID, hashUserIDForLog(userID))
	}
	// Build ChatRequest
	req := &agentv1.ChatRequest{
		RequestId:         reqID,
		UserId:            userID,
		SessionId:         sessionID,
		History:           historyMessages,
		FileIds:           input.FileIds,
		DocumentFilter:    documentFilter,
		IncludeReferences: input.IncludeReferences,
		ActiveTools:       input.ActiveTools,
		ChatMode:          normalizedChatMode,
		UserProfile:       buildAgentUserProfile(input.Nickname, userContextJSON, profileSnapshot, resolvedUser),
	}
	req.UseDocumentContext = &useDocumentContext

	// Set input based on whether this is a tool result or a regular message
	if input.IsToolResult {
		req.Input = &agentv1.ChatRequest_ToolResult{
			ToolResult: &agentv1.ToolResult{
				ToolCallId:   input.ToolCallID,
				ToolName:     input.ToolName,
				ResultJson:   input.ToolResultJSON,
				IsError:      input.ToolIsError,
				ErrorMessage: input.ToolErrorMsg,
			},
		}
	} else {
		req.Input = &agentv1.ChatRequest_Message{
			Message: input.Message,
		}
	}
	if input.ExtraContext != nil {
		if extra, err := structpb.NewStruct(input.ExtraContext); err == nil {
			req.ExtraContext = extra
		}
	}

	if h.agentClient == nil {
		log.Printf("Agent client not initialized")
		switch r := responder.(type) {
		case *envelopeResponder:
			r.SendError("unavailable", "AI Service Unavailable", true)
		case *protobufResponder:
			r.SendError("unavailable", "AI Service Unavailable", true)
		case *wsSafeWriter:
			writeLegacyJSONLogged(r, "agent unavailable error", gin.H{"type": "message_nack", "message_id": requestID, "error_code": "service_unavailable", "error_message": "AI Service Unavailable", "retry_after_ms": 5000, "permanent": false})
		}
		return false
	}

	// Call Python Agent via gRPC (server-side streaming)
	grpcCtx, grpcSpan := tracer.Start(ctx, "grpc.agent_call")
	stream, err := h.agentClient.StreamChatWithFallback(grpcCtx, req)
	grpcSpan.End()

	if err != nil {
		log.Printf("Failed to call StreamChat: %v", err)
		switch r := responder.(type) {
		case *envelopeResponder:
			r.SendError("unavailable", "AI Service Unavailable", true)
		case *protobufResponder:
			r.SendError("unavailable", "AI Service Unavailable", true)
		case *wsSafeWriter:
			writeLegacyJSONLogged(r, "agent call unavailable error", gin.H{"type": "message_nack", "message_id": requestID, "error_code": "service_unavailable", "error_message": "AI Service Unavailable", "retry_after_ms": 5000, "permanent": false})
		}
		return false
	}

	// P1: Get string builder from pool for efficient text accumulation
	textBuilder := stringBuilderPool.Get().(*strings.Builder)
	textBuilder.Reset()
	defer func() {
		textBuilder.Reset()
		stringBuilderPool.Put(textBuilder)
	}()

	// Receive and forward streaming responses
	var fullText string
	var usageTotalTokens int64
	var segmentRecorded int64
	var segmentIndex int
	var outputRuneCount int
	var responseEventCount int64
	var sawAuroraRuntime bool
	var sawUpstreamFinishReason bool
	var firstEventAt time.Time
	var firstTokenAt time.Time
	segmentSize := cachedStreamTokenSegment()
	for {
		// Trace each streaming response
		_, streamSpan := tracer.Start(ctx, "stream.receive")
		resp, err := stream.Recv()
		streamSpan.End()

		if err == io.EOF {
			// Stream ended normally
			break
		}
		if err != nil {
			log.Printf("Stream recv error: %v", err)
			respondStreamRecvError(responder, err)
			if textBuilder.Len() > 0 && input.SessionID != "" {
				partialText := textBuilder.String()
				h.saveMessage(ctx, userID, input.SessionID, "assistant", partialText, map[string]interface{}{
					"trace_id":  traceID,
					"truncated": true,
				})
			}
			return false
		}

		// Accumulate full text for persistence using pooled builder
		if firstEventAt.IsZero() {
			firstEventAt = time.Now()
		}
		responseEventCount++
		if delta := resp.GetDelta(); delta != "" {
			textBuilder.WriteString(delta)
			outputRuneCount += countRunes(delta)
			if firstTokenAt.IsZero() {
				firstTokenAt = time.Now()
			}
		}
		if ft := resp.GetFullText(); ft != "" {
			textBuilder.Reset()
			textBuilder.WriteString(ft)
			outputRuneCount = countRunes(ft)
			if firstTokenAt.IsZero() {
				firstTokenAt = time.Now()
			}
		}
		if usage := resp.GetUsage(); usage != nil {
			usageTotalTokens = int64(usage.TotalTokens)
		}
		if isAuroraRuntimeResponse(resp) {
			sawAuroraRuntime = true
		}
		if resp.GetFinishReason() != agentv1.FinishReason_NULL {
			sawUpstreamFinishReason = true
		}

		if h.quota != nil && segmentSize > 0 {
			estimatedTokens := estimateTokensFromRunes(outputRuneCount)
			for estimatedTokens-segmentRecorded >= segmentSize {
				if dailyLimit > 0 && dailyUsageStart+segmentRecorded+segmentSize > dailyLimit {
					log.Printf("Daily quota exceeded mid-stream user=%s request=%s", hashUserIDForLog(userID), reqID)
					cancel()
					switch r := responder.(type) {
					case *envelopeResponder:
						r.SendError("resource_exhausted", "Daily quota exceeded", false)
					case *protobufResponder:
						r.SendError("resource_exhausted", "Daily quota exceeded", false)
					case *wsSafeWriter:
						writeLegacyJSONLogged(r, "daily quota error", gin.H{"type": "message_nack", "message_id": requestID, "error_code": "quota_exceeded", "error_message": "Daily quota exceeded", "retry_after_ms": 60000, "permanent": false})
					}
					return false
				}
				segmentIndex++
				if _, err := h.quota.RecordUsageSegment(ctx, userID, reqID, segmentIndex, segmentSize, 24*time.Hour); err != nil {
					log.Printf("Failed to record usage segment: %v", err)
					break
				}
				segmentRecorded += segmentSize
			}
		}

		// Trace response processing and forwarding
		_, respSpan := tracer.Start(ctx, "stream.process_response")
		switch r := responder.(type) {
		case *envelopeResponder:
			if err := r.SendChatResponse(resp); err != nil {
				log.Printf("Failed to write to WebSocket: %v", err)
				respSpan.End()
				return true
			}
		case *protobufResponder:
			if err := r.SendChatResponse(resp); err != nil {
				log.Printf("Failed to write to WebSocket: %v", err)
				respSpan.End()
				return true
			}
		case *wsSafeWriter:
			// Convert protobuf response to JSON-friendly map
			jsonResp := convertResponseToJSON(ctx, resp)
			// Forward to WebSocket client
			if err := writeLegacyJSON(r, jsonResp); err != nil {
				log.Printf("Failed to write to WebSocket: %v", err)
				respSpan.End()
				return true
			}
		}
		respSpan.End()
	}
	fullText = textBuilder.String()

	if h.quota != nil && usageTotalTokens > 0 {
		delta := usageTotalTokens - segmentRecorded
		if delta < 0 {
			delta = 0
		}
		if _, err := h.quota.RecordUsage(ctx, userID, reqID, delta, 24*time.Hour); err != nil {
			log.Printf("Failed to record usage: %v", err)
		}
	} else if h.quota != nil && usageTotalTokens == 0 {
		estimatedTokens := estimateTokensFromRunes(outputRuneCount)
		delta := estimatedTokens - segmentRecorded
		if delta < 0 {
			delta = 0
		}
		if _, err := h.quota.RecordUsage(ctx, userID, reqID, delta, 24*time.Hour); err != nil {
			log.Printf("Failed to record usage: %v", err)
		}
		if delta == 0 {
			log.Printf("Usage missing for request=%s user=%s", reqID, hashUserIDForLog(userID))
		}
	}

	// Add metadata for the final state
	latency := time.Since(startTime).Milliseconds()
	firstEventMs := int64(0)
	firstTokenMs := int64(0)
	streamDurationMs := int64(0)
	if !firstEventAt.IsZero() {
		firstEventMs = firstEventAt.Sub(startTime).Milliseconds()
	}
	if !firstTokenAt.IsZero() {
		firstTokenMs = firstTokenAt.Sub(startTime).Milliseconds()
		streamDurationMs = time.Since(firstTokenAt).Milliseconds()
	} else if !firstEventAt.IsZero() {
		streamDurationMs = time.Since(firstEventAt).Milliseconds()
	}
	normalizedMode := normalizedChatMode
	wsmetrics.AIChatTotalDuration.WithLabelValues(normalizedMode).Observe(float64(latency) / 1000.0)
	if firstEventMs > 0 {
		wsmetrics.AIChatFirstEventDuration.WithLabelValues(normalizedMode).Observe(float64(firstEventMs) / 1000.0)
	}
	if firstTokenMs > 0 {
		wsmetrics.AIChatFirstTokenDuration.WithLabelValues(normalizedMode).Observe(float64(firstTokenMs) / 1000.0)
	}
	if streamDurationMs > 0 {
		wsmetrics.AIChatStreamDuration.WithLabelValues(normalizedMode).Observe(float64(streamDurationMs) / 1000.0)
	}
	qLen, _ := h.chatHistory.GetQueueLength(ctx)
	threshold := h.chatHistory.GetBreakerThreshold()

	meta := map[string]interface{}{
		"latency_ms":           latency,
		"total_duration_ms":    latency,
		"first_event_ms":       firstEventMs,
		"first_token_ms":       firstTokenMs,
		"stream_duration_ms":   streamDurationMs,
		"response_event_count": responseEventCount,
		"is_cache_hit":         isCacheHit,
		"cost_saved":           0.0,
		"breaker_status":       "closed",
	}
	if qLen >= threshold {
		meta["breaker_status"] = "open"
	}

	switch r := responder.(type) {
	case *envelopeResponder:
		if err := r.SendMeta(meta); err != nil {
			logWebSocketWriteError("envelope metadata", err)
			return true
		}
	case *protobufResponder:
		if err := r.SendMeta(meta); err != nil {
			logWebSocketWriteError("protobuf metadata", err)
			return true
		}
	case *wsSafeWriter:
		// Send final metadata
		if !writeLegacyJSONLogged(r, "legacy metadata", gin.H{
			"type": "meta",
			"meta": meta,
		}) {
			return true
		}
	}

	doneResp := &agentv1.ChatResponse{
		ResponseId:    uuid.New().String(),
		CreatedAt:     time.Now().Unix(),
		RequestId:     reqID,
		TraceId:       traceID,
		WorkflowId:    workflowIDForChatMode(normalizedChatMode),
		PromptVersion: "v1",
		SessionId:     input.SessionID,
		FinishReason:  agentv1.FinishReason_STOP,
		EventTime:     timestamppb.New(time.Now()),
	}

	if shouldEmitSyntheticDone(sawAuroraRuntime, sawUpstreamFinishReason) {
		switch r := responder.(type) {
		case *envelopeResponder:
			if err := r.SendChatResponse(doneResp); err != nil {
				logWebSocketWriteError("envelope synthetic done", err)
				return true
			}
		case *protobufResponder:
			if err := r.SendChatResponse(doneResp); err != nil {
				logWebSocketWriteError("protobuf synthetic done", err)
				return true
			}
		case *wsSafeWriter:
			if !writeLegacyJSONLogged(r, "legacy synthetic done", convertResponseToJSON(ctx, doneResp)) {
				return true
			}
		}
	}

	// Persist completed message to database and cache (async)
	if fullText != "" && input.SessionID != "" {
		// Multi-turn chat depends on the assistant turn being visible in Redis
		// before the client sends the next user message, so persist history
		// synchronously and keep only semantic-cache updates async.
		sessionID := input.SessionID
		queryText := input.Message
		result := fullText

		h.saveMessage(ctx, userID, sessionID, "assistant", result, map[string]interface{}{
			"meta":           meta,
			"workflow_id":    doneResp.WorkflowId,
			"prompt_version": doneResp.PromptVersion,
			"trace_id":       traceID,
			"response_id":    doneResp.ResponseId,
		})

		cacheCtx, cancelCache := context.WithTimeout(context.WithoutCancel(ctx), 5*time.Second)
		go func() {
			defer cancelCache()
			// Update Semantic Cache
			if h.semantic != nil {
				if err := h.semantic.SetExact(cacheCtx, cacheScope, queryText, result); err != nil {
					log.Printf("Failed to update cache: %v", err)
				}
			}
		}()
	}

	return false
}

func respondStreamRecvError(responder interface{}, err error) {
	code, message, retryable := grpcStreamErrorDetails(err)
	switch r := responder.(type) {
	case *envelopeResponder:
		r.SendError(code, message, retryable)
	case *protobufResponder:
		r.SendError(code, message, retryable)
	case *wsSafeWriter:
		writeLegacyJSONLogged(r, "stream error", legacyStreamErrorPayload(code, message, retryable))
	}
}

func grpcStreamErrorDetails(err error) (string, string, bool) {
	message := "Stream interrupted"
	retryable := true
	if err == nil {
		return "unknown", message, retryable
	}

	st, ok := grpcstatus.FromError(err)
	if !ok {
		return "unknown", defaultWSInternalMessage, retryable
	}

	if strings.TrimSpace(st.Message()) != "" {
		message = st.Message()
	}

	switch st.Code() {
	case codes.InvalidArgument:
		return "invalid_argument", message, false
	case codes.Unauthenticated:
		return "unauthorized", message, false
	case codes.PermissionDenied:
		return "forbidden", message, false
	case codes.NotFound:
		return "not_found", message, false
	case codes.AlreadyExists, codes.Aborted:
		return "conflict", message, true
	case codes.ResourceExhausted:
		return "resource_exhausted", message, false
	case codes.DeadlineExceeded:
		return "timeout", message, true
	case codes.Unavailable:
		return "unavailable", message, true
	case codes.Internal, codes.DataLoss:
		return "internal", publicStreamErrorMessage("internal", message), true
	default:
		return "unknown", publicStreamErrorMessage("unknown", message), retryable
	}
}

func legacyStreamErrorPayload(code, message string, retryable bool) gin.H {
	return gin.H{
		"type":       "error",
		"message":    message,
		"error_code": code,
		"retryable":  retryable,
	}
}

func estimateTokensFromRunes(runes int) int64 {
	if runes <= 0 {
		return 0
	}
	estimated := int64(float64(runes) * 1.5)
	if estimated < 1 {
		return 1
	}
	return estimated
}

func countRunes(text string) int {
	return len([]rune(text))
}

// Cached env vars to avoid os.Getenv on every request.
var (
	dailyQuotaOnce      sync.Once
	dailyQuotaValue     int64
	streamTokenSegOnce  sync.Once
	streamTokenSegValue int64
)

func cachedDailyQuota() int64 {
	dailyQuotaOnce.Do(func() {
		dailyQuotaValue = getEnvInt64("DAILY_QUOTA", 100000)
	})
	return dailyQuotaValue
}

func cachedStreamTokenSegment() int64 {
	streamTokenSegOnce.Do(func() {
		streamTokenSegValue = getEnvInt64("STREAM_TOKEN_SEGMENT", 200)
	})
	return streamTokenSegValue
}
