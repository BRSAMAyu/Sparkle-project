package agent

import (
	"context"
	"testing"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

// ============================================================
// gRPC Client Benchmark Tests
// ============================================================

func BenchmarkMetadataInjection(b *testing.B) {
	b.Run("basic_metadata", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			ctx := context.Background()
			md := metadata.New(map[string]string{
				"user-id":            "user-123",
				"x-internal-api-key": "test-key",
			})
			_ = metadata.NewOutgoingContext(ctx, md)
		}
	})

	b.Run("metadata_with_trace_id", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			ctx := context.Background()
			traceID := "trace-123-456-789"
			ctx = WithTraceID(ctx, traceID)

			md := metadata.New(map[string]string{
				"user-id":            "user-123",
				"x-internal-api-key": "test-key",
				"x-trace-id":         traceID,
			})
			_ = metadata.NewOutgoingContext(ctx, md)
		}
	})
}

func BenchmarkChatRequestAllocation(b *testing.B) {
	testCases := []struct {
		name       string
		messageLen int
	}{
		{"small_message", 100},
		{"medium_message", 1000},
		{"large_message", 10000},
	}

	for _, tc := range testCases {
		b.Run(tc.name, func(b *testing.B) {
			b.ReportAllocs()

			content := make([]byte, tc.messageLen)
			for i := range content {
				content[i] = 'x'
			}

			for i := 0; i < b.N; i++ {
				req := &agentv1.ChatRequest{
					UserId:    "user-123",
					SessionId: "session-456",
					RequestId: "req-789",
					Input: &agentv1.ChatRequest_Message{
						Message: string(content),
					},
				}
				_ = req
			}
		})
	}
}

func BenchmarkContextCreation(b *testing.B) {
	b.Run("background_context", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			_ = context.Background()
		}
	})

	b.Run("timeout_context", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
			cancel()
			_ = ctx
		}
	})

	b.Run("context_with_trace_id", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			ctx := context.Background()
			_ = WithTraceID(ctx, "trace-123-456-789")
		}
	})
}

func BenchmarkTraceIDOperations(b *testing.B) {
	b.Run("with_trace_id", func(b *testing.B) {
		b.ReportAllocs()
		ctx := context.Background()

		for i := 0; i < b.N; i++ {
			ctx = WithTraceID(ctx, "trace-123-456-789")
		}
	})

	b.Run("trace_id_from_context", func(b *testing.B) {
		b.ReportAllocs()
		ctx := WithTraceID(context.Background(), "trace-123-456-789")

		for i := 0; i < b.N; i++ {
			_ = traceIDFromContext(ctx)
		}
	})

	b.Run("round_trip", func(b *testing.B) {
		b.ReportAllocs()
		traceID := "trace-123-456-789"

		for i := 0; i < b.N; i++ {
			ctx := WithTraceID(context.Background(), traceID)
			_ = traceIDFromContext(ctx)
		}
	})
}

func BenchmarkGRPCErrorCreation(b *testing.B) {
	b.Run("status_error", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			_ = status.Error(codes.Unavailable, "service unavailable")
		}
	})

	b.Run("status_error_with_details", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			st := status.New(codes.Internal, "internal error")
			_ = st.Err()
		}
	})
}

func BenchmarkMessageSerialization(b *testing.B) {
	testCases := []struct {
		name       string
		messageLen int
	}{
		{"minimal", 10},
		{"standard", 500},
		{"complex", 2000},
	}

	for _, tc := range testCases {
		b.Run(tc.name, func(b *testing.B) {
			b.ReportAllocs()

			content := make([]byte, tc.messageLen)
			for i := range content {
				content[i] = 'x'
			}

			for i := 0; i < b.N; i++ {
				req := &agentv1.ChatRequest{
					UserId:    "user-123",
					SessionId: "session-456",
					RequestId: "req-789",
					Input: &agentv1.ChatRequest_Message{
						Message: string(content),
					},
					Config: &agentv1.ChatConfig{
						Temperature: 0.7,
						MaxTokens:   2000,
					},
				}
				_ = req
			}
		})
	}
}

// ============================================================
// Throughput Benchmarks
// ============================================================

func BenchmarkThroughput_SmallMessages(b *testing.B) {
	b.ReportAllocs()

	for i := 0; i < b.N; i++ {
		req := &agentv1.ChatRequest{
			UserId:    "user-123",
			SessionId: "session-456",
			Input: &agentv1.ChatRequest_Message{
				Message: "Hello, world!",
			},
		}
		_ = req
	}
}

func BenchmarkThroughput_MediumMessages(b *testing.B) {
	b.ReportAllocs()
	content := make([]byte, 500)
	for i := range content {
		content[i] = 'x'
	}

	for i := 0; i < b.N; i++ {
		req := &agentv1.ChatRequest{
			UserId:    "user-123",
			SessionId: "session-456",
			Input: &agentv1.ChatRequest_Message{
				Message: string(content),
			},
		}
		_ = req
	}
}

func BenchmarkThroughput_LargeMessages(b *testing.B) {
	b.ReportAllocs()
	content := make([]byte, 5000)
	for i := range content {
		content[i] = 'x'
	}

	for i := 0; i < b.N; i++ {
		req := &agentv1.ChatRequest{
			UserId:    "user-123",
			SessionId: "session-456",
			Input: &agentv1.ChatRequest_Message{
				Message: string(content),
			},
		}
		_ = req
	}
}

// ============================================================
// Memory Allocation Benchmarks
// ============================================================

func BenchmarkMemoryAllocation_ChatResponse(b *testing.B) {
	b.Run("small_response", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			resp := &agentv1.ChatResponse{
				ResponseId: "resp-123",
				RequestId:  "req-456",
				Content: &agentv1.ChatResponse_Delta{
					Delta: "Hello!",
				},
				FinishReason: agentv1.FinishReason_STOP,
			}
			_ = resp
		}
	})

	b.Run("large_response", func(b *testing.B) {
		b.ReportAllocs()
		content := make([]byte, 10000)
		for i := range content {
			content[i] = 'y'
		}

		for i := 0; i < b.N; i++ {
			resp := &agentv1.ChatResponse{
				ResponseId: "resp-123",
				RequestId:  "req-456",
				Content: &agentv1.ChatResponse_Delta{
					Delta: string(content),
				},
				FinishReason: agentv1.FinishReason_STOP,
			}
			_ = resp
		}
	})
}
