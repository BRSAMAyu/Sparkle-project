package agent

import (
	"context"
	"crypto/tls"
	"log"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
)

type Client struct {
	conn *grpc.ClientConn
	api  agentv1.AgentServiceClient
}

func NewClient(cfg *config.Config) (*Client, error) {
	// Simple retry logic or keepalive can be added here
	timeoutSeconds := cfg.GRPCTimeoutSeconds
	if timeoutSeconds <= 0 {
		timeoutSeconds = 5
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSeconds)*time.Second)
	defer cancel()

	creds := insecure.NewCredentials()
	if cfg.AgentTLSEnabled {
		if cfg.AgentTLSCACertPath != "" {
			tlsCreds, err := credentials.NewClientTLSFromFile(cfg.AgentTLSCACertPath, cfg.AgentTLSServerName)
			if err != nil {
				log.Printf("Failed to load agent TLS CA cert: %v", err)
				return nil, err
			}
			creds = tlsCreds
		} else {
			creds = credentials.NewTLS(&tls.Config{
				ServerName:         cfg.AgentTLSServerName,
				InsecureSkipVerify: cfg.AgentTLSInsecure,
			})
		}
	}

	conn, err := grpc.DialContext(ctx, cfg.AgentAddress,
		grpc.WithTransportCredentials(creds),
		grpc.WithBlock(),
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
	)
	if err != nil {
		log.Printf("Failed to connect to agent service at %s: %v", cfg.AgentAddress, err)
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
