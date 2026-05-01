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

func TestHealthHandler_Liveness(t *testing.T) {
	h := NewHealthHandler(nil, nil, nil, "test-version")
	r := gin.New()
		// route-tier: internal
	r.GET("/healthz", h.handleLiveness)

	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, "alive", resp["status"])
}

func TestHealthHandler_LivenessAlt(t *testing.T) {
	h := NewHealthHandler(nil, nil, nil, "test-version")
	r := gin.New()
		// route-tier: internal
	r.GET("/live", h.handleLiveness)

	req := httptest.NewRequest(http.MethodGet, "/live", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestHealthHandler_Readiness_NoDeps(t *testing.T) {
	h := NewHealthHandler(nil, nil, nil, "test-version")
	r := gin.New()
		// route-tier: internal
	r.GET("/readyz", h.handleReadiness)

	req := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	// Without DB/Redis/Agent, components should be unhealthy → 503
	assert.Equal(t, http.StatusServiceUnavailable, w.Code)

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, "not_ready", resp["status"])
}

func TestHealthHandler_RegisterRoutes(t *testing.T) {
	h := NewHealthHandler(nil, nil, nil, "1.0.0")
	r := gin.New()
	h.RegisterRoutes(r)

	routes := r.Routes()
	routeMap := make(map[string]bool)
	for _, route := range routes {
		routeMap[route.Path] = true
	}

	assert.True(t, routeMap["/healthz"])
	assert.True(t, routeMap["/readyz"])
	assert.True(t, routeMap["/health"])
	assert.True(t, routeMap["/live"])
	assert.True(t, routeMap["/ready"])
	assert.True(t, routeMap["/health/live"])
	assert.True(t, routeMap["/health/ready"])
}

func TestHealthHandler_DetailedHealth(t *testing.T) {
	h := NewHealthHandler(nil, nil, nil, "test-version")
	r := gin.New()
		// route-tier: internal
	r.GET("/health", h.handleHealth)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	// Without deps, should be unhealthy
	assert.Equal(t, http.StatusServiceUnavailable, w.Code)

	var resp HealthResponse
	err := json.Unmarshal(w.Body.Bytes(), &resp)
	require.NoError(t, err)
	assert.Equal(t, "unhealthy", resp.Status)
	assert.Equal(t, "test-version", resp.Version)
	assert.NotEmpty(t, resp.Components)
}

func TestHealthResponse_Structure(t *testing.T) {
	resp := HealthResponse{
		Status:    "healthy",
		Version:   "1.0.0",
		Uptime:    "1h30m",
		Timestamp: time.Now(),
		Components: map[string]ComponentStatus{
			"database": {Status: "healthy", Latency: 5},
		},
	}
	assert.Equal(t, "healthy", resp.Status)
	assert.Equal(t, "1.0.0", resp.Version)
	assert.Equal(t, int64(5), resp.Components["database"].Latency)
}

func TestComponentStatus_Structure(t *testing.T) {
	cs := ComponentStatus{
		Status:       "degraded",
		Latency:      100,
		Message:      "high latency",
		CircuitState: "half-open",
	}
	assert.Equal(t, "degraded", cs.Status)
	assert.Equal(t, int64(100), cs.Latency)
	assert.Equal(t, "half-open", cs.CircuitState)
}

func TestSystemInfo_Structure(t *testing.T) {
	info := SystemInfo{
		GoVersion:    "go1.24",
		NumGoroutine: 42,
		NumCPU:       8,
		MemAllocMB:   64,
	}
	assert.Equal(t, "go1.24", info.GoVersion)
	assert.Equal(t, 42, info.NumGoroutine)
}
