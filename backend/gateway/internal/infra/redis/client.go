package redis

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/config"
)

func NewClient(cfg *config.Config) (*redis.Client, error) {
	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisURL,
		Password: cfg.RedisPassword,
		DB:       0, // use default DB

		// Connection Pool Configuration
		PoolSize:     100, // Peak concurrent connections
		MinIdleConns: 10,  // Minimum idle connections

		// Timeout Settings (Fail-Fast)
		DialTimeout:  5 * time.Second,
		ReadTimeout:  300 * time.Millisecond,
		WriteTimeout: 300 * time.Millisecond,
	})

	// Verify connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, err
	}

	return rdb, nil
}
