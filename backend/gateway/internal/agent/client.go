package agent

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
)

type Client struct {
	conn *grpc.ClientConn
	api  agentv1.AgentServiceClient
}

func NewClient(addr string) (*Client, error) {
	// Simple retry logic or keepalive can be added here
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(ctx, addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		log.Printf("Failed to connect to agent service at %s: %v", addr, err)
		return nil, err
	}

	client := agentv1.NewAgentServiceClient(conn)
	return &Client{conn: conn, api: client}, nil
}

func (c *Client) Close() {
	if c.conn != nil {
		c.conn.Close()
	}
}

func (c *Client) StreamChat(ctx context.Context, req *agentv1.ChatRequest) (agentv1.AgentService_StreamChatClient, error) {
	// Inject Metadata for context propagation
	md := metadata.New(map[string]string{
		"user-id": req.UserId,
	})

	// Inject OTel Trace ID
	span := trace.SpanFromContext(ctx)
	if span.SpanContext().IsValid() {
		md.Set("x-trace-id", span.SpanContext().TraceID().String())
	} else {
		md.Set("x-trace-id", fmt.Sprintf("trace_%s", uuid.New().String()))
	}

	outCtx := metadata.NewOutgoingContext(ctx, md)

	// StreamChat is server-side streaming: single request, stream of responses
	return c.api.StreamChat(outCtx, req)
}