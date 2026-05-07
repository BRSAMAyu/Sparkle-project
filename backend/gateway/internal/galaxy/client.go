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
		UserId:   userID,
		NodeId:   nodeID,
		Mastery:  mastery,
		Revision: version.UnixMilli(),
		Reason:   reason,
	}

	return c.api.UpdateNodeMastery(ctx, req)
}

func (c *Client) GetUserGalaxy(ctx context.Context, userID string) (*galaxyv1.GetUserGalaxyResponse, error) {
	req := &galaxyv1.GetUserGalaxyRequest{UserId: userID}
	return c.api.GetUserGalaxy(ctx, req)
}

func (c *Client) RecordNodeInteraction(ctx context.Context, userID, nodeID, interactionType string, metadata map[string]string) (*galaxyv1.RecordNodeInteractionResponse, error) {
	req := &galaxyv1.RecordNodeInteractionRequest{
		UserId:          userID,
		NodeId:          nodeID,
		InteractionType: interactionType,
		Metadata:        metadata,
	}
	return c.api.RecordNodeInteraction(ctx, req)
}

func (c *Client) GetNodeDetail(ctx context.Context, userID, nodeID string) (*galaxyv1.GetNodeDetailResponse, error) {
	req := &galaxyv1.GetNodeDetailRequest{UserId: userID, NodeId: nodeID}
	return c.api.GetNodeDetail(ctx, req)
}

func (c *Client) SearchNodes(ctx context.Context, userID, query string, limit int32) (*galaxyv1.SearchNodesResponse, error) {
	req := &galaxyv1.SearchNodesRequest{UserId: userID, Query: query, Limit: limit}
	return c.api.SearchNodes(ctx, req)
}

func (c *Client) GetLearningPath(ctx context.Context, userID, fromNodeID, toNodeID string) (*galaxyv1.GetLearningPathResponse, error) {
	req := &galaxyv1.GetLearningPathRequest{UserId: userID, FromNodeId: fromNodeID, ToNodeId: toNodeID}
	return c.api.GetLearningPath(ctx, req)
}

func (c *Client) GetNodeDependencies(ctx context.Context, userID, nodeID string) (*galaxyv1.GetNodeDependenciesResponse, error) {
	req := &galaxyv1.GetNodeDependenciesRequest{UserId: userID, NodeId: nodeID}
	return c.api.GetNodeDependencies(ctx, req)
}

func (c *Client) GetGalaxyStats(ctx context.Context, userID string) (*galaxyv1.GetGalaxyStatsResponse, error) {
	req := &galaxyv1.GetGalaxyStatsRequest{UserId: userID}
	return c.api.GetGalaxyStats(ctx, req)
}

func (c *Client) GetRecommendedNodes(ctx context.Context, userID string, limit int32) (*galaxyv1.GetRecommendedNodesResponse, error) {
	req := &galaxyv1.GetRecommendedNodesRequest{UserId: userID, Limit: limit}
	return c.api.GetRecommendedNodes(ctx, req)
}

func (c *Client) SyncCollaborativeGalaxy(ctx context.Context, galaxyID string, partialUpdate []byte, userID string) (*galaxyv1.SyncCollaborativeGalaxyResponse, error) {
	req := &galaxyv1.SyncCollaborativeGalaxyRequest{
		GalaxyId:       galaxyID,
		PartialUpdate:  partialUpdate,
		UserId:         userID,
	}
	return c.api.SyncCollaborativeGalaxy(ctx, req)
}
