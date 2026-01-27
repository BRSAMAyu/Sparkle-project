//go:build integration
// +build integration

package handler

/*
E2E Test: Go Gateway Complete Flow
===================================

Tests Go Gateway → Python gRPC → WebSocket → Flutter Client flow
*/
import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"google.golang.org/grpc"

	"github.com/user/sparkle/gateway/internal/agent"
)

// MockAgentClient mocks the Python gRPC client
type MockAgentClient struct {
	mock.Mock
}

func (m *MockAgentClient) StreamChat(ctx context.Context, req *agent.ChatRequest, opts ...grpc.CallOption) (agent.AgentService_StreamChatClient, error) {
	args := m.Called(ctx, req)
	return args.Get(0).(agent.AgentService_StreamChatClient), args.Error(1)
}

// MockStreamClient mocks the streaming response
type MockStreamClient struct {
	mock.Mock
	messages []*agent.ChatResponse
	current  int
}

func (m *MockStreamClient) Recv() (*agent.ChatResponse, error) {
	if m.current >= len(m.messages) {
		return nil, nil // EOF
	}

	msg := m.messages[m.current]
	m.current++
	return msg, nil
}

func (m *MockStreamClient) CloseSend() error {
	args := m.Called()
	return args.Error(0)
}

func (m *MockStreamClient) Header() (metadata.MD, error) {
	args := m.Called()
	return args.Get(0).(metadata.MD), args.Error(1)
}

func (m *MockStreamClient) Trailer() metadata.MD {
	args := m.Called()
	return args.Get(0).(metadata.MD)
}

func (m *MockStreamClient) Context() context.Context {
	args := m.Called()
	return args.Get(0).(context.Context)
}

func (m *MockStreamClient) SendMsg(msg interface{}) error {
	args := m.Called(msg)
	return args.Error(0)
}

func (m *MockStreamClient) RecvMsg(msg interface{}) error {
	args := m.Called(msg)
	return args.Error(0)
}

// =============================================================================
// Test 1: Complete Chat Flow (WebSocket → Gateway → gRPC)
// =============================================================================

func TestE2E_CompleteChatFlow(t *testing.T) {
	// Setup
	gin.SetMode(gin.TestMode)
	router := gin.New()

	// Mock auth middleware
	router.Use(func(c *gin.Context) {
		token := c.Query("token")
		if token == "valid-token" {
			c.Set("userID", "user-123")
			c.Set("sessionID", "session-456")
		}
		c.Next()
	})

	// Create mock agent client
	mockAgent := new(MockAgentClient)

	// Setup chat orchestrator with mock
	orchestrator := NewChatOrchestratorWithClient(mockAgent)
	router.GET("/ws/chat", func(c *gin.Context) {
		orchestrator.HandleWebSocket(c)
	})

	// Create test server
	ts := httptest.NewServer(router)
	defer ts.Close()

	// Convert to WebSocket URL
	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat?token=valid-token"

	t.Run("WebSocket connection established", func(t *testing.T) {
		// Connect
		conn, resp, err := websocket.DefaultDialer.Dial(wsURL, nil)
		assert.NoError(t, err)
		assert.Equal(t, 101, resp.StatusCode)
		defer conn.Close()

		// Send chat message
		chatMsg := map[string]interface{}{
			"type":    "message",
			"content": "Hello, I want to learn Python",
			"userId":  "user-123",
			"session": "session-456",
		}

		err = conn.WriteJSON(chatMsg)
		assert.NoError(t, err)

		// Receive response (streaming chunks)
		messageCount := 0
		timeout := time.After(5 * time.Second)

		for {
			select {
			case <-timeout:
				t.Fatal("Timeout waiting for response")
			default:
				var msg map[string]interface{}
				err := conn.ReadJSON(&msg)
				if err != nil {
					if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
						assert.NoError(t, err)
					}
					return // Connection closed normally
				}

				// Verify message structure
				assert.Contains(t, msg, "type")
				assert.Contains(t, msg, "delta")

				if msg["type"] == "delta" {
					messageCount++
				}

				// After receiving some chunks, we're done
				if messageCount >= 3 {
					return
				}
			}
		}

		assert.Greater(t, messageCount, 0, "Should receive at least one message chunk")
	})

	t.Run("Authentication failed without token", func(t *testing.T) {
		// Try to connect without token
		wsURLNoAuth := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

		_, _, err := websocket.DefaultDialer.Dial(wsURLNoAuth, nil)
		assert.Error(t, err, "Should fail without auth token")
	})
}

// =============================================================================
// Test 2: Plan Creation Flow
// =============================================================================

