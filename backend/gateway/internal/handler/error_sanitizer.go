package handler

import (
	"context"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/sparkle/gateway/internal/i18n"
	"github.com/sparkle/gateway/internal/logsafe"
	"go.uber.org/zap"
)

var sanitizedErrorResponsesTotal = promauto.NewCounterVec(prometheus.CounterOpts{
	Name: "sparkle_gateway_sanitized_error_responses_total",
	Help: "Total gateway error responses sanitized before returning to clients.",
}, []string{"status_code", "handler", "category"})

// isDevelopmentModeForErrors checks if client error responses should keep raw
// error text for local debugging.
func isDevelopmentModeForErrors() bool {
	env := strings.ToLower(os.Getenv("ENVIRONMENT"))
	return env == "" || env == "dev" || env == "development"
}

func sanitizeErrorResponse(c *gin.Context, statusCode int, err error, internalMsg string) {
	c.JSON(statusCode, sanitizeErrorPayload(c, statusCode, err, internalMsg))
}

func sanitizeErrorPayload(c *gin.Context, statusCode int, err error, internalMsg string) gin.H {
	handlerLabel := handlerLabel(c, internalMsg)
	category := errorCategory(statusCode)
	recordSanitizedError(c.Request.Context(), strconv.Itoa(statusCode), handlerLabel, category, err, internalMsg, requestIDFromGin(c))

	message := safeErrorMessage(c.Request.Context(), statusCode, err)
	return gin.H{
		"error":      message,
		"error_code": errorCode(statusCode),
		"category":   category,
	}
}

func sanitizeError(err error, fallback string) string {
	if err == nil {
		return fallback
	}
	if isDevelopmentModeForErrors() {
		return err.Error()
	}
	recordSanitizedError(context.Background(), "unknown", "legacy", "unknown", err, fallback, "")
	return i18n.T(context.Background(), "errors.generic")
}

func sanitizeErrorWithDetail(err error, fallback string, detail string) gin.H {
	if err == nil {
		return gin.H{"error": fallback}
	}
	if isDevelopmentModeForErrors() {
		return gin.H{"error": fallback, "detail": err.Error()}
	}
	recordSanitizedError(context.Background(), "unknown", normalizeErrorLabel(detail), "unknown", err, fallback, "")
	return gin.H{
		"error":      i18n.T(context.Background(), "errors.generic"),
		"error_code": "internal_error",
		"category":   "server_error",
	}
}

func sanitizePlainError(ctx context.Context, statusCode int, err error, internalMsg string) string {
	if err == nil {
		return ""
	}
	recordSanitizedError(ctx, strconv.Itoa(statusCode), normalizeErrorLabel(internalMsg), errorCategory(statusCode), err, internalMsg, "")
	return safeErrorMessage(ctx, statusCode, err)
}

func sanitizeWebSocketError(ctx context.Context, err error, internalMsg string) string {
	if err == nil {
		return ""
	}
	recordSanitizedError(ctx, "websocket", normalizeErrorLabel(internalMsg), "websocket_error", err, internalMsg, "")
	if isDevelopmentModeForErrors() {
		return err.Error()
	}
	return i18n.T(ctx, "errors.generic")
}

func safeErrorMessage(ctx context.Context, statusCode int, err error) string {
	if err == nil {
		return i18n.T(ctx, "errors.generic")
	}
	if isDevelopmentModeForErrors() {
		return err.Error()
	}
	switch statusCode {
	case http.StatusBadRequest:
		return i18n.T(ctx, "errors.bad_request")
	case http.StatusUnauthorized:
		return i18n.T(ctx, "errors.unauthorized")
	case http.StatusForbidden:
		return i18n.T(ctx, "errors.forbidden")
	case http.StatusNotFound:
		return i18n.T(ctx, "errors.not_found")
	case http.StatusBadGateway, http.StatusServiceUnavailable, http.StatusGatewayTimeout:
		return i18n.T(ctx, "errors.upstream")
	default:
		return i18n.T(ctx, "errors.generic")
	}
}

func recordSanitizedError(ctx context.Context, statusCode string, handlerName string, category string, err error, internalMsg string, requestID string) {
	if err == nil {
		return
	}
	sanitizedErrorResponsesTotal.WithLabelValues(statusCode, handlerName, category).Inc()

	fields := []zap.Field{
		zap.String("status_code", statusCode),
		zap.String("handler", handlerName),
		zap.String("category", category),
		zap.String("internal_message", logsafe.RedactText(internalMsg)),
		zap.String("error", logsafe.RedactText(err.Error())),
	}
	if requestID != "" {
		fields = append(fields, zap.String("request_id", requestID))
	}
	if ctx != nil {
		if requestIDFromContext, ok := ctx.Value("request_id").(string); ok && requestIDFromContext != "" && requestID == "" {
			fields = append(fields, zap.String("request_id", requestIDFromContext))
		}
	}
	zap.L().Warn("sanitized client error response", fields...)
}

func requestIDFromGin(c *gin.Context) string {
	if c == nil {
		return ""
	}
	if requestID := c.GetString("request_id"); requestID != "" {
		return requestID
	}
	if c.Request != nil {
		return c.GetHeader("X-Request-ID")
	}
	return ""
}

func handlerLabel(c *gin.Context, fallback string) string {
	if c != nil {
		if fullPath := c.FullPath(); fullPath != "" {
			return normalizeErrorLabel(fullPath)
		}
		if c.Request != nil && c.Request.URL != nil && c.Request.URL.Path != "" {
			return normalizeErrorLabel(c.Request.URL.Path)
		}
	}
	return normalizeErrorLabel(fallback)
}

func normalizeErrorLabel(value string) string {
	value = strings.TrimSpace(strings.ToLower(value))
	if value == "" {
		return "unknown"
	}
	replacer := strings.NewReplacer("/", "_", " ", "_", ":", "_", "-", "_", ".", "_")
	value = replacer.Replace(value)
	value = strings.Trim(value, "_")
	if value == "" {
		return "unknown"
	}
	return value
}

func errorCategory(statusCode int) string {
	switch {
	case statusCode >= 500:
		return "server_error"
	case statusCode == http.StatusUnauthorized || statusCode == http.StatusForbidden:
		return "auth_error"
	case statusCode == http.StatusNotFound:
		return "not_found"
	case statusCode >= 400:
		return "client_error"
	default:
		return "unknown"
	}
}

func errorCode(statusCode int) string {
	switch statusCode {
	case http.StatusBadRequest:
		return "bad_request"
	case http.StatusUnauthorized:
		return "unauthorized"
	case http.StatusForbidden:
		return "forbidden"
	case http.StatusNotFound:
		return "not_found"
	case http.StatusConflict:
		return "conflict"
	case http.StatusBadGateway:
		return "bad_gateway"
	case http.StatusServiceUnavailable:
		return "service_unavailable"
	default:
		if statusCode >= 500 {
			return "internal_error"
		}
		if statusCode >= 400 {
			return "request_failed"
		}
	}
	return "operation_failed"
}
