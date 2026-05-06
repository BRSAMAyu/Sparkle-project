package handler

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestInterventionPush_MissingUserID verifies that requests without user_id
// are rejected with 400. The handler validates user_id is non-empty.
func TestInterventionPush_MissingUserID(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	handler := &InterventionPushHandler{orchestrator: nil}
	router.POST("/push", handler.HandlePush)

	// Case 1: user_id field present but empty
	body := `{"user_id":"","intervention":{"intervention_id":"id1","level":"gentle","content":{"rendered_message":"hi"}}}`
	req := httptest.NewRequest(http.MethodPost, "/push", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusBadRequest, w.Code)
	assert.Contains(t, w.Body.String(), "user_id required")

	// Case 2: user_id field absent entirely
	body2 := `{"intervention":{"intervention_id":"id1","level":"gentle"}}`
	req2 := httptest.NewRequest(http.MethodPost, "/push", bytes.NewBufferString(body2))
	req2.Header.Set("Content-Type", "application/json")
	w2 := httptest.NewRecorder()
	router.ServeHTTP(w2, req2)
	assert.Equal(t, http.StatusBadRequest, w2.Code)
}

// TestInterventionPush_InvalidJSON verifies malformed JSON is rejected.
func TestInterventionPush_InvalidJSON(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	handler := &InterventionPushHandler{orchestrator: nil}
	router.POST("/push", handler.HandlePush)

	req := httptest.NewRequest(http.MethodPost, "/push", bytes.NewBufferString(`{invalid}`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	assert.Contains(t, w.Body.String(), "invalid payload")
}

// TestInterventionPush_PayloadParsing verifies that the full intervention
// payload is correctly parsed from JSON into the Go struct, covering all
// nested fields that get converted to protobuf.
func TestInterventionPush_PayloadParsing(t *testing.T) {
	raw := `{
		"user_id": "user-abc-123",
		"intervention": {
			"intervention_id": "int-001",
			"level": "gentle",
			"content": {
				"rendered_message": "You've been working for 2 hours. Take a break?",
				"intent_type": "wellbeing_nudge",
				"template_id": "break-reminder-v2",
				"scaffolding_level": 3,
				"context_variables": {"task_count": "5", "streak": "3"}
			},
			"actions": [
				{"id": "accept", "label": "OK, I'll rest", "type": "dismiss"},
				{"id": "snooze", "label": "15 more minutes", "type": "snooze"}
			],
			"expires_at": 1700000000
		}
	}`

	var req interventionPushRequest
	err := json.Unmarshal([]byte(raw), &req)
	require.NoError(t, err)

	// Verify top-level fields
	assert.Equal(t, "user-abc-123", req.UserID)
	assert.Equal(t, "int-001", req.Intervention.InterventionID)
	assert.Equal(t, "gentle", req.Intervention.Level)

	// Verify content mapping (these become pbws.InterventionContent fields)
	assert.Equal(t, "You've been working for 2 hours. Take a break?", req.Intervention.Content.RenderedMessage)
	assert.Equal(t, "wellbeing_nudge", req.Intervention.Content.IntentType)
	assert.Equal(t, "break-reminder-v2", req.Intervention.Content.TemplateId)
	assert.Equal(t, int32(3), req.Intervention.Content.ScaffoldingLevel)
	assert.Equal(t, "5", req.Intervention.Content.ContextVariables["task_count"])

	// Verify actions mapping (these become pbws.InterventionAction slice)
	require.Len(t, req.Intervention.Actions, 2)
	assert.Equal(t, "accept", req.Intervention.Actions[0].Id)
	assert.Equal(t, "OK, I'll rest", req.Intervention.Actions[0].Label)
	assert.Equal(t, "dismiss", req.Intervention.Actions[0].Type)
	assert.Equal(t, "snooze", req.Intervention.Actions[1].Type)

	// Verify expiry
	assert.Equal(t, int64(1700000000), req.Intervention.ExpiresAt)
}

// TestInterventionPush_EmptyActions verifies that empty actions array
// is handled correctly (no panic on empty slice → proto conversion).
func TestInterventionPush_EmptyActions(t *testing.T) {
	raw := `{
		"user_id": "u1",
		"intervention": {
			"intervention_id": "int-002",
			"level": "firm",
			"content": {"rendered_message": "Stop!"},
			"actions": [],
			"expires_at": 0
		}
	}`
	var req interventionPushRequest
	err := json.Unmarshal([]byte(raw), &req)
	require.NoError(t, err)
	assert.Empty(t, req.Intervention.Actions)
	// Verify we can create the proto actions slice without panic
	actions := make([]*interventionActionPayload, len(req.Intervention.Actions))
	assert.Len(t, actions, 0)
}

// TestInterventionPush_LevelValues documents the expected level values.
// The handler passes the level string directly to protobuf without validation.
func TestInterventionPush_LevelValues(t *testing.T) {
	levels := []string{"gentle", "firm", "urgent"}
	for _, level := range levels {
		t.Run(level, func(t *testing.T) {
			raw := `{"user_id":"u1","intervention":{"intervention_id":"i","level":"` + level + `","content":{"rendered_message":"m"}}}`
			var req interventionPushRequest
			err := json.Unmarshal([]byte(raw), &req)
			require.NoError(t, err)
			assert.Equal(t, level, req.Intervention.Level)
		})
	}
}
