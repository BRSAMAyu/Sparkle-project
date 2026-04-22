package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/service"
	"github.com/stretchr/testify/require"
)

func TestGetConversationHistoryIncludesMobileContractFields(t *testing.T) {
	gin.SetMode(gin.TestMode)
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := service.NewChatHistoryService(rdb)
	handler := NewChatHistoryHandler(svc)

	payload := `{
		"id":"msg-1",
		"session_id":"session-1",
		"user_id":"user-1",
		"task_id":"task-1",
		"role":"assistant",
		"content":"hello",
		"timestamp":"1710000001",
		"widgets":[{"type":"cta","data":{"label":"继续"}}],
		"tool_results":[{"success":true,"tool_name":"planner","data":{"ok":true}}],
		"has_errors":true,
		"errors":[{"tool":"planner","message":"warn"}],
		"requires_confirmation":true,
		"confirmation_data":{"action_id":"act-1"},
		"reasoning_steps":[{"title":"step-1"}],
		"reasoning_summary":"done",
		"is_reasoning_complete":true,
		"meta":{"latency_ms":12},
		"agentCollaboration":{"workflow":"team"}
	}`
	require.NoError(t, svc.SaveMessage(createGinContext().Request.Context(), "session-1", []byte(payload)))

	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("user_id", "user-1")
		c.Next()
	})
	router.GET("/history/:conversation_id", handler.GetConversationHistory)

	req := httptest.NewRequest(http.MethodGet, "/history/session-1", nil)
	resp := httptest.NewRecorder()
	router.ServeHTTP(resp, req)

	require.Equal(t, http.StatusOK, resp.Code)
	var body []map[string]interface{}
	require.NoError(t, json.Unmarshal(resp.Body.Bytes(), &body))
	require.Len(t, body, 1)
	msg := body[0]

	for _, key := range []string{
		"id", "user_id", "conversation_id", "session_id", "task_id", "role", "content", "created_at",
		"widgets", "tool_results", "has_errors", "errors", "requires_confirmation", "confirmation_data",
		"reasoning_steps", "reasoning_summary", "is_reasoning_complete", "meta", "agentCollaboration",
	} {
		_, ok := msg[key]
		require.Truef(t, ok, "expected key %s in response", key)
	}
}

func TestGetConversationHistoryKeepsNullShapeForOptionalFields(t *testing.T) {
	gin.SetMode(gin.TestMode)
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := service.NewChatHistoryService(rdb)
	handler := NewChatHistoryHandler(svc)

	require.NoError(
		t,
		svc.SaveMessage(
			createGinContext().Request.Context(),
			"session-2",
			[]byte(`{"id":"msg-2","session_id":"session-2","user_id":"user-2","role":"user","content":"hi","timestamp":"1710000002"}`),
		),
	)

	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("user_id", "user-2")
		c.Next()
	})
	router.GET("/history/:conversation_id", handler.GetConversationHistory)

	req := httptest.NewRequest(http.MethodGet, "/history/session-2", nil)
	resp := httptest.NewRecorder()
	router.ServeHTTP(resp, req)

	require.Equal(t, http.StatusOK, resp.Code)
	var body []map[string]interface{}
	require.NoError(t, json.Unmarshal(resp.Body.Bytes(), &body))
	require.Len(t, body, 1)
	msg := body[0]

	require.Contains(t, msg, "meta")
	require.Contains(t, msg, "widgets")
	require.Contains(t, msg, "tool_results")
	require.Contains(t, msg, "agentCollaboration")
}

func createGinContext() *gin.Context {
	recorder := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(recorder)
	ctx.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	return ctx
}
