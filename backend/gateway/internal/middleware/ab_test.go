// Package middleware provides A/B testing middleware for the Go Gateway
package middleware

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// ABTestConfig holds configuration for A/B testing
type ABTestConfig struct {
	BackendURL            string
	ExperimentServiceAddr string
	Timeout              time.Duration
	Enabled              bool
}

// ABTestMiddleware handles experiment variant assignment
type ABTestMiddleware struct {
	config     *ABTestConfig
	httpClient *http.Client
}

// NewABTestMiddleware creates a new A/B test middleware
func NewABTestMiddleware(config *ABTestConfig) *ABTestMiddleware {
	return &ABTestMiddleware{
		config:     config,
		httpClient: &http.Client{Timeout: config.Timeout},
	}
}

// AssignVariant assigns a user to an experiment variant
func (m *ABTestMiddleware) AssignVariant() gin.HandlerFunc {
	return func(c *gin.Context) {
		if !m.config.Enabled {
			c.Next()
			return
		}

		// Get user ID from context (set by auth middleware)
		userID, exists := c.Get("user_id")
		if !exists {
			c.Next()
			return
		}

		userIDStr, ok := userID.(string)
		if !ok {
			c.Next()
			return
		}

		experimentID := c.GetHeader("X-Experiment-ID")
		if experimentID == "" {
			experimentID = m.getDefaultExperimentID(c.Request.URL.Path)
		}
		if experimentID == "" {
			c.Next()
			return
		}

		ctx, cancel := context.WithTimeout(c.Request.Context(), m.config.Timeout)
		defer cancel()

		variant, err := m.assignVariant(ctx, experimentID, c.GetHeader("Authorization"))
		if err != nil {
			// Log error but don't block request
			fmt.Printf("A/B test assignment failed: %v\n", err)
			c.Next()
			return
		}

		// Store variant info in context for downstream handlers
		c.Set("ab_test_variant", variant)
		c.Set("ab_test_user_id", userIDStr)

		// Add variant info to request headers for Python backend
		c.Request.Header.Set("X-AB-Experiment-ID", variant.ExperimentID)
		c.Request.Header.Set("X-AB-Variant-ID", variant.VariantID)
		c.Request.Header.Set("X-AB-Variant-Name", variant.VariantName)

		c.Next()
	}
}

// VariantInfo holds information about assigned variant
type VariantInfo struct {
	ExperimentID string
	VariantID    string
	VariantName  string
	IsNewAssignment bool
}

