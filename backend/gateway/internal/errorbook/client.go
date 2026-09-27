// Core: bridge
// Phase: reflect
// Stage: v1 网关基座
//
// 错题本引擎桥接客户端.

package errorbook

import (
	"context"
	"crypto/tls"
	"fmt"
	"log"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"

	errorbookv1 "github.com/sparkle/gateway/gen/proto/error_book"
	"github.com/sparkle/gateway/internal/config"
)

type Client struct {
	conn *grpc.ClientConn
	api  errorbookv1.ErrorBookServiceClient
}

func NewClient(cfg *config.Config) (*Client, error) {
	// Reuse agent address for now as they are hosted in the same Python process
	addr := cfg.AgentAddress

	timeoutSeconds := cfg.GRPCTimeoutSeconds
	if timeoutSeconds <= 0 {
		timeoutSeconds = 5
	}

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
			// InsecureSkipVerify is the AGENT_TLS_INSECURE operator switch,
			// a deliberate development escape hatch for environments without
			// a CA chain: config validation refuses to start with it set
			// outside development, and the AGENT_TLS_CA_CERT branch above
			// (NewClientTLSFromFile) takes precedence with verification on.
			// gosec G402 is adjudicated as config-gated by design; no nolint
			// (repo has none).
			creds = credentials.NewTLS(&tls.Config{
				ServerName:         cfg.AgentTLSServerName,
				InsecureSkipVerify: cfg.AgentTLSInsecure,
			})
		}
	}

	// grpc.NewClient replaced the deprecated grpc.DialContext; the explicit
	// wait below preserves the former grpc.WithBlock fail-fast startup
	// semantics (refuse to start unless the engine answers within the
	// configured timeout). passthrough keeps Dial's host:port resolution.
	conn, err := grpc.NewClient("passthrough:///"+addr,
		grpc.WithTransportCredentials(creds),
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
	)
	if err != nil {
		log.Printf("Failed to connect to error book service at %s: %v", addr, err)
		return nil, err
	}

	if err := waitForConnReady(conn, time.Duration(timeoutSeconds)*time.Second); err != nil {
		_ = conn.Close()
		log.Printf("Failed to connect to error book service at %s: %v", addr, err)
		return nil, err
	}

	client := errorbookv1.NewErrorBookServiceClient(conn)
	return &Client{conn: conn, api: client}, nil
}

// waitForConnReady blocks until conn reaches connectivity.Ready or the timeout
// elapses, mirroring the removed grpc.DialContext+grpc.WithBlock dial mode.
func waitForConnReady(conn *grpc.ClientConn, timeout time.Duration) error {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	for {
		state := conn.GetState()
		if state == connectivity.Ready {
			return nil
		}
		if state == connectivity.Idle {
			conn.Connect()
		}
		if !conn.WaitForStateChange(ctx, state) {
			return fmt.Errorf("connection not ready within %s (state=%s)", timeout, conn.GetState())
		}
	}
}

func (c *Client) Close() {
	if c.conn != nil {
		c.conn.Close()
	}
}

// Delegate methods
func (c *Client) CreateError(ctx context.Context, req *errorbookv1.CreateErrorRequest) (*errorbookv1.ErrorRecord, error) {
	return c.api.CreateError(ctx, req)
}

func (c *Client) ListErrors(ctx context.Context, req *errorbookv1.ListErrorsRequest) (*errorbookv1.ListErrorsResponse, error) {
	return c.api.ListErrors(ctx, req)
}

func (c *Client) GetError(ctx context.Context, req *errorbookv1.GetErrorRequest) (*errorbookv1.ErrorRecord, error) {
	return c.api.GetError(ctx, req)
}

func (c *Client) GetErrorSemanticSummary(ctx context.Context, req *errorbookv1.GetErrorRequest) (*errorbookv1.ErrorSemanticSummary, error) {
	return c.api.GetErrorSemanticSummary(ctx, req)
}

func (c *Client) UpdateError(ctx context.Context, req *errorbookv1.UpdateErrorRequest) (*errorbookv1.ErrorRecord, error) {
	return c.api.UpdateError(ctx, req)
}

func (c *Client) DeleteError(ctx context.Context, req *errorbookv1.DeleteErrorRequest) (*errorbookv1.DeleteErrorResponse, error) {
	return c.api.DeleteError(ctx, req)
}

func (c *Client) AnalyzeError(ctx context.Context, req *errorbookv1.AnalyzeErrorRequest) (*errorbookv1.AnalyzeErrorResponse, error) {
	return c.api.AnalyzeError(ctx, req)
}

func (c *Client) SubmitReview(ctx context.Context, req *errorbookv1.SubmitReviewRequest) (*errorbookv1.ErrorRecord, error) {
	return c.api.SubmitReview(ctx, req)
}

func (c *Client) GetReviewStats(ctx context.Context, req *errorbookv1.GetReviewStatsRequest) (*errorbookv1.ReviewStatsResponse, error) {
	return c.api.GetReviewStats(ctx, req)
}

func (c *Client) GetTodayReviews(ctx context.Context, req *errorbookv1.GetTodayReviewsRequest) (*errorbookv1.ListErrorsResponse, error) {
	return c.api.GetTodayReviews(ctx, req)
}
