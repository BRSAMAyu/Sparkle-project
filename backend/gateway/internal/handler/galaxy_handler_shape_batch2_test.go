package handler

// GW-SHAPE-BATCH2 contract tests (FIX-53 follow-up): the gateway's gRPC-first
// branches for GetNodeDetail / SearchNodes / GetGalaxyStats / GetRecommended
// must emit the same outbound JSON shapes as the engine's REST contracts —
//
//   - GetNodeDetail  → backend/app/api/v1/galaxy.py get_node_detail
//     ({node, userStats, relations, ...} — mobile KnowledgeDetailResponse)
//   - SearchNodes    → backend/app/schemas/galaxy.py SearchResponse
//     ({query, results: [{node, similarity}], total_count} — mobile
//     GalaxySearchResponse)
//   - GetGalaxyStats → backend/app/api/v1/galaxy.py get_galaxy_stats
//     ({"user_stats": ...})
//   - GetRecommended → node-item REST keys (no engine REST route exists for
//     GET /galaxy/predict; closest sibling POST /predict-next)
//
// Regression: these branches used to pass the flat proto shapes through
// (node_id/label/mastery, nodes/total_found, mastered_nodes/nodes_by_type),
// which the mobile client cannot parse (node detail and search threw on
// parse; stats matched no REST key).

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

// batch2FixtureNode is a fully-populated proto GalaxyNode shared by the
// search / recommended fixtures.
func batch2FixtureNode() *galaxyv1.GalaxyNode {
	return &galaxyv1.GalaxyNode{
		NodeId:   "node-9",
		Label:    "Thermodynamics",
		NodeType: "concept",
		Mastery:  63,
		Tags:     []string{"physics"},
	}
}

// assertRESTNodeItem checks one mapped node object: REST keys present, proto
// keys never leaked, values preserved.
func assertRESTNodeItem(t *testing.T, node map[string]any) {
	t.Helper()
	for _, key := range []string{"id", "name", "mastery_score"} {
		if _, ok := node[key]; !ok {
			t.Fatalf("node missing REST contract key %q (keys=%v)", key, payloadKeys(node))
		}
	}
	for _, key := range []string{"node_id", "label", "mastery"} {
		if _, ok := node[key]; ok {
			t.Fatalf("node leaked proto key %q (keys=%v)", key, payloadKeys(node))
		}
	}
	if node["id"] != "node-9" || node["name"] != "Thermodynamics" {
		t.Fatalf("node id/name = %v/%v, want node-9/Thermodynamics", node["id"], node["name"])
	}
	if got, want := node["mastery_score"], float64(63); got != want {
		t.Fatalf("node mastery_score = %v, want %v", got, want)
	}
}

// ---------------------------------------------------------------------------
// Mapper unit tests
// ---------------------------------------------------------------------------

// TestGalaxyNodeDetailRESTPayload_MapsProtoKeysToRESTContract pins the flat
// proto → nested REST (KnowledgeDetailResponse) mapping.
func TestGalaxyNodeDetailRESTPayload_MapsProtoKeysToRESTContract(t *testing.T) {
	resp := &galaxyv1.GetNodeDetailResponse{
		NodeId:      "node-9",
		Label:       "Thermodynamics",
		NodeType:    "seed",
		Mastery:     63,
		Description: "Laws of energy",
		Tags:        []string{"physics", "energy"},
		ParentIds:   []string{"node-1"},
		ChildIds:    []string{"node-5"},
		Metadata:    map[string]string{"doc_0": "lecture.pdf"},
	}
	raw, err := json.Marshal(galaxyNodeDetailRESTPayload(resp))
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	payload := mustDecodeGraphBody(t, string(raw))

	// Top level: nested node/userStats keys, never the flat proto keys.
	for _, key := range []string{"node", "userStats"} {
		if _, ok := payload[key]; !ok {
			t.Fatalf("payload missing REST key %q (keys=%v)", key, payloadKeys(payload))
		}
	}
	for _, key := range []string{"node_id", "label", "mastery", "parent_ids", "child_ids"} {
		if _, ok := payload[key]; ok {
			t.Fatalf("payload leaked flat proto key %q (keys=%v)", key, payloadKeys(payload))
		}
	}
	if got := payload["via"]; got != "grpc" {
		t.Fatalf("via = %v, want grpc", got)
	}

	node, ok := payload["node"].(map[string]any)
	if !ok {
		t.Fatalf("payload.node not an object: %v", payload["node"])
	}
	// REST node_dict keys the proto can fill; source documents / relations /
	// related tasks are proto-less and must be absent (client defaults them).
	for _, key := range []string{"id", "name", "description", "keywords", "source_type", "parent_id"} {
		if _, ok := node[key]; !ok {
			t.Fatalf("node missing REST key %q (keys=%v)", key, payloadKeys(node))
		}
	}
	for _, key := range []string{"node_id", "label", "node_type", "tags", "metadata"} {
		if _, ok := node[key]; ok {
			t.Fatalf("node leaked proto key %q (keys=%v)", key, payloadKeys(node))
		}
	}
	if node["id"] != "node-9" || node["name"] != "Thermodynamics" || node["description"] != "Laws of energy" {
		t.Fatalf("node = %v, want id/name/description preserved", node)
	}
	// tags → keywords and node_type → source_type are provenance-identical
	// (engine servicer fills both from the same DB fields REST reads).
	if ks, ok := node["keywords"].([]any); !ok || len(ks) != 2 || ks[0] != "physics" {
		t.Fatalf("node.keywords = %v, want [physics energy]", node["keywords"])
	}
	if node["source_type"] != "seed" {
		t.Fatalf("node.source_type = %v, want seed", node["source_type"])
	}
	if node["parent_id"] != "node-1" {
		t.Fatalf("node.parent_id = %v, want node-1", node["parent_id"])
	}

	userStats, ok := payload["userStats"].(map[string]any)
	if !ok {
		t.Fatalf("payload.userStats not an object: %v", payload["userStats"])
	}
	if got, want := userStats["mastery_score"], float64(63); got != want {
		t.Fatalf("userStats.mastery_score = %v, want %v", got, want)
	}
}

