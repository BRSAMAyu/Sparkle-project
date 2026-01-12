package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"golang.org/x/time/rate"
)

// RateLimiter 速率限制器
type RateLimiter struct {
	visitors map[string]*visitor
	mu       sync.RWMutex
	rate     rate.Limit // 每秒允许的请求数
	burst    int        // 突发请求容量
}

// visitor 访问者信息
type visitor struct {
	limiter  *rate.Limiter
	lastSeen time.Time
}

// NewRateLimiter 创建新的速率限制器
func NewRateLimiter(r rate.Limit, b int) *RateLimiter {
	rl := &RateLimiter{
		visitors: make(map[string]*visitor),
		rate:     r,
		burst:    b,
	}

	// 启动清理过期访问者的goroutine
	go rl.cleanupVisitors()

	return rl
}

// getVisitor 获取或创建访问者
func (rl *RateLimiter) getVisitor(ip string) *rate.Limiter {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	v, exists := rl.visitors[ip]
	if !exists {
		limiter := rate.NewLimiter(rl.rate, rl.burst)
		rl.visitors[ip] = &visitor{limiter, time.Now()}
		return limiter
	}

	v.lastSeen = time.Now()
	return v.limiter
}

// cleanupVisitors 定期清理过期的访问者
func (rl *RateLimiter) cleanupVisitors() {
	for {
		time.Sleep(time.Minute)

		rl.mu.Lock()
		for ip, v := range rl.visitors {
			if time.Since(v.lastSeen) > 5*time.Minute {
				delete(rl.visitors, ip)
			}
		}
		rl.mu.Unlock()
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
				"message":     "请求过于频繁，请稍后再试",
				"retry_after": retryAfterSeconds(limiter),
			})
			c.Abort()
			return
		}

		// 添加速率限制头部信息
		c.Header("X-RateLimit-Limit", string(rune(rl.burst)))
		c.Header("X-RateLimit-Remaining", string(rune(int(limiter.Tokens()))))
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
				"message":     "请求过于频繁，请稍后再试",
				"retry_after": retryAfterSeconds(limiter),
			})
			c.Abort()
			return
		}

		// 添加速率限制头部信息
		c.Header("X-RateLimit-Limit", string(rune(rl.burst)))
		c.Header("X-RateLimit-Remaining", string(rune(int(limiter.Tokens()))))
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
				"message":     "该端点请求过于频繁，请稍后再试",
				"retry_after": retryAfterSeconds(limiter),
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// AdaptiveRateLimitMiddleware 自适应速率限制
func AdaptiveRateLimitMiddleware(baseRate float64, burst int) gin.HandlerFunc {
	// 创建不同的限流器用于不同场景
	normalRL := NewRateLimiter(rate.Limit(baseRate), burst)
	strictRL := NewRateLimiter(rate.Limit(baseRate/2), burst/2)

	return func(c *gin.Context) {
		var rl *RateLimiter

		// 根据请求特征选择不同的限流策略
		path := c.Request.URL.Path
		method := c.Request.Method

		// 对敏感端点使用更严格的限制
		if path == "/api/v1/auth/login" || path == "/api/v1/auth/register" {
			rl = strictRL
		} else if method == "POST" || method == "PUT" || method == "DELETE" {
			// 写操作使用中等限制
			rl = NewRateLimiter(rate.Limit(baseRate*0.8), int(float64(burst)*0.8))
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
				"message":     "请求过于频繁，请稍后再试",
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
				"message": "WebSocket连接过于频繁，请稍后再试",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}
