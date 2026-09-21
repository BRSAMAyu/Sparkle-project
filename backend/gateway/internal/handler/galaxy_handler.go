package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	redisv9 "github.com/redis/go-redis/v9"

	galaxyv1 "github.com/sparkle/gateway/gen/galaxy/v1"
	"github.com/sparkle/gateway/internal/galaxy"
	"github.com/sparkle/gateway/internal/service"
)

// GalaxyHandler handles HTTP requests for the Galaxy service.
// It provides authentication passthrough and rate limiting for Galaxy REST endpoints.
// High-frequency endpoints (spark, mastery) use gRPC direct calls.
// Other endpoints proxy to Python backend.
type GalaxyHandler struct {
	galaxyClient  *galaxy.Client
	galaxyCommand *service.GalaxyCommandService
	cache         *redisv9.Client
	backendURL    string
	proxy         *httputil.ReverseProxy
}

// NewGalaxyHandler creates a new GalaxyHandler.
func NewGalaxyHandler(
	galaxyClient *galaxy.Client,
	galaxyCommand *service.GalaxyCommandService,
	cache *redisv9.Client,
	backendURL string,
) (*GalaxyHandler, error) {
	targetURL, err := url.Parse(backendURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse backend URL %q: %w", backendURL, err)
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.FlushInterval = -1 // Flush immediately for SSE support
	proxy.Director = func(req *http.Request) {
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
	}

	return &GalaxyHandler{
		galaxyClient:  galaxyClient,
		galaxyCommand: galaxyCommand,
		cache:         cache,
		backendURL:    backendURL,
		proxy:         proxy,
	}, nil
}

// RegisterRoutes registers the galaxy routes with authentication and rate limiting.
func (h *GalaxyHandler) RegisterRoutes(r *gin.RouterGroup, authMiddleware gin.HandlerFunc, rateLimit gin.HandlerFunc) {
	galaxy := r.Group("/galaxy")
	galaxy.Use(authMiddleware)

	{
		// Core study interactions are part of the primary product loop.
		// The shared global limiter was causing normal taps/updates to fail with 429,
		// so keep these outside that narrow limiter and rely on auth/business checks.
		galaxy.POST("/node/:id/spark", h.SparkNode)
		galaxy.POST("/nodes/:id/spark", h.SparkNode)
		galaxy.POST("/node/:id/mastery", h.UpdateMastery)
		galaxy.POST("/nodes/:id/mastery", h.UpdateMastery)
		// route-tier: authed
		galaxy.POST("/node/:id/update-mastery", h.UpdateMastery)
		// route-tier: authed
		galaxy.POST("/nodes/:id/update-mastery", h.UpdateMastery)
		// route-tier: authed — record study session via Go CQRS
		galaxy.POST("/node/:id/study", h.RecordStudy)
		galaxy.POST("/nodes/:id/study", h.RecordStudy)

		// Read-heavy graph endpoints are used by page rendering and AI context hydration.
		// Do not put them behind the tight shared rate limiter, or normal navigation can
		// sporadically fail with 429 and break the knowledge graph experience.
		galaxy.GET("/graph", h.GetGraph)
		galaxy.GET("/contribution-stats", h.ProxyToBackend)
		// R2-08 §2.2 #22: GET /nodes removed — the engine only serves
		// POST /galaxy/nodes (the surviving sibling below).
		galaxy.POST("/nodes", h.ProxyToBackend)
		galaxy.GET("/node/:id", h.GetNodeDetailGPRC)
		galaxy.GET("/node/:id/history", h.ProxyToBackend)
		galaxy.GET("/nodes/:id", h.GetNodeDetailGPRC)
		galaxy.GET("/nodes/:id/history", h.ProxyToBackend)
		galaxy.GET("/search", h.SearchNodesGPRC)
		galaxy.POST("/search", h.SearchNodesGPRC)
		galaxy.POST("/expansion/feedback", h.ProxyToBackend)
		galaxy.GET("/review/suggestions", h.ProxyToBackend)
		galaxy.GET("/stats", h.GetGalaxyStatsGPRC)
		galaxy.GET("/heatmap", h.ProxyToBackend)
		galaxy.GET("/predict", h.GetRecommendedGPRC)
		galaxy.POST("/predict-next", h.ProxyToBackend)
		galaxy.GET("/learning-path", h.GetLearningPath)
		galaxy.GET("/node/:id/dependencies", h.GetNodeDependencies)
		galaxy.GET("/nodes/:id/dependencies", h.GetNodeDependencies)
		galaxy.POST("/node/:id/expansion/candidates", h.ProxyToBackend)
		galaxy.POST("/nodes/:id/expansion/candidates", h.ProxyToBackend)
		galaxy.POST("/node/:id/expansion/apply", h.ProxyToBackend)
		galaxy.POST("/nodes/:id/expansion/apply", h.ProxyToBackend)
		galaxy.POST("/node/:id/favorite", h.ProxyToBackend)
		galaxy.POST("/nodes/:id/favorite", h.ProxyToBackend)
		galaxy.POST("/node/:id/decay/pause", h.ProxyToBackend)
		galaxy.POST("/nodes/:id/decay/pause", h.ProxyToBackend)
		galaxy.POST("/node/:id/autolink", h.ProxyToBackend)
		galaxy.POST("/nodes/:id/autolink", h.ProxyToBackend)
		galaxy.DELETE("/node/:id/draft", h.ProxyToBackend)
		galaxy.DELETE("/nodes/:id/draft", h.ProxyToBackend)
		galaxy.PATCH("/node/:id/content", h.ProxyToBackend)
		galaxy.PATCH("/nodes/:id/content", h.ProxyToBackend)
		galaxy.POST("/vocabulary", h.ProxyToBackend)
		galaxy.POST("/nodes/viewport", h.ProxyToBackend)
		galaxy.POST("/nodes/positions", h.ProxyToBackend)
		// Document-node integration (knowledge library)
		galaxy.GET("/drafts", h.ProxyToBackend)
		galaxy.GET("/documents/:file_id/suggested-nodes", h.ProxyToBackend)
		galaxy.POST("/documents/:file_id/review-nodes", h.ProxyToBackend)
		galaxy.POST("/documents/:file_id/approve-all", h.ProxyToBackend)
		galaxy.POST("/nodes/:id/documents", h.ProxyToBackend)
		galaxy.POST("/node/:id/documents", h.ProxyToBackend)
		galaxy.DELETE("/nodes/:id/documents/:file_id", h.ProxyToBackend)
		galaxy.DELETE("/node/:id/documents/:file_id", h.ProxyToBackend)
		galaxy.POST("/documents/:file_id/move", h.ProxyToBackend)
		galaxy.GET("/nodes/:id/chunks", h.ProxyToBackend)
		galaxy.GET("/node/:id/chunks", h.ProxyToBackend)
		if rateLimit != nil {
			galaxy.GET("/events", rateLimit, h.ProxyToBackend) // SSE stream for real-time galaxy updates
			galaxy.POST("/sync", rateLimit, h.SyncGalaxy)
			galaxy.POST("/sync/mastery", rateLimit, h.ProxyToBackend)
		} else {
			galaxy.GET("/events", h.ProxyToBackend) // SSE stream for real-time galaxy updates
			galaxy.POST("/sync", h.SyncGalaxy)
			galaxy.POST("/sync/mastery", h.ProxyToBackend)
		}
	}
}

// SparkNode handles POST /galaxy/nodes/:id/spark
// Calls gRPC to update mastery (spark) a node - high performance path.
func (h *GalaxyHandler) SparkNode(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	nodeID := c.Param("id")
	if nodeID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "node_id required"})
		return
	}

	var req struct {
		StudyMinutes int    `json:"study_minutes"`
		TaskID       string `json:"task_id"`
	}
	rawBody, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "failed to read request body"})
		return
	}
	c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
	if len(bytes.TrimSpace(rawBody)) > 0 {
		if err := json.Unmarshal(rawBody, &req); err != nil {
			sanitizeErrorResponse(c, http.StatusBadRequest, err, "galaxy.spark_node.unmarshal")
			return
		}
	}
	if req.StudyMinutes <= 0 {
		req.StudyMinutes = 1
	}

	// Try gRPC RecordNodeInteraction with study_minutes / task_id in metadata.
	metadata := map[string]string{
		"study_minutes": fmt.Sprintf("%d", req.StudyMinutes),
	}
	if req.TaskID != "" {
		metadata["task_id"] = req.TaskID
	}

	if h.galaxyClient != nil {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()
		resp, grpcErr := h.galaxyClient.RecordNodeInteraction(
			ctx, userID, nodeID, "study", metadata,
		)
		if grpcErr == nil && resp != nil && resp.Success {
			c.JSON(http.StatusOK, gin.H{
				"success":       true,
				"node_id":       nodeID,
				"study_minutes": req.StudyMinutes,
				"task_id":       req.TaskID,
				"via":           "grpc",
			})
			return
		}
		log.Printf("Galaxy SparkNode gRPC failed, falling back to REST: %v", grpcErr)
	}

	// Fallback to REST proxy
	c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
	h.ProxyToBackend(c)
}