// TestGalaxyNodeDetailRESTPayload_EmptyParentEmitsNull pins the REST parity
// detail: parent_id is JSON null when the proto parent_ids slice is empty
// (REST emits None), and zero-valued scalar keys are still emitted.
func TestGalaxyNodeDetailRESTPayload_EmptyParentEmitsNull(t *testing.T) {
	raw, err := json.Marshal(galaxyNodeDetailRESTPayload(&galaxyv1.GetNodeDetailResponse{NodeId: "node-3"}))
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	payload := mustDecodeGraphBody(t, string(raw))
	node := payload["node"].(map[string]any)
	for _, key := range []string{"id", "name", "description", "keywords", "source_type", "parent_id"} {
		if _, ok := node[key]; !ok {
			t.Fatalf("zero-valued node dropped REST key %q (omitempty trap, keys=%v)", key, payloadKeys(node))
		}
	}
	if _, exists := node["parent_id"]; !exists || node["parent_id"] != nil {
		t.Fatalf("node.parent_id = %v, want explicit null", node["parent_id"])
	}
}

// TestGalaxySearchRESTPayload_MapsProtoKeysToRESTContract pins the proto
// SearchNodesResponse → REST SearchResponse mapping.
func TestGalaxySearchRESTPayload_MapsProtoKeysToRESTContract(t *testing.T) {
	resp := &galaxyv1.SearchNodesResponse{
		Nodes:      []*galaxyv1.GalaxyNode{batch2FixtureNode()},
		TotalFound: 1,
	}
	raw, err := json.Marshal(galaxySearchRESTPayload("thermo", resp))
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	payload := mustDecodeGraphBody(t, string(raw))

	for _, key := range []string{"query", "results", "total_count"} {
		if _, ok := payload[key]; !ok {
			t.Fatalf("payload missing REST key %q (keys=%v)", key, payloadKeys(payload))
		}
	}
	for _, key := range []string{"nodes", "total_found"} {
		if _, ok := payload[key]; ok {
			t.Fatalf("payload leaked proto key %q (keys=%v)", key, payloadKeys(payload))
		}
	}
	if payload["query"] != "thermo" {
		t.Fatalf("query = %v, want the request query echoed (REST SearchResponse.query)", payload["query"])
	}
	if got, want := payload["total_count"], float64(1); got != want {
		t.Fatalf("total_count = %v, want %v (mapped from total_found)", got, want)
	}

	results, ok := payload["results"].([]any)
	if !ok || len(results) != 1 {
		t.Fatalf("results = %v, want a 1-item list", payload["results"])
	}
	item := results[0].(map[string]any)
	// Mobile GalaxySearchResult.fromJson requires node + similarity (both
	// without defaults).
	for _, key := range []string{"node", "similarity"} {
		if _, ok := item[key]; !ok {
			t.Fatalf("result item missing required key %q (keys=%v)", key, payloadKeys(item))
		}
	}
	if _, ok := item["similarity"].(float64); !ok {
		t.Fatalf("similarity = %v, want a number (neutral placeholder)", item["similarity"])
	}
	assertRESTNodeItem(t, item["node"].(map[string]any))
}

