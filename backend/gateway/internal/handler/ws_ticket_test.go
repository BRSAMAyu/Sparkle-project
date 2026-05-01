package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
)

func TestWSTicket_MissingUserContext(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := NewWSTicketHandler(&config.Config{WSTicketTTLSeconds: 300}, nil)
	r := gin.New()
		// route-tier: internal
	r.POST("/ws/ticket", h.Issue)

	req := httptest.NewRequest(http.MethodPost, "/ws/ticket", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, "missing user context", resp["error"])
}

func TestWSTicket_ResponseFormat(t *testing.T) {
	gin.SetMode(gin.TestMode)
	cfg := &config.Config{WSTicketTTLSeconds: 600}

	r := gin.New()
	r.Use(func(c *gin.Context) {
		c.Set("user_id", "user-123")
		c.Set("auth_token", "tok-456")
		c.Next()
	})
	h := NewWSTicketHandler(cfg, nil)
		// route-tier: internal
	r.POST("/ws/ticket", h.Issue)

	req := httptest.NewRequest(http.MethodPost, "/ws/ticket", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	// nil Redis → graceful 503, no panic
	assert.Equal(t, http.StatusInternalServerError, w.Code)
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	assert.Equal(t, "ticket service unavailable", resp["error"])
}

func TestWSTicket_IssueEndpointRequiresAuth(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := NewWSTicketHandler(&config.Config{}, nil)
	r := gin.New()
		// route-tier: internal
	r.POST("/ws/ticket", h.Issue)

	// No user_id set → should return 401
	req := httptest.NewRequest(http.MethodPost, "/ws/ticket", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}
