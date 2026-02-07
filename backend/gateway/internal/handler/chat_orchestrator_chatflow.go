package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/service"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/protobuf/types/known/structpb"
	"google.golang.org/protobuf/types/known/timestamppb"
)

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

	// Set timeout for the entire chat message processing
	// Default 60s, configurable via GRPC_TIMEOUT_SECONDS
	timeoutSeconds := 60
	if h.cfg != nil && h.cfg.GRPCTimeoutSeconds > 0 {
		timeoutSeconds = h.cfg.GRPCTimeoutSeconds
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

	// P0: Semantic Cache Check
	if h.semantic != nil {
		cacheCtx, cacheSpan := tracer.Start(ctx, "semantic_cache.search")
		cachedResp, err := h.semantic.SearchExact(cacheCtx, input.Message)
		cacheSpan.End()

		if err == nil && cachedResp != "" {
			isCacheHit = true
			log.Printf("Semantic cache hit for user=%s", userID)

			// Construct cached response
			now := time.Now()
			resp := &agentv1.ChatResponse{
				ResponseId:    uuid.New().String(),
				CreatedAt:     now.Unix(),
				RequestId:     requestID,
				TraceId:       traceID,
				WorkflowId:    "standard_chat",
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
			default:
				conn := responder.(*websocket.Conn)
				conn.WriteJSON(convertResponseToJSON(resp, input.SessionID))
				conn.WriteJSON(gin.H{
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
				default:
					conn := responder.(*websocket.Conn)
					conn.WriteJSON(gin.H{"type": "error", "message": "Quota exhausted"})
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
		ChatMode:          input.ChatMode,
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
		default:
			conn := responder.(*websocket.Conn)
			conn.WriteJSON(gin.H{"type": "error", "message": "AI Service Unavailable"})
		}
		return false
	}

	// Call Python Agent via gRPC (server-side streaming)
	grpcCtx, grpcSpan := tracer.Start(ctx, "grpc.agent_call")
	stream, err := h.agentClient.StreamChat(grpcCtx, req)
	grpcSpan.End()

	if err != nil {
		log.Printf("Failed to call StreamChat: %v", err)
		switch r := responder.(type) {
		case *envelopeResponder:
			r.SendError("unavailable", "AI Service Unavailable", true)
		default:
			conn := responder.(*websocket.Conn)
			conn.WriteJSON(gin.H{"type": "error", "message": "AI Service Unavailable"})
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
			default:
				conn := responder.(*websocket.Conn)
				conn.WriteJSON(gin.H{"type": "error", "message": "Stream interrupted"})
			}
			break
		}

		// Accumulate full text for persistence using pooled builder
		if delta := resp.GetDelta(); delta != "" {
			textBuilder.WriteString(delta)
			outputRuneCount += countRunes(delta)
		}
		if ft := resp.GetFullText(); ft != "" {
			textBuilder.Reset()
			textBuilder.WriteString(ft)
			outputRuneCount = countRunes(ft)
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
					default:
						conn := responder.(*websocket.Conn)
						conn.WriteJSON(gin.H{"type": "error", "message": "Daily quota exceeded"})
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
		default:
			conn := responder.(*websocket.Conn)
			// Convert protobuf response to JSON-friendly map
			jsonResp := convertResponseToJSON(resp, input.SessionID)
			// Forward to WebSocket client
			if err := conn.WriteJSON(jsonResp); err != nil {
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
	qLen, _ := h.chatHistory.GetQueueLength(ctx)
	threshold := h.chatHistory.GetBreakerThreshold()

	meta := map[string]interface{}{
		"latency_ms":     latency,
		"is_cache_hit":   isCacheHit,
		"cost_saved":     0.0,
		"breaker_status": "closed",
	}
	if qLen >= threshold {
		meta["breaker_status"] = "open"
	}

	switch r := responder.(type) {
	case *envelopeResponder:
		_ = r.SendMeta(meta)
	default:
		conn := responder.(*websocket.Conn)
		// Send final metadata
		conn.WriteJSON(gin.H{
			"type": "meta",
			"meta": meta,
		})
	}

	// Persist completed message to database and cache (async)
	if fullText != "" && input.SessionID != "" {
		// Capture values for goroutine before returning input to pool
		sessionID := input.SessionID
		result := fullText

		go func() {
			// Update Semantic Cache
			if h.semantic != nil {
				if err := h.semantic.SetExact(context.Background(), input.Message, result); err != nil {
					log.Printf("Failed to update cache: %v", err)
				}
			}
			// Save to History
			h.saveMessage(userID, sessionID, "assistant", result)
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
