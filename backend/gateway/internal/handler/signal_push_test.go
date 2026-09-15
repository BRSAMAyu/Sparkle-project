package handler

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"

	"github.com/sparkle/gateway/internal/config"
)

func TestSignalPushAuthorizationFailsClosedWithoutConfiguredKey(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/internal/signals/push", nil)
	c.Request.Header.Set("X-Internal-API-Key", "provided")

	handler := NewSignalPushHandler(&config.Config{}, nil)

	if handler.isAuthorized(c) {
		t.Fatal("expected signal push authorization to fail closed when InternalAPIKey is empty")
	}
}

func TestSignalPushAuthorizationRequiresMatchingKey(t *testing.T) {
	gin.SetMode(gin.TestMode)

	tests := []struct {
		name       string
		header     string
		authorized bool
	}{
		{name: "missing", header: "", authorized: false},
		{name: "wrong", header: "wrong", authorized: false},
		{name: "matching", header: "secret", authorized: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest(http.MethodPost, "/internal/signals/push", nil)
			if tt.header != "" {
				c.Request.Header.Set("X-Internal-API-Key", tt.header)
			}

			handler := NewSignalPushHandler(&config.Config{InternalAPIKey: "secret"}, nil)
			if got := handler.isAuthorized(c); got != tt.authorized {
				t.Fatalf("isAuthorized() = %v, want %v", got, tt.authorized)
			}
		})
	}
}
