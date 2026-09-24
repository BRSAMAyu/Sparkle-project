package middleware

import (
	"net/http"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"golang.org/x/time/rate"

	"github.com/sparkle/gateway/internal/i18n"
)

const defaultMaxVisitors = 10000

// rateLimiterRegistry tracks all created rate limiters so they can be
// stopped together on graceful shutdown, preventing goroutine leaks.
var (
	rateLimiterRegistryMu sync.Mutex
	rateLimiterRegistry   []*RateLimiter
)

// RegisterRateLimiter adds a rate limiter to the global registry.
func RegisterRateLimiter(rl *RateLimiter) {
	rateLimiterRegistryMu.Lock()
	defer rateLimiterRegistryMu.Unlock()
	rateLimiterRegistry = append(rateLimiterRegistry, rl)
}

// StopAllRateLimiters stops all registered rate limiters' background
// goroutines. Call this during graceful shutdown.
func StopAllRateLimiters() {
	rateLimiterRegistryMu.Lock()
	defer rateLimiterRegistryMu.Unlock()
	for _, rl := range rateLimiterRegistry {
		rl.Stop()
	}
	rateLimiterRegistry = nil
}

// RateLimiter 速率限制器
type RateLimiter struct {
	visitors           map[string]*visitor
	mu                 sync.RWMutex
	rate               rate.Limit // 每秒允许的请求数
	burst              int        // 突发请求容量
	maxVisitors        int
	cleanupIntervalSec int           // 清理间隔(秒)
	expirySec          int           // 访客过期时间(秒)
	stopCh             chan struct{} // 停止信号通道，用于优雅关闭
}

// visitor 访问者信息
type visitor struct {
	limiter  *rate.Limiter
	lastSeen time.Time
}

// NewRateLimiter 创建新的速率限制器
func NewRateLimiter(r rate.Limit, b int) *RateLimiter {
	return NewRateLimiterWithMax(r, b, defaultMaxVisitors)
}

// NewRateLimiterWithMax 创建新的速率限制器并限制最大访客数
func NewRateLimiterWithMax(r rate.Limit, b int, maxVisitors int) *RateLimiter {
	rl := &RateLimiter{
		visitors:    make(map[string]*visitor),
		rate:        r,
		burst:       b,
		maxVisitors: maxVisitors,
		stopCh:      make(chan struct{}),
	}

	RegisterRateLimiter(rl)

	// 启动清理过期访问者的goroutine
	go rl.cleanupVisitors()

	return rl
}

// Stop 停止限流器的后台清理goroutine
func (rl *RateLimiter) Stop() {
	select {
	case <-rl.stopCh:
		// 已经关闭
	default:
		close(rl.stopCh)
	}
}

// getVisitor 获取或创建访问者
func (rl *RateLimiter) getVisitor(ip string) *rate.Limiter {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	v, exists := rl.visitors[ip]
	if !exists {
		if rl.maxVisitors > 0 && len(rl.visitors) >= rl.maxVisitors {
			rl.evictOldest(len(rl.visitors) - rl.maxVisitors + 1)
		}
		limiter := rate.NewLimiter(rl.rate, rl.burst)
		rl.visitors[ip] = &visitor{limiter, time.Now()}
		return limiter
	}

	v.lastSeen = time.Now()
	return v.limiter
}

// cleanupVisitors 定期清理过期的访问者
func (rl *RateLimiter) cleanupVisitors() {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-rl.stopCh:
			// 收到停止信号，退出goroutine
			return
		case <-ticker.C:
			rl.mu.Lock()
			for ip, v := range rl.visitors {
				if time.Since(v.lastSeen) > 5*time.Minute {
					delete(rl.visitors, ip)
				}
			}
			rl.mu.Unlock()
		}
	}
}

func (rl *RateLimiter) evictOldest(count int) {
	if count <= 0 {
		count = 1
	}

	entries := make([]struct {
		key      string
		lastSeen time.Time
	}, 0, len(rl.visitors))

	for key, v := range rl.visitors {
		entries = append(entries, struct {
			key      string
			lastSeen time.Time
		}{key: key, lastSeen: v.lastSeen})
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].lastSeen.Before(entries[j].lastSeen)
	})

	for i := 0; i < count && i < len(entries); i++ {
		delete(rl.visitors, entries[i].key)
	}
}

func retryAfterSeconds(limiter *rate.Limiter) int {
	res := limiter.Reserve()
	if !res.OK() {
		return 0
	}
	delay := res.Delay()
	res.CancelAt(time.Now())
	if delay <= 0 {
		return 0
	}
	return int(delay.Seconds())
}