// TestGalaxyStatsRESTPayload_MapsProtoKeysToRESTContract pins the flat proto
// stats → REST {"user_stats": ...} mapping, including the exact
// unlocked_count reconstruction (mastered + in_progress).
func TestGalaxyStatsRESTPayload_MapsProtoKeysToRESTContract(t *testing.T) {
	resp := &galaxyv1.GetGalaxyStatsResponse{
		TotalNodes:      20,
		MasteredNodes:   5,
		InProgressNodes: 7,
		NotStartedNodes: 8,
		AverageMastery:  41.5,
		NodesByType:     map[string]int32{"COSMOS": 12, "TECH": 8},
	}
	raw, err := json.Marshal(galaxyStatsRESTPayload(resp))
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	payload := mustDecodeGraphBody(t, string(raw))

	if _, ok := payload["user_stats"]; !ok {
		t.Fatalf("payload missing REST key user_stats (keys=%v)", payloadKeys(payload))
	}
	for _, key := range []string{"total_nodes", "mastered_nodes", "in_progress_nodes", "not_started_nodes", "nodes_by_type"} {
		if _, ok := payload[key]; ok {
			t.Fatalf("payload leaked flat proto key %q (keys=%v)", key, payloadKeys(payload))
		}
	}

	userStats := payload["user_stats"].(map[string]any)
	for _, key := range []string{"total_nodes", "unlocked_count", "mastered_count", "sector_distribution"} {
		if _, ok := userStats[key]; !ok {
			t.Fatalf("user_stats missing REST key %q (keys=%v)", key, payloadKeys(userStats))
		}
	}
	if got, want := userStats["total_nodes"], float64(20); got != want {
		t.Fatalf("user_stats.total_nodes = %v, want %v", got, want)
	}
	if got, want := userStats["mastered_count"], float64(5); got != want {
		t.Fatalf("user_stats.mastered_count = %v, want %v", got, want)
	}
	// Engine servicer: in_progress = max(0, unlocked - mastered) ⇒
	// unlocked = mastered + in_progress exactly.
	if got, want := userStats["unlocked_count"], float64(12); got != want {
		t.Fatalf("user_stats.unlocked_count = %v, want %v (mastered+in_progress)", got, want)
	}
	sd, ok := userStats["sector_distribution"].(map[string]any)
	if !ok || sd["COSMOS"] != float64(12) || sd["TECH"] != float64(8) {
		t.Fatalf("sector_distribution = %v, want nodes_by_type values verbatim", userStats["sector_distribution"])
	}
	if got, want := userStats["average_mastery"], 41.5; got != want {
		t.Fatalf("user_stats.average_mastery = %v, want %v (proto-only extra kept)", got, want)
	}
}

// TestGalaxyRecommendedRESTPayload_MapsRESTNodeKeys pins the GetRecommended
// node-item alignment (top-level nodes/reasons cardinality is proto-shaped by
// design — see mapper doc comment).
func TestGalaxyRecommendedRESTPayload_MapsRESTNodeKeys(t *testing.T) {
	resp := &galaxyv1.GetRecommendedNodesResponse{
		Nodes:   []*galaxyv1.GalaxyNode{batch2FixtureNode()},
		Reasons: []string{"Predicted best next step based on your learning pattern"},
	}
	raw, err := json.Marshal(galaxyRecommendedRESTPayload(resp))
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	payload := mustDecodeGraphBody(t, string(raw))

	nodes, ok := payload["nodes"].([]any)
	if !ok || len(nodes) != 1 {
		t.Fatalf("nodes = %v, want a 1-item list", payload["nodes"])
	}
	assertRESTNodeItem(t, nodes[0].(map[string]any))
	reasons, ok := payload["reasons"].([]any)
	if !ok || len(reasons) != 1 || reasons[0] != "Predicted best next step based on your learning pattern" {
		t.Fatalf("reasons = %v, want verbatim passthrough", payload["reasons"])
	}
	if got := payload["via"]; got != "grpc" {
		t.Fatalf("via = %v, want grpc", got)
	}
}

// ---------------------------------------------------------------------------
// End-to-end: real gRPC client → handler → HTTP body shape assertions
// ---------------------------------------------------------------------------