// UpdateMastery handles POST /galaxy/nodes/:id/mastery
// Direct gRPC call to update mastery.
func (h *GalaxyHandler) UpdateMastery(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	nodeID := c.Param("id")
	if nodeID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "node_id required"})
		return
	}

	var req struct {
		Mastery int    `json:"mastery"`
		Reason  string `json:"reason"`
	}
	rawBody, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "failed to read request body"})
		return
	}
	c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
	if len(bytes.TrimSpace(rawBody)) > 0 {
		if err := json.Unmarshal(rawBody, &req); err != nil {
			sanitizeErrorResponse(c, http.StatusBadRequest, err, "galaxy.update_mastery.unmarshal")
			return
		}
	}

	if h.galaxyClient == nil {
		c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
		h.ProxyToBackend(c)
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.UpdateNodeMastery(
		ctx,
		userID,
		nodeID,
		int32(req.Mastery),
		time.Now(),
		req.Reason,
	)
	if err != nil {
		log.Printf("Failed to update mastery via gRPC, falling back to proxy: %v", err)
		c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
		h.ProxyToBackend(c)
		return
	}

	if !resp.Success {
		c.JSON(http.StatusConflict, gin.H{
			"error":            resp.Reason,
			"current_revision": resp.CurrentRevision,
			"node_id":          nodeID,
		})
		return
	}

	h.invalidateGalaxyGraphCache(ctx, userID)

	c.JSON(http.StatusOK, gin.H{
		"success":     true,
		"old_mastery": resp.OldMastery,
		"new_mastery": resp.NewMastery,
		"revision":    resp.CurrentRevision,
		"node_id":     nodeID,
	})
}

