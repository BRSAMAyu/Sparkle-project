package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	cqrsEvent "github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	cqrsWorker "github.com/sparkle/gateway/internal/cqrs/worker"
	"github.com/sparkle/gateway/internal/db"
	"go.uber.org/zap"
)

const (
	// GalaxyStreamKey is the Redis stream for galaxy events.
	GalaxyStreamKey = "cqrs:stream:galaxy"
	// GalaxyConsumerGroup is the consumer group for galaxy projection.
	GalaxyConsumerGroup = "galaxy_projection_group"
)

// NodeView represents the read model for a knowledge node.
type NodeView struct {
	ID              string     `json:"id"`
	Name            string     `json:"name"`
	NameEn          string     `json:"name_en,omitempty"`
	Description     string     `json:"description,omitempty"`
	Keywords        []string   `json:"keywords,omitempty"`
	ImportanceLevel int32      `json:"importance_level"`
	IsSeed          bool       `json:"is_seed"`
	ParentID        string     `json:"parent_id,omitempty"`
	SubjectID       int32      `json:"subject_id,omitempty"`
	ChildCount      int        `json:"child_count"`
	CreatedAt       time.Time  `json:"created_at"`
}

// UserNodeView represents a user's progress on a knowledge node.
type UserNodeView struct {
	NodeID           string     `json:"node_id"`
	UserID           string     `json:"user_id"`
	MasteryScore     float64    `json:"mastery_score"`
	TotalMinutes     int32      `json:"total_minutes"`
	StudyCount       int32      `json:"study_count"`
	IsUnlocked       bool       `json:"is_unlocked"`
	IsCollapsed      bool       `json:"is_collapsed"`
	IsFavorite       bool       `json:"is_favorite"`
	LastStudyAt      *time.Time `json:"last_study_at,omitempty"`
	NextReviewAt     *time.Time `json:"next_review_at,omitempty"`
	FirstUnlockAt    *time.Time `json:"first_unlock_at,omitempty"`
	UpdatedAt        time.Time  `json:"updated_at"`
}

// UserGalaxyStats represents aggregated galaxy statistics for a user.
type UserGalaxyStats struct {
	UserID            string  `json:"user_id"`
	TotalNodes        int     `json:"total_nodes"`
	UnlockedNodes     int     `json:"unlocked_nodes"`
	MasteredNodes     int     `json:"mastered_nodes"` // mastery_score >= 0.8
	TotalStudyMinutes int     `json:"total_study_minutes"`
	AverageMastery    float64 `json:"average_mastery"`
}

// GalaxySyncWorker synchronizes galaxy events to Redis read models.
type GalaxySyncWorker struct {
	baseWorker *cqrsWorker.BaseWorker
	redis      *redis.Client
	queries    *db.Queries
	pool       *pgxpool.Pool
	logger     *zap.Logger
}

// GalaxySyncWorkerConfig configures the galaxy sync worker.
type GalaxySyncWorkerConfig struct {
	ConsumerName string
	Options      cqrsWorker.WorkerOptions
}

// DefaultGalaxySyncWorkerConfig returns sensible defaults.
func DefaultGalaxySyncWorkerConfig() GalaxySyncWorkerConfig {
	return GalaxySyncWorkerConfig{
		ConsumerName: "galaxy_worker_1",
		Options:      cqrsWorker.DefaultWorkerOptions(),
	}
}

// NewGalaxySyncWorker creates a new galaxy sync worker.
func NewGalaxySyncWorker(
	rdb *redis.Client,
	pool *pgxpool.Pool,
	cqrsMetrics *metrics.CQRSMetrics,
	logger *zap.Logger,
	config ...GalaxySyncWorkerConfig,
) *GalaxySyncWorker {
	cfg := DefaultGalaxySyncWorkerConfig()
	if len(config) > 0 {
		cfg = config[0]
	}

	queries := db.New(pool)
	processedEvents := outbox.NewProcessedEventsRepository(pool)

	baseWorker := cqrsWorker.NewBaseWorker(
		rdb,
		processedEvents,
		cqrsMetrics,
		logger,
		GalaxyStreamKey,
		GalaxyConsumerGroup,
		cfg.ConsumerName,
		cfg.Options,
	)

	return &GalaxySyncWorker{
		baseWorker: baseWorker,
		redis:      rdb,
		queries:    queries,
		pool:       pool,
		logger:     logger.Named("galaxy-sync"),
	}
}

// Run starts the worker. Blocks until context is cancelled.
func (w *GalaxySyncWorker) Run(ctx context.Context) error {
	return w.baseWorker.Run(ctx, w.handleEvent)
}

// IsRunning returns true if the worker is currently running.
func (w *GalaxySyncWorker) IsRunning() bool {
	return w.baseWorker.IsRunning()
}

