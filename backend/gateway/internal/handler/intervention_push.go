package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
	pbws "github.com/sparkle/gateway/gen/ws"
)

type InterventionPushHandler struct {
	orchestrator *ChatOrchestrator
}

type interventionPushRequest struct {
	UserID       string                  `json:"user_id"`
	Intervention interventionPushPayload `json:"intervention"`
}

type interventionPushPayload struct {
	InterventionID string                      `json:"intervention_id"`
	Level          string                      `json:"level"`
	Content        interventionContentPayload  `json:"content"`
	Actions        []interventionActionPayload `json:"actions"`
	ExpiresAt      int64                       `json:"expires_at"`
}

type interventionContentPayload struct {
	RenderedMessage  string            `json:"rendered_message"`
	IntentType       string            `json:"intent_type"`
	TemplateId       string            `json:"template_id"`
	ScaffoldingLevel int32             `json:"scaffolding_level"`
	ContextVariables map[string]string `json:"context_variables"`
}

type interventionActionPayload struct {
	Id    string `json:"id"`
	Label string `json:"label"`
	Type  string `json:"type"`
}

func NewInterventionPushHandler(orchestrator *ChatOrchestrator) *InterventionPushHandler {
	return &InterventionPushHandler{orchestrator: orchestrator}
}

func (h *InterventionPushHandler) HandlePush(c *gin.Context) {
	var req interventionPushRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid payload"})
		return
	}
	if req.UserID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user_id required"})
		return
	}

	content := &pbws.InterventionContent{
		RenderedMessage:  req.Intervention.Content.RenderedMessage,
		IntentType:       req.Intervention.Content.IntentType,
		TemplateId:       req.Intervention.Content.TemplateId,
		ScaffoldingLevel: req.Intervention.Content.ScaffoldingLevel,
		ContextVariables: req.Intervention.Content.ContextVariables,
	}

	actions := make([]*pbws.InterventionAction, len(req.Intervention.Actions))
	for i, action := range req.Intervention.Actions {
		actions[i] = &pbws.InterventionAction{
			Id:    action.Id,
			Label: action.Label,
			Type:  action.Type,
		}
	}

	msg := &pbws.InterventionPushMessage{
		InterventionId: req.Intervention.InterventionID,
		Level:          req.Intervention.Level,
		Content:        content,
		Actions:        actions,
		ExpiresAt:      req.Intervention.ExpiresAt,
	}

	if err := h.orchestrator.PushIntervention(req.UserID, msg); err != nil {
		payload := sanitizeErrorPayload(c, http.StatusAccepted, err, "intervention_push.push_intervention")
		payload["status"] = "queued"
		c.JSON(http.StatusAccepted, payload)
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "delivered"})
}
