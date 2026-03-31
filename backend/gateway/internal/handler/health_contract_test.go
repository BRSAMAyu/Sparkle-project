package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestHealthRouteContract_LiveEnvelope(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	NewHealthHandler(nil, nil, nil, "test-version").RegisterRoutes(r)

	req := httptest.NewRequest(http.MethodGet, "/health/live", nil)
	resp := httptest.NewRecorder()
	r.ServeHTTP(resp, req)

	require.Equal(t, http.StatusOK, resp.Code)
	var payload map[string]any
	require.NoError(t, json.Unmarshal(resp.Body.Bytes(), &payload))
	assert.Equal(t, "alive", payload["status"])
	_, hasTimestamp := payload["timestamp"]
	assert.True(t, hasTimestamp)
}

func TestHealthRouteContract_ReadyIncludesComponentsOnFailure(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	NewHealthHandler(nil, nil, nil, "test-version").RegisterRoutes(r)

	req := httptest.NewRequest(http.MethodGet, "/health/ready", nil)
	resp := httptest.NewRecorder()
	r.ServeHTTP(resp, req)

	require.Equal(t, http.StatusServiceUnavailable, resp.Code)
	var payload map[string]any
	require.NoError(t, json.Unmarshal(resp.Body.Bytes(), &payload))
	assert.Equal(t, "not_ready", payload["status"])
	components, ok := payload["components"].(map[string]any)
	require.True(t, ok)
	assert.Contains(t, components, "database")
	assert.Contains(t, components, "redis")
	assert.Contains(t, components, "grpc_agent")
}

func TestHealthRouteContract_HealthEnvelopeOnCachedHealthyState(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	handler := NewHealthHandler(nil, nil, nil, "test-version")
	handler.cachedCheck = &HealthResponse{
		Status:    "healthy",
		Version:   "test-version",
		Uptime:    "42s",
		Timestamp: time.Now().UTC(),
		Components: map[string]ComponentStatus{
			"database":   {Status: "healthy", Latency: 12},
			"redis":      {Status: "healthy", Latency: 4},
			"grpc_agent": {Status: "healthy", Message: "connected"},
		},
		System: &SystemInfo{
			GoVersion:    "go1.test",
			NumGoroutine: 7,
			NumCPU:       8,
			MemAllocMB:   64,
		},
	}
	handler.cachedAt = time.Now()
	handler.RegisterRoutes(r)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	resp := httptest.NewRecorder()
	r.ServeHTTP(resp, req)

	require.Equal(t, http.StatusOK, resp.Code)
	var payload map[string]any
	require.NoError(t, json.Unmarshal(resp.Body.Bytes(), &payload))
	assert.Equal(t, "healthy", payload["status"])
	assert.Equal(t, "test-version", payload["version"])
	assert.Equal(t, "42s", payload["uptime"])
	components, ok := payload["components"].(map[string]any)
	require.True(t, ok)
	assert.Contains(t, components, "database")
	assert.Contains(t, components, "redis")
	assert.Contains(t, components, "grpc_agent")
	system, ok := payload["system"].(map[string]any)
	require.True(t, ok)
	assert.Equal(t, "go1.test", system["go_version"])
}