// RateLimitMiddleware 速率限制中间件
func RateLimitMiddleware(rl *RateLimiter) gin.HandlerFunc {
	return func(c *gin.Context) {
		// 获取客户端IP
		clientIP := c.ClientIP()
		if clientIP == "" {
			clientIP = "unknown"
		}

		// 获取该IP的限流器
		limiter := rl.getVisitor(clientIP)

		// 检查是否允许请求
		if !limiter.Allow() {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":       "rate_limit_exceeded",
				"message":     i18n.T(c.Request.Context(), "ratelimit.exceeded"),
				"retry_after": retryAfterSeconds(limiter),
			})
			c.Abort()
			return
		}

		// 添加速率限制头部信息
		c.Header("X-RateLimit-Limit", strconv.Itoa(rl.burst))
		c.Header("X-RateLimit-Remaining", strconv.Itoa(int(limiter.Tokens())))
		c.Header("X-RateLimit-Reset", time.Now().Add(time.Second).Format(time.RFC3339))

		c.Next()
	}
}

// IPBasedRateLimit IP基础的速率限制
func IPBasedRateLimit(requestsPerSecond float64, burst int) gin.HandlerFunc {
	rl := NewRateLimiter(rate.Limit(requestsPerSecond), burst)
	return RateLimitMiddleware(rl)
}

