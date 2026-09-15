package galaxy

import (
	"context"
	"crypto/tls"
	"log"
	"sync"
	"time"

	galaxyv1 "github.com/sparkle/gateway/gen/galaxy/v1"
	"github.com/sparkle/gateway/internal/config"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
)

type Client struct {
	conn   *grpc.ClientConn
	api    galaxyv1.GalaxyServiceClient
	config *config.Config
	connMu sync.RWMutex

	reconnectMu     sync.Mutex
	lastReconnectAt time.Time
	minReconnectGap time.Duration
	dialOptions     []grpc.DialOption
}

func NewClient(cfg *config.Config) (*Client, error) {
	timeoutSeconds := cfg.GRPCTimeoutSeconds
	if timeoutSeconds <= 0 {
		timeoutSeconds = 5
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSeconds)*time.Second)
	defer cancel()

	dialOptions, err := buildDialOptions(cfg)
	if err != nil {
		return nil, err
	}

	conn, err := grpc.DialContext(ctx, cfg.AgentAddress, dialOptions...)
	if err != nil {
		log.Printf("Failed to connect to galaxy service at %s: %v", cfg.AgentAddress, err)
		return nil, err
	}

	client := galaxyv1.NewGalaxyServiceClient(conn)
	return &Client{
		conn:           conn,
		api:            client,
		config:         cfg,
		dialOptions:    dialOptions,
		minReconnectGap: 2 * time.Second,
	}, nil
}

func buildDialOptions(cfg *config.Config) ([]grpc.DialOption, error) {
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

	// Retry policy matching agent/client.go pattern
	retryPolicy := `{
		"methodConfig": [{
			"name": [{"service": "galaxy.v1.GalaxyService"}],
			"waitForReady": true,
			"retryPolicy": {
				"MaxAttempts": 4,
				"InitialBackoff": "0.5s",
				"MaxBackoff": "10s",
				"BackoffMultiplier": 2.0,
				"RetryableStatusCodes": ["UNAVAILABLE", "RESOURCE_EXHAUSTED"]
			}
		}]
	}`

	return []grpc.DialOption{
		grpc.WithTransportCredentials(creds),
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
		grpc.WithDefaultServiceConfig(retryPolicy),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                20 * time.Second,
			Timeout:             10 * time.Second,
			PermitWithoutStream: true,
		}),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(50*1024*1024),
			grpc.MaxCallSendMsgSize(50*1024*1024),
		),
	}, nil
}

func (c *Client) currentConn() *grpc.ClientConn {
	c.connMu.RLock()
	defer c.connMu.RUnlock()
	return c.conn
}

func (c *Client) currentAPI() galaxyv1.GalaxyServiceClient {
	c.connMu.RLock()
	defer c.connMu.RUnlock()
	return c.api
}

func (c *Client) reconnect(ctx context.Context) error {
	if c == nil || c.config == nil {
		return nil
	}

	minGap := c.minReconnectGap
	if minGap == 0 {
		minGap = 2 * time.Second
	}
	var sleepDur time.Duration
	c.reconnectMu.Lock()
	if elapsed := time.Since(c.lastReconnectAt); elapsed < minGap {
		sleepDur = minGap - elapsed
	}
	c.lastReconnectAt = time.Now()
	c.reconnectMu.Unlock()

	if sleepDur > 0 {
		time.Sleep(sleepDur)
	}

	if conn := c.currentConn(); conn != nil {
		state := conn.GetState()
		if state == connectivity.Ready || state == connectivity.Idle {
			return nil
		}
	}

	// Create new connection
	conn, err := grpc.DialContext(ctx, c.config.AgentAddress, c.dialOptions...)
	if err != nil {
		log.Printf("Failed to reconnect to galaxy service: %v", err)
		return err
	}

	c.connMu.Lock()
	c.conn = conn
	c.api = galaxyv1.NewGalaxyServiceClient(conn)
	c.connMu.Unlock()

	return nil
}

func (c *Client) Close() {
	c.connMu.RLock()
	conn := c.conn
	c.connMu.RUnlock()
	if conn != nil {
		conn.Close()
	}
}

func (c *Client) UpdateNodeMastery(ctx context.Context, userID, nodeID string, mastery int32, version time.Time, reason string) (*galaxyv1.UpdateNodeMasteryResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.UpdateNodeMasteryRequest{
		UserId:   userID,
		NodeId:   nodeID,
		Mastery:  mastery,
		Revision: version.UnixMilli(),
		Reason:  reason,
	}
	return api.UpdateNodeMastery(ctx, req)
}

func (c *Client) GetUserGalaxy(ctx context.Context, userID string) (*galaxyv1.GetUserGalaxyResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.GetUserGalaxyRequest{UserId: userID}
	return api.GetUserGalaxy(ctx, req)
}

func (c *Client) RecordNodeInteraction(ctx context.Context, userID, nodeID, interactionType string, metadata map[string]string) (*galaxyv1.RecordNodeInteractionResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.RecordNodeInteractionRequest{
		UserId:          userID,
		NodeId:          nodeID,
		InteractionType: interactionType,
		Metadata:        metadata,
	}
	return api.RecordNodeInteraction(ctx, req)
}

func (c *Client) GetNodeDetail(ctx context.Context, userID, nodeID string) (*galaxyv1.GetNodeDetailResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.GetNodeDetailRequest{UserId: userID, NodeId: nodeID}
	return api.GetNodeDetail(ctx, req)
}

func (c *Client) SearchNodes(ctx context.Context, userID, query string, limit int32) (*galaxyv1.SearchNodesResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.SearchNodesRequest{UserId: userID, Query: query, Limit: limit}
	return api.SearchNodes(ctx, req)
}

func (c *Client) GetLearningPath(ctx context.Context, userID, fromNodeID, toNodeID string) (*galaxyv1.GetLearningPathResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.GetLearningPathRequest{UserId: userID, FromNodeId: fromNodeID, ToNodeId: toNodeID}
	return api.GetLearningPath(ctx, req)
}

func (c *Client) GetNodeDependencies(ctx context.Context, userID, nodeID string) (*galaxyv1.GetNodeDependenciesResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.GetNodeDependenciesRequest{UserId: userID, NodeId: nodeID}
	return api.GetNodeDependencies(ctx, req)
}

func (c *Client) GetGalaxyStats(ctx context.Context, userID string) (*galaxyv1.GetGalaxyStatsResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.GetGalaxyStatsRequest{UserId: userID}
	return api.GetGalaxyStats(ctx, req)
}

func (c *Client) GetRecommendedNodes(ctx context.Context, userID string, limit int32) (*galaxyv1.GetRecommendedNodesResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.GetRecommendedNodesRequest{UserId: userID, Limit: limit}
	return api.GetRecommendedNodes(ctx, req)
}

func (c *Client) SyncCollaborativeGalaxy(ctx context.Context, galaxyID string, partialUpdate []byte, userID string) (*galaxyv1.SyncCollaborativeGalaxyResponse, error) {
	api := c.currentAPI()
	if api == nil {
		if err := c.reconnect(ctx); err != nil {
			return nil, err
		}
		api = c.currentAPI()
	}

	req := &galaxyv1.SyncCollaborativeGalaxyRequest{
		GalaxyId:      galaxyID,
		PartialUpdate: partialUpdate,
		UserId:        userID,
	}
	return api.SyncCollaborativeGalaxy(ctx, req)
}