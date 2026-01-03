package service

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/db"
)

type QuotaService struct {
	rdb *redis.Client
}

func NewQuotaService(rdb *redis.Client) *QuotaService {
	return &QuotaService{rdb: rdb}
}

func (s *QuotaService) DecrQuota(ctx context.Context, uid string) (int64, error) {
	// Use script exported from internal/db
	script := redis.NewScript(db.DecrQuotaScript)

	payload := fmt.Sprintf(`{"uid":"%s", "delta":-1, "ts":%d}`, uid, time.Now().Unix())

	val, err := script.Run(ctx, s.rdb,
		[]string{fmt.Sprintf("user:quota:%s", uid), "queue:sync:quota"}, // KEYS
		payload, // ARGV
	).Int64()

	return val, err
}
