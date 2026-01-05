// Package projection provides projection handlers for CQRS.
package projection

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
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/service"
	"go.uber.org/zap"
)

// CommunityProjectionHandler handles community events for projection rebuilding.
type CommunityProjectionHandler struct {
	redis   *redis.Client
	queries *db.Queries
	logger  *zap.Logger
}

// NewCommunityProjectionHandler creates a new community projection handler.
func NewCommunityProjectionHandler(redis *redis.Client, pool *pgxpool.Pool, logger *zap.Logger) *CommunityProjectionHandler {
	return &CommunityProjectionHandler{
		redis:   redis,
		queries: db.New(pool),
		logger:  logger.Named("community-projection"),
	}
}

// Name returns the projection name.
func (h *CommunityProjectionHandler) Name() string {
	return "community_projection"
}

// HandleEvent processes a single event for projection rebuilding.
func (h *CommunityProjectionHandler) HandleEvent(ctx context.Context, eventData []byte) error {
	var evt cqrsEvent.DomainEvent
	if err := json.Unmarshal(eventData, &evt); err != nil {
		return fmt.Errorf("unmarshal event: %w", err)
	}

	switch evt.Type {
	case cqrsEvent.EventPostCreated:
		return h.handlePostCreated(ctx, evt)
	case cqrsEvent.EventPostLiked:
		return h.handlePostLiked(ctx, evt)
	case cqrsEvent.EventPostUnliked:
		return h.handlePostUnliked(ctx, evt)
	case cqrsEvent.EventPostDeleted:
		return h.handlePostDeleted(ctx, evt)
	default:
		h.logger.Debug("Ignoring unhandled event type",
			zap.String("event_type", string(evt.Type)),
			zap.String("event_id", evt.ID),
		)
		return nil
	}
}

// Reset clears the projection state.
func (h *CommunityProjectionHandler) Reset(ctx context.Context) error {
	// Delete all community-related keys from Redis
	keys, err := h.redis.Keys(ctx, "post:view:*").Result()
	if err != nil {
		return fmt.Errorf("get post keys: %w", err)
	}

	if len(keys) > 0 {
		if err := h.redis.Del(ctx, keys...).Err(); err != nil {
			return fmt.Errorf("delete post keys: %w", err)
		}
	}

	// Delete feed
	if err := h.redis.Del(ctx, "feed:global").Err(); err != nil {
		return fmt.Errorf("delete feed: %w", err)
	}

	h.logger.Info("Community projection reset", zap.Int("keys_deleted", len(keys)))
	return nil
}

func (h *CommunityProjectionHandler) handlePostCreated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	postIDStr, ok := evt.Payload["post_id"].(string)
	if !ok {
		return fmt.Errorf("missing post_id in payload")
	}

	postID, err := uuid.Parse(postIDStr)
	if err != nil {
		return fmt.Errorf("invalid post_id: %w", err)
	}

	createdAt := evt.Timestamp
	if raw, ok := evt.Payload["created_at"]; ok {
		if ts, err := parseEventTime(raw); err == nil {
			createdAt = ts
		}
	}
	post, err := h.queries.GetPost(ctx, db.GetPostParams{
		ID:        pgtype.UUID{Bytes: postID, Valid: true},
		CreatedAt: pgtype.Timestamp{Time: createdAt, Valid: true},
	})
	if err != nil {
		return fmt.Errorf("fetch post: %w", err)
	}

	user, err := h.queries.GetUser(ctx, post.UserID)
	if err != nil {
		return fmt.Errorf("fetch user: %w", err)
	}

	var imageUrls []string
	if post.ImageUrls != nil {
		_ = json.Unmarshal(post.ImageUrls, &imageUrls)
	}

	userID, _ := uuid.FromBytes(user.ID.Bytes[:])

	view := service.PostView{
		ID:        postIDStr,
		UserID:    userID.String(),
		Content:   post.Content,
		ImageURLs: imageUrls,
		Topic:     post.Topic.String,
		LikeCount: 0,
		CreatedAt: post.CreatedAt.Time,
		User: service.UserView{
			ID:        userID.String(),
			Username:  user.Username,
			AvatarURL: user.AvatarUrl.String,
		},
	}

	viewJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal view: %w", err)
	}

	pipe := h.redis.Pipeline()
	pipe.Set(ctx, "post:view:"+postIDStr, viewJSON, 0)
	pipe.ZAdd(ctx, "feed:global", redis.Z{
		Score:  float64(post.CreatedAt.Time.Unix()),
		Member: postIDStr,
	})
	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	return nil
}

