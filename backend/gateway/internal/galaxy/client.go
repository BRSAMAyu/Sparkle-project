package galaxy

import (
	"context"
	"crypto/tls"
	"log"
	"time"

	galaxyv1 "github.com/sparkle/gateway/gen/galaxy/v1"
	"github.com/sparkle/gateway/internal/config"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/types/known/timestamppb"
)

type Client struct {
	conn *grpc.ClientConn
	api  galaxyv1.GalaxyServiceClient
}

func NewClient(cfg *config.Config) (*Client, error) {
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
				return nil, err
			}
			creds = tlsCreds
		} else {
			creds = credentials.NewTLS(&tls.Config{
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
		log.Printf("Failed to connect to galaxy service at %s: %v", cfg.AgentAddress, err)
		return nil, err
	}

	client := galaxyv1.NewGalaxyServiceClient(conn)
	return &Client{conn: conn, api: client}, nil
}

func (c *Client) Close() {
	if c.conn != nil {
		c.conn.Close()
	}
}

func (c *Client) UpdateNodeMastery(ctx context.Context, userID, nodeID string, mastery int32, version time.Time, reason string) (*galaxyv1.UpdateNodeMasteryResponse, error) {
	req := &galaxyv1.UpdateNodeMasteryRequest{
		UserId:  userID,
		NodeId:  nodeID,
		Mastery: mastery,
		Version: timestamppb.New(version),
		Reason:  reason,
	}
	
	return c.api.UpdateNodeMastery(ctx, req)
}
