package service

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// MessageDedupService provides message deduplication using Redis
// Prevents duplicate message processing within a configurable TTL window
type MessageDedupService struct {
	rdb       *redis.Client
	ttl       time.Duration // 默认 5 分钟
	keyPrefix string
}

// NewMessageDedupService creates a new message deduplication service
func NewMessageDedupService(rdb *redis.Client) *MessageDedupService {
	return &MessageDedupService{
		rdb:       rdb,
		ttl:       5 * time.Minute,
		keyPrefix: "msg_dedup",
	}
}

// NewMessageDedupServiceWithTTL creates a dedup service with custom TTL
func NewMessageDedupServiceWithTTL(rdb *redis.Client, ttl time.Duration) *MessageDedupService {
	return &MessageDedupService{
		rdb:       rdb,
		ttl:       ttl,
		keyPrefix: "msg_dedup",
	}
}

// CheckAndMark checks if a message is a duplicate, and marks it as processed if not
// Returns:
//   - isDup: true if the message was already processed (duplicate)
//   - error: non-nil if Redis operation failed
//
// Usage pattern:
//
//	isDup, err := dedup.CheckAndMark(ctx, userID, requestID)
//	if isDup {
//	    // Message is duplicate, skip processing but still send ACK
//	    return
//	}
func (s *MessageDedupService) CheckAndMark(ctx context.Context, userID, requestID string) (isDup bool, err error) {
	key := fmt.Sprintf("%s:%s:%s", s.keyPrefix, userID, requestID)

	// 使用 SETNX 原子操作 (Set if Not eXists)
	// 返回 true 表示设置成功（消息未重复）
	// 返回 false 表示 key 已存在（消息重复）
	ok, err := s.rdb.SetNX(ctx, key, "1", s.ttl).Result()
	if err != nil {
		return false, fmt.Errorf("redis SETNX failed: %w", err)
	}

	// 如果 SetNX 返回 false，说明 key 已存在，是重复消息
	return !ok, nil
}

// MarkProcessed explicitly marks a message as processed
// Useful for manual marking when you want to ensure a message is tracked
func (s *MessageDedupService) MarkProcessed(ctx context.Context, userID, requestID string) error {
	key := fmt.Sprintf("%s:%s:%s", s.keyPrefix, userID, requestID)
	return s.rdb.Set(ctx, key, "1", s.ttl).Err()
}

// IsProcessed checks if a message has been processed without marking it
// This is a read-only check
func (s *MessageDedupService) IsProcessed(ctx context.Context, userID, requestID string) (bool, error) {
	key := fmt.Sprintf("%s:%s:%s", s.keyPrefix, userID, requestID)
	exists, err := s.rdb.Exists(ctx, key).Result()
	if err != nil {
		return false, fmt.Errorf("redis EXISTS failed: %w", err)
	}
	return exists > 0, nil
}

// Clear removes the dedup record for a specific message
// Useful for testing or when you want to allow reprocessing
func (s *MessageDedupService) Clear(ctx context.Context, userID, requestID string) error {
	key := fmt.Sprintf("%s:%s:%s", s.keyPrefix, userID, requestID)
	return s.rdb.Del(ctx, key).Err()
}

// ClearAllForUser removes all dedup records for a specific user
// Use with caution - typically only needed for testing or account cleanup
func (s *MessageDedupService) ClearAllForUser(ctx context.Context, userID string) error {
	pattern := fmt.Sprintf("%s:%s:*", s.keyPrefix, userID)
	iter := s.rdb.Scan(ctx, 0, pattern, 0).Iterator()
	for iter.Next(ctx) {
		if err := s.rdb.Del(ctx, iter.Val()).Err(); err != nil {
			return err
		}
	}
	return iter.Err()
}
