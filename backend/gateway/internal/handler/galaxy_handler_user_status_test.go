package handler

// GRAPH-GRPC-SHAPE contract tests: the gateway's gRPC-first GetGraph branch
// must carry the per-node user_status block to the client in the REST shape.
//
// Breakage this pins: the proto GalaxyNode (proto/galaxy_service.proto) only
// carried node_id/label/node_type/mastery(int32)/tags — the whole per-user
// status structure (UserStatusInfo in backend/app/schemas/galaxy.py) had no
// proto counterpart, so every /api/v1/galaxy/graph answered through the
// gateway dropped user_status entirely. Mobile (GalaxyNodeModel.fromJson,
// mobile/lib/shared/entities/galaxy_model.dart) reads 10 fields out of
// user_status (is_unlocked/study_count/review signals/...) and silently
// defaulted them — unlocked nodes rendered locked, review urgency vanished.
// The REST face (:8000) was unaffected, so the two paths diverged for the
// same user at the same moment.
//
// The 10-key list below is transcribed from GalaxyNodeModel.fromJson
// (userStatus?['…'] reads) and MUST stay in lockstep with that parser.

import (
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/timestamppb"

	galaxyv1 "github.com/sparkle/gateway/gen/galaxy/v1"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/galaxy"
)

// mobileUserStatusKeys — every key mobile reads out of node["user_status"],
// per mobile/lib/shared/entities/galaxy_model.dart GalaxyNodeModel.fromJson:
//
//	is_unlocked, mastery_score, study_count, recent_error_count,
//	review_urgency_score, is_review_recommended, review_urgency_reason,
//	mastery_last_updated_at, days_since_mastery_update, first_unlock_at
var mobileUserStatusKeys = []string{
	"is_unlocked",
	"mastery_score",
	"study_count",
	"recent_error_count",
	"review_urgency_score",
	"is_review_recommended",
	"review_urgency_reason",
	"mastery_last_updated_at",
	"days_since_mastery_update",
	"first_unlock_at",
}

// TestGalaxyNodeRESTPayload_EmitsUserStatusContract: when the engine servicer
// fills a node's user_status, the shared node mapper must surface a
// user_status block speaking the REST keys mobile parses — all ten of them.
func TestGalaxyNodeRESTPayload_EmitsUserStatusContract(t *testing.T) {
	node := &galaxyv1.GalaxyNode{NodeId: "node-1", Label: "命题逻辑", Mastery: 25, UserStatus: userStatusFixture()}
	raw, err := json.Marshal(galaxyNodeRESTPayload(node))
	if err != nil {
		t.Fatalf("marshal node payload: %v", err)
	}
	var decoded map[string]any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatalf("decode node payload: %v (%s)", err, raw)
	}

	us, ok := decoded["user_status"].(map[string]any)
	if !ok {
		t.Fatalf("node payload has no user_status object (keys=%v) — gateway gRPC path drops per-node user_status; mobile defaults is_unlocked=false and loses every review signal", payloadKeys(decoded))
	}
	for _, key := range mobileUserStatusKeys {
		if _, ok := us[key]; !ok {
			t.Fatalf("user_status missing mobile-consumed key %q (keys=%v)", key, payloadKeys(us))
		}
	}
}

// userStatusFixture mirrors the REST UserStatusInfo the engine serves for an
// active node; values chosen to catch int truncation (mastery 25.5, urgency
// 0.75) and timestamp reformatting.
func userStatusFixture() *galaxyv1.GalaxyNodeUserStatus {
	return &galaxyv1.GalaxyNodeUserStatus{
		MasteryScore:           25.5,
		IsUnlocked:             true,
		StudyCount:             7,
		RecentErrorCount:       2,
		ReviewUrgencyScore:     0.75,
		IsReviewRecommended:    true,
		ReviewUrgencyReason:    "3 days since last mastery update",
		DaysSinceMasteryUpdate: 3.5,
		MasteryLastUpdatedAt:   timestamppb.New(time.Date(2026, 9, 19, 12, 30, 0, 0, time.UTC)),
		FirstUnlockAt:          timestamppb.New(time.Date(2026, 9, 10, 8, 0, 0, 0, time.UTC)),
	}
}

