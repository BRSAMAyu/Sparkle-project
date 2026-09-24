package handler

import (
	"context"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"github.com/gin-gonic/gin"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	galaxyv1 "github.com/sparkle/gateway/gen/galaxy/v1"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/galaxy"
)

func TestGalaxyHandlerRegistersFrontendEndpoints(t *testing.T) {
	gin.SetMode(gin.TestMode)

	type capturedRequest struct {
		method string
		path   string
		userID string
	}
	var captured []capturedRequest

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		captured = append(captured, capturedRequest{
			method: r.Method,
			path:   r.URL.Path,
			userID: r.Header.Get("X-User-ID"),
		})
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"ok":true}`))
	}))
	defer backend.Close()

	router := gin.New()
	auth := func(c *gin.Context) {
		c.Set("user_id", "user-123")
		c.Next()
	}
	handler, err := NewGalaxyHandler(nil, nil, nil, backend.URL)
	if err != nil {
		t.Fatalf("NewGalaxyHandler failed: %v", err)
	}
	handler.RegisterRoutes(router.Group("/api/v1"), auth, nil)
	gateway := httptest.NewServer(router)
	defer gateway.Close()

	cases := []struct {
		method string
		path   string
	}{
		{method: http.MethodGet, path: "/api/v1/galaxy/graph"},
		{method: http.MethodGet, path: "/api/v1/galaxy/contribution-stats"},
		{method: http.MethodPost, path: "/api/v1/galaxy/nodes"},
		{method: http.MethodPost, path: "/api/v1/galaxy/search"},
		{method: http.MethodGet, path: "/api/v1/galaxy/node/node-1/history"},
		{method: http.MethodPost, path: "/api/v1/galaxy/node/node-1/expansion/candidates"},
		{method: http.MethodPost, path: "/api/v1/galaxy/node/node-1/expansion/apply"},
		{method: http.MethodPost, path: "/api/v1/galaxy/node/node-1/favorite"},
		{method: http.MethodPost, path: "/api/v1/galaxy/node/node-1/decay/pause"},
		{method: http.MethodPost, path: "/api/v1/galaxy/predict-next"},
		{method: http.MethodPost, path: "/api/v1/galaxy/nodes/viewport"},
		{method: http.MethodPost, path: "/api/v1/galaxy/nodes/positions"},
		{method: http.MethodPost, path: "/api/v1/galaxy/sync/mastery"},
	}

	for index, tc := range cases {
		req, err := http.NewRequest(tc.method, gateway.URL+tc.path, nil)
		if err != nil {
			t.Fatalf("new request: %v", err)
		}
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatalf("%s %s request failed: %v", tc.method, tc.path, err)
		}
		_ = resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Fatalf("%s %s returned %d, want 200", tc.method, tc.path, resp.StatusCode)
		}
		if len(captured) != index+1 {
			t.Fatalf("%s %s was not proxied", tc.method, tc.path)
		}
		got := captured[index]
		if got.method != tc.method || got.path != tc.path {
			t.Fatalf("proxied request = %s %s, want %s %s", got.method, got.path, tc.method, tc.path)
		}
		if got.userID != "user-123" {
			t.Fatalf("X-User-ID = %q, want user-123", got.userID)
		}
	}
}

// capturingGalaxyServer is an in-process stand-in for the engine's
// GalaxyService that records the gRPC invocation metadata of every call,
// mimicking the SEC-3 auth checks the real engine applies.
type capturingGalaxyServer struct {
	galaxyv1.UnimplementedGalaxyServiceServer

	mu       sync.Mutex
	seenMD   map[string]metadata.MD
	failAuth bool
}

func (s *capturingGalaxyServer) record(ctx context.Context, method string) error {
	md, _ := metadata.FromIncomingContext(ctx)
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.seenMD == nil {
		s.seenMD = make(map[string]metadata.MD)
	}
	s.seenMD[method] = md
	if s.failAuth && len(md.Get("user-id")) == 0 {
		// Mirror the engine AuthInterceptor: no authentication metadata → 401.
		return status.Error(codes.Unauthenticated, "missing authentication metadata")
	}
	return nil
}

func (s *capturingGalaxyServer) metadataFor(method string) metadata.MD {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.seenMD[method]
}

func (s *capturingGalaxyServer) UpdateNodeMastery(ctx context.Context, req *galaxyv1.UpdateNodeMasteryRequest) (*galaxyv1.UpdateNodeMasteryResponse, error) {
	if err := s.record(ctx, "UpdateNodeMastery"); err != nil {
		return nil, err
	}
	return &galaxyv1.UpdateNodeMasteryResponse{Success: true, OldMastery: 1, NewMastery: 2, CurrentRevision: 42}, nil
}

func (s *capturingGalaxyServer) SyncCollaborativeGalaxy(ctx context.Context, req *galaxyv1.SyncCollaborativeGalaxyRequest) (*galaxyv1.SyncCollaborativeGalaxyResponse, error) {
	if err := s.record(ctx, "SyncCollaborativeGalaxy"); err != nil {
		return nil, err
	}
	return &galaxyv1.SyncCollaborativeGalaxyResponse{Success: true}, nil
}

func (s *capturingGalaxyServer) GetUserGalaxy(ctx context.Context, req *galaxyv1.GetUserGalaxyRequest) (*galaxyv1.GetUserGalaxyResponse, error) {
	if err := s.record(ctx, "GetUserGalaxy"); err != nil {
		return nil, err
	}
	return &galaxyv1.GetUserGalaxyResponse{TotalNodes: 1}, nil
}

func (s *capturingGalaxyServer) GetNodeDetail(ctx context.Context, req *galaxyv1.GetNodeDetailRequest) (*galaxyv1.GetNodeDetailResponse, error) {
	if err := s.record(ctx, "GetNodeDetail"); err != nil {
		return nil, err
	}
	return &galaxyv1.GetNodeDetailResponse{NodeId: req.NodeId}, nil
}

func (s *capturingGalaxyServer) SearchNodes(ctx context.Context, req *galaxyv1.SearchNodesRequest) (*galaxyv1.SearchNodesResponse, error) {
	if err := s.record(ctx, "SearchNodes"); err != nil {
		return nil, err
	}
	return &galaxyv1.SearchNodesResponse{TotalFound: 1}, nil
}

func (s *capturingGalaxyServer) GetLearningPath(ctx context.Context, req *galaxyv1.GetLearningPathRequest) (*galaxyv1.GetLearningPathResponse, error) {
	if err := s.record(ctx, "GetLearningPath"); err != nil {
		return nil, err
	}
	return &galaxyv1.GetLearningPathResponse{PathFound: true}, nil
}

func (s *capturingGalaxyServer) GetNodeDependencies(ctx context.Context, req *galaxyv1.GetNodeDependenciesRequest) (*galaxyv1.GetNodeDependenciesResponse, error) {
	if err := s.record(ctx, "GetNodeDependencies"); err != nil {
		return nil, err
	}
	return &galaxyv1.GetNodeDependenciesResponse{}, nil
}

func (s *capturingGalaxyServer) RecordNodeInteraction(ctx context.Context, req *galaxyv1.RecordNodeInteractionRequest) (*galaxyv1.RecordNodeInteractionResponse, error) {
	if err := s.record(ctx, "RecordNodeInteraction"); err != nil {
		return nil, err
	}
	return &galaxyv1.RecordNodeInteractionResponse{Success: true}, nil
}

func (s *capturingGalaxyServer) GetGalaxyStats(ctx context.Context, req *galaxyv1.GetGalaxyStatsRequest) (*galaxyv1.GetGalaxyStatsResponse, error) {
	if err := s.record(ctx, "GetGalaxyStats"); err != nil {
		return nil, err
	}
	return &galaxyv1.GetGalaxyStatsResponse{TotalNodes: 3}, nil
}

func (s *capturingGalaxyServer) GetRecommendedNodes(ctx context.Context, req *galaxyv1.GetRecommendedNodesRequest) (*galaxyv1.GetRecommendedNodesResponse, error) {
	if err := s.record(ctx, "GetRecommendedNodes"); err != nil {
		return nil, err
	}
	return &galaxyv1.GetRecommendedNodesResponse{}, nil
}

// TestGalaxyGRPCEndpoints_InjectAuthMetadata is the red/green regression for
// the galaxy gRPC bridge: the engine's AuthInterceptor aborts every call that
// carries no `authorization`/`user-id` metadata (SEC-3), and its servicers
// reject a request body user_id without matching `user-id` metadata. Every
// gin handler that issues an outbound galaxy gRPC call must therefore run
// injectAuthContext (same contract as error_book.go, P1-E1).
func TestGalaxyGRPCEndpoints_InjectAuthMetadata(t *testing.T) {
	gin.SetMode(gin.TestMode)

	server := &capturingGalaxyServer{}
	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	grpcServer := grpc.NewServer()
	galaxyv1.RegisterGalaxyServiceServer(grpcServer, server)
	go func() { _ = grpcServer.Serve(lis) }()
	defer grpcServer.Stop()

	galaxyClient, err := galaxy.NewClient(&config.Config{AgentAddress: lis.Addr().String()})
	if err != nil {
		t.Fatalf("galaxy.NewClient: %v", err)
	}
	defer galaxyClient.Close()

	proxyBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Errorf("%s %s unexpectedly fell back to the REST proxy", r.Method, r.URL.Path)
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"ok":true}`))
	}))
	defer proxyBackend.Close()

	ginHandler, err := NewGalaxyHandler(galaxyClient, nil, nil, proxyBackend.URL)
	if err != nil {
		t.Fatalf("NewGalaxyHandler: %v", err)
	}

	auth := func(c *gin.Context) {
		// Mirrors AuthMiddleware: identity comes from JWT validation.
		c.Set("user_id", "user-42")
		c.Set("auth_token", "jwt-test")
		c.Next()
	}

	router := gin.New()
	router.Use(auth)
	g := router.Group("/api/v1/galaxy")
	g.POST("/nodes/:id/spark", ginHandler.SparkNode)
	g.POST("/nodes/:id/mastery", ginHandler.UpdateMastery)
	g.GET("/nodes/:id", ginHandler.GetNodeDetailGPRC)
	g.GET("/search", ginHandler.SearchNodesGPRC)
	g.GET("/stats", ginHandler.GetGalaxyStatsGPRC)
	g.GET("/predict", ginHandler.GetRecommendedGPRC)
	g.GET("/graph", ginHandler.GetGraph)
	g.POST("/sync", ginHandler.SyncGalaxy)
	g.GET("/learning-path", ginHandler.GetLearningPath)
	g.GET("/nodes/:id/dependencies", ginHandler.GetNodeDependencies)

	gateway := httptest.NewServer(router)
	defer gateway.Close()

	cases := []struct {
		name       string
		method     string
		path       string
		body       string
		rpcMethod  string
		wantInBody string
	}{
		{name: "SparkNode", method: http.MethodPost, path: "/api/v1/galaxy/nodes/n-1/spark", body: `{"study_minutes":2}`, rpcMethod: "RecordNodeInteraction", wantInBody: `"via":"grpc"`},
		{name: "UpdateMastery", method: http.MethodPost, path: "/api/v1/galaxy/nodes/n-1/mastery", body: `{"mastery":3}`, rpcMethod: "UpdateNodeMastery", wantInBody: `"success":true`},
		{name: "GetNodeDetail", method: http.MethodGet, path: "/api/v1/galaxy/nodes/n-1", rpcMethod: "GetNodeDetail", wantInBody: `"via":"grpc"`},
		{name: "SearchNodes", method: http.MethodGet, path: "/api/v1/galaxy/search?q=kinetics", rpcMethod: "SearchNodes", wantInBody: `"via":"grpc"`},
		{name: "GetGalaxyStats", method: http.MethodGet, path: "/api/v1/galaxy/stats", rpcMethod: "GetGalaxyStats", wantInBody: `"via":"grpc"`},
		{name: "GetRecommendedNodes", method: http.MethodGet, path: "/api/v1/galaxy/predict", rpcMethod: "GetRecommendedNodes", wantInBody: `"via":"grpc"`},
		{name: "GetGraph", method: http.MethodGet, path: "/api/v1/galaxy/graph", rpcMethod: "GetUserGalaxy", wantInBody: `"via":"grpc"`},
		{name: "SyncCollaborativeGalaxy", method: http.MethodPost, path: "/api/v1/galaxy/sync", body: `{"galaxy_id":"g-1","partial_update":{}}`, rpcMethod: "SyncCollaborativeGalaxy", wantInBody: `"via":"grpc"`},
		{name: "GetLearningPath", method: http.MethodGet, path: "/api/v1/galaxy/learning-path?from=a&to=b", rpcMethod: "GetLearningPath", wantInBody: `"via":"grpc"`},
		{name: "GetNodeDependencies", method: http.MethodGet, path: "/api/v1/galaxy/nodes/n-1/dependencies", rpcMethod: "GetNodeDependencies", wantInBody: `"via":"grpc"`},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var bodyReader *strings.Reader
			if tc.body != "" {
				bodyReader = strings.NewReader(tc.body)
			} else {
				bodyReader = strings.NewReader("")
			}
			req, err := http.NewRequestWithContext(context.Background(), tc.method, gateway.URL+tc.path, bodyReader)
			if err != nil {
				t.Fatalf("new request: %v", err)
			}
			if tc.body != "" {
				req.Header.Set("Content-Type", "application/json")
			}
			resp, err := http.DefaultClient.Do(req)
			if err != nil {
				t.Fatalf("%s %s request failed: %v", tc.method, tc.path, err)
			}
			defer resp.Body.Close()
			bodyBytes, err := io.ReadAll(resp.Body)
			if err != nil {
				t.Fatalf("%s %s read body: %v", tc.method, tc.path, err)
			}
			body := string(bodyBytes)

			if resp.StatusCode != http.StatusOK {
				t.Fatalf("%s %s returned %d, want 200 (body=%s)", tc.method, tc.path, resp.StatusCode, body)
			}
			if tc.wantInBody != "" && !strings.Contains(body, tc.wantInBody) {
				t.Fatalf("%s %s body = %s, want it to contain %q (gRPC path not taken?)", tc.name, tc.path, body, tc.wantInBody)
			}

			md := server.metadataFor(tc.rpcMethod)
			if md == nil {
				t.Fatalf("%s: engine never saw the %s gRPC call", tc.name, tc.rpcMethod)
			}
			if got := md.Get("user-id"); len(got) != 1 || got[0] != "user-42" {
				t.Fatalf("%s: engine saw user-id metadata %v, want [user-42] (SEC-3: missing metadata → engine 401)", tc.name, got)
			}
			if got := md.Get("authorization"); len(got) != 1 || got[0] != "Bearer jwt-test" {
				t.Fatalf("%s: engine saw authorization metadata %v, want [Bearer jwt-test]", tc.name, got)
			}
		})
	}
}