func parseEventTime(value interface{}) (time.Time, error) {
	switch v := value.(type) {
	case string:
		return time.Parse(time.RFC3339Nano, v)
	case time.Time:
		return v, nil
	case float64:
		return time.Unix(int64(v), 0).UTC(), nil
	default:
		return time.Time{}, fmt.Errorf("unsupported time type")
	}
}

func (h *CommunityProjectionHandler) handlePostLiked(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	postIDStr, ok := evt.Payload["post_id"].(string)
	if !ok {
		return fmt.Errorf("missing post_id in payload")
	}

	viewKey := "post:view:" + postIDStr
	viewJSON, err := h.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		if err == redis.Nil {
			return nil
		}
		return fmt.Errorf("get post view: %w", err)
	}

	var view service.PostView
	if err := json.Unmarshal(viewJSON, &view); err != nil {
		return fmt.Errorf("unmarshal view: %w", err)
	}

	view.LikeCount++

	updatedJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal updated view: %w", err)
	}

	if err := h.redis.Set(ctx, viewKey, updatedJSON, 0).Err(); err != nil {
		return fmt.Errorf("set post view: %w", err)
	}

	return nil
}

func (h *CommunityProjectionHandler) handlePostUnliked(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	postIDStr, ok := evt.Payload["post_id"].(string)
	if !ok {
		return fmt.Errorf("missing post_id in payload")
	}

	viewKey := "post:view:" + postIDStr
	viewJSON, err := h.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		if err == redis.Nil {
			return nil
		}
		return fmt.Errorf("get post view: %w", err)
	}

	var view service.PostView
	if err := json.Unmarshal(viewJSON, &view); err != nil {
		return fmt.Errorf("unmarshal view: %w", err)
	}

	if view.LikeCount > 0 {
		view.LikeCount--
	}

	updatedJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal updated view: %w", err)
	}

	if err := h.redis.Set(ctx, viewKey, updatedJSON, 0).Err(); err != nil {
		return fmt.Errorf("set post view: %w", err)
	}

	return nil
}

func (h *CommunityProjectionHandler) handlePostDeleted(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	postIDStr, ok := evt.Payload["post_id"].(string)
	if !ok {
		return fmt.Errorf("missing post_id in payload")
	}

	pipe := h.redis.Pipeline()
	pipe.Del(ctx, "post:view:"+postIDStr)
	pipe.ZRem(ctx, "feed:global", postIDStr)
	_, err := pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("remove from redis: %w", err)
	}

	return nil
}

// TaskProjectionHandler handles task events for projection rebuilding.
type TaskProjectionHandler struct {
	redis   *redis.Client
	queries *db.Queries
	logger  *zap.Logger
}

// NewTaskProjectionHandler creates a new task projection handler.
func NewTaskProjectionHandler(redis *redis.Client, pool *pgxpool.Pool, logger *zap.Logger) *TaskProjectionHandler {
	return &TaskProjectionHandler{
		redis:   redis,
		queries: db.New(pool),
		logger:  logger.Named("task-projection"),
	}
}

// Name returns the projection name.
func (h *TaskProjectionHandler) Name() string {
	return "task_projection"
}

// HandleEvent processes a single event for projection rebuilding.
func (h *TaskProjectionHandler) HandleEvent(ctx context.Context, eventData []byte) error {
	var evt cqrsEvent.DomainEvent
	if err := json.Unmarshal(eventData, &evt); err != nil {
		return fmt.Errorf("unmarshal event: %w", err)
	}

	switch evt.Type {
	case cqrsEvent.EventTaskCreated:
		return h.handleTaskCreated(ctx, evt)
	case cqrsEvent.EventTaskStarted:
		return h.handleTaskStarted(ctx, evt)
	case cqrsEvent.EventTaskCompleted:
		return h.handleTaskCompleted(ctx, evt)
	case cqrsEvent.EventTaskAbandoned:
		return h.handleTaskAbandoned(ctx, evt)
	case cqrsEvent.EventTaskDeleted:
		return h.handleTaskDeleted(ctx, evt)
	case cqrsEvent.EventTaskUpdated:
		return h.handleTaskUpdated(ctx, evt)
	default:
		h.logger.Debug("Ignoring unhandled event type",
			zap.String("event_type", string(evt.Type)),
			zap.String("event_id", evt.ID),
		)
		return nil
	}
}

