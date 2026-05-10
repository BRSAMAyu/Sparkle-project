package middleware

import (
	"context"
	"fmt"
	"log"
	"math"
	"strconv"
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

	rateLimiterTokensCurrent = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "rate_limiter_tokens_current",
		Help: "Current token count left in the distributed token bucket (sampled)",
	})

	rateLimiterRejectionsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "rate_limiter_rejections_total",
		Help: "Total distributed token bucket rejections by reason",
	}, []string{"reason"})
)

var distributedTokenBucketScript = redis.NewScript(`
	local key = KEYS[1]
	local rate_per_s = tonumber(ARGV[1])
	local burst = tonumber(ARGV[2])
	local now_ms = tonumber(ARGV[3])
	local initial_tokens = tonumber(ARGV[4])

	local last_ms = redis.call('HGET', key, 'last')
	local tokens = redis.call('HGET', key, 'tokens')

	-- Initialize if not exists.
	if last_ms == false then
		last_ms = now_ms
		tokens = initial_tokens
	end

	-- elapsed_unit=ms, rate_unit=tokens/s
	local elapsed_ms = now_ms - tonumber(last_ms)
	-- tokens_added = (elapsed_ms / 1000.0) * (rate_per_s)
	local tokens_added = (elapsed_ms / 1000.0) * rate_per_s
	local new_tokens = math.min(burst, tonumber(tokens) + tokens_added)

	local allowed = 0
	local remaining = new_tokens

	if new_tokens >= 1 then
		new_tokens = new_tokens - 1
		allowed = 1
		remaining = new_tokens
	end

	redis.call('HMSET', key, 'last', now_ms, 'tokens', new_tokens)
	redis.call('PEXPIRE', key, 300000)

	return {allowed, tostring(remaining)}
`)

var distributedSlidingWindowScript = redis.NewScript(`
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
		-- Add a unique member even when multiple requests arrive in the same millisecond.
		local seq_key = key .. ':seq'
		local seq = redis.call('INCR', seq_key)
		redis.call('PEXPIRE', seq_key, window_ms)
		redis.call('ZADD', key, now, now .. '-' .. seq)
		redis.call('PEXPIRE', key, window_ms)
		return {1, limit - count - 1}
	end

	return {0, 0}
`)

// DistributedRateLimiter implements Token Bucket algorithm using Redis
// This ensures rate limiting works across multiple gateway instances
type DistributedRateLimiter struct {
	rdb           *redis.Client
	rate          float64 // tokens per second
	burst         int     // max bucket size
	initialTokens int     // initial tokens in bucket (default: 0 to prevent burst abuse)
	keyPrefix     string
	nowFn         func() time.Time
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
		nowFn:         time.Now,
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
		nowFn:         time.Now,
	}
}

// tokensAddedForElapsed aligns the token bucket units explicitly for Rule AW.
// elapsed_unit=ms, rate_unit=tokens/s
// tokens_added = (elapsed_ms / 1000.0) * (rate_per_s)
func tokensAddedForElapsed(elapsedMs int64, ratePerSecond float64) float64 {
	if elapsedMs <= 0 || ratePerSecond <= 0 {
		return 0
	}
	return (float64(elapsedMs) / 1000.0) * ratePerSecond
}

func parseScriptFloat(result any) (float64, error) {
	switch value := result.(type) {
	case float64:
		return value, nil
	case int64:
		return float64(value), nil
	case string:
		return strconv.ParseFloat(value, 64)
	case []byte:
		return strconv.ParseFloat(string(value), 64)
	default:
		return 0, fmt.Errorf("unsupported numeric script result type %T", result)
	}
}

func parseScriptInt(result any) (int64, error) {
	switch value := result.(type) {
	case int64:
		return value, nil
	case float64:
		return int64(value), nil
	case string:
		parsed, err := strconv.ParseInt(value, 10, 64)
		if err == nil {
			return parsed, nil
		}
		floatParsed, floatErr := strconv.ParseFloat(value, 64)
		if floatErr != nil {
			return 0, err
		}
		return int64(floatParsed), nil
	case []byte:
		return parseScriptInt(string(value))
	default:
		return 0, fmt.Errorf("unsupported integer script result type %T", result)
	}
}

// Allow checks if a request is allowed using Token Bucket algorithm
// The Lua script ensures atomicity across multiple gateway instances
func (d *DistributedRateLimiter) Allow(ctx context.Context, key string) (bool, int64, error) {
	allowed, remaining, err := d.allowAtMillis(ctx, key, d.nowFn().UnixMilli())
	if err != nil {
		return false, 0, err
	}
	return allowed, int64(math.Floor(remaining)), nil
}

func (d *DistributedRateLimiter) allowAtMillis(ctx context.Context, key string, nowMillis int64) (bool, float64, error) {
	fullKey := fmt.Sprintf("%s:%s", d.keyPrefix, key)

	result, err := distributedTokenBucketScript.Run(ctx, d.rdb, []string{fullKey},
		d.rate, d.burst, nowMillis, d.initialTokens).Slice()
	if err != nil {
		// Log and increment Prometheus metrics for Redis errors
		log.Printf("[ALERT] Rate limiter Redis error: %v, falling back to local", err)
		redisFallbackCounter.Inc()
		redisErrorCounter.WithLabelValues("script_error").Inc()
		rateLimiterRejectionsTotal.WithLabelValues("redis_error").Inc()
		return false, 0, fmt.Errorf("redis script execution failed: %w", err)
	}

	if len(result) != 2 {
		return false, 0, fmt.Errorf("unexpected redis script result length: %d", len(result))
	}

	allowedValue, err := parseScriptInt(result[0])
	if err != nil {
		return false, 0, fmt.Errorf("parse allowed flag: %w", err)
	}
	remaining, err := parseScriptFloat(result[1])
	if err != nil {
		return false, 0, fmt.Errorf("parse remaining tokens: %w", err)
	}

	rateLimiterTokensCurrent.Set(remaining)
	allowed := allowedValue == 1
	if !allowed {
		rateLimiterRejectionsTotal.WithLabelValues("insufficient_tokens").Inc()
	}
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

	// Returns: [allowed (0/1), remaining]
	result, err := distributedSlidingWindowScript.Run(ctx, s.rdb, []string{fullKey},
		now, windowStart, s.limit, int64(s.window.Milliseconds())).Slice()
	if err != nil {
		return false, 0, fmt.Errorf("redis script execution failed: %w", err)
	}

	allowedRaw, err := parseScriptInt(result[0])
	if err != nil {
		return false, 0, fmt.Errorf("parse allowed flag: %w", err)
	}
	remainingRaw, err := parseScriptInt(result[1])
	if err != nil {
		return false, 0, fmt.Errorf("parse remaining count: %w", err)
	}
	allowed := allowedRaw == 1
	remaining := int(remainingRaw)

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
			return
		case <-ticker.C:
			rl.mu.Lock()
			for ip, v := range rl.visitors {
				if time.Since(v.lastSeen) > 3*interval {
					delete(rl.visitors, ip)
				}
			}
			rl.mu.Unlock()
		}
	}
}
