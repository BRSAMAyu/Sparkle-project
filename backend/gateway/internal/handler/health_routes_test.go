package handler

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestHealthRoutesExposeLiveAndReadyAliases(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	NewHealthHandler(nil, nil, nil, "test").RegisterRoutes(r)

	liveReq := httptest.NewRequest(http.MethodGet, "/live", nil)
	liveResp := httptest.NewRecorder()
	r.ServeHTTP(liveResp, liveReq)
	assert.Equal(t, http.StatusOK, liveResp.Code)

	readyReq := httptest.NewRequest(http.MethodGet, "/ready", nil)
	readyResp := httptest.NewRecorder()
	r.ServeHTTP(readyResp, readyReq)
	assert.Equal(t, http.StatusServiceUnavailable, readyResp.Code)
}
