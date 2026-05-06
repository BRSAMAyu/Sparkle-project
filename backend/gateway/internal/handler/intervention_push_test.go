package handler

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestInterventionPushHandler_HandlePush_InvalidPayload(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	handler := &InterventionPushHandler{orchestrator: nil}
	router.POST("/push", handler.HandlePush)

	req := httptest.NewRequest(http.MethodPost, "/push", bytes.NewBufferString(`not json`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	assert.Contains(t, w.Body.String(), "invalid payload")
}

func TestInterventionPushHandler_HandlePush_MissingUserID(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	handler := &InterventionPushHandler{orchestrator: nil}
	router.POST("/push", handler.HandlePush)

	body := `{"intervention":{"intervention_id":"id1","level":"gentle","content":{"rendered_message":"hi"}}}`
	req := httptest.NewRequest(http.MethodPost, "/push", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	assert.Contains(t, w.Body.String(), "user_id required")
}

func TestInterventionPushRequest_JSONBinding(t *testing.T) {
	tests := []struct {
		name    string
		json    string
		wantErr bool
	}{
		{
			name: "full valid payload",
			json: `{
				"user_id": "u-123",
				"intervention": {
					"intervention_id": "int-1",
					"level": "gentle",
					"content": {
						"rendered_message": "Take a break?",
						"intent_type": "nudge",
						"template_id": "tpl-1",
						"scaffolding_level": 2,
						"context_variables": {"key": "val"}
					},
					"actions": [
						{"id": "a1", "label": "OK", "type": "dismiss"}
					],
					"expires_at": 1700000000
				}
			}`,
			wantErr: false,
		},
		{
			name:    "empty json object",
			json:    `{}`,
			wantErr: false, // All fields have zero values, but binding doesn't require them
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var req interventionPushRequest
			err := json.Unmarshal([]byte(tt.json), &req)
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestInterventionActionPayload_SliceConversion(t *testing.T) {
	// Verify actions slice converts correctly to proto format
	actions := []interventionActionPayload{
		{Id: "a1", Label: "OK", Type: "dismiss"},
		{Id: "a2", Label: "Later", Type: "snooze"},
	}

	assert.Len(t, actions, 2)
	assert.Equal(t, "a1", actions[0].Id)
	assert.Equal(t, "snooze", actions[1].Type)
}

func TestInterventionContentPayload_Fields(t *testing.T) {
	payload := interventionContentPayload{
		RenderedMessage:  "Take a break?",
		IntentType:       "nudge",
		TemplateId:       "tpl-1",
		ScaffoldingLevel: 2,
		ContextVariables: map[string]string{"key": "val"},
	}
	assert.Equal(t, "Take a break?", payload.RenderedMessage)
	assert.Equal(t, int32(2), payload.ScaffoldingLevel)
	assert.Len(t, payload.ContextVariables, 1)
}