// handleEvent processes a single galaxy event.
func (w *GalaxySyncWorker) handleEvent(ctx context.Context, evt cqrsEvent.DomainEvent, messageID string) error {
	switch evt.Type {
	case cqrsEvent.EventNodeCreated:
		return w.handleNodeCreated(ctx, evt)
	case cqrsEvent.EventNodeUnlocked:
		return w.handleNodeUnlocked(ctx, evt)
	case cqrsEvent.EventNodeExpanded:
		return w.handleNodeExpanded(ctx, evt)
	case cqrsEvent.EventMasteryUpdated:
		return w.handleMasteryUpdated(ctx, evt)
	case cqrsEvent.EventRelationCreated:
		return w.handleRelationCreated(ctx, evt)
	case cqrsEvent.EventStudyRecordAdded:
		return w.handleStudyRecordAdded(ctx, evt)
	default:
		w.logger.Debug("Ignoring unhandled event type",
			zap.String("event_type", string(evt.Type)),
			zap.String("event_id", evt.ID),
		)
		return nil
	}
}

// handleNodeCreated processes a NodeCreated event.
func (w *GalaxySyncWorker) handleNodeCreated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	nodeID, err := uuid.Parse(nodeIDStr)
	if err != nil {
		return fmt.Errorf("invalid node_id: %w", err)
	}

	// Fetch node from database
	node, err := w.getNode(ctx, nodeID)
	if err != nil {
		return fmt.Errorf("fetch node: %w", err)
	}

	// Build view model
	view := w.buildNodeView(node)

	viewJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal view: %w", err)
	}

	// Update Redis
	pipe := w.redis.Pipeline()

	// Node view
	pipe.Set(ctx, "galaxy:node:"+nodeIDStr, viewJSON, 0)

	// Add to global node set (for graph queries)
	pipe.SAdd(ctx, "galaxy:nodes:all", nodeIDStr)

	// If it has a parent, add to parent's children set
	if node.ParentID.Valid {
		parentID, _ := uuid.FromBytes(node.ParentID.Bytes[:])
		pipe.SAdd(ctx, "galaxy:node:children:"+parentID.String(), nodeIDStr)
		// Increment parent's child count
		pipe.HIncrBy(ctx, "galaxy:node:stats:"+parentID.String(), "child_count", 1)
	} else {
		// Root node
		pipe.SAdd(ctx, "galaxy:nodes:roots", nodeIDStr)
	}

	// If it has a subject, add to subject's node set
	if node.SubjectID.Valid {
		pipe.SAdd(ctx, fmt.Sprintf("galaxy:subject:%d:nodes", node.SubjectID.Int32), nodeIDStr)
	}

	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Info("Node view created",
		zap.String("node_id", nodeIDStr),
		zap.String("name", node.Name),
	)

	return nil
}

// handleNodeUnlocked processes a NodeUnlocked event.
func (w *GalaxySyncWorker) handleNodeUnlocked(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	nodeID, err := uuid.Parse(nodeIDStr)
	if err != nil {
		return fmt.Errorf("invalid node_id: %w", err)
	}

	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		return fmt.Errorf("invalid user_id: %w", err)
	}

	// Fetch user node status from database
	status, err := w.getUserNodeStatus(ctx, userID, nodeID)
	if err != nil {
		return fmt.Errorf("fetch user node status: %w", err)
	}

	// Build view model
	view := w.buildUserNodeView(status)

	viewJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal view: %w", err)
	}

	// Update Redis
	pipe := w.redis.Pipeline()

	// User node view
	pipe.Set(ctx, "galaxy:user:"+userIDStr+":node:"+nodeIDStr, viewJSON, 0)

	// Add to user's unlocked nodes set
	pipe.SAdd(ctx, "galaxy:user:"+userIDStr+":unlocked", nodeIDStr)

	// Update user stats
	pipe.HIncrBy(ctx, "galaxy:user:"+userIDStr+":stats", "unlocked_nodes", 1)

	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Info("Node unlocked",
		zap.String("node_id", nodeIDStr),
		zap.String("user_id", userIDStr),
	)

	return nil
}

// handleNodeExpanded processes a NodeExpanded event.
func (w *GalaxySyncWorker) handleNodeExpanded(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	// Update the user node view is_collapsed field
	viewKey := "galaxy:user:" + userIDStr + ":node:" + nodeIDStr
	viewJSON, err := w.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		if err == redis.Nil {
			w.logger.Warn("User node view not found", zap.String("node_id", nodeIDStr))
			return nil
		}
		return fmt.Errorf("get user node view: %w", err)
	}

	var view UserNodeView
	if err := json.Unmarshal(viewJSON, &view); err != nil {
		return fmt.Errorf("unmarshal view: %w", err)
	}

	view.IsCollapsed = false
	view.UpdatedAt = time.Now()

	updatedJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal updated view: %w", err)
	}

	if err := w.redis.Set(ctx, viewKey, updatedJSON, 0).Err(); err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Debug("Node expanded",
		zap.String("node_id", nodeIDStr),
		zap.String("user_id", userIDStr),
	)

	return nil
}

