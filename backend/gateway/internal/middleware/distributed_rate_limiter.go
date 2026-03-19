package middleware

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/redis/go-redis/v9"
	"golang.org/x/time/rate"
)

// Prometheus metrics for Redis rate limiter monitoring
var (
	redisFallbackCounter = promauto.NewCounter(prometheus.CounterOpts{
		Name: "sparkle_rate_limiter_redis_fallback_total",
		Help: "Total number of fallbacks to local rate limiter due to Redis errors",
	})

	redisErrorCounter = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "sparkle_rate_limiter_redis_errors_total",
		Help: "Total Redis errors in rate limiter by error type",
	}, []string{"error_type"})
)

// DistributedRateLimiter implements Token Bucket algorithm using Redis
// This ensures rate limiting works across multiple gateway instances
type DistributedRateLimiter struct {
	rdb           *redis.Client
	rate          float64 // tokens per second
	burst         int     // max bucket size
	initialTokens int     // initial tokens in bucket (default: 0 to prevent burst abuse)
	keyPrefix     string
}

// NewDistributedRateLimiter creates a Redis-backed rate limiter using Token Bucket algorithm
func NewDistributedRateLimiter(rdb *redis.Client, rate float64, burst int, keyPrefix string) *DistributedRateLimiter {
	return &DistributedRateLimiter{
		rdb:   rdb,
		rate:  rate,
		burst: burst,
		// Start full like a standard token bucket. Starting at 0 causes fresh
		// sessions and low-frequency pages to get sporadic first-request 429s.
		initialTokens: burst,
		keyPrefix:     keyPrefix,
	}
}

// NewDistributedRateLimiterWithInitialTokens creates a rate limiter with custom initial tokens
func NewDistributedRateLimiterWithInitialTokens(rdb *redis.Client, rate float64, burst, initialTokens int, keyPrefix string) *DistributedRateLimiter {
	return &DistributedRateLimiter{
		rdb:           rdb,
		rate:          rate,
		burst:         burst,
		initialTokens: initialTokens,
		keyPrefix:     keyPrefix,
	}
}

// Allow checks if a request is allowed using Token Bucket algorithm
// The Lua script ensures atomicity across multiple gateway instances
func (d *DistributedRateLimiter) Allow(ctx context.Context, key string) (bool, int64, error) {
	fullKey := fmt.Sprintf("%s:%s", d.keyPrefix, key)

	// Token Bucket Lua script
	// Returns: [allowed (0/1), remaining_tokens]
	// Fixed: Use configurable initial_tokens instead of burst to prevent burst abuse
	script := redis.NewScript(`
		local key = KEYS[1]
		local rate = tonumber(ARGV[1])
		local burst = tonumber(ARGV[2])
		local now = tonumber(ARGV[3])
		local initial_tokens = tonumber(ARGV[4])

		local last = redis.call('HGET', key, 'last')
		local tokens = redis.call('HGET', key, 'tokens')

		-- Initialize if not exists
		if last == false then
			last = now
			tokens = initial_tokens
		end

		-- Calculate token replenishment
		local elapsed = now - tonumber(last)
		local new_tokens = math.min(burst, tonumber(tokens) + elapsed * rate)

		local allowed = 0
		local remaining = new_tokens

		-- Check if we can consume a token
		if new_tokens >= 1 then
			new_tokens = new_tokens - 1
			allowed = 1
			remaining = new_tokens
		end

		-- Update state
		redis.call('HMSET', key, 'last', now, 'tokens', new_tokens)
		redis.call('PEXPIRE', key, 300000) -- 5 minute TTL

		return {allowed, remaining}
	`)

	result, err := script.Run(ctx, d.rdb, []string{fullKey},
		d.rate, d.burst, float64(time.Now().UnixMilli()), d.initialTokens).Slice()
	if err != nil {
		// Log and increment Prometheus metrics for Redis errors
		log.Printf("[ALERT] Rate limiter Redis error: %v, falling back to local", err)
		redisFallbackCounter.Inc()
		redisErrorCounter.WithLabelValues("script_error").Inc()
		return false, 0, fmt.Errorf("redis script execution failed: %w", err)
	}

	allowed := result[0].(int64) == 1
	remaining := result[1].(int64)

	return allowed, remaining, nil
}

// SlidingWindowRateLimiter implements sliding window rate limiting algorithm
// More precise than fixed window but slightly higher memory usage
type SlidingWindowRateLimiter struct {
	rdb       *redis.Client
	window    time.Duration
	limit     int
	keyPrefix string
}

// NewSlidingWindowRateLimiter creates a Redis-backed sliding window rate limiter
func NewSlidingWindowRateLimiter(rdb *redis.Client, window time.Duration, limit int, keyPrefix string) *SlidingWindowRateLimiter {
	return &SlidingWindowRateLimiter{
		rdb:       rdb,
		window:    window,
		limit:     limit,
		keyPrefix: keyPrefix,
	}
}

