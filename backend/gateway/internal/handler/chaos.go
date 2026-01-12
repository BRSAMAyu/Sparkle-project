package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/service"
)

type ChaosHandler struct {
	chatHistory     *service.ChatHistoryService
	toxiproxyURL    string
	chaosHTTPClient *http.Client
}

func NewChaosHandler(ch *service.ChatHistoryService, toxiproxyURL string) *ChaosHandler {
	if toxiproxyURL == "" {
		toxiproxyURL = "http://toxiproxy:8474"
	}
	return &ChaosHandler{
		chatHistory:     ch,
		toxiproxyURL:    strings.TrimRight(toxiproxyURL, "/"),
		chaosHTTPClient: &http.Client{Timeout: 5 * time.Second},
	}
}

func (h *ChaosHandler) SetThreshold(c *gin.Context) {
	var req struct {
		Target string `json:"target"` // "queue_persist"
		Value  int64  `json:"value"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	if req.Target == "queue_persist" {
		h.chatHistory.SetBreakerThreshold(req.Value)

		qLen, _ := h.chatHistory.GetQueueLength(c.Request.Context())

		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
			"msg":    fmt.Sprintf("Threshold updated to %d", req.Value),
			"details": gin.H{
				"current_queue":   qLen,
				"new_threshold":   req.Value,
				"breaker_tripped": qLen >= req.Value,
			},
		})
	} else {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Unknown target"})
	}
}

func (h *ChaosHandler) GetStatus(c *gin.Context) {
	qLen, _ := h.chatHistory.GetQueueLength(c.Request.Context())
	threshold := h.chatHistory.GetBreakerThreshold()

	c.JSON(http.StatusOK, gin.H{
		"queue_length": qLen,
		"threshold":    threshold,
		"is_tripped":   qLen >= threshold,
	})
}

func (h *ChaosHandler) SetGrpcLatency(c *gin.Context) {
	var req struct {
		Proxy     string `json:"proxy"`
		LatencyMs int    `json:"latency_ms"`
		JitterMs  int    `json:"jitter_ms"`
		ToxicName string `json:"toxic_name"`
		Stream    string `json:"stream"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	if req.LatencyMs <= 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "latency_ms must be > 0"})
		return
	}

	proxy := req.Proxy
	if proxy == "" {
		proxy = "grpc_backend"
	}
	toxicName := req.ToxicName
	if toxicName == "" {
		toxicName = "grpc_latency"
	}
	stream := req.Stream
	if stream == "" {
		stream = "upstream"
	}

	payload := map[string]interface{}{
		"name":   toxicName,
		"type":   "latency",
		"stream": stream,
		"attributes": map[string]int{
			"latency": req.LatencyMs,
			"jitter":  req.JitterMs,
		},
	}

	if err := h.postToxiproxy(c, proxy, payload); err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "injected", "proxy": proxy, "toxic": toxicName})
}

func (h *ChaosHandler) ResetGrpcLatency(c *gin.Context) {
	proxy := c.Query("proxy")
	if proxy == "" {
		proxy = "grpc_backend"
	}
	toxicName := c.Query("toxic")
	if toxicName == "" {
		toxicName = "grpc_latency"
	}

	if err := h.deleteToxic(c, proxy, toxicName); err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "reset", "proxy": proxy, "toxic": toxicName})
}

func (h *ChaosHandler) postToxiproxy(c *gin.Context, proxy string, payload map[string]interface{}) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequestWithContext(c.Request.Context(), http.MethodPost, h.toxiproxyURL+"/proxies/"+proxy+"/toxics", bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := h.chaosHTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("toxiproxy error: %s", resp.Status)
	}
	return nil
}

func (h *ChaosHandler) deleteToxic(c *gin.Context, proxy string, toxicName string) error {
	req, err := http.NewRequestWithContext(c.Request.Context(), http.MethodDelete, h.toxiproxyURL+"/proxies/"+proxy+"/toxics/"+toxicName, nil)
	if err != nil {
		return err
	}

	resp, err := h.chaosHTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil
	}
	if resp.StatusCode >= 300 {
		return fmt.Errorf("toxiproxy error: %s", resp.Status)
	}
	return nil
}