// handleMasteryUpdated processes a MasteryUpdated event.
func (w *GalaxySyncWorker) handleMasteryUpdated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	masteryDelta := float64(0)
	if md, ok := evt.Payload["mastery_delta"].(float64); ok {
		masteryDelta = md
	}

	studyMinutes := int64(0)
	if sm, ok := evt.Payload["study_minutes"].(float64); ok {
		studyMinutes = int64(sm)
	}

	// Update user node view
	viewKey := "galaxy:user:" + userIDStr + ":node:" + nodeIDStr
	viewJSON, err := w.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		if err == redis.Nil {
			w.logger.Warn("User node view not found for mastery update", zap.String("node_id", nodeIDStr))
			return nil
		}
		return fmt.Errorf("get user node view: %w", err)
	}

	var view UserNodeView
	if err := json.Unmarshal(viewJSON, &view); err != nil {
		return fmt.Errorf("unmarshal view: %w", err)
	}

	// Check if newly mastered
	wasMastered := view.MasteryScore >= 0.8
	view.MasteryScore = clamp(view.MasteryScore+masteryDelta, 0, 1)
	view.TotalMinutes += int32(studyMinutes)
	view.StudyCount++
	now := time.Now()
	view.LastStudyAt = &now
	view.UpdatedAt = now
	isMastered := view.MasteryScore >= 0.8

	updatedJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal updated view: %w", err)
	}

	pipe := w.redis.Pipeline()
	pipe.Set(ctx, viewKey, updatedJSON, 0)

	// Update user stats
	pipe.HIncrBy(ctx, "galaxy:user:"+userIDStr+":stats", "total_study_minutes", studyMinutes)

	// If mastery crossed threshold, update mastered count
	if !wasMastered && isMastered {
		pipe.HIncrBy(ctx, "galaxy:user:"+userIDStr+":stats", "mastered_nodes", 1)
	} else if wasMastered && !isMastered {
		pipe.HIncrBy(ctx, "galaxy:user:"+userIDStr+":stats", "mastered_nodes", -1)
	}

	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Debug("Mastery updated",
		zap.String("node_id", nodeIDStr),
		zap.String("user_id", userIDStr),
		zap.Float64("new_mastery", view.MasteryScore),
	)

	return nil
}

// handleRelationCreated processes a RelationCreated event.
func (w *GalaxySyncWorker) handleRelationCreated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	sourceNodeIDStr, ok := evt.Payload["source_node_id"].(string)
	if !ok {
		return fmt.Errorf("missing source_node_id in payload")
	}

	targetNodeIDStr, ok := evt.Payload["target_node_id"].(string)
	if !ok {
		return fmt.Errorf("missing target_node_id in payload")
	}

	relationType, _ := evt.Payload["relation_type"].(string)
	strength := float64(1.0)
	if s, ok := evt.Payload["strength"].(float64); ok {
		strength = s
	}

	// Store relation in Redis
	relationKey := "galaxy:relation:" + sourceNodeIDStr + ":" + targetNodeIDStr
	relationData := map[string]interface{}{
		"source":        sourceNodeIDStr,
		"target":        targetNodeIDStr,
		"relation_type": relationType,
		"strength":      strength,
	}

	relationJSON, err := json.Marshal(relationData)
	if err != nil {
		return fmt.Errorf("marshal relation: %w", err)
	}

	pipe := w.redis.Pipeline()
	pipe.Set(ctx, relationKey, relationJSON, 0)
	pipe.SAdd(ctx, "galaxy:node:"+sourceNodeIDStr+":relations:out", targetNodeIDStr)
	pipe.SAdd(ctx, "galaxy:node:"+targetNodeIDStr+":relations:in", sourceNodeIDStr)
	_, err = pipe.Exec(ctx)

	if err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Debug("Relation created",
		zap.String("source", sourceNodeIDStr),
		zap.String("target", targetNodeIDStr),
		zap.String("type", relationType),
	)

	return nil
}

