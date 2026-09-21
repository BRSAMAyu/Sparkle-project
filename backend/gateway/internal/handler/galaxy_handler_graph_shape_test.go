package handler

// GW-GRAPH-SHAPE contract tests: the gateway's gRPC-first GetGraph branch
// must emit the same outbound JSON shape as the engine's REST contract —
// backend/app/schemas/galaxy.py (GalaxyGraphResponse / NodeWithStatus /
// NodeRelationInfo) — because the mobile client (GalaxyNodeModel /
// GalaxyEdgeModel) parses REST keys (id/name/mastery_score,
// source_node_id/target_node_id/relation_type).
//
// V24 root cause regression: the gRPC branch used to marshal the proto
// GetUserGalaxyResponse directly (json tags node_id/label/mastery +
// source_id/target_id/relation), so first loads answered by gRPC parsed into
// nameless node shells and rendered an empty universe.

import (
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"google.golang.org/grpc"

	galaxyv1 "github.com/sparkle/gateway/gen/galaxy/v1"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/galaxy"
)

// REST contract keys (source of truth: backend/app/schemas/galaxy.py).
var (
	// NodeWithStatus keys the proto payload can carry a value for; the client
	// requires id/name/mastery_score to render a node at all.
	graphRESTNodeKeys = []string{"id", "name", "mastery_score", "tags"}
	// Proto json tags that must never leak through the gateway.
	graphForbiddenNodeKeys = []string{"node_id", "label", "mastery"}

	// NodeRelationInfo keys; the client requires all three to draw an edge.
	graphRESTEdgeKeys = []string{"source_node_id", "target_node_id", "relation_type"}
	// Proto json tags that must never leak through the gateway.
	graphForbiddenEdgeKeys = []string{"source_id", "target_id", "relation"}
)

func graphFixtureResponse() *galaxyv1.GetUserGalaxyResponse {
	return &galaxyv1.GetUserGalaxyResponse{
		UserId: "user-42",
		Nodes: []*galaxyv1.GalaxyNode{
			{NodeId: "node-1", Label: "Newtonian mechanics", NodeType: "concept", Mastery: 87, Tags: []string{"physics", "core"}},
			{NodeId: "node-2", Label: "Calculus", NodeType: "skill", Mastery: 42, Tags: []string{"math"}},
		},
		Edges: []*galaxyv1.GalaxyEdge{
			{SourceId: "node-2", TargetId: "node-1", Relation: "prerequisite"},
		},
		TotalNodes: 2,
	}
}

func mustDecodeGraphBody(t *testing.T, body string) map[string]any {
	t.Helper()
	var payload map[string]any
	if err := json.Unmarshal([]byte(body), &payload); err != nil {
		t.Fatalf("decode graph payload: %v (body=%s)", err, body)
	}
	return payload
}

