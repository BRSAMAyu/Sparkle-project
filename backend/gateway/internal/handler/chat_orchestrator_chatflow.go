package handler

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"sort"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	wsmetrics "github.com/sparkle/gateway/internal/metrics"
	"github.com/sparkle/gateway/internal/service"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/protobuf/types/known/structpb"
	"google.golang.org/protobuf/types/known/timestamppb"
)

const (
	defaultChatMode = "standard"
	expertModeAuto  = "expert_auto"
	expertModePref  = "expert::"
	teamModePref    = "team::"
)

func shortHash(parts ...string) string {
	h := sha1.New()
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

func semanticCacheScope(userID, chatMode, userContextJSON string, fileIDs []string, includeReferences bool) string {
	sortedFileIDs := append([]string(nil), fileIDs...)
	sort.Strings(sortedFileIDs)

	referencesFlag := "refs_off"
	if includeReferences {
		referencesFlag = "refs_on"
	}

	contextHash := shortHash(userContextJSON)
	fileHash := shortHash(strings.Join(sortedFileIDs, ","))

	return fmt.Sprintf(
		"user:%s|mode:%s|ctx:%s|files:%s|%s",
		userID,
		normalizeChatMode(chatMode),
		contextHash,
		fileHash,
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

func (h *ChatOrchestrator) resolveUserUUID(ctx context.Context, userID string) (uuid.UUID, string, error) {
	if parsed, err := uuid.Parse(userID); err == nil {
		return parsed, userID, nil
	}

	if h.queries == nil {
		return uuid.Nil, userID, nil
	}

	user, err := h.queries.GetUserByEmail(ctx, userID)
	if err != nil {
		return uuid.Nil, userID, nil
	}
	if !user.ID.Valid {
		return uuid.Nil, userID, nil
	}

	parsed, err := uuid.FromBytes(user.ID.Bytes[:])
	if err != nil {
		return uuid.Nil, userID, nil
	}
	return parsed, parsed.String(), nil
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

	// Sanitize Input (Security Hygiene) - reuse global sanitizer
	input.Message = sanitizer.Sanitize(input.Message)

	// Persist user message to Redis history for context pruning
	if input.SessionID != "" {
		sessionID := input.SessionID
		message := input.Message
		go h.saveMessage(userID, sessionID, "user", message)
	}

	startTime := time.Now()
	isCacheHit := false
	traceID := ""
	if span := trace.SpanFromContext(ctx); span.SpanContext().IsValid() {
		traceID = span.SpanContext().TraceID().String()
	}

	// Resolve user identity to UUID (token sub may be email)
	userUUID, resolvedUserID, _ := h.resolveUserUUID(ctx, userID)
	if resolvedUserID != "" {
		userID = resolvedUserID
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
				userID, contextFetchLatency.Milliseconds(), err)
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
					userID, pendingTasksCount, activePlansCount, focusMinutes, recentProgressCount,
					len(userContextJSON), contextFetchLatency.Milliseconds())
			} else {
				log.Printf("[CONTEXT] User=%s, Size=%dB, Latency=%dms (JSON parse error: %v)",
					userID, len(userContextJSON), contextFetchLatency.Milliseconds(), jsonErr)
			}
		}
	}

	reqID := requestID
	if reqID == "" {
		reqID = fmt.Sprintf("req_%s", uuid.New().String())
	}
	if traceID != "" {
		log.Printf("Chat request trace_id=%s user_id=%s session_id=%s request_id=%s", traceID, userID, input.SessionID, reqID)
	}

	// P0: Semantic Cache Check (scoped by user + mode, after context resolution)
	normalizedChatMode := normalizeChatMode(input.ChatMode)
	cacheScope := semanticCacheScope(
		userID,
		normalizedChatMode,
		userContextJSON,
		input.FileIds,
		input.IncludeReferences,
	)
	if h.semantic != nil {
		cacheCtx, cacheSpan := tracer.Start(ctx, "semantic_cache.search")
		cachedResp, err := h.semantic.SearchExact(cacheCtx, cacheScope, input.Message)
		cacheSpan.End()

		if err == nil && cachedResp != "" {
			isCacheHit = true
			log.Printf("Semantic cache hit for user=%s scope=%s", userID, cacheScope)

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
				_ = r.SendChatResponse(resp)
				_ = r.SendMeta(map[string]interface{}{
					"latency_ms":   time.Since(startTime).Milliseconds(),
					"is_cache_hit": true,
				})
			case *protobufResponder:
				_ = r.SendChatResponse(resp)
				_ = r.SendMeta(map[string]interface{}{
					"latency_ms":   time.Since(startTime).Milliseconds(),
					"is_cache_hit": true,
				})
			case *wsSafeWriter:
				_ = writeLegacyJSON(r, convertResponseToJSON(resp))
				_ = writeLegacyJSON(r, gin.H{
					"type": "meta",
					"meta": map[string]interface{}{
						"latency_ms":   time.Since(startTime).Milliseconds(),
						"is_cache_hit": true,
					},
				})
			}

			return false
		}
	}

	var dailyLimit int64
	var dailyUsageStart int64
	skipQuota := false
	if h.quota != nil {
		dailyLimit = getEnvInt64("DAILY_QUOTA", 100000)
		if dailyLimit <= 0 || isDevelopmentEnv() {
			skipQuota = true
		} else {
			if usage, err := h.quota.GetDailyUsage(ctx, userID); err == nil {
				dailyUsageStart = usage
			} else {
				log.Printf("Failed to load daily usage: %v", err)
			}
		}
	}

	if h.quota != nil && !skipQuota {
		quotaCtx, quotaSpan := tracer.Start(ctx, "quota.reserve")
		remaining, err := h.quota.ReserveRequest(quotaCtx, userID, reqID, 24*time.Hour)
		quotaSpan.End()

		if err != nil {
			if err == service.ErrQuotaInsufficient {
				log.Printf("Quota exhausted for user=%s request=%s", userID, reqID)
				switch r := responder.(type) {
				case *envelopeResponder:
					r.SendError("resource_exhausted", "Quota exhausted", false)
				case *protobufResponder:
					r.SendError("resource_exhausted", "Quota exhausted", false)
				case *wsSafeWriter:
					_ = writeLegacyJSON(r, gin.H{"type": "error", "message": "Quota exhausted"})
				}
				return false
			}
			log.Printf("Failed to reserve quota: %v", err)
		} else {
			span := trace.SpanFromContext(ctx)
			span.SetAttributes(attribute.Int64("quota_remaining", remaining))
		}
	}

	// Build ChatRequest
	req := &agentv1.ChatRequest{
		RequestId: reqID,
		UserId:    userID,
		SessionId: input.SessionID,
		Input: &agentv1.ChatRequest_Message{
			Message: input.Message,
		},
		FileIds:           input.FileIds,
		IncludeReferences: input.IncludeReferences,
		ChatMode:          normalizedChatMode,
		UserProfile: &agentv1.UserProfile{
			Nickname:     input.Nickname,
			Timezone:     "Asia/Shanghai",
			Language:     "zh-CN",
			ExtraContext: userContextJSON, // P0: Inject user context here
		},
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
			_ = writeLegacyJSON(r, gin.H{"type": "error", "message": "AI Service Unavailable"})
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
			_ = writeLegacyJSON(r, gin.H{"type": "error", "message": "AI Service Unavailable"})
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
	var firstEventAt time.Time
	var firstTokenAt time.Time
	segmentSize := getEnvInt64("STREAM_TOKEN_SEGMENT", 200)
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
			switch r := responder.(type) {
			case *envelopeResponder:
				r.SendError("aborted", "Stream interrupted", true)
			case *protobufResponder:
				r.SendError("aborted", "Stream interrupted", true)
			case *wsSafeWriter:
				_ = writeLegacyJSON(r, gin.H{"type": "error", "message": "Stream interrupted"})
			}
			break
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

		if h.quota != nil && segmentSize > 0 {
			estimatedTokens := estimateTokensFromRunes(outputRuneCount)
			for estimatedTokens-segmentRecorded >= segmentSize {
				if dailyLimit > 0 && dailyUsageStart+segmentRecorded+segmentSize > dailyLimit {
					log.Printf("Daily quota exceeded mid-stream user=%s request=%s", userID, reqID)
					cancel()
					switch r := responder.(type) {
					case *envelopeResponder:
						r.SendError("resource_exhausted", "Daily quota exceeded", false)
					case *protobufResponder:
						r.SendError("resource_exhausted", "Daily quota exceeded", false)
					case *wsSafeWriter:
						_ = writeLegacyJSON(r, gin.H{"type": "error", "message": "Daily quota exceeded"})
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
			jsonResp := convertResponseToJSON(resp)
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
			log.Printf("Usage missing for request=%s user=%s", reqID, userID)
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
		_ = r.SendMeta(meta)
	case *protobufResponder:
		_ = r.SendMeta(meta)
	case *wsSafeWriter:
		// Send final metadata
		_ = writeLegacyJSON(r, gin.H{
			"type": "meta",
			"meta": meta,
		})
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

	switch r := responder.(type) {
	case *envelopeResponder:
		_ = r.SendChatResponse(doneResp)
	case *protobufResponder:
		_ = r.SendChatResponse(doneResp)
	case *wsSafeWriter:
		_ = writeLegacyJSON(r, convertResponseToJSON(doneResp))
	}

	// Persist completed message to database and cache (async)
	if fullText != "" && input.SessionID != "" {
		// Multi-turn chat depends on the assistant turn being visible in Redis
		// before the client sends the next user message, so persist history
		// synchronously and keep only semantic-cache updates async.
		sessionID := input.SessionID
		queryText := input.Message
		result := fullText

		h.saveMessage(userID, sessionID, "assistant", result)

		go func() {
			// Update Semantic Cache
			if h.semantic != nil {
				if err := h.semantic.SetExact(context.Background(), cacheScope, queryText, result); err != nil {
					log.Printf("Failed to update cache: %v", err)
				}
			}
		}()
	}

	return false
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
