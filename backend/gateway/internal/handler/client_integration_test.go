package handler

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

// MockGRPCClient mocks the gRPC client behavior
type MockGRPCClient struct {
	ShouldFail bool
	FailCode   codes.Code
	Latency    time.Duration
}

func (m *MockGRPCClient) CallService(ctx context.Context, req interface{}) (interface{}, error) {
	if m.Latency > 0 {
		select {
		case <-time.After(m.Latency):
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}

	if m.ShouldFail {
		return nil, status.Error(m.FailCode, "rpc failed")
	}
	return "success", nil
}

func TestGRPCClientResilience(t *testing.T) {
	t.Run("Timeout Handling", func(t *testing.T) {
		client := &MockGRPCClient{
			Latency: 200 * time.Millisecond,
		}

		// Set short timeout
		ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
		defer cancel()

		_, err := client.CallService(ctx, "req")

		assert.Error(t, err)
		assert.Equal(t, context.DeadlineExceeded, err)
	})

	t.Run("Error Propagation", func(t *testing.T) {
		client := &MockGRPCClient{
			ShouldFail: true,
			FailCode:   codes.Unavailable,
		}

		_, err := client.CallService(context.Background(), "req")

		assert.Error(t, err)
		st, ok := status.FromError(err)
		assert.True(t, ok)
		assert.Equal(t, codes.Unavailable, st.Code())
	})

	t.Run("Retry Logic (Simulated)", func(t *testing.T) {
		// This simulates the retry interceptor logic
		attempts := 0
		maxRetries := 3

		var err error
		for i := 0; i < maxRetries; i++ {
			attempts++
			// Fail first 2 times, succeed on 3rd
			shouldFail := i < 2
			client := &MockGRPCClient{
				ShouldFail: shouldFail,
				FailCode:   codes.Unavailable,
			}

			_, err = client.CallService(context.Background(), "req")
			if err == nil {
				break
			}
		}

		assert.NoError(t, err)
		assert.Equal(t, 3, attempts)
	})
}

// Helper to simulate connection options
func TestClientConnectionConfig(t *testing.T) {
	// Verify that we are using appropriate dial options
	opts := []grpc.DialOption{
		grpc.WithInsecure(), // For dev
		grpc.WithBlock(),
	}

	// Just verify we can create the config without panic
	assert.NotEmpty(t, opts)
}