// handleStudyRecordAdded processes a StudyRecordAdded event.
func (w *GalaxySyncWorker) handleStudyRecordAdded(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	minutes := int64(0)
	if m, ok := evt.Payload["minutes"].(float64); ok {
		minutes = int64(m)
	}

	// Add to user's recent study list
	studyRecord := map[string]interface{}{
		"node_id":   nodeIDStr,
		"minutes":   minutes,
		"timestamp": time.Now().Unix(),
	}
	recordJSON, _ := json.Marshal(studyRecord)

	pipe := w.redis.Pipeline()

	// Add to recent studies (keep last 50)
	pipe.LPush(ctx, "galaxy:user:"+userIDStr+":recent_studies", recordJSON)
	pipe.LTrim(ctx, "galaxy:user:"+userIDStr+":recent_studies", 0, 49)

	// Update daily study count
	today := time.Now().Format("2006-01-02")
	pipe.HIncrBy(ctx, "galaxy:user:"+userIDStr+":daily:"+today, "study_count", 1)
	pipe.HIncrBy(ctx, "galaxy:user:"+userIDStr+":daily:"+today, "study_minutes", minutes)
	pipe.Expire(ctx, "galaxy:user:"+userIDStr+":daily:"+today, 7*24*time.Hour)

	_, err := pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Debug("Study record added",
		zap.String("node_id", nodeIDStr),
		zap.String("user_id", userIDStr),
		zap.Int64("minutes", minutes),
	)

	return nil
}

// getNode fetches a knowledge node from the database.
func (w *GalaxySyncWorker) getNode(ctx context.Context, nodeID uuid.UUID) (*db.KnowledgeNode, error) {
	node, err := w.queries.GetKnowledgeNodeByID(ctx, pgtype.UUID{Bytes: nodeID, Valid: true})
	if err != nil {
		return nil, err
	}
	return &node, nil
}

// getUserNodeStatus fetches user node status from the database.
func (w *GalaxySyncWorker) getUserNodeStatus(ctx context.Context, userID, nodeID uuid.UUID) (*db.UserNodeStatus, error) {
	status, err := w.queries.GetUserNodeStatus(ctx, db.GetUserNodeStatusParams{
		UserID: pgtype.UUID{Bytes: userID, Valid: true},
		NodeID: pgtype.UUID{Bytes: nodeID, Valid: true},
	})
	if err != nil {
		return nil, err
	}
	return &status, nil
}

// buildNodeView constructs a NodeView from a db.KnowledgeNode.
func (w *GalaxySyncWorker) buildNodeView(node *db.KnowledgeNode) NodeView {
	nodeID, _ := uuid.FromBytes(node.ID.Bytes[:])

	var keywords []string
	if node.Keywords != nil {
		_ = json.Unmarshal(node.Keywords, &keywords)
	}

	view := NodeView{
		ID:              nodeID.String(),
		Name:            node.Name,
		ImportanceLevel: node.ImportanceLevel,
		CreatedAt:       node.CreatedAt.Time,
	}

	if node.NameEn.Valid {
		view.NameEn = node.NameEn.String
	}

	if node.Description.Valid {
		view.Description = node.Description.String
	}

	if node.IsSeed.Valid {
		view.IsSeed = node.IsSeed.Bool
	}

	if node.ParentID.Valid {
		parentID, _ := uuid.FromBytes(node.ParentID.Bytes[:])
		view.ParentID = parentID.String()
	}

	if node.SubjectID.Valid {
		view.SubjectID = node.SubjectID.Int32
	}

	view.Keywords = keywords

	return view
}

// buildUserNodeView constructs a UserNodeView from a db.UserNodeStatus.
func (w *GalaxySyncWorker) buildUserNodeView(status *db.UserNodeStatus) UserNodeView {
	nodeID, _ := uuid.FromBytes(status.NodeID.Bytes[:])
	userID, _ := uuid.FromBytes(status.UserID.Bytes[:])

	view := UserNodeView{
		NodeID:       nodeID.String(),
		UserID:       userID.String(),
		MasteryScore: status.MasteryScore,
		TotalMinutes: status.TotalMinutes,
		IsUnlocked:   status.IsUnlocked,
		UpdatedAt:    status.UpdatedAt.Time,
	}

	if status.StudyCount.Valid {
		view.StudyCount = status.StudyCount.Int32
	}

	if status.IsCollapsed.Valid {
		view.IsCollapsed = status.IsCollapsed.Bool
	}

	if status.IsFavorite.Valid {
		view.IsFavorite = status.IsFavorite.Bool
	}

	if status.LastStudyAt.Valid {
		view.LastStudyAt = &status.LastStudyAt.Time
	}

	if status.NextReviewAt.Valid {
		view.NextReviewAt = &status.NextReviewAt.Time
	}

	if status.FirstUnlockAt.Valid {
		view.FirstUnlockAt = &status.FirstUnlockAt.Time
	}

	return view
}

// clamp restricts a value to a range.
func clamp(value, min, max float64) float64 {
	if value < min {
		return min
	}
	if value > max {
		return max
	}
	return value
}
