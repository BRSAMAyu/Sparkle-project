package service

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	"github.com/sparkle/gateway/internal/db"
)

type CreatePostRequest struct {
	UserID    uuid.UUID
	Content   string
	ImageURLs []string
	Topic     string
}

// CommunityCommandService handles write operations for the community module.
// Uses the Outbox pattern for reliable event publishing with transactional consistency.
type CommunityCommandService struct {
	pool       *pgxpool.Pool
	queries    *db.Queries
	unitOfWork *outbox.UnitOfWork
}

// NewCommunityCommandService creates a new community command service.
func NewCommunityCommandService(pool *pgxpool.Pool) *CommunityCommandService {
	return &CommunityCommandService{
		pool:       pool,
		queries:    db.New(pool),
		unitOfWork: outbox.NewUnitOfWork(pool),
	}
}

// CreatePost creates a new post and publishes a PostCreated event atomically.
// Uses the Outbox pattern to ensure consistency between the database write and event publishing.
func (s *CommunityCommandService) CreatePost(ctx context.Context, req CreatePostRequest) (*db.Post, error) {
	if req.Content == "" {
		return nil, fmt.Errorf("content cannot be empty")
	}

	imagesJSON, err := json.Marshal(req.ImageURLs)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal images: %w", err)
	}

	var post db.Post

	// Execute in transaction with Outbox pattern
	err = s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Insert post in transaction
		row := txCtx.QueryRow(ctx, `
			INSERT INTO posts (user_id, content, image_urls, topic, created_at, updated_at)
			VALUES ($1, $2, $3, $4, NOW(), NOW())
			RETURNING id, user_id, content, image_urls, topic, created_at, updated_at, deleted_at
		`, pgtype.UUID{Bytes: req.UserID, Valid: true}, req.Content, imagesJSON,
			pgtype.Text{String: req.Topic, Valid: req.Topic != ""})

		err := row.Scan(
			&post.ID,
			&post.UserID,
			&post.Content,
			&post.ImageUrls,
			&post.Topic,
			&post.CreatedAt,
			&post.UpdatedAt,
			&post.DeletedAt,
		)
		if err != nil {
			return fmt.Errorf("failed to create post: %w", err)
		}

		// Create domain event
		postID, _ := uuid.FromBytes(post.ID.Bytes[:])
		domainEvent := event.NewDomainEvent(
			event.EventPostCreated,
			event.AggregatePost,
			postID,
			map[string]interface{}{
				"post_id":    postID.String(),
				"user_id":    req.UserID.String(),
				"content":    req.Content,
				"image_urls": req.ImageURLs,
				"topic":      req.Topic,
			},
			event.EventMetadata{
				UserID: req.UserID,
				Source: "community_command_service",
			},
		)

		// Save event to outbox in the same transaction
		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})

	if err != nil {
		return nil, err
	}

	return &post, nil
}

// LikePost creates a like for a post and publishes a PostLiked event atomically.
func (s *CommunityCommandService) LikePost(ctx context.Context, userID, postID uuid.UUID) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Create like in transaction
		_, err := txCtx.Tx().Exec(ctx, `
			INSERT INTO post_likes (user_id, post_id, created_at)
			VALUES ($1, $2, NOW())
			ON CONFLICT DO NOTHING
		`, pgtype.UUID{Bytes: userID, Valid: true}, pgtype.UUID{Bytes: postID, Valid: true})

		if err != nil {
			return fmt.Errorf("failed to create like: %w", err)
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventPostLiked,
			event.AggregatePost,
			postID,
			map[string]interface{}{
				"post_id": postID.String(),
				"user_id": userID.String(),
			},
			event.EventMetadata{
				UserID: userID,
				Source: "community_command_service",
			},
		)

		// Save event to outbox in the same transaction
		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// UnlikePost removes a like from a post and publishes a PostUnliked event atomically.
func (s *CommunityCommandService) UnlikePost(ctx context.Context, userID, postID uuid.UUID) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Delete like in transaction
		result, err := txCtx.Tx().Exec(ctx, `
			DELETE FROM post_likes
			WHERE user_id = $1 AND post_id = $2
		`, pgtype.UUID{Bytes: userID, Valid: true}, pgtype.UUID{Bytes: postID, Valid: true})

		if err != nil {
			return fmt.Errorf("failed to delete like: %w", err)
		}

		// Only publish event if a like was actually deleted
		if result.RowsAffected() == 0 {
			return nil
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventPostUnliked,
			event.AggregatePost,
			postID,
			map[string]interface{}{
				"post_id": postID.String(),
				"user_id": userID.String(),
			},
			event.EventMetadata{
				UserID: userID,
				Source: "community_command_service",
			},
		)

		// Save event to outbox in the same transaction
		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// DeletePost soft deletes a post and publishes a PostDeleted event atomically.
func (s *CommunityCommandService) DeletePost(ctx context.Context, userID, postID uuid.UUID) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Soft delete post in transaction (only if user owns the post)
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE posts
			SET deleted_at = NOW(), updated_at = NOW()
			WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
		`, pgtype.UUID{Bytes: postID, Valid: true}, pgtype.UUID{Bytes: userID, Valid: true})

		if err != nil {
			return fmt.Errorf("failed to delete post: %w", err)
		}

		if result.RowsAffected() == 0 {
			return fmt.Errorf("post not found or already deleted")
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventPostDeleted,
			event.AggregatePost,
			postID,
			map[string]interface{}{
				"post_id": postID.String(),
				"user_id": userID.String(),
			},
			event.EventMetadata{
				UserID: userID,
				Source: "community_command_service",
			},
		)

		// Save event to outbox in the same transaction
		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// Deprecated: Use the pool-based constructor instead.
// NewCommunityCommandServiceLegacy creates a service with the old event bus pattern.
// This is kept for backward compatibility during migration.
func NewCommunityCommandServiceLegacy(queries *db.Queries, pool *pgxpool.Pool) *CommunityCommandService {
	return &CommunityCommandService{
		pool:       pool,
		queries:    queries,
		unitOfWork: outbox.NewUnitOfWork(pool),
	}
}
