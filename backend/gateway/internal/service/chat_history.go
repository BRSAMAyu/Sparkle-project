package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sort"
	"strconv"
	"strings"
	"sync/atomic"
	"time"

	"github.com/redis/go-redis/v9"
)

const (
	DefaultMaxQueueSize = 10000
	ChatHistoryTTL      = 30 * time.Minute
)

type ChatHistoryService struct {
	rdb              *redis.Client
	breakerThreshold atomic.Int64
	chatHistoryTTL   time.Duration
}

type ChatHistoryMessage struct {
	SessionID string `json:"session_id"`
	UserID    string `json:"user_id"`
	Role      string `json:"role"`
	Content   string `json:"content"`
	Timestamp string `json:"timestamp"`
}

type ChatSessionSummary struct {
	ID        string `json:"id"`
	Title     string `json:"title"`
	UpdatedAt string `json:"updated_at"`
}

func NewChatHistoryService(rdb *redis.Client) *ChatHistoryService {
	return NewChatHistoryServiceWithTTL(rdb, ChatHistoryTTL)
}

func NewChatHistoryServiceWithTTL(rdb *redis.Client, ttl time.Duration) *ChatHistoryService {
	s := &ChatHistoryService{
		rdb:            rdb,
		chatHistoryTTL: ttl,
	}
	s.breakerThreshold.Store(DefaultMaxQueueSize)
	return s
}

// SetBreakerThreshold updates the circuit breaker limit dynamically
func (s *ChatHistoryService) SetBreakerThreshold(val int64) {
	s.breakerThreshold.Store(val)
}

// GetBreakerThreshold returns the current limit
func (s *ChatHistoryService) GetBreakerThreshold() int64 {
	return s.breakerThreshold.Load()
}

// GetQueueLength returns the current persistent queue size
func (s *ChatHistoryService) GetQueueLength(ctx context.Context) (int64, error) {
	return s.rdb.LLen(ctx, "queue:persist:history").Result()
}

// PublishConnectionEvent publishes a WebSocket connection event to Redis Pub/Sub
func (s *ChatHistoryService) PublishConnectionEvent(ctx context.Context, userID string, event string) error {
	if s.rdb == nil {
		return nil
	}

	eventKey := fmt.Sprintf("ws:connection:events:%s", userID)
	eventValue := fmt.Sprintf("%s:%d", event, time.Now().Unix())

	return s.rdb.Publish(ctx, eventKey, eventValue).Err()
}

func (s *ChatHistoryService) SaveMessage(ctx context.Context, sid string, msg []byte) error {
	pipe := s.rdb.Pipeline()

	// 1. Write to cache (for AI context, with TTL)
	cacheKey := "chat:history:" + sid
	pipe.RPush(ctx, cacheKey, msg)
	pipe.LTrim(ctx, cacheKey, -20, -1) // Keep last 20 messages
	pipe.Expire(ctx, cacheKey, s.chatHistoryTTL)

	// 2. Write to persistent queue (for DB, with Circuit Breaker)
	queueKey := "queue:persist:history"

	// Check queue length (Circuit Breaker)
	// We do this check outside the pipeline for simplicity, acknowledging the small race condition.
	// For strict atomicity, a Lua script could be used, but this is sufficient for OOM protection.
	qLen, err := s.rdb.LLen(ctx, queueKey).Result()
	if err != nil {
		// If Redis is reachable but LLEN fails, it's risky.
		// If Redis is unreachable, pipeline exec will fail anyway.
		log.Printf("Failed to check queue length: %v", err)
		return err
	}

	threshold := s.breakerThreshold.Load()
	if qLen < threshold {
		pipe.RPush(ctx, queueKey, msg)
	} else {
		// Circuit Breaker triggered
		// Return explicit error instead of silently dropping message
		return fmt.Errorf("persistence queue overloaded (%d/%d), retry later", qLen, threshold)
	}

	var payload ChatHistoryMessage
	if err := json.Unmarshal(msg, &payload); err == nil && payload.UserID != "" {
		sessionsKey := fmt.Sprintf("chat:sessions:user:%s", payload.UserID)
		metaKey := fmt.Sprintf("chat:session_meta:%s", sid)
		updatedAt := parseUnixString(payload.Timestamp)
		preview := strings.TrimSpace(payload.Content)
		if len(preview) > 120 {
			preview = preview[:120]
		}

		pipe.ZAdd(ctx, sessionsKey, redis.Z{
			Score:  float64(updatedAt.Unix()),
			Member: sid,
		})
		pipe.Expire(ctx, sessionsKey, s.chatHistoryTTL)
		fields := map[string]interface{}{
			"user_id":         payload.UserID,
			"last_preview":    preview,
			"last_message":    preview,
			"last_role":       payload.Role,
			"last_message_at": updatedAt.UTC().Format(time.RFC3339),
		}
		if payload.Role == "user" {
			fields["title"] = buildSessionTitle(payload.Role, payload.Content)
		}
		pipe.HSet(ctx, metaKey, fields)
		pipe.Expire(ctx, metaKey, s.chatHistoryTTL)
	}

	_, err = pipe.Exec(ctx)
	return err
}