func assertGraphShape(t *testing.T, payload map[string]any) {
	t.Helper()

	// Top-level contract: REST emits both edge aliases; the client reads
	// `edges` first and falls back to `relations`.
	for _, key := range []string{"nodes", "edges", "relations", "total_nodes"} {
		if _, ok := payload[key]; !ok {
			t.Fatalf("graph payload missing top-level key %q (keys=%v)", key, payloadKeys(payload))
		}
	}
	if payload["relations"] == nil {
		t.Fatalf("graph payload relations = nil, want a non-null edge list (REST emits both aliases)")
	}

	// via=grpc proves the assertions below exercise the gRPC branch, not the
	// REST proxy fallback (which already speaks the contract natively).
	if got := payload["via"]; got != "grpc" {
		t.Fatalf("graph payload via = %v, want \"grpc\"", got)
	}

	rawNodes, err := json.Marshal(payload["nodes"])
	if err != nil {
		t.Fatalf("marshal nodes: %v", err)
	}
	var nodes []map[string]any
	if err := json.Unmarshal(rawNodes, &nodes); err != nil {
		t.Fatalf("decode nodes: %v", err)
	}
	if len(nodes) != 2 {
		t.Fatalf("nodes count = %d, want 2", len(nodes))
	}
	for i, node := range nodes {
		for _, key := range graphRESTNodeKeys {
			if _, ok := node[key]; !ok {
				t.Fatalf("node[%d] missing REST contract key %q (keys=%v)", i, key, payloadKeys(node))
			}
		}
		for _, key := range graphForbiddenNodeKeys {
			if _, ok := node[key]; ok {
				t.Fatalf("node[%d] leaked proto key %q (keys=%v)", i, key, payloadKeys(node))
			}
		}
	}

	rawEdges, err := json.Marshal(payload["edges"])
	if err != nil {
		t.Fatalf("marshal edges: %v", err)
	}
	var edges []map[string]any
	if err := json.Unmarshal(rawEdges, &edges); err != nil {
		t.Fatalf("decode edges: %v", err)
	}
	if len(edges) != 1 {
		t.Fatalf("edges count = %d, want 1", len(edges))
	}
	for i, edge := range edges {
		for _, key := range graphRESTEdgeKeys {
			if _, ok := edge[key]; !ok {
				t.Fatalf("edge[%d] missing REST contract key %q (keys=%v)", i, key, payloadKeys(edge))
			}
		}
		for _, key := range graphForbiddenEdgeKeys {
			if _, ok := edge[key]; ok {
				t.Fatalf("edge[%d] leaked proto key %q (keys=%v)", i, key, payloadKeys(edge))
			}
		}
	}

	// Values must survive the mapping unchanged.
	node0 := nodes[0]
	if node0["id"] != "node-1" || node0["name"] != "Newtonian mechanics" {
		t.Fatalf("node[0] id/name = %v/%v, want node-1/Newtonian mechanics", node0["id"], node0["name"])
	}
	if got, want := node0["mastery_score"], float64(87); got != want {
		t.Fatalf("node[0] mastery_score = %v, want %v", got, want)
	}
	edge0 := edges[0]
	if edge0["source_node_id"] != "node-2" || edge0["target_node_id"] != "node-1" {
		t.Fatalf("edge[0] endpoints = %v→%v, want node-2→node-1", edge0["source_node_id"], edge0["target_node_id"])
	}
	// Relation values pass through verbatim (engine gRPC servicer copies
	// relation_type from the same DB source REST reads); the client maps
	// "parent"→parentChild itself, so no value rewriting happens here.
	if edge0["relation_type"] != "prerequisite" {
		t.Fatalf("edge[0] relation_type = %v, want prerequisite (verbatim passthrough)", edge0["relation_type"])
	}
}

func payloadKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	return keys
}

// TestGalaxyGraphRESTPayload_MapsProtoKeysToRESTContract pins the proto→REST
// key mapping at the mapper level (unit).
func TestGalaxyGraphRESTPayload_MapsProtoKeysToRESTContract(t *testing.T) {
	raw, err := json.Marshal(galaxyGraphRESTPayload(graphFixtureResponse()))
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	assertGraphShape(t, mustDecodeGraphBody(t, string(raw)))
}