// stubBatch2GalaxyServer serves fixtures for the four batch-2 RPCs so the
// end-to-end tests exercise the real handler gRPC branches.
type stubBatch2GalaxyServer struct {
	galaxyv1.UnimplementedGalaxyServiceServer
}

func (s *stubBatch2GalaxyServer) GetNodeDetail(ctx context.Context, req *galaxyv1.GetNodeDetailRequest) (*galaxyv1.GetNodeDetailResponse, error) {
	return &galaxyv1.GetNodeDetailResponse{
		NodeId:      "node-9",
		Label:       "Thermodynamics",
		NodeType:    "seed",
		Mastery:     63,
		Description: "Laws of energy",
		Tags:        []string{"physics", "energy"},
		ParentIds:   []string{"node-1"},
	}, nil
}

func (s *stubBatch2GalaxyServer) SearchNodes(ctx context.Context, req *galaxyv1.SearchNodesRequest) (*galaxyv1.SearchNodesResponse, error) {
	return &galaxyv1.SearchNodesResponse{
		Nodes:      []*galaxyv1.GalaxyNode{batch2FixtureNode()},
		TotalFound: 1,
	}, nil
}

func (s *stubBatch2GalaxyServer) GetGalaxyStats(ctx context.Context, req *galaxyv1.GetGalaxyStatsRequest) (*galaxyv1.GetGalaxyStatsResponse, error) {
	return &galaxyv1.GetGalaxyStatsResponse{
		TotalNodes:      20,
		MasteredNodes:   5,
		InProgressNodes: 7,
		NotStartedNodes: 8,
		AverageMastery:  41.5,
		NodesByType:     map[string]int32{"COSMOS": 12, "TECH": 8},
	}, nil
}

func (s *stubBatch2GalaxyServer) GetRecommendedNodes(ctx context.Context, req *galaxyv1.GetRecommendedNodesRequest) (*galaxyv1.GetRecommendedNodesResponse, error) {
	return &galaxyv1.GetRecommendedNodesResponse{
		Nodes:   []*galaxyv1.GalaxyNode{batch2FixtureNode()},
		Reasons: []string{"Predicted best next step based on your learning pattern"},
	}, nil
}