func TestE2E_PlanCreationFlow(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()

	// Mock auth
	router.Use(func(c *gin.Context) {
		c.Set("userID", "user-123")
		c.Next()
	})

	// Mock agent client
	mockAgent := new(MockAgentClient)

	// Mock streaming response with plan creation
	mockStream := &MockStreamClient{
		messages: []*agent.ChatResponse{
			{
				Type: agent.ChatResponse_DELTA,
				Content: &agent.ChatContent{
					Delta: "好的,我来为您制定一个学习计划",
				},
			},
			{
				Type: agent.ChatResponse_METADATA,
				Metadata: &agent.ResponseMetadata{
					"plan_created": "true",
					"plan_id":      "plan-789",
					"task_count":   "5",
				},
			},
		},
	}

	mockAgent.On("StreamChat", mock.Anything, mock.Anything).Return(mockStream, nil)

	orchestrator := NewChatOrchestratorWithClient(mockAgent)
	router.POST("/api/v1/chat", func(c *gin.Context) {
		orchestrator.HandleHTTP(c)
	})

	// Create plan request
	planReq := map[string]interface{}{
		"type":    "plan_creation",
		"subject": "Python",
		"days":    7,
		"goals":   []string{"Learn basics", "Write programs"},
	}

	reqBody, _ := json.Marshal(planReq)
	req := httptest.NewRequest("POST", "/api/v1/chat", strings.NewReader(string(reqBody)))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Assert response
	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)

	assert.Contains(t, response, "status")
	assert.Equal(t, "success", response["status"])

	mockAgent.AssertExpectations(t)
}

// =============================================================================
// Test 3: Concurrent WebSocket Connections
// =============================================================================

func TestE2E_ConcurrentWebSocketConnections(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()

	// Mock auth
	router.Use(func(c *gin.Context) {
		c.Set("userID", c.Query("userId"))
		c.Set("sessionID", c.Query("sessionId"))
		c.Next()
	})

	mockAgent := new(MockAgentClient)
	orchestrator := NewChatOrchestratorWithClient(mockAgent)
	router.GET("/ws/chat", func(c *gin.Context) {
		orchestrator.HandleWebSocket(c)
	})

	ts := httptest.NewServer(router)
	defer ts.Close()

	// Create 10 concurrent connections
	numConnections := 10
	connections := make([]*websocket.Conn, numConnections)
	errors := make(chan error, numConnections)

	for i := 0; i < numConnections; i++ {
		go func(index int) {
			wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat?userId=user-" + string(rune('0'+index)) + "&sessionId=session-" + string(rune('0'+index))
			conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
			if err != nil {
				errors <- err
				return
			}
			connections[index] = conn
			errors <- nil
		}(i)
	}

	// Wait for all connections
	for i := 0; i < numConnections; i++ {
		err := <-errors
		assert.NoError(t, err, "Connection %d should succeed", i)
	}

	// Cleanup
	for _, conn := range connections {
		if conn != nil {
			conn.Close()
		}
	}
}

// =============================================================================
// Test 4: WebSocket Reconnection
// =============================================================================

func TestE2E_WebSocketReconnection(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()

	router.Use(func(c *gin.Context) {
		c.Set("userID", "user-123")
		c.Set("sessionID", "session-456")
		c.Next()
	})

	mockAgent := new(MockAgentClient)
	orchestrator := NewChatOrchestratorWithClient(mockAgent)
	router.GET("/ws/chat", func(c *gin.Context) {
		orchestrator.HandleWebSocket(c)
	})

	ts := httptest.NewServer(router)
	defer ts.Close()

	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

	// First connection
	conn1, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	assert.NoError(t, err)
	conn1.Close()

	// Wait a bit
	time.Sleep(100 * time.Millisecond)

	// Reconnect
	conn2, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	assert.NoError(t, err)
	defer conn2.Close()

	// Send message on reconnected socket
	chatMsg := map[string]interface{}{
		"type":    "message",
		"content": "Reconnected test",
	}

	err = conn2.WriteJSON(chatMsg)
	assert.NoError(t, err)
}

// =============================================================================
// Test 5: Large Message Handling
// =============================================================================

func TestE2E_LargeMessageHandling(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()

	router.Use(func(c *gin.Context) {
		c.Set("userID", "user-123")
		c.Next()
	})

	mockAgent := new(MockAgentClient)
	orchestrator := NewChatOrchestratorWithClient(mockAgent)
	router.GET("/ws/chat", func(c *gin.Context) {
		orchestrator.HandleWebSocket(c)
	})

	ts := httptest.NewServer(router)
	defer ts.Close()

	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	assert.NoError(t, err)
	defer conn.Close()

	// Send large message (10KB)
	largeContent := strings.Repeat("Hello ", 2500) // ~10KB

	chatMsg := map[string]interface{}{
		"type":    "message",
		"content": largeContent,
	}

	err = conn.WriteJSON(chatMsg)
	assert.NoError(t, err, "Should handle large messages")

	// Verify connection still alive
	err = conn.WriteMessage(websocket.PingMessage, nil)
	assert.NoError(t, err, "Connection should still be alive after large message")
}
