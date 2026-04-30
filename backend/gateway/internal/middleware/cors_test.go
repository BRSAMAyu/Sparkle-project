package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
)

func TestCORS_AllowedOrigin(t *testing.T) {
	cfg := &config.Config{AllowedOrigins: []string{"https://sparkle.app", "http://localhost:3000"}}
	r := gin.New()
	r.Use(CORSMiddleware(cfg))
	r.GET("/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Origin", "https://sparkle.app")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "https://sparkle.app", w.Header().Get("Access-Control-Allow-Origin"))
	assert.Equal(t, "Origin", w.Header().Get("Vary"))
	assert.Equal(t, "true", w.Header().Get("Access-Control-Allow-Credentials"))
	assert.Contains(t, w.Header().Get("Access-Control-Allow-Headers"), "Authorization")
	assert.Contains(t, w.Header().Get("Access-Control-Allow-Methods"), "GET")
	assert.Contains(t, w.Header().Get("Access-Control-Allow-Methods"), "POST")
}

func TestCORS_DisallowedOrigin(t *testing.T) {
	cfg := &config.Config{AllowedOrigins: []string{"https://sparkle.app"}}
	r := gin.New()
	r.Use(CORSMiddleware(cfg))
	r.GET("/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Origin", "https://evil.com")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
}

func TestCORS_NoOrigin(t *testing.T) {
	cfg := &config.Config{AllowedOrigins: []string{"https://sparkle.app"}}
	r := gin.New()
	r.Use(CORSMiddleware(cfg))
	r.GET("/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
}

func TestCORS_PreflightRequest(t *testing.T) {
	cfg := &config.Config{AllowedOrigins: []string{"https://sparkle.app"}}
	r := gin.New()
	r.Use(CORSMiddleware(cfg))
	r.OPTIONS("/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodOptions, "/test", nil)
	req.Header.Set("Origin", "https://sparkle.app")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code)
	assert.Equal(t, "https://sparkle.app", w.Header().Get("Access-Control-Allow-Origin"))
}

func TestCORS_Preflight_Disallowed(t *testing.T) {
	cfg := &config.Config{AllowedOrigins: []string{"https://sparkle.app"}}
	r := gin.New()
	r.Use(CORSMiddleware(cfg))
	r.OPTIONS("/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodOptions, "/test", nil)
	req.Header.Set("Origin", "https://evil.com")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNoContent, w.Code) // OPTIONS still returns 204
	assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
}
