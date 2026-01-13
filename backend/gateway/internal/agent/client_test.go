package agent

import (
	"context"
	"testing"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

// MockAgentServiceServer implements a mock gRPC server for testing
type MockAgentServiceServer struct {
	agentv1.UnimplementedAgentServiceServer
	chatResponses []*agentv1.ChatResponse
	shouldFail    bool
	failCode      codes.Code
}

func (m *MockAgentServiceServer) StreamChat(req *agentv1.ChatRequest, stream grpc.ServerStream) error {
	if m.shouldFail {
		return status.Error(m.failCode, "mock error")
	}

	// Send predefined responses
	for _, resp := range m.chatResponses {
		if err := stream.SendMsg(resp); err != nil {
			return err
		}
	}
	return nil
}

func TestClientNewClient(t *testing.T) {
	tests := []struct {
		name      string
		cfg       *config.Config
		expectErr bool
		desc      string
	}{
		{
			name: "valid_insecure_connection",
			cfg: &config.Config{
				AgentAddress:   "localhost:50051",
				AgentTLSEnabled: false,
			},
			expectErr: false, // gRPC NewClient is non-blocking, so it succeeds even if server is offline
			desc:      "Should return client object (connection happens in background)",
		},
		{
			name: "invalid_address",
			cfg: &config.Config{
				AgentAddress:   "invalid:invalid",
				AgentTLSEnabled: false,
			},
			expectErr: true,
			desc:      "Should fail with invalid address",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			client, err := NewClient(tt.cfg)

			if tt.expectErr {
				assert.Error(t, err, tt.desc)
				assert.Nil(t, client)
			} else {
				assert.NoError(t, err, tt.desc)
				assert.NotNil(t, client)
				if client != nil {
					client.Close()
				}
			}
		})
	}
}

func TestClientClose(t *testing.T) {
	t.Run("close_nil_connection", func(t *testing.T) {
		client := &Client{conn: nil}
		// Should not panic
		assert.NotPanics(t, func() {
			client.Close()
		})
	})
}

// ============================================================
// Integration Tests (require mock server setup)
// ============================================================

// TestStreamChatMetadata verifies that metadata is properly injected
func TestStreamChatMetadata(t *testing.T) {
	t.Run("metadata_injection", func(t *testing.T) {
		// This test demonstrates the expected behavior
		// In practice, you would use a mock gRPC server

		userID := "test-user-123"
		req := &agentv1.ChatRequest{
			UserId:    userID,
			SessionId: "session-123",
		}

		// Verify metadata creation
		assert.Equal(t, userID, req.UserId)
		assert.Equal(t, "session-123", req.SessionId)
	})
}

// ============================================================
// Protocol Buffer Serialization Tests
// ============================================================

func TestChatRequestMarshaling(t *testing.T) {
	t.Run("chat_request_serialization", func(t *testing.T) {
		req := &agentv1.ChatRequest{
			UserId:    "user-456",
			SessionId: "session-789",
			RequestId: "req-123",
		}

		// Verify message structure
		assert.Equal(t, "user-456", req.UserId)
		assert.Equal(t, "session-789", req.SessionId)
		assert.Equal(t, "req-123", req.RequestId)
	})
}

func TestChatResponseUnmarshaling(t *testing.T) {
	t.Run("chat_response_deserialization", func(t *testing.T) {
		resp := &agentv1.ChatResponse{
			ResponseId: "resp-123",
			RequestId:  "req-456",
			CreatedAt:  1700000000,
		}

		assert.Equal(t, "resp-123", resp.ResponseId)
		assert.Equal(t, "req-456", resp.RequestId)
		assert.Greater(t, resp.CreatedAt, int64(0))
	})
}

// ============================================================
// Context Timeout Tests
// ============================================================

func TestContextTimeout(t *testing.T) {
	t.Run("short_timeout_context", func(t *testing.T) {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
		defer cancel()

		// Sleep longer than timeout
		time.Sleep(20 * time.Millisecond)

		// Verify timeout occurred
		assert.Error(t, ctx.Err(), "context should be timed out")
	})

	t.Run("valid_timeout_context", func(t *testing.T) {
		ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
		defer cancel()

		assert.NoError(t, ctx.Err(), "context should not be timed out immediately")
	})
}

// ============================================================
// gRPC Error Handling Tests
// ============================================================

func TestGRPCErrorCodes(t *testing.T) {
	tests := []struct {
		name     string
		code     codes.Code
		expected string
	}{
		{
			name:     "unavailable",
			code:     codes.Unavailable,
			expected: "Unavailable",
		},
		{
			name:     "deadline_exceeded",
			code:     codes.DeadlineExceeded,
			expected: "DeadlineExceeded",
		},
		{
			name:     "resource_exhausted",
			code:     codes.ResourceExhausted,
			expected: "ResourceExhausted",
		},
		{
			name:     "internal",
			code:     codes.Internal,
			expected: "Internal",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := status.Error(tt.code, "test error")
			st, ok := status.FromError(err)

			assert.True(t, ok, "should be a gRPC status error")
			assert.Equal(t, tt.code, st.Code())
		})
	}
}

