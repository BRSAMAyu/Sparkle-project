package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

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