// setupBatch2Gateway spins a real gRPC server + galaxy client + gin handler
// and returns a router with the four batch-2 routes registered.
func setupBatch2Gateway(t *testing.T, register func(g *gin.RouterGroup, h *GalaxyHandler)) *httptest.Server {
	t.Helper()
	gin.SetMode(gin.TestMode)

	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	grpcServer := grpc.NewServer()
	galaxyv1.RegisterGalaxyServiceServer(grpcServer, &stubBatch2GalaxyServer{})
	go func() { _ = grpcServer.Serve(lis) }()
	t.Cleanup(grpcServer.Stop)

	galaxyClient, err := galaxy.NewClient(&config.Config{AgentAddress: lis.Addr().String()})
	if err != nil {
		t.Fatalf("galaxy.NewClient: %v", err)
	}
	t.Cleanup(func() { galaxyClient.Close() })

	// The REST fallback must NOT be hit: a hit would mean the test asserts the
	// proxy shape, not the gRPC branch shape.
	proxyBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Errorf("unexpectedly fell back to the REST proxy: %s %s", r.Method, r.URL.Path)
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{}`))
	}))
	t.Cleanup(proxyBackend.Close)

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
	register(router.Group("/api/v1/galaxy"), ginHandler)

	gateway := httptest.NewServer(router)
	t.Cleanup(gateway.Close)
	return gateway
}

func getBatch2Body(t *testing.T, url string) (int, map[string]any) {
	t.Helper()
	req, err := http.NewRequestWithContext(context.Background(), http.MethodGet, url, nil)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("GET %s: %v", url, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("GET %s returned %d (body=%s)", url, resp.StatusCode, body)
	}
	if !strings.Contains(string(body), `"via":"grpc"`) {
		t.Fatalf("GET %s body = %s, want the gRPC branch marker", url, body)
	}
	return resp.StatusCode, mustDecodeGraphBody(t, string(body))
}

// TestGetNodeDetailGPRC_EmitsRESTContractShape is the end-to-end regression:
// the node detail answered by the gRPC branch must be the nested
// KnowledgeDetailResponse shape mobile parses ({node, userStats}), not the
// flat proto shape.
func TestGetNodeDetailGPRC_EmitsRESTContractShape(t *testing.T) {
	gateway := setupBatch2Gateway(t, func(g *gin.RouterGroup, h *GalaxyHandler) {
		g.GET("/node/:id", h.GetNodeDetailGPRC)
	})
	_, payload := getBatch2Body(t, gateway.URL+"/api/v1/galaxy/node/node-9")

	node, ok := payload["node"].(map[string]any)
	if !ok {
		t.Fatalf("payload.node missing (keys=%v) — flat proto shape leaked", payloadKeys(payload))
	}
	if node["id"] != "node-9" || node["name"] != "Thermodynamics" {
		t.Fatalf("node id/name = %v/%v, want node-9/Thermodynamics", node["id"], node["name"])
	}
	userStats, ok := payload["userStats"].(map[string]any)
	if !ok {
		t.Fatalf("payload.userStats missing (keys=%v)", payloadKeys(payload))
	}
	if got, want := userStats["mastery_score"], float64(63); got != want {
		t.Fatalf("userStats.mastery_score = %v, want %v", got, want)
	}
	for _, key := range []string{"node_id", "label", "mastery"} {
		if _, ok := payload[key]; ok {
			t.Fatalf("payload leaked flat proto key %q (keys=%v)", key, payloadKeys(payload))
		}
	}
}

// TestSearchNodesGPRC_EmitsRESTContractShape: search answered by the gRPC
// branch must be SearchResponse-shaped ({query, results[].node,
// total_count}) so mobile GalaxySearchResponse.fromJson parses instead of
// throwing on the old {nodes, total_found} shape.
func TestSearchNodesGPRC_EmitsRESTContractShape(t *testing.T) {
	gateway := setupBatch2Gateway(t, func(g *gin.RouterGroup, h *GalaxyHandler) {
		g.GET("/search", h.SearchNodesGPRC)
	})
	_, payload := getBatch2Body(t, gateway.URL+"/api/v1/galaxy/search?q=thermo")

	if payload["query"] != "thermo" {
		t.Fatalf("query = %v, want thermo (mobile requires this key, no default)", payload["query"])
	}
	results, ok := payload["results"].([]any)
	if !ok || len(results) != 1 {
		t.Fatalf("results = %v, want 1-item list (mobile requires this key)", payload["results"])
	}
	item := results[0].(map[string]any)
	if _, ok := item["similarity"]; !ok {
		t.Fatalf("result item missing similarity (mobile parser has no default; keys=%v)", payloadKeys(item))
	}
	assertRESTNodeItem(t, item["node"].(map[string]any))
	if got, want := payload["total_count"], float64(1); got != want {
		t.Fatalf("total_count = %v, want %v", got, want)
	}
}

// TestGetGalaxyStatsGPRC_EmitsRESTContractShape: stats answered by the gRPC
// branch must nest counts under user_stats with REST field names.
func TestGetGalaxyStatsGPRC_EmitsRESTContractShape(t *testing.T) {
	gateway := setupBatch2Gateway(t, func(g *gin.RouterGroup, h *GalaxyHandler) {
		g.GET("/stats", h.GetGalaxyStatsGPRC)
	})
	_, payload := getBatch2Body(t, gateway.URL+"/api/v1/galaxy/stats")

	userStats, ok := payload["user_stats"].(map[string]any)
	if !ok {
		t.Fatalf("payload.user_stats missing (keys=%v) — flat proto shape leaked", payloadKeys(payload))
	}
	if got, want := userStats["unlocked_count"], float64(12); got != want {
		t.Fatalf("user_stats.unlocked_count = %v, want %v", got, want)
	}
	if got, want := userStats["mastered_count"], float64(5); got != want {
		t.Fatalf("user_stats.mastered_count = %v, want %v", got, want)
	}
}

// TestGetRecommendedGPRC_EmitsRESTNodeKeys: recommended answered by the gRPC
// branch must carry REST node keys inside nodes[].
func TestGetRecommendedGPRC_EmitsRESTNodeKeys(t *testing.T) {
	gateway := setupBatch2Gateway(t, func(g *gin.RouterGroup, h *GalaxyHandler) {
		g.GET("/predict", h.GetRecommendedGPRC)
	})
	_, payload := getBatch2Body(t, gateway.URL+"/api/v1/galaxy/predict")

	nodes, ok := payload["nodes"].([]any)
	if !ok || len(nodes) != 1 {
		t.Fatalf("nodes = %v, want 1-item list", payload["nodes"])
	}
	assertRESTNodeItem(t, nodes[0].(map[string]any))
}
