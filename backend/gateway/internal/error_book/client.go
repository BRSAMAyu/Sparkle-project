package error_book

import (
    "context"
    "crypto/tls"
    "log"
    "time"

    errorbookv1 "github.com/sparkle/gateway/gen/proto/error_book"
    "github.com/sparkle/gateway/internal/config"
    "go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"
    "google.golang.org/grpc/credentials/insecure"
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

    conn, err := grpc.DialContext(ctx, addr,
        grpc.WithTransportCredentials(creds),
        grpc.WithBlock(),
        grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
    )
    if err != nil {
        log.Printf("Failed to connect to error book service at %s: %v", addr, err)
        return nil, err
    }

    client := errorbookv1.NewErrorBookServiceClient(conn)
    return &Client{conn: conn, api: client}, nil
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
