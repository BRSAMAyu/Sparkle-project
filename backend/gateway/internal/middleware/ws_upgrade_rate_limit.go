package middleware

import (
	"math"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"golang.org/x/time/rate"

	"github.com/sparkle/gateway/internal/i18n"
	"github.com/sparkle/gateway/internal/metrics"
)

// wsUpgradeRateLimitKeyPrefix namespaces the fallback-pin buckets away from
// the per-route hybrid limiter keys (user/ip + METHOD + route template): the
// pin shares one per-IP budget across all 5 WS upgrade routes by design
// (WS-TICKET-DESIGN §2.1/§3.3), so endpoint rotation cannot multiply it.
const wsUpgradeRateLimitKeyPrefix = "wsupgrade"

// WSUpgradeRateLimitMiddleware is the pre-auth fallback pin in front of the
// 5 WS upgrade routes (WSQ-1 / WS-TICKET-DESIGN §四 Step 0). Those routes sit
// on the gin root engine, outside the /api/v1 rate-limited group, so an
// unauthenticated flood otherwise reaches jwt.Parse and the Redis-backed auth
// checks unthrottled (wt275 D6). The pin rejects it with 429 + Retry-After
// before any authentication cost.
//
// Shape mirrors HybridRateLimitMiddlewareSimple: Redis Lua token bucket
// (consistent across gateway replicas) with a local rate.Limiter fallback on
// Redis errors, so the pin still clamps floods while degraded. The key is
// always per-IP: the middleware runs before WsAuthMiddleware, so no user
// identity exists yet, and one shared limiter instance gives all five routes
// a single per-IP budget (the NAT budget math in §5-R1 assumes this).
func WSUpgradeRateLimitMiddleware(rdb *redis.Client, requestsPerSecond float64, burst int) gin.HandlerFunc {
	var distRL *DistributedRateLimiter
	if rdb != nil {
		distRL = NewDistributedRateLimiter(rdb, requestsPerSecond, burst, wsUpgradeRateLimitKeyPrefix)
	}
	localRL := NewRateLimiterWithCleanup(rate.Limit(requestsPerSecond), burst, time.Minute)

	return func(c *gin.Context) {
		clientIP := c.ClientIP()
		if clientIP == "" {
			clientIP = "unknown"
		}
		limitKey := "ip:" + clientIP

		var allowed bool
		var remaining int64

		if distRL != nil {
			got, rem, err := distRL.Allow(c.Request.Context(), limitKey)
			if err != nil {
				zap.L().Warn("WS upgrade rate limiter Redis failed; falling back to local",
					zap.String("limit_key", limitKey),
					zap.Error(err),
				)
				limiter := localRL.getVisitor(limitKey)
				allowed = limiter.Allow()
				remaining = int64(limiter.Tokens())
			} else {
				allowed, remaining = got, rem
			}
		} else {
			limiter := localRL.getVisitor(limitKey)
			allowed = limiter.Allow()
			remaining = int64(limiter.Tokens())
		}

		if !allowed {
			metrics.WSUpgradeLimited.WithLabelValues(wsEndpointLabel(c)).Inc()
			retryAfter := wsUpgradeRetryAfterSeconds(requestsPerSecond, remaining)
			c.Header("Retry-After", strconv.Itoa(retryAfter))
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":       "rate_limit_exceeded",
				"message":     i18n.T(c.Request.Context(), "ratelimit.exceeded"),
				"retry_after": retryAfter,
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// wsUpgradeRetryAfterSeconds estimates the wait until the per-IP bucket
// refills one token: (1 - remaining) / rate, floored at 1 second so clients
// never observe Retry-After: 0.
func wsUpgradeRetryAfterSeconds(requestsPerSecond float64, remaining int64) int {
	if requestsPerSecond <= 0 {
		return 1
	}
	need := 1 - float64(remaining)
	if need <= 0 {
		return 1
	}
	wait := int(math.Ceil(need / requestsPerSecond))
	if wait < 1 {
		return 1
	}
	return wait
}