// TestGalaxyNodeRESTPayload_UserStatusValuesSurvive: mapping is value-faithful
// (double precision kept, timestamps re-spelled to ISO strings, absent reason
// → null) — the same user on the REST face and the gateway face must see the
// same numbers.
func TestGalaxyNodeRESTPayload_UserStatusValuesSurvive(t *testing.T) {
	node := &galaxyv1.GalaxyNode{NodeId: "node-1", Label: "命题逻辑", Mastery: 25, UserStatus: userStatusFixture()}
	raw, err := json.Marshal(galaxyNodeRESTPayload(node))
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var decoded map[string]any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatalf("decode: %v (%s)", err, raw)
	}
	us, ok := decoded["user_status"].(map[string]any)
	if !ok {
		t.Fatalf("user_status missing after mapping (%s)", raw)
	}

	if got := us["mastery_score"]; got != 25.5 {
		t.Fatalf("user_status.mastery_score = %v, want 25.5 (int32 truncation must not resurface)", got)
	}
	for key, want := range map[string]any{
		"is_unlocked":               true,
		"study_count":               float64(7),
		"recent_error_count":        float64(2),
		"review_urgency_score":      0.75,
		"is_review_recommended":     true,
		"review_urgency_reason":     "3 days since last mastery update",
		"days_since_mastery_update": 3.5,
	} {
		if got := us[key]; got != want {
			t.Fatalf("user_status.%s = %v, want %v", key, got, want)
		}
	}
	if got := us["mastery_last_updated_at"]; got != "2026-09-19T12:30:00Z" {
		t.Fatalf("user_status.mastery_last_updated_at = %v, want an ISO instant mobile DateTime.tryParse accepts", got)
	}
	if got := us["first_unlock_at"]; got != "2026-09-10T08:00:00Z" {
		t.Fatalf("user_status.first_unlock_at = %v, want an ISO instant", got)
	}
}

// TestGalaxyNodeRESTPayload_NilUserStatusEmitsNull: REST serves
// user_status=null for nodes without personal signal; the gateway must emit
// the key with null, not a zeroed block (which would read as "locked" rather
// than "no signal") and not a missing key (branch-shape divergence).
func TestGalaxyNodeRESTPayload_NilUserStatusEmitsNull(t *testing.T) {
	raw, err := json.Marshal(galaxyNodeRESTPayload(&galaxyv1.GalaxyNode{NodeId: "node-9"}))
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var node map[string]any
	if err := json.Unmarshal(raw, &node); err != nil {
		t.Fatalf("decode: %v (%s)", err, raw)
	}
	got, ok := node["user_status"]
	if !ok {
		t.Fatalf("user_status key missing entirely (keys=%v) — gRPC branch would diverge from REST null", payloadKeys(node))
	}
	if got != nil {
		t.Fatalf("user_status = %v, want null for a status-less node", got)
	}
}

// TestGalaxyUserStatusRESTPayload_EmptyReasonEmitsNull pins the ""→null
// re-spell (proto has no presence for optional strings; REST nulls them).
func TestGalaxyUserStatusRESTPayload_EmptyReasonEmitsNull(t *testing.T) {
	raw, err := json.Marshal(galaxyUserStatusRESTPayload(&galaxyv1.GalaxyNodeUserStatus{MasteryScore: 10}))
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var us map[string]any
	if err := json.Unmarshal(raw, &us); err != nil {
		t.Fatalf("decode: %v (%s)", err, raw)
	}
	if got := us["review_urgency_reason"]; got != nil {
		t.Fatalf("review_urgency_reason = %v, want null when the proto string is empty", got)
	}
}

