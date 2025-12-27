package agent

import (
	"context"
	"log"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
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
		grpc.WithUnaryInterceptor(otelgrpc.UnaryClientInterceptor()),
		grpc.WithStreamInterceptor(otelgrpc.StreamClientInterceptor()),
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
	// Inject Metadata for business context
	md := metadata.New(map[string]string{
		"user-id": req.UserId,
	})

	outCtx := metadata.NewOutgoingContext(ctx, md)

	// StreamChat is server-side streaming: single request, stream of responses
	// otelgrpc interceptor will handle the TraceContext propagation automatically
	return c.api.StreamChat(outCtx, req)
}