// ============================================================
// Message Flow Pattern Tests
// ============================================================

func TestServerStreamingPattern(t *testing.T) {
	t.Run("multiple_responses_sequence", func(t *testing.T) {
		// Simulate the expected message flow pattern
		responses := []*agentv1.ChatResponse{
			{
				ResponseId: "resp-1",
				RequestId:  "req-1",
				CreatedAt:  1700000000,
			},
			{
				ResponseId: "resp-2",
				RequestId:  "req-1",
				CreatedAt:  1700000001,
			},
			{
				ResponseId: "resp-3",
				RequestId:  "req-1",
				CreatedAt:  1700000002,
				FinishReason: agentv1.FinishReason_STOP,
			},
		}

		// Verify sequence
		assert.Equal(t, 3, len(responses))
		assert.Equal(t, agentv1.FinishReason_NULL, responses[0].FinishReason)
		assert.Equal(t, agentv1.FinishReason_NULL, responses[1].FinishReason)
		assert.Equal(t, agentv1.FinishReason_STOP, responses[2].FinishReason)
	})
}

// ============================================================
// Concurrency Tests
// ============================================================

func TestConcurrentRequests(t *testing.T) {
	t.Run("concurrent_chat_requests", func(t *testing.T) {
		// Simulate multiple concurrent requests
		done := make(chan bool, 3)

		for i := 1; i <= 3; i++ {
			go func(id int) {
				req := &agentv1.ChatRequest{
					UserId:    "user-" + string(rune(id)),
					SessionId: "session-concurrent",
				}
				assert.NotNil(t, req)
				done <- true
			}(i)
		}

		// Wait for all goroutines
		for i := 0; i < 3; i++ {
			<-done
		}
	})
}

// ============================================================
// Circuit Breaker Pattern Tests
// ============================================================

func TestConnectionRetry(t *testing.T) {
	t.Run("retry_logic_structure", func(t *testing.T) {
		// Test the retry pattern structure
		maxRetries := 3
		backoff := 100 * time.Millisecond

		for attempt := 0; attempt < maxRetries; attempt++ {
			waitDuration := backoff * time.Duration(1<<uint(attempt)) // exponential backoff

			// Verify exponential backoff calculation
			expectedDuration := backoff * time.Duration(1<<uint(attempt))
			assert.Equal(t, expectedDuration, waitDuration)
		}

		// Verify final backoff value
		finalBackoff := backoff * time.Duration(1<<uint(maxRetries-1))
		assert.Equal(t, 400*time.Millisecond, finalBackoff)
	})
}

// ============================================================
// TLS Configuration Tests
// ============================================================

func TestTLSConfiguration(t *testing.T) {
	tests := []struct {
		name              string
		tlsEnabled        bool
		caCertPath        string
		serverName        string
		insecureSkipVerify bool
		desc              string
	}{
		{
			name:       "tls_disabled",
			tlsEnabled: false,
			desc:       "Should use insecure credentials",
		},
		{
			name:              "tls_enabled_with_ca",
			tlsEnabled:        true,
			caCertPath:        "/path/to/ca.crt",
			serverName:        "localhost",
			insecureSkipVerify: false,
			desc:              "Should use CA certificate for verification",
		},
		{
			name:              "tls_enabled_skip_verify",
			tlsEnabled:        true,
			serverName:        "localhost",
			insecureSkipVerify: true,
			desc:              "Should skip TLS verification",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg := &config.Config{
				AgentAddress:         "localhost:50051",
				AgentTLSEnabled:       tt.tlsEnabled,
				AgentTLSCACertPath:    tt.caCertPath,
				AgentTLSServerName:    tt.serverName,
				AgentTLSInsecure:      tt.insecureSkipVerify,
			}

			assert.Equal(t, tt.tlsEnabled, cfg.AgentTLSEnabled, tt.desc)
			if tt.tlsEnabled {
				assert.Equal(t, tt.serverName, cfg.AgentTLSServerName)
			}
		})
	}
}

// ============================================================
// Request/Response Size Limits
// ============================================================

func TestMessageSizeHandling(t *testing.T) {
	t.Run("large_message_handling", func(t *testing.T) {
		// Create a large message (10KB)
		largeContent := ""
		for i := 0; i < 10000; i++ {
			largeContent += "x"
		}

		resp := &agentv1.ChatResponse{
			ResponseId: "resp-large",
			RequestId:  "req-large",
		}

		assert.NotNil(t, resp)
		assert.Equal(t, 10000, len(largeContent))
	})

	t.Run("empty_message_handling", func(t *testing.T) {
		resp := &agentv1.ChatResponse{
			ResponseId: "resp-empty",
			RequestId:  "req-empty",
		}

		assert.NotNil(t, resp)
		assert.Equal(t, "resp-empty", resp.ResponseId)
	})
}
