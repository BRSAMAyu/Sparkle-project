package service

import (
	"context"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
)

const (
	MaxQueueSize   = 10000
	ChatHistoryTTL = 30 * time.Minute
)

type ChatHistoryService struct {
	rdb *redis.Client
}

func NewChatHistoryService(rdb *redis.Client) *ChatHistoryService {
	return &ChatHistoryService{rdb: rdb}
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

	if qLen < MaxQueueSize {
		pipe.RPush(ctx, queueKey, msg)
	} else {
		// Circuit Breaker triggered
		log.Printf("Persistence queue overloaded (%d), dropping message for session %s", qLen, sid)
		// We execute the pipeline (to save to cache) but skip the DB queue push.
	}

	_, err = pipe.Exec(ctx)
	return err
}