// RecordStudy handles POST /galaxy/nodes/:id/study
// Records a study session for a knowledge node via Go CQRS command service.
func (h *GalaxyHandler) RecordStudy(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	nodeID := c.Param("id")
	if nodeID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "node_id required"})
		return
	}

	var req struct {
		Minutes          int     `json:"minutes"`
		PerformanceScore float64 `json:"performance_score"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}
	if req.Minutes <= 0 {
		req.Minutes = 1
	}
	if req.PerformanceScore <= 0 {
		req.PerformanceScore = 0.5
	}

	parsedUserID, err := uuid.Parse(userID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user_id"})
		return
	}
	parsedNodeID, err := uuid.Parse(nodeID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid node_id"})
		return
	}

	if h.galaxyCommand == nil {
		h.ProxyToBackend(c)
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	if err := h.galaxyCommand.RecordStudy(ctx, parsedUserID, parsedNodeID, int32(req.Minutes), req.PerformanceScore); err != nil {
		log.Printf("RecordStudy CQRS failed for node %s user %s: %v", nodeID, hashUserIDForLog(userID), err)
		h.ProxyToBackend(c)
		return
	}

	h.invalidateGalaxyGraphCache(ctx, userID)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"node_id": nodeID,
		"minutes": req.Minutes,
		"via":     "cqrs",
	})
}

func (h *GalaxyHandler) invalidateGalaxyGraphCache(ctx context.Context, userID string) {
	if h.cache == nil || userID == "" {
		return
	}

	if err := h.cache.Del(ctx, "galaxy:graph:"+userID).Err(); err != nil {
		log.Printf("Failed to delete galaxy cache key for user %s: %v", hashUserIDForLog(userID), err)
	}

	pattern := "*:view:get_galaxy_graph:" + userID + ":*"
	iter := h.cache.Scan(ctx, 0, pattern, 0).Iterator()
	var keys []string
	for iter.Next(ctx) {
		keys = append(keys, iter.Val())
	}
	if err := iter.Err(); err != nil {
		log.Printf("Failed to scan galaxy cache pattern for user %s: %v", hashUserIDForLog(userID), err)
		return
	}
	if len(keys) == 0 {
		return
	}
	if err := h.cache.Del(ctx, keys...).Err(); err != nil {
		log.Printf("Failed to delete galaxy cache pattern for user %s: %v", hashUserIDForLog(userID), err)
	}
}

// GetNodeDetailGPRC handles GET /galaxy/node/:id via gRPC with REST fallback.
func (h *GalaxyHandler) GetNodeDetailGPRC(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	nodeID := c.Param("id")
	if nodeID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "node_id required"})
		return
	}
	if h.galaxyClient != nil {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()
		resp, err := h.galaxyClient.GetNodeDetail(ctx, userID, nodeID)
		if err == nil && resp != nil {
			// GW-SHAPE-BATCH2: outbound REST contract shape (KnowledgeDetailResponse),
			// not the flat proto shape.
			c.JSON(http.StatusOK, galaxyNodeDetailRESTPayload(resp))
			return
		}
		log.Printf("Galaxy GetNodeDetail gRPC failed, falling back to REST: %v", err)
	}
	h.ProxyToBackend(c)
}

// SearchNodesGPRC handles GET/POST /galaxy/search via gRPC with REST fallback.
func (h *GalaxyHandler) SearchNodesGPRC(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	if h.galaxyClient == nil {
		h.ProxyToBackend(c)
		return
	}

	query := c.Query("q")
	if query == "" {
		// Try JSON body
		var body struct {
			Query string `json:"query"`
			Limit int32  `json:"limit"`
		}
		rawBody, _ := io.ReadAll(io.LimitReader(c.Request.Body, 64*1024))
		c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
		if len(rawBody) > 0 {
			if err := json.Unmarshal(rawBody, &body); err != nil {
				log.Printf("SearchNodes JSON unmarshal fallback failed: %v", err)
			}
			query = body.Query
		}
	}
	if query == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "query required"})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()
	resp, err := h.galaxyClient.SearchNodes(ctx, userID, query, 20)
	if err == nil && resp != nil {
		// GW-SHAPE-BATCH2: outbound REST contract shape (SearchResponse),
		// not {nodes, total_found}.
		c.JSON(http.StatusOK, galaxySearchRESTPayload(query, resp))
		return
	}
	log.Printf("Galaxy SearchNodes gRPC failed, falling back to REST: %v", err)

	h.ProxyToBackend(c)
}

// GetGalaxyStatsGPRC handles GET /galaxy/stats via gRPC with REST fallback.
func (h *GalaxyHandler) GetGalaxyStatsGPRC(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	if h.galaxyClient != nil {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()
		resp, err := h.galaxyClient.GetGalaxyStats(ctx, userID)
		if err == nil && resp != nil {
			// GW-SHAPE-BATCH2: outbound REST contract shape
			// ({"user_stats": ...}), not the flat proto keys.
			c.JSON(http.StatusOK, galaxyStatsRESTPayload(resp))
			return
		}
		log.Printf("Galaxy GetGalaxyStats gRPC failed, falling back to REST: %v", err)
	}
	h.ProxyToBackend(c)
}

// GetRecommendedGPRC handles GET /galaxy/predict via gRPC with REST fallback.
func (h *GalaxyHandler) GetRecommendedGPRC(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	if h.galaxyClient != nil {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()
		resp, err := h.galaxyClient.GetRecommendedNodes(ctx, userID, 10)
		if err == nil && resp != nil {
			// GW-SHAPE-BATCH2: node items re-spelled to REST contract keys;
			// see galaxyRecommendedRESTPayload for the cardinality note.
			c.JSON(http.StatusOK, galaxyRecommendedRESTPayload(resp))
			return
		}
		log.Printf("Galaxy GetRecommendedNodes gRPC failed, falling back to REST: %v", err)
	}
	h.ProxyToBackend(c)
}

// GetGraph handles GET /galaxy/graph via gRPC with REST fallback.
func (h *GalaxyHandler) GetGraph(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	if h.galaxyClient != nil {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()

		resp, err := h.galaxyClient.GetUserGalaxy(ctx, userID)
		if err == nil && resp != nil {
			c.JSON(http.StatusOK, galaxyGraphRESTPayload(resp))
			return
		}
		log.Printf("Galaxy GetGraph gRPC failed, falling back to REST: %v", err)
	}

	h.ProxyToBackend(c)
}

// galaxyGraphRESTPayload maps the engine's gRPC GetUserGalaxyResponse
// (proto GalaxyNode/GalaxyEdge shape) into the JSON shape of the engine's
// REST contract (backend/app/schemas/galaxy.py: GalaxyGraphResponse /
// NodeWithStatus / NodeRelationInfo) — the shape the mobile client parses.
//
// GW-GRAPH-SHAPE: the gRPC branch used to marshal the proto messages
// directly (node_id/label/mastery + source_id/target_id/relation), which
// diverged from the REST contract keys (id/name/mastery_score +
// source_node_id/target_node_id/relation_type). On first load answered by
// gRPC the client defensively parsed missing id/name into empty strings and
// rendered an empty universe (V24). Both branches now speak the same
// outbound contract; value semantics are already aligned upstream because
// the engine's gRPC servicer derives its payload from the same
// get_galaxy_graph source as REST (relation values pass through unchanged).
//
// Note: explicit mapping always emits the REST keys even when the proto
// value is zero/empty, avoiding the generated `json:"...,omitempty"` trap
// where e.g. mastery=0 would silently drop the key.
func galaxyGraphRESTPayload(resp *galaxyv1.GetUserGalaxyResponse) gin.H {
	nodes := make([]gin.H, 0, len(resp.GetNodes()))
	for _, node := range resp.GetNodes() {
		nodes = append(nodes, galaxyNodeRESTPayload(node))
	}
	edges := make([]gin.H, 0, len(resp.GetEdges()))
	for _, edge := range resp.GetEdges() {
		edges = append(edges, gin.H{
			"source_node_id": edge.GetSourceId(),
			"target_node_id": edge.GetTargetId(),
			"relation_type":  edge.GetRelation(),
		})
	}
	return gin.H{
		"nodes": nodes,
		// REST GalaxyGraphResponse carries both aliases; the client reads
		// `edges` first and falls back to `relations`.
		"edges":       edges,
		"relations":   edges,
		"total_nodes": resp.GetTotalNodes(),
		"via":         "grpc",
	}
}

// galaxyNodeRESTPayload maps a proto GalaxyNode into the REST node keys the
// mobile client parses (GalaxyNodeModel reads id/name/mastery_score; the
// FIX-52/V24-B fallbacks for node_id/label/mastery stay as client-side
// defense only — the gateway no longer relies on them).
//
// GW-GRAPH-SHAPE (FIX-53 follow-up, batch 2): shared by the GetGraph,
// SearchNodes and GetRecommendedNodes outbound payloads so every galaxy
// response speaks one node shape.
//
// node_type/tags are proto-only provenance keys (no direct REST counterpart
// in GalaxyGraphResponse/NodeBase context); kept as a harmless superset,
// same call as FIX-53.
func galaxyNodeRESTPayload(node *galaxyv1.GalaxyNode) gin.H {
	return gin.H{
		"id":            node.GetNodeId(),
		"name":          node.GetLabel(),
		"mastery_score": node.GetMastery(),
		"node_type":     node.GetNodeType(),
		"tags":          node.GetTags(),
	}
}

// galaxyNodeDetailRESTPayload maps the engine's gRPC GetNodeDetailResponse
// (flat proto shape) into the JSON shape of the engine's REST contract
// (backend/app/api/v1/galaxy.py get_node_detail → the Flutter
// KnowledgeDetailResponse shape: {node: {...}, userStats: {...}, relations,
// ...} — mobile parses KnowledgeDetailResponse.fromJson).
//
// GW-SHAPE-BATCH2: the gRPC branch used to pass the flat proto keys through
// (node_id/label/mastery/...), so mobile json['node'] resolved to null and
// node detail answered by gRPC failed to parse outright.
//
// Value provenance is aligned upstream: the engine's gRPC servicer fills
// label=node.name, node_type=node.source_type, tags=node.keywords,
// parent_ids=[node.parent_id], mastery=int(knowledge_stats.mastery_score) —
// the same DB fields the REST route emits as name/source_type/keywords/
// parent_id/userStats.mastery_score. Only key names are re-spelled here.
//
// Skipped on purpose (proto carries no counterpart; the mobile model defaults
// them, so emitting nothing is contract-honest):
//   - relations / source_documents / knowledge_stats / relatedTasks /
//     relatedPlans / learningPathSnapshot (client defaults to empty)
//   - userStats.total_study_minutes / study_count / is_unlocked /
//     is_favorite / last_study_at / next_review_at / decay_paused
//
// Note: explicit mapping always emits the REST keys even when the proto value
// is zero/empty, avoiding the generated `json:"...,omitempty"` trap.
func galaxyNodeDetailRESTPayload(resp *galaxyv1.GetNodeDetailResponse) gin.H {
	// REST emits parent_id as null when absent; the servicer stores the single
	// parent as parent_ids[0] (empty slice otherwise), so this reconstruction
	// is exact.
	var parentID any
	if ids := resp.GetParentIds(); len(ids) > 0 {
		parentID = ids[0]
	}
	return gin.H{
		"node": gin.H{
			"id":          resp.GetNodeId(),
			"name":        resp.GetLabel(),
			"description": resp.GetDescription(),
			// engine servicer: tags = node.keywords (same provenance as REST
			// node_dict["keywords"]).
			"keywords": resp.GetTags(),
			// engine servicer: node_type = node.source_type (same provenance
			// as REST node_dict["source_type"]).
			"source_type": resp.GetNodeType(),
			"parent_id":   parentID,
		},
		"userStats": gin.H{
			// int32 truncation of the REST float happens upstream in the
			// engine servicer; the gateway passes the value through verbatim.
			"mastery_score": resp.GetMastery(),
		},
		"via": "grpc",
	}
}

// galaxySearchRESTPayload maps the engine's gRPC SearchNodesResponse into the
// JSON shape of the engine's REST contract (backend/app/schemas/galaxy.py
// SearchResponse: {query, results: [{node, similarity, user_status}],
// total_count} — mobile parses GalaxySearchResponse.fromJson).
//
// GW-SHAPE-BATCH2: the gRPC branch used to emit {nodes: [proto GalaxyNode],
// total_found}; mobile requires json['query'] (String, no default) and
// results[].node, so search answered by gRPC threw on parse and silently
// degraded to an empty result list.
//
// Deliberate deviation, flagged: proto SearchNodesResponse carries no
// similarity score and the mobile parser has NO default for it
// (`(json['similarity'] as num).toDouble()` throws when missing). Skipping
// the key would keep the endpoint unparseable, so we emit a neutral 0.0
// placeholder — no ranking signal is invented (result order is exactly the
// engine's ranking); carrying the real score needs a proto extension
// (registered as follow-up in v3-output/GW-SHAPE-BATCH2/REPORT.md).
func galaxySearchRESTPayload(query string, resp *galaxyv1.SearchNodesResponse) gin.H {
	results := make([]gin.H, 0, len(resp.GetNodes()))
	for _, node := range resp.GetNodes() {
		results = append(results, gin.H{
			"node": galaxyNodeRESTPayload(node),
			// See doc comment: neutral placeholder, key required by client.
			"similarity": 0.0,
		})
	}
	return gin.H{
		// Echo the request's own query back, exactly what the engine's REST
		// SearchResponse.query carries.
		"query":       query,
		"results":     results,
		"total_count": resp.GetTotalFound(),
		"via":         "grpc",
	}
}

// galaxyStatsRESTPayload maps the engine's gRPC GetGalaxyStatsResponse into
// the JSON shape of the engine's REST contract (backend/app/api/v1/galaxy.py
// get_galaxy_stats → {"user_stats": <GalaxyUserStats>, "decay_stats": ...}).
//
// GW-SHAPE-BATCH2: the gRPC branch used to emit the flat proto keys
// (mastered_nodes/in_progress_nodes/nodes_by_type/...) at top level, which
// matches no REST key.
//
// Value provenance: the engine servicer derives its payload from the same
// GalaxyStatsService.calculate_user_stats the REST route serves, and copies
// stats.sector_distribution verbatim into nodes_by_type. unlocked_count is
// not a proto field but is reconstructed exactly: the servicer defines
// in_progress = max(0, unlocked - mastered), so unlocked = mastered +
// in_progress holds by construction (modulo the max(0,·) clamp on anomalous
// data).
//
// Skipped on purpose: decay_stats, user_stats.total_study_minutes /
// streak_days (proto carries no counterpart). average_mastery is a proto-only
// extra (engine P1-8 computation) kept as a harmless superset. No mobile
// consumer exists for GET /galaxy/stats (verified by grep); the alignment
// keeps the gateway honest to the REST contract for any consumer.
func galaxyStatsRESTPayload(resp *galaxyv1.GetGalaxyStatsResponse) gin.H {
	return gin.H{
		"user_stats": gin.H{
			"total_nodes":    resp.GetTotalNodes(),
			"mastered_count": resp.GetMasteredNodes(),
			"unlocked_count": resp.GetMasteredNodes() + resp.GetInProgressNodes(),
			// provenance-identical: engine servicer copies
			// calculate_user_stats().sector_distribution into nodes_by_type.
			"sector_distribution": resp.GetNodesByType(),
			// proto-only extra (P1-8 real average), harmless superset.
			"average_mastery": resp.GetAverageMastery(),
		},
		"via": "grpc",
	}
}

// galaxyRecommendedRESTPayload maps the engine's gRPC GetRecommendedNodesResponse
// into REST node keys for GET /galaxy/predict.
//
// GW-SHAPE-BATCH2: the gRPC branch used to marshal proto GalaxyNode items
// inline (node_id/label/mastery). There is NO engine REST route for
// GET /galaxy/predict — the REST fallback 404s, so this gRPC branch is the
// only live path — and the closest REST sibling (POST /predict-next →
// NodeDetailResponse) is single-node while the proto payload is a list. The
// honest alignment is therefore at the node-item level: reuse the shared
// REST node keys. Top-level `nodes` cardinality and `reasons` (proto-only,
// no REST counterpart) are kept verbatim and flagged in the batch report.
func galaxyRecommendedRESTPayload(resp *galaxyv1.GetRecommendedNodesResponse) gin.H {
	nodes := make([]gin.H, 0, len(resp.GetNodes()))
	for _, node := range resp.GetNodes() {
		nodes = append(nodes, galaxyNodeRESTPayload(node))
	}
	return gin.H{
		"nodes":   nodes,
		"reasons": resp.GetReasons(),
		"via":     "grpc",
	}
}

// SyncGalaxy handles POST /galaxy/sync
// Direct gRPC call for collaborative CRDT galaxy sync.
func (h *GalaxyHandler) SyncGalaxy(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	var req struct {
		GalaxyID      string          `json:"galaxy_id"`
		PartialUpdate json.RawMessage `json:"partial_update"`
	}
	rawBody, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "failed to read request body"})
		return
	}
	c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
	if len(bytes.TrimSpace(rawBody)) > 0 {
		if err := json.Unmarshal(rawBody, &req); err != nil {
			sanitizeErrorResponse(c, http.StatusBadRequest, err, "galaxy.sync.unmarshal")
			return
		}
	}

	if h.galaxyClient == nil {
		c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
		h.ProxyToBackend(c)
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.SyncCollaborativeGalaxy(ctx, req.GalaxyID, req.PartialUpdate, userID)
	if err != nil {
		log.Printf("Failed to sync galaxy via gRPC, falling back to proxy: %v", err)
		c.Request.Body = io.NopCloser(bytes.NewReader(rawBody))
		h.ProxyToBackend(c)
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success":       resp.Success,
		"server_update": resp.ServerUpdate,
		"via":           "grpc",
	})
}

// GetLearningPath handles GET /galaxy/learning-path
// Returns the recommended learning path between two nodes via gRPC.
func (h *GalaxyHandler) GetLearningPath(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	if h.galaxyClient == nil {
		h.ProxyToBackend(c)
		return
	}

	fromNodeID := c.Query("from")
	toNodeID := c.Query("to")
	if fromNodeID == "" || toNodeID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "from and to query params required"})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.GetLearningPath(ctx, userID, fromNodeID, toNodeID)
	if err == nil && resp != nil {
		c.JSON(http.StatusOK, gin.H{
			"node_ids":   resp.NodeIds,
			"edges":      resp.Edges,
			"path_found": resp.PathFound,
			"via":        "grpc",
		})
		return
	}
	log.Printf("Galaxy GetLearningPath gRPC failed, falling back to REST: %v", err)

	h.ProxyToBackend(c)
}

// GetNodeDependencies handles GET /galaxy/node/:id/dependencies
// Returns node prerequisites and dependents via gRPC.
func (h *GalaxyHandler) GetNodeDependencies(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	// SEC-3: the engine's gRPC servicers require the gateway-injected
	// `user-id` metadata (plus Bearer token); without it the call is
	// rejected 401 and silently degrades to the REST proxy.
	injectAuthContext(c)

	if h.galaxyClient == nil {
		h.ProxyToBackend(c)
		return
	}

	nodeID := c.Param("id")
	if nodeID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "node_id required"})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.GetNodeDependencies(ctx, userID, nodeID)
	if err == nil && resp != nil {
		c.JSON(http.StatusOK, gin.H{
			"prerequisite_ids": resp.PrerequisiteIds,
			"dependent_ids":    resp.DependentIds,
			"via":              "grpc",
		})
		return
	}
	log.Printf("Galaxy GetNodeDependencies gRPC failed, falling back to REST: %v", err)

	h.ProxyToBackend(c)
}

// ProxyToBackend proxies requests to the Python backend.
func (h *GalaxyHandler) ProxyToBackend(c *gin.Context) {
	if h.proxy == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "backend proxy not configured"})
		return
	}

	// Add user context headers for backend
	userID := c.GetString("user_id")
	if userID != "" {
		c.Request.Header.Set("X-User-ID", userID)
	}

	// Preserve auth token - try both stored token and original Authorization header
	if token := c.GetString("auth_token"); token != "" {
		c.Request.Header.Set("Authorization", "Bearer "+token)
	} else if auth := c.GetHeader("Authorization"); auth != "" {
		// Keep original Authorization header if auth_token not set
		c.Request.Header.Set("Authorization", auth)
	}

	h.proxy.ServeHTTP(c.Writer, c.Request)
}
