package middleware

import (
	"log"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/i18n"
	"golang.org/x/time/rate"
)

const defaultMaxVisitors = 10000

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

// UserBasedRateLimit 用户基础的速率限制（需要认证）
func UserBasedRateLimit(requestsPerSecond float64, burst int) gin.HandlerFunc {
	rl := NewRateLimiter(rate.Limit(requestsPerSecond), burst)

	return func(c *gin.Context) {
		// 尝试从上下文中获取用户ID
		userID, exists := c.Get("user_id")
		if !exists {
			// 如果没有用户ID，回退到IP基础的限制
			clientIP := c.ClientIP()
			if clientIP == "" {
				clientIP = "unknown"
			}
			userID = "ip:" + clientIP
		}

		// 获取该用户的限流器
		limiter := rl.getVisitor(userID.(string))

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

// AdaptiveRateLimitMiddleware 自适应速率限制
// 修复: 预创建所有限流器，避免每次请求创建新实例
func AdaptiveRateLimitMiddleware(baseRate float64, burst int) gin.HandlerFunc {
	// 预创建所有限流器用于不同场景
	normalRL := NewRateLimiter(rate.Limit(baseRate), burst)
	strictRL := NewRateLimiter(rate.Limit(baseRate/2), burst/2)
	writeRL := NewRateLimiter(rate.Limit(baseRate*0.8), int(float64(burst)*0.8))

	return func(c *gin.Context) {
		var rl *RateLimiter

		// 根据请求特征选择不同的限流策略
		path := c.Request.URL.Path
		method := c.Request.Method

		// 对敏感端点使用更严格的限制
		if path == "/api/v1/auth/login" || path == "/api/v1/auth/register" {
			rl = strictRL
		} else if method == "POST" || method == "PUT" || method == "DELETE" {
			// 写操作使用中等限制（使用预创建的限流器）
			rl = writeRL
		} else {
			// 读操作使用正常限制
			rl = normalRL
		}

		// 获取客户端标识
		clientIP := c.ClientIP()
		if clientIP == "" {
			clientIP = "unknown"
		}

		// 组合路径和IP作为标识
		identifier := path + ":" + clientIP

		// 获取限流器
		limiter := rl.getVisitor(identifier)

		// 检查是否允许请求
		if !limiter.Allow() {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":       "rate_limit_exceeded",
				"message":     i18n.T(c.Request.Context(), "ratelimit.exceeded"),
				"retry_after": retryAfterSeconds(limiter),
				"endpoint":    path,
			})
			c.Abort()
			return
		}

		// 记录速率限制信息
		c.Set("rate_limit_info", map[string]interface{}{
			"limit":     rl.burst,
			"remaining": int(limiter.Tokens()),
			"reset":     time.Now().Add(time.Second),
			"strategy":  "adaptive",
		})

		c.Next()
	}
}

// GlobalRateLimitConfig 全局速率限制配置
var GlobalRateLimitConfig = struct {
	// 普通API限制
	APIRequestsPerSecond float64
	APIBurst             int

	// 认证相关限制
	AuthRequestsPerSecond float64
	AuthBurst             int

	// WebSocket连接限制
	WebSocketConnectionsPerMinute float64
	WebSocketBurst                int
}{
	APIRequestsPerSecond: 10.0, // 每秒10个请求
	APIBurst:             30,   // 突发30个请求

	AuthRequestsPerSecond: 5.0, // 认证端点每秒5个请求
	AuthBurst:             15,  // 突发15个请求

	WebSocketConnectionsPerMinute: 5.0, // 每分钟5个WebSocket连接
	WebSocketBurst:                10,  // 突发10个连接
}

// DefaultRateLimitMiddleware 默认速率限制中间件
func DefaultRateLimitMiddleware() gin.HandlerFunc {
	return IPBasedRateLimit(
		GlobalRateLimitConfig.APIRequestsPerSecond,
		GlobalRateLimitConfig.APIBurst,
	)
}

// AuthRateLimitMiddleware 认证端点速率限制中间件
func AuthRateLimitMiddleware() gin.HandlerFunc {
	return EndpointSpecificRateLimit(
		"/api/v1/auth",
		GlobalRateLimitConfig.AuthRequestsPerSecond,
		GlobalRateLimitConfig.AuthBurst,
	)
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

// WebSocketRateLimitMiddleware WebSocket连接速率限制
func WebSocketRateLimitMiddleware() gin.HandlerFunc {
	// WebSocket连接限制按分钟计算
	rl := NewRateLimiter(
		rate.Limit(GlobalRateLimitConfig.WebSocketConnectionsPerMinute/60.0),
		GlobalRateLimitConfig.WebSocketBurst,
	)

	return func(c *gin.Context) {
		clientIP := c.ClientIP()
		if clientIP == "" {
			clientIP = "unknown"
		}

		limiter := rl.getVisitor("websocket:" + clientIP)

		if !limiter.Allow() {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":   "websocket_rate_limit_exceeded",
				"message": i18n.T(c.Request.Context(), "ratelimit.websocket_exceeded"),
			})
			c.Abort()
			return
		}

		c.Next()
	}
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
				log.Printf("[HybridRateLimiter] Redis sliding window error: %v, falling back to local", err)
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
				log.Printf("[HybridRateLimiter] Redis error: %v, falling back to local", err)
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

func normalizeRateLimitRoutePath(c *gin.Context) string {
	routePath := c.FullPath()
	if routePath == "" {
		return c.Request.URL.Path
	}

	// Catch-all proxy routes like /api/v1/user/*path collapse unrelated
	// interactive requests into the same rate-limit bucket. Use the concrete
	// request path for wildcard templates so /settings and /settings/ai-usage
	// do not throttle each other.
	if strings.Contains(routePath, "*") {
		return c.Request.URL.Path
	}

	return routePath
}

// SlidingWindowRateLimitMiddleware uses sliding window algorithm for rate limiting
func SlidingWindowRateLimitMiddleware(rdb *redis.Client, window time.Duration, limit int) gin.HandlerFunc {
	swl := NewSlidingWindowRateLimiter(rdb, window, limit, "ratelimit")

	return func(c *gin.Context) {
		clientID := c.GetString("user_id")
		if clientID == "" {
			clientID = "ip:" + c.ClientIP()
		}

		allowed, remaining, err := swl.Allow(c.Request.Context(), clientID)
		if err != nil {
			log.Printf("[SlidingWindowRateLimiter] Error: %v", err)
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
