package handler

import (
	"strings"

	"github.com/sparkle/gateway/internal/config"
	"golang.org/x/time/rate"
)

const (
	defaultWSRateLimitMessage = "Message rate limit exceeded"
	defaultWSInternalMessage  = "Internal service error"
	defaultWSStreamMessage    = "Stream interrupted"
)

func newWSMessageRateLimiter(cfg *config.Config) *rate.Limiter {
	msgRate := 0.0
	msgBurst := 0
	if cfg != nil {
		msgRate = cfg.WSMessageRateRPS
		msgBurst = cfg.WSMessageRateBurst
	}
	if msgRate <= 0 {
		msgRate = config.DefaultWSMessageRateRPS
	}
	if msgBurst <= 0 {
		msgBurst = config.DefaultWSMessageRateBurst
	}
	return rate.NewLimiter(rate.Limit(msgRate), msgBurst)
}

func publicStreamErrorMessage(code, raw string) string {
	message := strings.TrimSpace(raw)
	switch code {
	case "internal", "unknown":
		return defaultWSInternalMessage
	case "":
		if message == "" {
			return defaultWSStreamMessage
		}
		return message
	default:
		if message == "" {
			return defaultWSStreamMessage
		}
		return message
	}
}
