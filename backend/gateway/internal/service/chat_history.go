package service

import (
	"context"
	"log"
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
}

func NewChatHistoryService(rdb *redis.Client) *ChatHistoryService {
	s := &ChatHistoryService{rdb: rdb}
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

func (s *ChatHistoryService) SaveMessage(ctx context.Context, sid string, msg []byte) error {
	pipe := s.rdb.Pipeline()

	// 1. Write to cache (for AI context, with TTL)
	cacheKey := "chat:history:" + sid
	pipe.RPush(ctx, cacheKey, msg)
	pipe.LTrim(ctx, cacheKey, -20, -1) // Keep last 20 messages
	pipe.Expire(ctx, cacheKey, ChatHistoryTTL)

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
		log.Printf("Persistence queue overloaded (%d/%d), dropping message for session %s", qLen, threshold, sid)
		// We execute the pipeline (to save to cache) but skip the DB queue push.
	}

	_, err = pipe.Exec(ctx)
	return err
}