// stubUserStatusGraphServer serves a fixture GetUserGalaxyResponse carrying a
// per-node user_status so the end-to-end test exercises the real handler.
type stubUserStatusGraphServer struct {
	galaxyv1.UnimplementedGalaxyServiceServer

	resp *galaxyv1.GetUserGalaxyResponse
}

func (s *stubUserStatusGraphServer) GetUserGalaxy(ctx context.Context, req *galaxyv1.GetUserGalaxyRequest) (*galaxyv1.GetUserGalaxyResponse, error) {
	return s.resp, nil
}

// TestGetGraph_GRPCBranch_EquivalentToRESTUserStatus is the end-to-end red/
// green regression for the true endpoint break: GET /api/v1/galaxy/graph
// answered by the gateway's gRPC branch must expose the same per-node
// user_status the REST direct face serves — every mobile-consumed field
// present, mastery_score at double precision.
func TestGetGraph_GRPCBranch_EquivalentToRESTUserStatus(t *testing.T) {
	gin.SetMode(gin.TestMode)

	resp := &galaxyv1.GetUserGalaxyResponse{
		UserId: "user-42",
		Nodes: []*galaxyv1.GalaxyNode{
			{NodeId: "node-1", Label: "命题逻辑", NodeType: "concept", Mastery: 25, UserStatus: userStatusFixture()},
			{NodeId: "node-2", Label: "锁住的概念", NodeType: "concept"}, // no status → REST null
		},
		TotalNodes: 2,
	}

	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	grpcServer := grpc.NewServer()
	galaxyv1.RegisterGalaxyServiceServer(grpcServer, &stubUserStatusGraphServer{resp: resp})
	go func() { _ = grpcServer.Serve(lis) }()
	defer grpcServer.Stop()

	galaxyClient, err := galaxy.NewClient(&config.Config{AgentAddress: lis.Addr().String()})
	if err != nil {
		t.Fatalf("galaxy.NewClient: %v", err)
	}
	defer galaxyClient.Close()

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

	httpResp, err := http.Get(gateway.URL + "/api/v1/galaxy/graph")
	if err != nil {
		t.Fatalf("GET /graph: %v", err)
	}
	defer httpResp.Body.Close()
	body, err := io.ReadAll(httpResp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	if httpResp.StatusCode != http.StatusOK {
		t.Fatalf("GET /graph returned %d, want 200 (body=%s)", httpResp.StatusCode, body)
	}
	if !strings.Contains(string(body), `"via":"grpc"`) {
		t.Fatalf("GET /graph body = %s, want the gRPC branch marker", body)
	}

	var payload struct {
		Nodes []struct {
			ID         string         `json:"id"`
			UserStatus map[string]any `json:"user_status"`
		} `json:"nodes"`
	}
	if err := json.Unmarshal(body, &payload); err != nil {
		t.Fatalf("decode body: %v (%s)", err, body)
	}
	if len(payload.Nodes) != 2 {
		t.Fatalf("nodes = %d, want 2 (%s)", len(payload.Nodes), body)
	}

	unlocked := payload.Nodes[0]
	if unlocked.UserStatus == nil {
		t.Fatalf("gateway path still drops user_status for unlocked node (%s)", body)
	}
	for _, key := range mobileUserStatusKeys {
		if _, ok := unlocked.UserStatus[key]; !ok {
			t.Fatalf("gateway path user_status missing mobile-consumed key %q (keys=%v)", key, payloadKeys(unlocked.UserStatus))
		}
	}
	if unlocked.UserStatus["mastery_score"] != 25.5 {
		t.Fatalf("gateway mastery_score = %v, want 25.0-scale double equal to the REST face", unlocked.UserStatus["mastery_score"])
	}

	locked := payload.Nodes[1]
	if locked.UserStatus != nil {
		t.Fatalf("status-less node user_status = %v, want null (REST parity)", locked.UserStatus)
	}
}
