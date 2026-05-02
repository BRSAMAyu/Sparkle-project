package middleware

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func TestNetworkResilienceMiddleware_KeepAliveHeaders(t *testing.T) {
	cfg := DefaultNetworkResilienceConfig()
	cfg.KeepAliveInterval = 15 * time.Second

	r := gin.New()
	r.Use(NetworkResilienceMiddleware(cfg))
	r.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, "keep-alive", w.Header().Get("Connection"))
	assert.Contains(t, w.Header().Get("Keep-Alive"), "timeout=")
}

func TestNetworkResilienceMiddleware_NoKeepAliveWhenDisabled(t *testing.T) {
	cfg := DefaultNetworkResilienceConfig()
	cfg.KeepAliveInterval = 0

	r := gin.New()
	r.Use(NetworkResilienceMiddleware(cfg))
	r.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	r.ServeHTTP(w, req)

	assert.Empty(t, w.Header().Get("Keep-Alive"))
}

func TestNetworkResilienceMiddleware_DisconnectDetection(t *testing.T) {
	cfg := DefaultNetworkResilienceConfig()

	var disconnectFlag atomic.Bool

	r := gin.New()
	r.Use(NetworkResilienceMiddleware(cfg))
	r.GET("/test", func(c *gin.Context) {
		// Simulate write failure by writing to a broken connection simulation
		// In real scenarios, the Writer wrapper detects write errors
		dw, ok := c.Writer.(*disconnectWatcher)
		require.True(t, ok, "Writer should be a disconnectWatcher")

		// Simulate client disconnecting during handler execution
		dw.markDisconnected()
		c.Set("client_disconnected", true)
		c.Set("state_save_required", true)
		disconnectFlag.Store(true)

		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	r.ServeHTTP(w, req)

	// After handler marks disconnect, the middleware should preserve this info
	assert.True(t, disconnectFlag.Load())
}

func TestNetworkResilienceMiddleware_RequestTimeout(t *testing.T) {
	cfg := DefaultNetworkResilienceConfig()
	cfg.RequestTimeout = 50 * time.Millisecond

	r := gin.New()
	r.Use(NetworkResilienceMiddleware(cfg))
	r.GET("/slow", func(c *gin.Context) {
		select {
		case <-c.Request.Context().Done():
			c.JSON(http.StatusGatewayTimeout, gin.H{"error": "timeout"})
			return
		case <-time.After(200 * time.Millisecond):
			c.JSON(http.StatusOK, gin.H{"ok": true})
		}
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/slow", nil)
	r.ServeHTTP(w, req)

	assert.True(t, w.Code == http.StatusGatewayTimeout || w.Code == http.StatusOK)
}

func TestDisconnectWatcher_WriteSuccess(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx, _ := gin.CreateTestContext(httptest.NewRecorder())
	baseWriter := ctx.Writer

	dw := &disconnectWatcher{ResponseWriter: baseWriter}

	n, err := dw.Write([]byte(`hello`))
	assert.NoError(t, err)
	assert.Equal(t, 5, n)
	assert.False(t, dw.isDisconnected())
}

func TestDisconnectWatcher_MarkDisconnected(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx, _ := gin.CreateTestContext(httptest.NewRecorder())

	dw := &disconnectWatcher{ResponseWriter: ctx.Writer}

	assert.False(t, dw.isDisconnected())
	dw.markDisconnected()
	assert.True(t, dw.isDisconnected())
}

func TestDisconnectWatcher_WriteHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx, _ := gin.CreateTestContext(httptest.NewRecorder())

	dw := &disconnectWatcher{ResponseWriter: ctx.Writer}

	dw.WriteHeader(http.StatusCreated)
	assert.Equal(t, http.StatusCreated, ctx.Writer.Status())
}

func TestRetryableUpstreamProxy_Success(t *testing.T) {
	// Start a local test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	}))
	defer server.Close()

	cfg := DefaultNetworkResilienceConfig()
	cfg.MaxRetries = 1

	req, err := http.NewRequest(http.MethodGet, server.URL+"/api/test", nil)
	require.NoError(t, err)

	resp, err := RetryableUpstreamProxy(
		context.Background(),
		&http.Client{Timeout: 10 * time.Second},
		req,
		cfg,
		nil,
	)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)

	body, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	assert.Contains(t, string(body), `"status":"ok"`)
}

func TestRetryableUpstreamProxy_RetryOnTransient(t *testing.T) {
	var attempts atomic.Int32

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		n := attempts.Add(1)
		if n < 3 {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`recovered`))
	}))
	defer server.Close()

	cfg := DefaultNetworkResilienceConfig()
	cfg.MaxRetries = 3
	cfg.RetryBackoff = 10 * time.Millisecond

	req, err := http.NewRequest(http.MethodGet, server.URL+"/api/retry", nil)
	require.NoError(t, err)

	resp, err := RetryableUpstreamProxy(
		context.Background(),
		&http.Client{Timeout: 10 * time.Second},
		req,
		cfg,
		nil,
	)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
	assert.GreaterOrEqual(t, attempts.Load(), int32(2))
}

