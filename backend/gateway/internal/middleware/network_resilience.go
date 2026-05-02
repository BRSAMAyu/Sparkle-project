// Core: infra
// Phase: sense
// Stage: FV-24
//
// Network resilience middleware for Go Gateway.
// Provides request keepalive, upstream retry with backoff,
// and client disconnect detection with state-save signaling.

package middleware

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"go.uber.org/zap"
)

var (
	networkResilienceRetries = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "sparkle_network_resilience_retries_total",
			Help: "Number of upstream retries performed by network resilience middleware",
		},
		[]string{"path", "status"},
	)

	networkResilienceDisconnects = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "sparkle_network_resilience_client_disconnects_total",
			Help: "Number of client disconnects detected during upstream proxying",
		},
		[]string{"path"},
	)

	networkResilienceStateSaves = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "sparkle_network_resilience_state_saves_total",
			Help: "Number of intermediate state saves triggered by client disconnect",
		},
		[]string{"path", "status"},
	)
)

// NetworkResilienceConfig holds configuration for the resilience middleware.
type NetworkResilienceConfig struct {
	// MaxRetries is the maximum number of upstream retry attempts (default 2).
	MaxRetries int
	// RetryBackoff is the base duration for exponential backoff between retries.
	RetryBackoff time.Duration
	// RetryableStatusCodes defines which upstream status codes trigger a retry.
	RetryableStatusCodes map[int]bool
	// KeepAliveInterval controls how often keepalive probes are sent (0 = disabled).
	KeepAliveInterval time.Duration
	// RequestTimeout is the total timeout for a request including retries.
	RequestTimeout time.Duration
}

// DefaultNetworkResilienceConfig returns sensible defaults.
func DefaultNetworkResilienceConfig() NetworkResilienceConfig {
	return NetworkResilienceConfig{
		MaxRetries:   2,
		RetryBackoff: 200 * time.Millisecond,
		RetryableStatusCodes: map[int]bool{
			http.StatusBadGateway:         true,
			http.StatusServiceUnavailable: true,
			http.StatusGatewayTimeout:     true,
			http.StatusTooManyRequests:    true,
		},
		KeepAliveInterval: 15 * time.Second,
		RequestTimeout:    30 * time.Second,
	}
}

// NetworkResilienceMiddleware creates a gin middleware that provides:
// 1. Upstream retry with exponential backoff for transient failures
// 2. Client disconnect detection
// 3. Request timeout enforcement
// 4. Keepalive header injection
func NetworkResilienceMiddleware(cfg NetworkResilienceConfig) gin.HandlerFunc {
	if cfg.MaxRetries <= 0 {
		cfg.MaxRetries = 2
	}
	if cfg.RetryBackoff <= 0 {
		cfg.RetryBackoff = 200 * time.Millisecond
	}
	if cfg.RequestTimeout <= 0 {
		cfg.RequestTimeout = 30 * time.Second
	}

	return func(c *gin.Context) {
		path := c.Request.URL.Path

		// Set keepalive headers for long-running connections
		if cfg.KeepAliveInterval > 0 {
			c.Header("Keep-Alive", fmt.Sprintf("timeout=%d", int(cfg.KeepAliveInterval.Seconds())))
			c.Header("Connection", "keep-alive")
		}

		// Wrap the writer to detect client disconnects via write failures
		dw := &disconnectWatcher{
			ResponseWriter: c.Writer,
			path:           path,
		}
		c.Writer = dw

		// Enforce overall request timeout
		ctx, cancel := context.WithTimeout(c.Request.Context(), cfg.RequestTimeout)
		defer cancel()
		c.Request = c.Request.WithContext(ctx)

		// Monitor for client disconnect in background
		done := make(chan struct{})
		go func() {
			select {
			case <-ctx.Done():
				// Request timed out or cancelled
				if ctx.Err() == context.Canceled {
					dw.markDisconnected()
					networkResilienceDisconnects.WithLabelValues(path).Inc()
				}
			case <-done:
				// Request completed normally
			}
		}()

		c.Next()
		close(done)

		// If client disconnected during processing, signal state save
		if dw.isDisconnected() {
			networkResilienceStateSaves.WithLabelValues(path, "triggered").Inc()
			c.Set("client_disconnected", true)
			c.Set("state_save_required", true)
		}
	}
}

// disconnectWatcher wraps gin.ResponseWriter to detect write failures
// that indicate client disconnect.
type disconnectWatcher struct {
	gin.ResponseWriter
	path         string
	disconnected bool
}

func (w *disconnectWatcher) markDisconnected() {
	w.disconnected = true
}

func (w *disconnectWatcher) isDisconnected() bool {
	return w.disconnected
}

func (w *disconnectWatcher) Write(data []byte) (int, error) {
	n, err := w.ResponseWriter.Write(data)
	if err != nil {
		w.disconnected = true
		networkResilienceDisconnects.WithLabelValues(w.path).Inc()
	}
	return n, err
}

func (w *disconnectWatcher) WriteHeader(statusCode int) {
	w.ResponseWriter.WriteHeader(statusCode)
}

// RetryableUpstreamProxy performs an upstream HTTP request with retry logic.
// This is used by proxy handlers to retry on transient failures.
func RetryableUpstreamProxy(
	ctx context.Context,
	client *http.Client,
	req *http.Request,
	cfg NetworkResilienceConfig,
	logger *zap.Logger,
) (*http.Response, error) {
	// Read and buffer the request body for retries
	var bodyBytes []byte
	if req.Body != nil {
		var err error
		bodyBytes, err = io.ReadAll(req.Body)
		if err != nil {
			return nil, fmt.Errorf("read request body: %w", err)
		}
		req.Body.Close()
	}

	var lastResp *http.Response
	var lastErr error

	for attempt := 0; attempt <= cfg.MaxRetries; attempt++ {
		if attempt > 0 {
			backoff := cfg.RetryBackoff * time.Duration(1<<uint(attempt-1))
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(backoff):
			}

			networkResilienceRetries.WithLabelValues(req.URL.Path, "attempt").Inc()
		}

		// Reset body for each attempt
		if bodyBytes != nil {
			req.Body = io.NopCloser(bytes.NewReader(bodyBytes))
		}
		req.ContentLength = int64(len(bodyBytes))

		resp, err := client.Do(req.WithContext(ctx))
		if err != nil {
			lastErr = err
			if logger != nil {
				logger.Debug("upstream request failed, may retry",
					zap.Int("attempt", attempt),
					zap.String("error", err.Error()),
				)
			}
			continue
		}

		if cfg.RetryableStatusCodes[resp.StatusCode] {
			lastResp = resp
			resp.Body.Close()
			if logger != nil {
				logger.Debug("upstream returned retryable status",
					zap.Int("attempt", attempt),
					zap.Int("status", resp.StatusCode),
				)
			}
			continue
		}

		return resp, nil
	}

	networkResilienceRetries.WithLabelValues(req.URL.Path, "exhausted").Inc()

	if lastResp != nil {
		return lastResp, nil
	}
	return nil, fmt.Errorf("upstream request failed after %d attempts: %w", cfg.MaxRetries+1, lastErr)
}
