package handler

import (
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// PredictiveProxyHandler proxies predictive analytics requests to Python backend.
type PredictiveProxyHandler struct {
	backendURL string
	client     *http.Client
}

// NewPredictiveProxyHandler creates a new predictive proxy handler.
func NewPredictiveProxyHandler(backendURL string) *PredictiveProxyHandler {
	return &PredictiveProxyHandler{
		backendURL: strings.TrimRight(backendURL, "/"),
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// Proxy forwards predictive requests to the backend.
func (h *PredictiveProxyHandler) Proxy(c *gin.Context) {
	path := c.Param("path")
	targetURL := h.backendURL + "/api/v1/predictive" + path
	if c.Request.URL.RawQuery != "" {
		targetURL += "?" + c.Request.URL.RawQuery
	}

	req, err := http.NewRequestWithContext(c.Request.Context(), c.Request.Method, targetURL, c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "invalid request"})
		return
	}

	copyHeader(c.Request.Header, req.Header)

	resp, err := h.client.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "backend unavailable"})
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	for key, values := range resp.Header {
		for _, value := range values {
			c.Writer.Header().Add(key, value)
		}
	}
	c.Status(resp.StatusCode)
	c.Writer.Write(body)
}