// Reset clears the projection state.
func (h *TaskProjectionHandler) Reset(ctx context.Context) error {
	// Delete all task-related keys from Redis
	keysPattern := []string{"task:view:*", "user:tasks:*", "user:tasks:pending:*", "user:tasks:in_progress:*", "user:tasks:completed:*", "user:task:stats:*"}

	for _, pattern := range keysPattern {
		keys, err := h.redis.Keys(ctx, pattern).Result()
		if err != nil {
			return fmt.Errorf("get keys for %s: %w", pattern, err)
		}
		if len(keys) > 0 {
			if err := h.redis.Del(ctx, keys...).Err(); err != nil {
				return fmt.Errorf("delete keys for %s: %w", pattern, err)
			}
		}
	}

	h.logger.Info("Task projection reset")
	return nil
}

func (h *TaskProjectionHandler) handleTaskCreated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	// Fetch task from database
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	taskID, err := uuid.Parse(taskIDStr)
	if err != nil {
		return fmt.Errorf("invalid task_id: %w", err)
	}

	task, err := h.queries.GetTaskByID(ctx, pgtype.UUID{Bytes: taskID, Valid: true})
	if err != nil {
		return fmt.Errorf("fetch task: %w", err)
	}

	// Build view
	view := map[string]interface{}{
		"task_id":           taskIDStr,
		"user_id":           userIDStr,
		"title":             task.Title,
		"type":              string(task.Type),
		"status":            string(task.Status),
		"estimated_minutes": task.EstimatedMinutes,
		"difficulty":        task.Difficulty,
		"priority":          task.Priority,
		"created_at":        task.CreatedAt.Time,
		"started_at":        nil,
		"completed_at":      nil,
	}

	viewJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal view: %w", err)
	}

	pipe := h.redis.Pipeline()

	// Task view
	pipe.Set(ctx, "task:view:"+taskIDStr, viewJSON, 0)

	// User tasks sorted set
	pipe.ZAdd(ctx, "user:tasks:"+userIDStr, redis.Z{
		Score:  float64(task.CreatedAt.Time.Unix()),
		Member: taskIDStr,
	})

	// Pending tasks
	pipe.ZAdd(ctx, "user:tasks:pending:"+userIDStr, redis.Z{
		Score:  float64(task.CreatedAt.Time.Unix()),
		Member: taskIDStr,
	})

	// Stats
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "total_tasks", 1)
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "pending_tasks", 1)

	_, err = pipe.Exec(ctx)
	return err
}

func (h *TaskProjectionHandler) handleTaskStarted(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	// Update task view
	viewKey := "task:view:" + taskIDStr
	viewJSON, err := h.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		return fmt.Errorf("get task view: %w", err)
	}

	var view map[string]interface{}
	if err := json.Unmarshal(viewJSON, &view); err != nil {
		return fmt.Errorf("unmarshal view: %w", err)
	}

	view["status"] = "in_progress"
	view["started_at"] = evt.Timestamp

	updatedJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal updated view: %w", err)
	}

	pipe := h.redis.Pipeline()
	pipe.Set(ctx, viewKey, updatedJSON, 0)

	// Move from pending to in_progress
	pipe.ZRem(ctx, "user:tasks:pending:"+userIDStr, taskIDStr)
	pipe.ZAdd(ctx, "user:tasks:in_progress:"+userIDStr, redis.Z{
		Score:  float64(evt.Timestamp.Unix()),
		Member: taskIDStr,
	})

	// Update stats
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "pending_tasks", -1)
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "in_progress_tasks", 1)

	_, err = pipe.Exec(ctx)
	return err
}

