package worker

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	cqrsEvent "github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	cqrsWorker "github.com/sparkle/gateway/internal/cqrs/worker"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/service"
	"go.uber.org/zap"
)

const (
	// CommunityStreamKey is the Redis stream for community events.
	CommunityStreamKey = "cqrs:stream:community"
	// CommunityConsumerGroup is the consumer group for community projection.
	CommunityConsumerGroup = "community_projection_group"
)

// CommunitySyncWorker synchronizes community events to Redis read models.
type CommunitySyncWorker struct {
	baseWorker *cqrsWorker.BaseWorker
	redis      *redis.Client
	queries    *db.Queries
	logger     *zap.Logger
}

// CommunitySyncWorkerConfig configures the community sync worker.
type CommunitySyncWorkerConfig struct {
	ConsumerName string
	Options      cqrsWorker.WorkerOptions
}

// DefaultCommunitySyncWorkerConfig returns sensible defaults.
func DefaultCommunitySyncWorkerConfig() CommunitySyncWorkerConfig {
	return CommunitySyncWorkerConfig{
		ConsumerName: "community_worker_1",
		Options:      cqrsWorker.DefaultWorkerOptions(),
	}
}

// NewCommunitySyncWorker creates a new community sync worker using the enhanced BaseWorker.
func NewCommunitySyncWorker(
	rdb *redis.Client,
	pool *pgxpool.Pool,
	cqrsMetrics *metrics.CQRSMetrics,
	logger *zap.Logger,
	config ...CommunitySyncWorkerConfig,
) *CommunitySyncWorker {
	cfg := DefaultCommunitySyncWorkerConfig()
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
		CommunityStreamKey,
		CommunityConsumerGroup,
		cfg.ConsumerName,
		cfg.Options,
	)

	return &CommunitySyncWorker{
		baseWorker: baseWorker,
		redis:      rdb,
		queries:    queries,
		logger:     logger.Named("community-sync"),
	}
}

// Run starts the worker. Blocks until context is cancelled.
func (w *CommunitySyncWorker) Run(ctx context.Context) error {
	return w.baseWorker.Run(ctx, w.handleEvent)
}

// IsRunning returns true if the worker is currently running.
func (w *CommunitySyncWorker) IsRunning() bool {
	return w.baseWorker.IsRunning()
}

// handleEvent processes a single community event.
func (w *CommunitySyncWorker) handleEvent(ctx context.Context, evt cqrsEvent.DomainEvent, messageID string) error {
	switch evt.Type {
	case cqrsEvent.EventPostCreated:
		return w.handlePostCreated(ctx, evt)
	case cqrsEvent.EventPostLiked:
		return w.handlePostLiked(ctx, evt)
	case cqrsEvent.EventPostUnliked:
		return w.handlePostUnliked(ctx, evt)
	case cqrsEvent.EventPostDeleted:
		return w.handlePostDeleted(ctx, evt)
	default:
		w.logger.Debug("Ignoring unhandled event type",
			zap.String("event_type", string(evt.Type)),
			zap.String("event_id", evt.ID),
		)
		return nil
	}
}

// handlePostCreated processes a PostCreated event.
func (w *CommunitySyncWorker) handlePostCreated(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	postIDStr, ok := evt.Payload["post_id"].(string)
	if !ok {
		return fmt.Errorf("missing post_id in payload")
	}

	postID, err := uuid.Parse(postIDStr)
	if err != nil {
		return fmt.Errorf("invalid post_id: %w", err)
	}

	// Fetch post from database
	post, err := w.queries.GetPost(ctx, pgtype.UUID{Bytes: postID, Valid: true})
	if err != nil {
		return fmt.Errorf("fetch post: %w", err)
	}

	// Fetch user
	user, err := w.queries.GetUser(ctx, post.UserID)
	if err != nil {
		return fmt.Errorf("fetch user: %w", err)
	}

	// Build view model
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

	// Update Redis read model
	pipe := w.redis.Pipeline()
	pipe.Set(ctx, "post:view:"+postIDStr, viewJSON, 0)
	pipe.ZAdd(ctx, "feed:global", redis.Z{
		Score:  float64(post.CreatedAt.Time.Unix()),
		Member: postIDStr,
	})
	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("update redis: %w", err)
	}

	w.logger.Info("Post view created",
		zap.String("post_id", postIDStr),
		zap.String("user_id", userID.String()),
	)

	return nil
}