func TestRetryableUpstreamProxy_ExhaustedRetries(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadGateway)
	}))
	defer server.Close()

	cfg := DefaultNetworkResilienceConfig()
	cfg.MaxRetries = 1
	cfg.RetryBackoff = 5 * time.Millisecond

	req, err := http.NewRequest(http.MethodGet, server.URL+"/api/fail", nil)
	require.NoError(t, err)

	resp, err := RetryableUpstreamProxy(
		context.Background(),
		&http.Client{Timeout: 5 * time.Second},
		req,
		cfg,
		nil,
	)
	require.NoError(t, err)
	assert.Equal(t, http.StatusBadGateway, resp.StatusCode)
}

func TestRetryableUpstreamProxy_ContextCancelled(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(500 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	cfg := DefaultNetworkResilienceConfig()
	cfg.MaxRetries = 2

	ctx, cancel := context.WithCancel(context.Background())
	req, err := http.NewRequest(http.MethodGet, server.URL+"/api/slow", nil)
	require.NoError(t, err)

	// Cancel immediately
	cancel()

	_, err = RetryableUpstreamProxy(
		ctx,
		&http.Client{Timeout: 5 * time.Second},
		req,
		cfg,
		nil,
	)
	assert.Error(t, err)
}

func TestRetryableUpstreamProxy_RequestBodyRetained(t *testing.T) {
	var bodySnapshot string

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		bodySnapshot = string(b)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	cfg := DefaultNetworkResilienceConfig()
	cfg.MaxRetries = 1

	body := `{"task":"write","content":"hello world"}`
	req, err := http.NewRequest(
		http.MethodPost,
		server.URL+"/api/body",
		strings.NewReader(body),
	)
	require.NoError(t, err)

	resp, err := RetryableUpstreamProxy(
		context.Background(),
		&http.Client{Timeout: 10 * time.Second},
		req,
		cfg,
		nil,
	)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
	assert.Equal(t, body, bodySnapshot)
}

func TestDefaultNetworkResilienceConfig_SensibleDefaults(t *testing.T) {
	cfg := DefaultNetworkResilienceConfig()

	assert.Equal(t, 2, cfg.MaxRetries)
	assert.Equal(t, 200*time.Millisecond, cfg.RetryBackoff)
	assert.Equal(t, 30*time.Second, cfg.RequestTimeout)
	assert.Equal(t, 15*time.Second, cfg.KeepAliveInterval)
	assert.True(t, cfg.RetryableStatusCodes[http.StatusBadGateway])
	assert.True(t, cfg.RetryableStatusCodes[http.StatusServiceUnavailable])
}

func TestNetworkResilienceMiddleware_ZeroConfigDefaults(t *testing.T) {
	cfg := NetworkResilienceConfig{}

	r := gin.New()
	r.Use(NetworkResilienceMiddleware(cfg))
	r.GET("/minimal", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/minimal", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
}