// Allow checks if a request is allowed using Sliding Window algorithm
// Returns: (allowed, remaining_count, error)
func (s *SlidingWindowRateLimiter) Allow(ctx context.Context, key string) (bool, int, error) {
	fullKey := fmt.Sprintf("%s:%s", s.keyPrefix, key)
	now := float64(time.Now().UnixMilli())
	windowStart := now - float64(s.window.Milliseconds())

	// Sliding Window Lua script using sorted sets
	// Returns: [allowed (0/1), remaining]
	script := redis.NewScript(`
		local key = KEYS[1]
		local now = tonumber(ARGV[1])
		local window_start = tonumber(ARGV[2])
		local limit = tonumber(ARGV[3])
		local window_ms = tonumber(ARGV[4])

		-- Remove expired entries
		redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

		-- Count current entries
		local count = redis.call('ZCARD', key)

		if count < limit then
			-- Add new entry with unique score
			redis.call('ZADD', key, now, now .. '-' .. math.random())
			redis.call('PEXPIRE', key, window_ms)
			return {1, limit - count - 1}
		end

		return {0, 0}
	`)

	result, err := script.Run(ctx, s.rdb, []string{fullKey},
		now, windowStart, s.limit, int64(s.window.Milliseconds())).Slice()
	if err != nil {
		return false, 0, fmt.Errorf("redis script execution failed: %w", err)
	}

	allowed := result[0].(int64) == 1
	remaining := int(result[1].(int64))

	return allowed, remaining, nil
}

// HybridRateLimiterConfig holds configuration for the hybrid rate limiter
type HybridRateLimiterConfig struct {
	// Backend: "redis" or "local"
	Backend string
	// Rate in requests per second
	Rate float64
	// Burst capacity
	Burst int
	// Window duration for sliding window (only used with sliding window mode)
	Window time.Duration
	// Cleanup interval for local limiter
	CleanupInterval time.Duration
	// Use sliding window algorithm (default: token bucket)
	UseSlidingWindow bool
}

// HybridRateLimitMiddlewareSimple is a simplified version that takes Redis client and rate, burst directly
// Used for quick setup when advanced config is not needed
func HybridRateLimitMiddlewareSimple(
	rdb *redis.Client,
	requestsPerSecond float64,
	burst int,
) gin.HandlerFunc {
	config := HybridRateLimiterConfig{
		Backend:          "redis",
		Rate:             requestsPerSecond,
		Burst:            burst,
		Window:           time.Minute,
		CleanupInterval:  time.Minute,
		UseSlidingWindow: false,
	}
	localRL := NewRateLimiterWithCleanup(rate.Limit(requestsPerSecond), burst, config.CleanupInterval)

	return HybridRateLimitMiddleware(rdb, localRL, config)
}

// HybridSlidingWindowMiddleware creates a middleware using sliding window algorithm
func HybridSlidingWindowMiddleware(
	rdb *redis.Client,
	window time.Duration,
	limit int,
) gin.HandlerFunc {
	config := HybridRateLimiterConfig{
		Backend:          "redis",
		Rate:             float64(limit) / window.Seconds(),
		Burst:            limit,
		Window:           window,
		CleanupInterval:  time.Minute,
		UseSlidingWindow: true,
	}
	localRL := NewRateLimiterWithCleanup(rate.Limit(config.Rate), config.Burst, config.CleanupInterval)

	return HybridRateLimitMiddleware(rdb, localRL, config)
}

// NewRateLimiterWithCleanup creates a rate limiter with configurable cleanup interval
func NewRateLimiterWithCleanup(r rate.Limit, b int, cleanupInterval time.Duration) *RateLimiter {
	rl := &RateLimiter{
		visitors:    make(map[string]*visitor),
		rate:        r,
		burst:       b,
		maxVisitors: defaultMaxVisitors,
		stopCh:      make(chan struct{}),
	}

	// Start cleanup goroutine with custom interval
	go rl.cleanupVisitorsWithInterval(cleanupInterval)

	return rl
}

// cleanupVisitorsWithInterval periodically cleans up expired visitors
func (rl *RateLimiter) cleanupVisitorsWithInterval(interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-rl.stopCh:
			// Graceful shutdown
			return
		case <-ticker.C:
			rl.mu.Lock()
			for ip, v := range rl.visitors {
				// Expire after 3 times the cleanup interval (reduced from 5 minutes)
				if time.Since(v.lastSeen) > 3*interval {
					delete(rl.visitors, ip)
				}
			}
			rl.mu.Unlock()
		}
	}
}