// handlePostLiked processes a PostLiked event.
func (w *CommunitySyncWorker) handlePostLiked(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	postIDStr, ok := evt.Payload["post_id"].(string)
	if !ok {
		return fmt.Errorf("missing post_id in payload")
	}

	// Increment like count in Redis
	viewKey := "post:view:" + postIDStr
	viewJSON, err := w.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		if err == redis.Nil {
			// Post view doesn't exist, this might be a race condition
			w.logger.Warn("Post view not found for like",
				zap.String("post_id", postIDStr),
			)
			return nil // Non-fatal, projection will be rebuilt
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

	if err := w.redis.Set(ctx, viewKey, updatedJSON, 0).Err(); err != nil {
		return fmt.Errorf("set post view: %w", err)
	}

	w.logger.Debug("Post like count incremented",
		zap.String("post_id", postIDStr),
		zap.Int("new_count", view.LikeCount),
	)

	return nil
}

// handlePostUnliked processes a PostUnliked event.
func (w *CommunitySyncWorker) handlePostUnliked(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	postIDStr, ok := evt.Payload["post_id"].(string)
	if !ok {
		return fmt.Errorf("missing post_id in payload")
	}

	// Decrement like count in Redis
	viewKey := "post:view:" + postIDStr
	viewJSON, err := w.redis.Get(ctx, viewKey).Bytes()
	if err != nil {
		if err == redis.Nil {
			w.logger.Warn("Post view not found for unlike",
				zap.String("post_id", postIDStr),
			)
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

	if err := w.redis.Set(ctx, viewKey, updatedJSON, 0).Err(); err != nil {
		return fmt.Errorf("set post view: %w", err)
	}

	w.logger.Debug("Post like count decremented",
		zap.String("post_id", postIDStr),
		zap.Int("new_count", view.LikeCount),
	)

	return nil
}

// handlePostDeleted processes a PostDeleted event.
func (w *CommunitySyncWorker) handlePostDeleted(ctx context.Context, evt cqrsEvent.DomainEvent) error {
	postIDStr, ok := evt.Payload["post_id"].(string)
	if !ok {
		return fmt.Errorf("missing post_id in payload")
	}

	// Remove from Redis
	pipe := w.redis.Pipeline()
	pipe.Del(ctx, "post:view:"+postIDStr)
	pipe.ZRem(ctx, "feed:global", postIDStr)
	_, err := pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("remove from redis: %w", err)
	}

	w.logger.Info("Post view deleted",
		zap.String("post_id", postIDStr),
	)

	return nil
}

// Legacy constructor for backwards compatibility.
// Deprecated: Use NewCommunitySyncWorker with proper dependencies instead.
func NewCommunitySyncWorkerLegacy(rdb *redis.Client, queries *db.Queries) *CommunitySyncWorkerLegacy {
	return &CommunitySyncWorkerLegacy{
		redis:   rdb,
		queries: queries,
	}
}

// CommunitySyncWorkerLegacy is the legacy worker without BaseWorker integration.
// Deprecated: Use CommunitySyncWorker instead.
type CommunitySyncWorkerLegacy struct {
	redis   *redis.Client
	queries *db.Queries
}

// Run starts the legacy worker. For backwards compatibility only.
func (w *CommunitySyncWorkerLegacy) Run(ctx context.Context) {
	// This is a stub for backwards compatibility
	// New code should use CommunitySyncWorker.Run(ctx)
	<-ctx.Done()
}