// TestGalaxyGraphRESTPayload_ZeroValuesStillEmitContractKeys guards against
// the generated `json:"...,omitempty"` trap: direct proto marshaling silently
// drops zero-valued fields (mastery=0, empty label), which is exactly how
// nameless shells reached the client. Explicit mapping must always emit the
// REST keys.
func TestGalaxyGraphRESTPayload_ZeroValuesStillEmitContractKeys(t *testing.T) {
	resp := &galaxyv1.GetUserGalaxyResponse{
		Nodes:      []*galaxyv1.GalaxyNode{{NodeId: "node-3"}},
		Edges:      []*galaxyv1.GalaxyEdge{{SourceId: "node-3", TargetId: "node-4"}},
		TotalNodes: 1,
	}
	raw, err := json.Marshal(galaxyGraphRESTPayload(resp))
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	payload := mustDecodeGraphBody(t, string(raw))

	rawNodes, _ := json.Marshal(payload["nodes"])
	var nodes []map[string]any
	if err := json.Unmarshal(rawNodes, &nodes); err != nil {
		t.Fatalf("decode nodes: %v", err)
	}
	node := nodes[0]
	for _, key := range graphRESTNodeKeys {
		if _, ok := node[key]; !ok {
			t.Fatalf("zero-valued node dropped REST key %q (omitempty trap, keys=%v)", key, payloadKeys(node))
		}
	}
	if node["id"] != "node-3" || node["name"] != "" || node["mastery_score"] != float64(0) {
		t.Fatalf("zero-valued node = %v, want id=node-3, name=\"\", mastery_score=0", node)
	}

	rawEdges, _ := json.Marshal(payload["edges"])
	var edges []map[string]any
	if err := json.Unmarshal(rawEdges, &edges); err != nil {
		t.Fatalf("decode edges: %v", err)
	}
	edge := edges[0]
	for _, key := range graphRESTEdgeKeys {
		if _, ok := edge[key]; !ok {
			t.Fatalf("zero-valued edge dropped REST key %q (omitempty trap, keys=%v)", key, payloadKeys(edge))
		}
	}
}

// stubGraphGalaxyServer serves a fixture GetUserGalaxyResponse so the
// end-to-end test exercises the real handler gRPC branch.
type stubGraphGalaxyServer struct {
	galaxyv1.UnimplementedGalaxyServiceServer

	resp *galaxyv1.GetUserGalaxyResponse
}

func (s *stubGraphGalaxyServer) GetUserGalaxy(ctx context.Context, req *galaxyv1.GetUserGalaxyRequest) (*galaxyv1.GetUserGalaxyResponse, error) {
	return s.resp, nil
}

// TestGetGraph_GRPCBranch_EmitsRESTContractShape is the end-to-end red/green
// regression: GET /galaxy/graph answered by the gRPC branch must serialize to
// the REST contract shape (node + edge keys), byte-for-byte comparable to
// what ProxyToBackend would return from the engine.
func TestGetGraph_GRPCBranch_EmitsRESTContractShape(t *testing.T) {
	gin.SetMode(gin.TestMode)

	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	grpcServer := grpc.NewServer()
	galaxyv1.RegisterGalaxyServiceServer(grpcServer, &stubGraphGalaxyServer{resp: graphFixtureResponse()})
	go func() { _ = grpcServer.Serve(lis) }()
	defer grpcServer.Stop()

	galaxyClient, err := galaxy.NewClient(&config.Config{AgentAddress: lis.Addr().String()})
	if err != nil {
		t.Fatalf("galaxy.NewClient: %v", err)
	}
	defer galaxyClient.Close()

	// The REST fallback must NOT be hit: a hit would mean the test is
	// asserting the proxy shape, not the gRPC branch shape.
	proxyBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Errorf("GetGraph unexpectedly fell back to the REST proxy: %s %s", r.Method, r.URL.Path)
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"nodes":[],"edges":null}`))
	}))
	defer proxyBackend.Close()

	ginHandler, err := NewGalaxyHandler(galaxyClient, nil, nil, proxyBackend.URL)
	if err != nil {
		t.Fatalf("NewGalaxyHandler: %v", err)
	}

	auth := func(c *gin.Context) {
		c.Set("user_id", "user-42")
		c.Next()
	}
	router := gin.New()
	router.Use(auth)
	router.GET("/api/v1/galaxy/graph", ginHandler.GetGraph)

	gateway := httptest.NewServer(router)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/api/v1/galaxy/graph")
	if err != nil {
		t.Fatalf("GET /graph: %v", err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("GET /graph returned %d, want 200 (body=%s)", resp.StatusCode, body)
	}
	if !strings.Contains(string(body), `"via":"grpc"`) {
		t.Fatalf("GET /graph body = %s, want the gRPC branch marker", body)
	}
	assertGraphShape(t, mustDecodeGraphBody(t, string(body)))
}