// assignVariant calls the Python experiment service to assign a variant
func (m *ABTestMiddleware) assignVariant(
	ctx context.Context,
	experimentID string,
	authHeader string,
) (*VariantInfo, error) {
	if m.config.BackendURL == "" {
		return nil, fmt.Errorf("backend URL is not configured")
	}

	url := strings.TrimRight(m.config.BackendURL, "/") +
		"/api/v1/experiments/" + experimentID + "/assign"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to build assign request: %w", err)
	}
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}

	resp, err := m.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("assign request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("assign request returned status %d", resp.StatusCode)
	}

	var payload struct {
		VariantID       string `json:"variant_id"`
		VariantName     string `json:"variant_name"`
		IsNewAssignment bool   `json:"is_new_assignment"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, fmt.Errorf("failed to decode assign response: %w", err)
	}

	return &VariantInfo{
		ExperimentID:    experimentID,
		VariantID:       payload.VariantID,
		VariantName:     payload.VariantName,
		IsNewAssignment: payload.IsNewAssignment,
	}, nil
}

// getDefaultExperimentID determines the experiment ID based on request path
func (m *ABTestMiddleware) getDefaultExperimentID(path string) string {
	// Map request paths to experiments
	switch {
	case path == "/api/v1/chat" || path == "/ws/chat":
		return "default-chat-experiment"
	case path == "/api/v1/plans":
		return "planning-experiment"
	case path == "/api/v1/recommendations":
		return "recommendation-experiment"
	default:
		return ""
	}
}

// RecordMetric records an A/B test metric
func (m *ABTestMiddleware) RecordMetric() gin.HandlerFunc {
	return func(c *gin.Context) {
		if !m.config.Enabled {
			c.Next()
			return
		}

		// Defer metric recording until after handler executes
		defer func() {
			variant, hasVariant := c.Get("ab_test_variant")
			if !hasVariant {
				return
			}

			variantInfo := variant.(*VariantInfo)
			authHeader := c.GetHeader("Authorization")

			// Extract metric info from response
			statusCode := c.Writer.Status()
			latency := c.GetString("latency") // Set by another middleware

			// Convert to metric type
			metricName := "success"
			metricValue := float64(0)

			if statusCode >= 200 && statusCode < 300 {
				metricValue = 1.0 // Success
			} else {
				metricValue = 0.0 // Failure
			}

			// Get latency if available
			if latency != "" {
				if latencyMs, err := strconv.ParseFloat(latency, 64); err == nil {
					// Record latency metric
					go m.recordMetricAsync(
						variantInfo.ExperimentID,
						variantInfo.VariantID,
						"latency",
						latencyMs,
						"latency",
						map[string]interface{}{
							"path":   c.Request.URL.Path,
							"method": c.Request.Method,
						},
						authHeader,
					)
				}
			}

			// Record success/error metric asynchronously
			go m.recordMetricAsync(
				variantInfo.ExperimentID,
				variantInfo.VariantID,
				metricName,
				metricValue,
				"success",
				map[string]interface{}{
					"path":        c.Request.URL.Path,
					"method":      c.Request.Method,
					"status_code": statusCode,
				},
				authHeader,
			)
		}()

		c.Next()
	}
}

// recordMetricAsync records a metric asynchronously
func (m *ABTestMiddleware) recordMetricAsync(
	experimentID string,
	variantID string,
	metricName string,
	metricValue float64,
	metricType string,
	contextData map[string]interface{},
	authHeader string,
) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if m.config.BackendURL == "" {
		fmt.Printf("Failed to record metric: backend URL not configured\n")
		return
	}

	url := strings.TrimRight(m.config.BackendURL, "/") +
		"/api/v1/experiments/" + experimentID + "/metrics?variant_id=" + variantID

	body, err := json.Marshal(map[string]interface{}{
		"metric_name":  metricName,
		"metric_value": metricValue,
		"metric_type":  metricType,
		"context_data": contextData,
	})
	if err != nil {
		fmt.Printf("Failed to marshal metric payload: %v\n", err)
		return
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		fmt.Printf("Failed to build metric request: %v\n", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}

	resp, err := m.httpClient.Do(req)
	if err != nil {
		fmt.Printf("Failed to record metric: %v\n", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		fmt.Printf("Failed to record metric, status: %d\n", resp.StatusCode)
	}
}

// ExperimentReporter handles reporting experiment results
type ExperimentReporter struct {
	config *ABTestConfig
}

// NewExperimentReporter creates a new experiment reporter
func NewExperimentReporter(config *ABTestConfig) *ExperimentReporter {
	return &ExperimentReporter{
		config: config,
	}
}

// GetExperimentStats fetches experiment statistics
func (r *ExperimentReporter) GetExperimentStats(
	experimentID string,
) (map[string]interface{}, error) {
	if r.config.BackendURL == "" {
		return nil, fmt.Errorf("backend URL is not configured")
	}

	ctx, cancel := context.WithTimeout(context.Background(), r.config.Timeout)
	defer cancel()

	url := strings.TrimRight(r.config.BackendURL, "/") +
		"/api/v1/experiments/" + experimentID + "/stats"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to build stats request: %w", err)
	}

	client := &http.Client{Timeout: r.config.Timeout}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("stats request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("stats request returned status %d", resp.StatusCode)
	}

	stats := make(map[string]interface{})
	if err := json.NewDecoder(resp.Body).Decode(&stats); err != nil {
		return nil, fmt.Errorf("failed to decode stats response: %w", err)
	}

	return stats, nil
}
