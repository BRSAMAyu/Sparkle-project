package middleware

import (
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.opentelemetry.io/otel/trace"
)

// RequestContextMiddleware injects request_id / trace_id into context and headers.
func RequestContextMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := headerOrDefault(c.GetHeader("X-Request-ID"), uuid.NewString())
		traceID := headerOrDefault(c.GetHeader("X-Trace-ID"), "")
		if traceID == "" {
			if span := trace.SpanFromContext(c.Request.Context()); span != nil {
				sc := span.SpanContext()
				if sc.IsValid() {
					traceID = sc.TraceID().String()
				}
			}
		}
		if traceID == "" {
			traceID = strings.ReplaceAll(uuid.NewString(), "-", "")
		}

		c.Set("request_id", requestID)
		c.Set("trace_id", traceID)
		c.Header("X-Request-ID", requestID)
		c.Header("X-Trace-ID", traceID)

		c.Next()
	}
}

func headerOrDefault(value string, fallback string) string {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return fallback
	}
	return trimmed
}