// EndpointSpecificRateLimit 端点特定的速率限制
func EndpointSpecificRateLimit(endpoint string, requestsPerSecond float64, burst int) gin.HandlerFunc {
	rl := NewRateLimiter(rate.Limit(requestsPerSecond), burst)

	return func(c *gin.Context) {
		// 组合端点和客户端标识
		clientIP := c.ClientIP()
		if clientIP == "" {
			clientIP = "unknown"
		}
		identifier := endpoint + ":" + clientIP

		// 获取限流器
		limiter := rl.getVisitor(identifier)

		// 检查是否允许请求
		if !limiter.Allow() {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":       "rate_limit_exceeded",
				"message":     i18n.T(c.Request.Context(), "ratelimit.endpoint_exceeded"),
				"retry_after": retryAfterSeconds(limiter),
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// AdminRateLimitMiddleware protects low-volume control-plane endpoints against
// brute-force and password-spraying attempts while keeping normal admin use fast.
func AdminRateLimitMiddleware(rdb *redis.Client) gin.HandlerFunc {
	return HybridRateLimitMiddlewareSimple(rdb, 10.0/60.0, 10)
}

// InternalRateLimitMiddleware protects authenticated internal service routes
// from burst amplification while allowing normal intra-service traffic.
func InternalRateLimitMiddleware(rdb *redis.Client) gin.HandlerFunc {
	return HybridRateLimitMiddlewareSimple(rdb, 60.0, 120)
}

// ============================================================================
// Hybrid Rate Limiting (Redis + Local Fallback)
// ============================================================================

// HybridRateLimitMiddleware uses Redis when available, falls back to local limiter.
// This provides distributed rate limiting across multiple gateway instances.
// localRL is used as fallback when Redis is unavailable.
func HybridRateLimitMiddleware(rdb *redis.Client, localRL *RateLimiter, config HybridRateLimiterConfig) gin.HandlerFunc {
	var distRL *DistributedRateLimiter
	var swRL *SlidingWindowRateLimiter

	if rdb != nil {
		if config.UseSlidingWindow {
			swRL = NewSlidingWindowRateLimiter(rdb, config.Window, config.Burst, "ratelimit")
		} else {
			distRL = NewDistributedRateLimiter(rdb, config.Rate, config.Burst, "ratelimit")
		}
	}

	return func(c *gin.Context) {
		clientID := c.GetString("user_id")
		if clientID == "" {
			clientID = "ip:" + c.ClientIP()
		}
		routePath := normalizeRateLimitRoutePath(c)
		// Scope buckets by route so noisy endpoints like telemetry do not
		// starve unrelated interactive flows behind the same simulator IP.
		limitKey := clientID + ":" + c.Request.Method + ":" + routePath

		var allowed bool
		var remaining int64

		if config.UseSlidingWindow && swRL != nil {
			allowedSW, remSW, err := swRL.Allow(c.Request.Context(), limitKey)
			if err != nil {
				zap.L().Warn("Hybrid rate limiter Redis sliding window failed; falling back to local",
					zap.String("limit_key", limitKey),
					zap.String("route_path", routePath),
					zap.Error(err),
				)
				limiter := localRL.getVisitor(limitKey)
				allowed = limiter.Allow()
				remaining = int64(limiter.Tokens())
			} else {
				allowed = allowedSW
				remaining = int64(remSW)
			}
		} else if distRL != nil {
			var err error
			allowed, remaining, err = distRL.Allow(c.Request.Context(), limitKey)
			if err != nil {
				zap.L().Warn("Hybrid rate limiter Redis failed; falling back to local",
					zap.String("limit_key", limitKey),
					zap.String("route_path", routePath),
					zap.Error(err),
				)
				limiter := localRL.getVisitor(limitKey)
				allowed = limiter.Allow()
				remaining = int64(limiter.Tokens())
			}
		} else {
			limiter := localRL.getVisitor(limitKey)
			allowed = limiter.Allow()
			remaining = int64(limiter.Tokens())
		}

		if !allowed {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":   "rate_limit_exceeded",
				"message": i18n.T(c.Request.Context(), "ratelimit.exceeded"),
			})
			c.Abort()
			return
		}

		c.Header("X-RateLimit-Limit", strconv.Itoa(config.Burst))
		c.Header("X-RateLimit-Remaining", strconv.FormatInt(remaining, 10))
		c.Next()
	}
}

// rateLimitMaxKeySegments caps how deep a concrete path may shape a rate
// limit bucket (GW-P3-1): it bounds the bucket namespace a client can create.
const rateLimitMaxKeySegments = 8

func rateLimitPathSegments(path string) []string {
	return strings.FieldsFunc(path, func(r rune) bool { return r == '/' })
}

// rateLimitDepthSuffix returns "#N" with N = min(segment count, cap).
func rateLimitDepthSuffix(path string) string {
	n := len(rateLimitPathSegments(path))
	if n > rateLimitMaxKeySegments {
		n = rateLimitMaxKeySegments
	}
	return "#" + strconv.Itoa(n)
}

// rateLimitFixedPrefix returns the first n path segments as "/a/b/c".
func rateLimitFixedPrefix(path string, n int) string {
	segs := rateLimitPathSegments(path)
	if len(segs) > n {
		segs = segs[:n]
	}
	return "/" + strings.Join(segs, "/")
}

// normalizeRateLimitRoutePath derives the rate limit bucket path.
//
// Explicit routes bucket by their route template. Catch-all (wildcard)
// templates and unmatched NoRoute paths must NOT bucket by the concrete
// request path: anonymous clients could otherwise mint unlimited buckets by
// appending suffix junk to proxyable prefixes (GW-P3-1). Instead the bucket
// is bounded to trusted structure — the template (or a short fixed prefix of
// the path for NoRoute, which has no template) plus a capped segment count,
// so same-depth suffixes share a bucket while /settings and
// /settings/ai-usage still do not throttle each other.
func normalizeRateLimitRoutePath(c *gin.Context) string {
	routePath := c.FullPath()
	if routePath == "" {
		return "noroute:" + rateLimitFixedPrefix(c.Request.URL.Path, 3) + rateLimitDepthSuffix(c.Request.URL.Path)
	}

	if strings.Contains(routePath, "*") {
		return routePath + rateLimitDepthSuffix(c.Request.URL.Path)
	}

	return routePath
}

// SlidingWindowRateLimitMiddleware uses sliding window algorithm for rate limiting
func SlidingWindowRateLimitMiddleware(rdb *redis.Client, window time.Duration, limit int) gin.HandlerFunc {
	swl := NewSlidingWindowRateLimiter(rdb, window, limit, "ratelimit")
	ratePerSec := float64(limit) / window.Seconds()
	localRL := NewRateLimiterWithCleanup(rate.Limit(ratePerSec), limit, time.Minute)

	return func(c *gin.Context) {
		clientID := c.GetString("user_id")
		if clientID == "" {
			clientID = "ip:" + c.ClientIP()
		}

		allowed, remaining, err := swl.Allow(c.Request.Context(), clientID)
		if err != nil {
			zap.L().Warn("Sliding window rate limiter Redis failed; falling back to local",
				zap.String("client_id", clientID),
				zap.Error(err),
			)
			limiter := localRL.getVisitor(clientID)
			allowed = limiter.Allow()
			remaining = int(limiter.Tokens())
		}

		if !allowed {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":     "rate_limit_exceeded",
				"message":   i18n.T(c.Request.Context(), "ratelimit.exceeded"),
				"limit":     limit,
				"remaining": remaining,
			})
			c.Abort()
			return
		}

		c.Header("X-RateLimit-Limit", strconv.Itoa(limit))
		c.Header("X-RateLimit-Remaining", strconv.Itoa(remaining))
		c.Next()
	}
}
