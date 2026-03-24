package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/db"
)

type QuotaService struct {
	rdb *redis.Client
}

var ErrQuotaInsufficient = errors.New("quota_insufficient")

func NewQuotaService(rdb *redis.Client) *QuotaService {
	return &QuotaService{rdb: rdb}
}

// quotaPayload represents the JSON payload for DecrQuota operation
type quotaPayload struct {
	UID   string `json:"uid"`
	Delta int    `json:"delta"`
	TS    int64  `json:"ts"`
}

// reservePayload represents the JSON payload for ReserveRequest operation
type reservePayload struct {
	UID       string `json:"uid"`
	Delta     int    `json:"delta"`
	TS        int64  `json:"ts"`
	RequestID string `json:"request_id"`
	Type      string `json:"type"`
}

func (s *QuotaService) DecrQuota(ctx context.Context, uid string) (int64, error) {
	// Use script exported from internal/db
	script := redis.NewScript(db.DecrQuotaScript)

	// Use json.Marshal instead of fmt.Sprintf to prevent JSON injection
	payload, err := json.Marshal(quotaPayload{
		UID:   uid,
		Delta: -1,
		TS:    time.Now().Unix(),
	})
	if err != nil {
		return 0, fmt.Errorf("failed to marshal quota payload: %w", err)
	}

	val, err := script.Run(ctx, s.rdb,
		[]string{fmt.Sprintf("user:quota:%s", uid), "queue:sync:quota"}, // KEYS
		payload, // ARGV
	).Int64()

	return val, err
}

func (s *QuotaService) ReserveRequest(ctx context.Context, uid, requestID string, ttl time.Duration) (int64, error) {
	if requestID == "" {
		return 0, fmt.Errorf("request_id is required for reserve")
	}

	script := redis.NewScript(db.ReserveQuotaScript)

	// Use json.Marshal instead of fmt.Sprintf to prevent JSON injection
	payload, err := json.Marshal(reservePayload{
		UID:       uid,
		Delta:     -1,
		TS:        time.Now().Unix(),
		RequestID: requestID,
		Type:      "reserve",
	})
	if err != nil {
		return 0, fmt.Errorf("failed to marshal reserve payload: %w", err)
	}

	result, err := script.Run(ctx, s.rdb,
		[]string{
			fmt.Sprintf("user:quota:%s", uid),
			fmt.Sprintf("quota:request:%s:%s", uid, requestID),
			"queue:sync:quota",
		},
		payload,
		int64(ttl.Seconds()),
	).Slice()
	if err != nil {
		return 0, err
	}

	if len(result) < 2 {
		return 0, fmt.Errorf("unexpected reserve result")
	}

	status, ok := result[0].(int64)
	if !ok {
		return 0, fmt.Errorf("unexpected reserve status type")
	}

	remaining, ok := result[1].(int64)
	if !ok {
		return 0, fmt.Errorf("unexpected reserve remaining type")
	}

	if status == -1 {
		return remaining, ErrQuotaInsufficient
	}

	return remaining, nil
}

func (s *QuotaService) RecordUsage(ctx context.Context, uid, requestID string, totalTokens int64, ttl time.Duration) (bool, error) {
	if requestID == "" {
		return false, nil
	}

	script := redis.NewScript(db.RecordUsageScript)
	now := time.Now()
	dayKey := now.Format("2006-01-02")

	val, err := script.Run(ctx, s.rdb,
		[]string{
			fmt.Sprintf("llm_tokens:%s:%s", uid, dayKey),
			fmt.Sprintf("usage:request:%s:%s", uid, requestID),
		},
		fmt.Sprintf("%d", totalTokens),
		fmt.Sprintf("%d", int64(ttl.Seconds())),
		fmt.Sprintf("%d", int64((24 * time.Hour).Seconds())),
	).Int64()
	if err != nil {
		return false, err
	}

	return val == 1, nil
}

func (s *QuotaService) RecordUsageSegment(ctx context.Context, uid, requestID string, segment int, tokens int64, ttl time.Duration) (bool, error) {
	if requestID == "" || segment <= 0 || tokens <= 0 {
		return false, nil
	}

	script := redis.NewScript(db.RecordUsageSegmentScript)
	now := time.Now()
	dayKey := now.Format("2006-01-02")
	year, week := now.ISOWeek()

	val, err := script.Run(ctx, s.rdb,
		[]string{
			fmt.Sprintf("llm_tokens:%s:%s", uid, dayKey),
			fmt.Sprintf("llm_tokens:%s:week:%d:%02d", uid, year, week),
			fmt.Sprintf("usage:segment:%s:%s:%d", uid, requestID, segment),
		},
		tokens,
		int64(ttl.Seconds()),
		int64((24 * time.Hour).Seconds()),
		int64((7 * 24 * time.Hour).Seconds()),
	).Int64()
	if err != nil {
		return false, err
	}

	return val == 1, nil
}

func (s *QuotaService) GetDailyUsage(ctx context.Context, uid string) (int64, error) {
	dayKey := time.Now().Format("2006-01-02")
	val, err := s.rdb.Get(ctx, fmt.Sprintf("llm_tokens:%s:%s", uid, dayKey)).Int64()
	if err == redis.Nil {
		return 0, nil
	}
	return val, err
}
