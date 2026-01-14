package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/service"
)

type SignalPushHandler struct {
	cfg *config.Config
	hub *service.SignalHub
}

type signalCandidate struct {
	ID          string            `json:"id"`
	Type        string            `json:"type"`
	Trigger     string            `json:"trigger"`
	ContentSeed string            `json:"content_seed"`
	Priority    float64           `json:"priority"`
	Metadata    map[string]string `json:"metadata"`
}

type signalPushRequest struct {
	UserID        string            `json:"user_id"`
	RequestID     string            `json:"request_id"`
	TraceID       string            `json:"trace_id"`
	SchemaVersion string            `json:"schema_version"`
	CandidateSet  map[string]any    `json:"candidate_set"`
	Candidates    []signalCandidate `json:"candidates"`
}

func NewSignalPushHandler(cfg *config.Config, hub *service.SignalHub) *SignalPushHandler {
	return &SignalPushHandler{cfg: cfg, hub: hub}
}

func (h *SignalPushHandler) HandlePush(c *gin.Context) {
	if !h.isAuthorized(c) {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	var req signalPushRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid payload"})
		return
	}

	if req.UserID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing user_id"})
		return
	}

	candidates := req.Candidates
	if len(candidates) == 0 && req.CandidateSet != nil {
		if req.RequestID == "" {
			if val, ok := req.CandidateSet["request_id"].(string); ok {
				req.RequestID = val
			}
		}
		if req.TraceID == "" {
			if val, ok := req.CandidateSet["trace_id"].(string); ok {
				req.TraceID = val
			}
		}
		if req.SchemaVersion == "" {
			if val, ok := req.CandidateSet["schema_version"].(string); ok {
				req.SchemaVersion = val
			}
		}
		if raw, ok := req.CandidateSet["candidates"]; ok {
			if list, ok := raw.([]any); ok {
				for _, item := range list {
					candidate, ok := item.(map[string]any)
					if !ok {
						continue
					}
					cand := signalCandidate{}
					if val, ok := candidate["id"].(string); ok {
						cand.ID = val
					}
					if val, ok := candidate["type"].(string); ok {
						cand.Type = val
					}
					if val, ok := candidate["trigger"].(string); ok {
						cand.Trigger = val
					}
					if val, ok := candidate["content_seed"].(string); ok {
						cand.ContentSeed = val
					}
					if val, ok := candidate["priority"].(float64); ok {
						cand.Priority = val
					}
					if meta, ok := candidate["metadata"].(map[string]any); ok {
						cand.Metadata = mapStringString(meta)
					}
					candidates = append(candidates, cand)
				}
			}
		}
	}

	for _, candidate := range candidates {
		if candidate.Type == "" {
			continue
		}
		payload := gin.H{
			"type":        "widget",
			"widget_type": candidate.Type,
			"widget_data": gin.H{
				"id":             candidate.ID,
				"title":          candidate.ContentSeed,
				"trigger":        candidate.Trigger,
				"priority":       candidate.Priority,
				"schema_version": req.SchemaVersion,
				"request_id":     req.RequestID,
				"trace_id":       req.TraceID,
			},
		}
		if len(candidate.Metadata) > 0 {
			payload["widget_data"].(gin.H)["metadata"] = candidate.Metadata
		}
		h.hub.Send(req.UserID, payload)
	}

	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func (h *SignalPushHandler) isAuthorized(c *gin.Context) bool {
	if h.cfg.InternalAPIKey == "" {
		return true
	}
	key := c.GetHeader("X-Internal-API-Key")
	return key != "" && key == h.cfg.InternalAPIKey
}

func mapStringString(input map[string]any) map[string]string {
	out := make(map[string]string, len(input))
	for key, value := range input {
		if str, ok := value.(string); ok {
			out[key] = str
		}
	}
	return out
}
