package handler

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/i18n"
	"github.com/stretchr/testify/require"
)

func TestSanitizeErrorResponse_ProductionHidesInternalDetails(t *testing.T) {
	t.Setenv("ENVIRONMENT", "prod")
	gin.SetMode(gin.TestMode)

	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		c.Set("request_id", "req-prod")
		sanitizeErrorResponse(c, http.StatusInternalServerError, errors.New("pq: syntax error near /var/lib/postgresql/private.sql"), "test.internal")
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))

	require.Equal(t, http.StatusInternalServerError, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	require.Equal(t, "操作失败，请稍后重试。", resp["error"])
	require.Equal(t, "internal_error", resp["error_code"])
	require.Equal(t, "server_error", resp["category"])
	require.NotContains(t, resp["error"], "postgresql")
	require.NotContains(t, resp["error"], "syntax")
}

func TestSanitizeErrorResponse_DevelopmentKeepsRawError(t *testing.T) {
	t.Setenv("ENVIRONMENT", "development")
	gin.SetMode(gin.TestMode)

	r := gin.New()
	r.POST("/test", func(c *gin.Context) {
		sanitizeErrorResponse(c, http.StatusBadRequest, errors.New("json: cannot unmarshal secret stack detail"), "test.bind")
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodPost, "/test", strings.NewReader("{}")))

	require.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	require.Equal(t, "json: cannot unmarshal secret stack detail", resp["error"])
	require.Equal(t, "bad_request", resp["error_code"])
	require.Equal(t, "client_error", resp["category"])
}

func TestSanitizeErrorResponse_UsesRequestLocale(t *testing.T) {
	t.Setenv("ENVIRONMENT", "prod")
	gin.SetMode(gin.TestMode)

	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		ctx := i18n.WithLocale(c.Request.Context(), "en")
		c.Request = c.Request.WithContext(ctx)
		sanitizeErrorResponse(c, http.StatusBadGateway, errors.New("upstream dial tcp 10.0.0.1: connection refused"), "test.upstream")
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/test", nil))

	require.Equal(t, http.StatusBadGateway, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	require.Equal(t, "The service is temporarily unavailable. Please try again later.", resp["error"])
	require.Equal(t, "bad_gateway", resp["error_code"])
	require.Equal(t, "server_error", resp["category"])
}
