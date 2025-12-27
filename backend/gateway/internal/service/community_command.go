package service

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/event"
)

type CreatePostRequest struct {
	UserID    uuid.UUID
	Content   string
	ImageURLs []string
	Topic     string
}

type CommunityCommandService struct {
	queries *db.Queries
	bus     event.EventBus
}

func NewCommunityCommandService(queries *db.Queries, bus event.EventBus) *CommunityCommandService {
	return &CommunityCommandService{
		queries: queries,
		bus:     bus,
	}
}

func (s *CommunityCommandService) CreatePost(ctx context.Context, req CreatePostRequest) (*db.Post, error) {
	if req.Content == "" {
		return nil, fmt.Errorf("content cannot be empty")
	}

	imagesJSON, err := json.Marshal(req.ImageURLs)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal images: %w", err)
	}

	// Insert into DB
	post, err := s.queries.CreatePost(ctx, db.CreatePostParams{
		UserID:    pgtype.UUID{Bytes: req.UserID, Valid: true},
		Content:   req.Content,
		ImageUrls: imagesJSON,
		Topic:     pgtype.Text{String: req.Topic, Valid: req.Topic != ""},
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create post in db: %w", err)
	}

	// Publish Event
	postID, _ := uuid.FromBytes(post.ID.Bytes[:])
	err = s.bus.Publish(ctx, event.DomainEvent{
		ID:        uuid.New().String(),
		Type:      event.EventPostCreated,
		Timestamp: time.Now(),
		Payload: map[string]interface{}{
			"post_id": postID.String(),
			"user_id": req.UserID.String(),
		},
	})
	if err != nil {
		// In a real production system, we should use the Outbox pattern here.
		// For MVP, we accept the small risk of inconsistency (DB write success, Event fail).
		return nil, fmt.Errorf("failed to publish event: %w", err)
	}

	return &post, nil
}

func (s *CommunityCommandService) LikePost(ctx context.Context, userID, postID uuid.UUID) error {
	err := s.queries.CreatePostLike(ctx, db.CreatePostLikeParams{
		UserID: pgtype.UUID{Bytes: userID, Valid: true},
		PostID: pgtype.UUID{Bytes: postID, Valid: true},
	})
	if err != nil {
		return err
	}

	// Publish Event
	return s.bus.Publish(ctx, event.DomainEvent{
		ID:        uuid.New().String(),
		Type:      event.EventPostLiked,
		Timestamp: time.Now(),
		Payload: map[string]interface{}{
			"post_id": postID.String(),
			"user_id": userID.String(),
		},
	})
}