func (h *TaskProjectionHandler) handleTaskCompleted(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	viewKey := "task:view:" + taskIDStr
	viewJSON, err := h.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		return fmt.Errorf("get task view: %w", err)
	}

	var view map[string]interface{}
	if err := json.Unmarshal(viewJSON, &view); err != nil {
		return fmt.Errorf("unmarshal view: %w", err)
	}

	view["status"] = "completed"
	view["completed_at"] = evt.Timestamp

	updatedJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal updated view: %w", err)
	}

	pipe := h.redis.Pipeline()
	pipe.Set(ctx, viewKey, updatedJSON, 0)

	// Move from in_progress to completed
	pipe.ZRem(ctx, "user:tasks:in_progress:"+userIDStr, taskIDStr)
	pipe.ZAdd(ctx, "user:tasks:completed:"+userIDStr, redis.Z{
		Score:  float64(evt.Timestamp.Unix()),
		Member: taskIDStr,
	})

	// Update stats
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "in_progress_tasks", -1)
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "completed_tasks", 1)

	_, err = pipe.Exec(ctx)
	return err
}

func (h *TaskProjectionHandler) handleTaskAbandoned(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	return h.handleTaskDeleted(ctx, evt) // Same as delete for projection
}

func (h *TaskProjectionHandler) handleTaskDeleted(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	pipe := h.redis.Pipeline()

	// Remove from all sets
	pipe.Del(ctx, "task:view:"+taskIDStr)
	pipe.ZRem(ctx, "user:tasks:"+userIDStr, taskIDStr)
	pipe.ZRem(ctx, "user:tasks:pending:"+userIDStr, taskIDStr)
	pipe.ZRem(ctx, "user:tasks:in_progress:"+userIDStr, taskIDStr)
	pipe.ZRem(ctx, "user:tasks:completed:"+userIDStr, taskIDStr)

	// Update stats
	pipe.HIncrBy(ctx, "user:task:stats:"+userIDStr, "total_tasks", -1)

	_, err := pipe.Exec(ctx)
	return err
}

func (h *TaskProjectionHandler) handleTaskUpdated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	taskIDStr, ok := evt.Payload["task_id"].(string)
	if !ok {
		return fmt.Errorf("missing task_id in payload")
	}

	viewKey := "task:view:" + taskIDStr
	viewJSON, err := h.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		return fmt.Errorf("get task view: %w", err)
	}

	var view map[string]interface{}
	if err := json.Unmarshal(viewJSON, &view); err != nil {
		return fmt.Errorf("unmarshal view: %w", err)
	}

	// Update fields from payload
	if title, ok := evt.Payload["title"].(string); ok {
		view["title"] = title
	}
	if difficulty, ok := evt.Payload["difficulty"].(float64); ok {
		view["difficulty"] = difficulty
	}
	if priority, ok := evt.Payload["priority"].(float64); ok {
		view["priority"] = priority
	}

	updatedJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal updated view: %w", err)
	}

	return h.redis.Set(ctx, viewKey, updatedJSON, 0).Err()
}

// GalaxyProjectionHandler handles galaxy events for projection rebuilding.
type GalaxyProjectionHandler struct {
	redis   *redis.Client
	queries *db.Queries
	logger  *zap.Logger
}

// NewGalaxyProjectionHandler creates a new galaxy projection handler.
func NewGalaxyProjectionHandler(redis *redis.Client, pool *pgxpool.Pool, logger *zap.Logger) *GalaxyProjectionHandler {
	return &GalaxyProjectionHandler{
		redis:   redis,
		queries: db.New(pool),
		logger:  logger.Named("galaxy-projection"),
	}
}

// Name returns the projection name.
func (h *GalaxyProjectionHandler) Name() string {
	return "galaxy_projection"
}

// HandleEvent processes a single event for projection rebuilding.
func (h *GalaxyProjectionHandler) HandleEvent(ctx context.Context, eventData []byte) error {
	var evt cqrsEvent.DomainEvent
	if err := json.Unmarshal(eventData, &evt); err != nil {
		return fmt.Errorf("unmarshal event: %w", err)
	}

	switch evt.Type {
	case cqrsEvent.EventNodeCreated:
		return h.handleNodeCreated(ctx, evt)
	case cqrsEvent.EventNodeUnlocked:
		return h.handleNodeUnlocked(ctx, evt)
	case cqrsEvent.EventNodeExpanded:
		return h.handleNodeExpanded(ctx, evt)
	case cqrsEvent.EventMasteryUpdated:
		return h.handleMasteryUpdated(ctx, evt)
	case cqrsEvent.EventRelationCreated:
		return h.handleRelationCreated(ctx, evt)
	case cqrsEvent.EventStudyRecordAdded:
		return h.handleStudyRecorded(ctx, evt)
	default:
		h.logger.Debug("Ignoring unhandled event type",
			zap.String("event_type", string(evt.Type)),
			zap.String("event_id", evt.ID),
		)
		return nil
	}
}

