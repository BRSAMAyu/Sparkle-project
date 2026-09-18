package service

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"

	"github.com/sparkle/gateway/internal/db"
)

// QuotaService implements the production quota chain: usage metering on
// date-suffixed keys (llm_tokens:{uid}:{YYYY-MM-DD} + weekly aggregate) with
// request-scoped idempotency. The former reserve/refund/decr family
// (ReserveRequest / RefundReservation / DecrQuota + their Lua scripts) was
// deleted as dead code — it had zero production callers and no initializer for
// its user:quota:* keys (R2-05 §4.1 option 1, executed by the P3 gateway
// handoff trio). Admission control is the pre-stream usage read (GW-P2-4
// bounded degrade) plus in-stream segment checks and post-stream accounting.
type QuotaService struct {
	rdb *redis.Client
}

func NewQuotaService(rdb *redis.Client) *QuotaService {
	return &QuotaService{rdb: rdb}
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
		fmt.Sprintf("%d", int64((24*time.Hour).Seconds())),
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