func (s *ChatHistoryService) GetMessages(ctx context.Context, userID, sessionID string, limit, offset int) ([]ChatHistoryMessage, error) {
	if limit <= 0 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}

	metaKey := fmt.Sprintf("chat:session_meta:%s", sessionID)
	owner, err := s.rdb.HGet(ctx, metaKey, "user_id").Result()
	if err != nil && err != redis.Nil {
		return nil, err
	}
	if owner != "" && owner != userID {
		return nil, fmt.Errorf("forbidden")
	}

	cacheKey := "chat:history:" + sessionID
	raw, err := s.rdb.LRange(ctx, cacheKey, 0, -1).Result()
	if err != nil {
		if err == redis.Nil {
			return []ChatHistoryMessage{}, nil
		}
		return nil, err
	}

	messages := make([]ChatHistoryMessage, 0, len(raw))
	for _, item := range raw {
		var msg ChatHistoryMessage
		if err := json.Unmarshal([]byte(item), &msg); err != nil {
			continue
		}
		if msg.UserID != "" && msg.UserID != userID {
			continue
		}
		messages = append(messages, msg)
	}

	if offset >= len(messages) {
		return []ChatHistoryMessage{}, nil
	}

	end := offset + limit
	if end > len(messages) {
		end = len(messages)
	}
	return messages[offset:end], nil
}

func (s *ChatHistoryService) GetRecentSessions(ctx context.Context, userID string, limit int) ([]ChatSessionSummary, error) {
	if limit <= 0 {
		limit = 20
	}

	sessionsKey := fmt.Sprintf("chat:sessions:user:%s", userID)
	ids, err := s.rdb.ZRevRange(ctx, sessionsKey, 0, int64(limit-1)).Result()
	if err != nil {
		if err == redis.Nil {
			return []ChatSessionSummary{}, nil
		}
		return nil, err
	}

	summaries := make([]ChatSessionSummary, 0, len(ids))
	for _, sid := range ids {
		metaKey := fmt.Sprintf("chat:session_meta:%s", sid)
		meta, err := s.rdb.HGetAll(ctx, metaKey).Result()
		if err != nil || len(meta) == 0 {
			continue
		}
		if owner := meta["user_id"]; owner != "" && owner != userID {
			continue
		}
		title := strings.TrimSpace(meta["title"])
		if title == "" {
			title = "新对话"
		}
		updatedAt := meta["last_message_at"]
		summaries = append(summaries, ChatSessionSummary{
			ID:        sid,
			Title:     title,
			UpdatedAt: updatedAt,
		})
	}

	sort.SliceStable(summaries, func(i, j int) bool {
		return summaries[i].UpdatedAt > summaries[j].UpdatedAt
	})
	return summaries, nil
}

func parseUnixString(raw string) time.Time {
	if raw == "" {
		return time.Now().UTC()
	}
	seconds, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		return time.Now().UTC()
	}
	return time.Unix(seconds, 0).UTC()
}

func buildSessionTitle(role, content string) string {
	if role != "user" {
		return "新对话"
	}
	title := strings.TrimSpace(content)
	if title == "" {
		return "新对话"
	}
	runes := []rune(title)
	if len(runes) > 24 {
		title = string(runes[:24]) + "..."
	}
	return title
}