// Reset clears the projection state.
func (h *GalaxyProjectionHandler) Reset(ctx context.Context) error {
	keysPattern := []string{"galaxy:node:*", "galaxy:nodes:*", "galaxy:subject:*", "galaxy:user:*", "galaxy:relation:*"}

	for _, pattern := range keysPattern {
		keys, err := h.redis.Keys(ctx, pattern).Result()
		if err != nil {
			return fmt.Errorf("get keys for %s: %w", pattern, err)
		}
		if len(keys) > 0 {
			if err := h.redis.Del(ctx, keys...).Err(); err != nil {
				return fmt.Errorf("delete keys for %s: %w", pattern, err)
			}
		}
	}

	h.logger.Info("Galaxy projection reset")
	return nil
}

func (h *GalaxyProjectionHandler) handleNodeCreated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	nodeID, err := uuid.Parse(nodeIDStr)
	if err != nil {
		return fmt.Errorf("invalid node_id: %w", err)
	}

	node, err := h.queries.GetKnowledgeNodeByID(ctx, pgtype.UUID{Bytes: nodeID, Valid: true})
	if err != nil {
		return fmt.Errorf("fetch node: %w", err)
	}

	// Convert subject_id to string
	subjectIDStr := fmt.Sprintf("%d", node.SubjectID.Int32)

	view := map[string]interface{}{
		"node_id":     nodeIDStr,
		"name":        node.Name,
		"description": node.Description.String,
		"subject_id":  subjectIDStr,
		"parent_id":   nil,
		"importance":  node.ImportanceLevel,
		"mastery":     0.0,
	}

	if node.ParentID.Valid {
		parentID, _ := uuid.FromBytes(node.ParentID.Bytes[:])
		view["parent_id"] = parentID.String()
	}

	viewJSON, err := json.Marshal(view)
	if err != nil {
		return fmt.Errorf("marshal view: %w", err)
	}

	pipe := h.redis.Pipeline()
	pipe.Set(ctx, "galaxy:node:"+nodeIDStr, viewJSON, 0)
	pipe.SAdd(ctx, "galaxy:nodes:all", nodeIDStr)

	if node.ParentID.Valid {
		parentIDStr := view["parent_id"].(string)
		pipe.SAdd(ctx, "galaxy:node:children:"+parentIDStr, nodeIDStr)
	} else {
		pipe.SAdd(ctx, "galaxy:nodes:roots", nodeIDStr)
	}

	pipe.SAdd(ctx, "galaxy:subject:"+subjectIDStr+":nodes", nodeIDStr)

	_, err = pipe.Exec(ctx)
	return err
}

func (h *GalaxyProjectionHandler) handleNodeUnlocked(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	pipe := h.redis.Pipeline()
	pipe.SAdd(ctx, "galaxy:user:"+userIDStr+":unlocked", nodeIDStr)
	pipe.Set(ctx, "galaxy:user:"+userIDStr+":node:"+nodeIDStr, `{"unlocked":true,"mastery":0}`, 0)
	_, err := pipe.Exec(ctx)
	return err
}

func (h *GalaxyProjectionHandler) handleNodeExpanded(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	key := "galaxy:user:" + userIDStr + ":node:" + nodeIDStr
	data, err := h.redis.Get(ctx, key).Bytes()
	if err != nil && err != redis.Nil {
		return fmt.Errorf("get user node: %w", err)
	}

	var state map[string]interface{}
	if err == redis.Nil {
		state = make(map[string]interface{})
	} else {
		if err := json.Unmarshal(data, &state); err != nil {
			return fmt.Errorf("unmarshal state: %w", err)
		}
	}

	state["expanded"] = true
	state["expanded_at"] = evt.Timestamp

	updatedJSON, err := json.Marshal(state)
	if err != nil {
		return fmt.Errorf("marshal state: %w", err)
	}

	return h.redis.Set(ctx, key, updatedJSON, 0).Err()
}

func (h *GalaxyProjectionHandler) handleMasteryUpdated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	mastery, ok := evt.Payload["mastery"].(float64)
	if !ok {
		return fmt.Errorf("missing mastery in payload")
	}

	// Update node view
	nodeKey := "galaxy:node:" + nodeIDStr
	nodeData, err := h.redis.Get(ctx, nodeKey).Bytes()
	if err == nil {
		var nodeView map[string]interface{}
		if err := json.Unmarshal(nodeData, &nodeView); err == nil {
			nodeView["mastery"] = mastery
			updatedJSON, _ := json.Marshal(nodeView)
			h.redis.Set(ctx, nodeKey, updatedJSON, 0)
		}
	}

	// Update user node state
	userNodeKey := "galaxy:user:" + userIDStr + ":node:" + nodeIDStr
	data, err := h.redis.Get(ctx, userNodeKey).Bytes()
	if err != nil && err != redis.Nil {
		return fmt.Errorf("get user node: %w", err)
	}

	var state map[string]interface{}
	if err == redis.Nil {
		state = make(map[string]interface{})
	} else {
		if err := json.Unmarshal(data, &state); err != nil {
			return fmt.Errorf("unmarshal state: %w", err)
		}
	}

	state["mastery"] = mastery
	state["last_updated"] = evt.Timestamp

	updatedJSON, err := json.Marshal(state)
	if err != nil {
		return fmt.Errorf("marshal state: %w", err)
	}

	return h.redis.Set(ctx, userNodeKey, updatedJSON, 0).Err()
}

func (h *GalaxyProjectionHandler) handleRelationCreated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	sourceIDStr, ok := evt.Payload["source_id"].(string)
	if !ok {
		return fmt.Errorf("missing source_id in payload")
	}

	targetIDStr, ok := evt.Payload["target_id"].(string)
	if !ok {
		return fmt.Errorf("missing target_id in payload")
	}

	relationType, ok := evt.Payload["relation_type"].(string)
	if !ok {
		relationType = "depends_on"
	}

	relation := map[string]interface{}{
		"source_id":     sourceIDStr,
		"target_id":     targetIDStr,
		"relation_type": relationType,
		"created_at":    evt.Timestamp,
	}

	relationJSON, err := json.Marshal(relation)
	if err != nil {
		return fmt.Errorf("marshal relation: %w", err)
	}

	key := "galaxy:relation:" + sourceIDStr + ":" + targetIDStr
	return h.redis.Set(ctx, key, relationJSON, 0).Err()
}

func (h *GalaxyProjectionHandler) handleStudyRecorded(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	userIDStr, ok := evt.Payload["user_id"].(string)
	if !ok {
		return fmt.Errorf("missing user_id in payload")
	}

	nodeIDStr, ok := evt.Payload["node_id"].(string)
	if !ok {
		return fmt.Errorf("missing node_id in payload")
	}

	minutes, ok := evt.Payload["minutes"].(float64)
	if !ok {
		return fmt.Errorf("missing minutes in payload")
	}

	performanceScore, ok := evt.Payload["performance_score"].(float64)
	if !ok {
		performanceScore = 0.0
	}

	// Add to recent studies list
	study := map[string]interface{}{
		"node_id":           nodeIDStr,
		"minutes":           minutes,
		"performance_score": performanceScore,
		"timestamp":         evt.Timestamp,
	}

	studyJSON, err := json.Marshal(study)
	if err != nil {
		return fmt.Errorf("marshal study: %w", err)
	}

	pipe := h.redis.Pipeline()
	pipe.LPush(ctx, "galaxy:user:"+userIDStr+":recent_studies", string(studyJSON))
	pipe.LTrim(ctx, "galaxy:user:"+userIDStr+":recent_studies", 0, 9) // Keep last 10

	// Daily stats
	dateKey := fmt.Sprintf("galaxy:user:%s:daily:%s", userIDStr, evt.Timestamp.Format("2006-01-02"))
	pipe.HIncrByFloat(ctx, dateKey, "total_minutes", minutes)
	pipe.HIncrByFloat(ctx, dateKey, "total_score", performanceScore)
	pipe.HIncrBy(ctx, dateKey, "study_count", 1)

	_, err = pipe.Exec(ctx)
	return err
}
