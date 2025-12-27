package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/event"
	"github.com/sparkle/gateway/internal/service"
)

type CommunitySyncWorker struct {
	redis    *redis.Client
	queries  *db.Queries
	group    string
	consumer string
}

func NewCommunitySyncWorker(rdb *redis.Client, queries *db.Queries) *CommunitySyncWorker {
	return &CommunitySyncWorker{
		redis:    rdb,
		queries:  queries,
		group:    "community_sync_group",
		consumer: "worker_1",
	}
}

func (w *CommunitySyncWorker) Run(ctx context.Context) {
	// Create Consumer Group
	// Ignore error if it already exists
	_ = w.redis.XGroupCreateMkStream(ctx, event.StreamKey, w.group, "0").Err()

	log.Println("Community Sync Worker Started")

	for {
		select {
		case <-ctx.Done():
			return
		default:
			entries, err := w.redis.XReadGroup(ctx, &redis.XReadGroupArgs{
				Group:    w.group,
				Consumer: w.consumer,
				Streams:  []string{event.StreamKey, ">"},
				Count:    10,
				Block:    2 * time.Second,
			}).Result()

			if err != nil {
				if err != redis.Nil {
					log.Printf("Error reading stream: %v", err)
				}
				continue
			}

			for _, stream := range entries {
				for _, msg := range stream.Messages {
					if err := w.processMessage(ctx, msg); err != nil {
						log.Printf("Error processing message %s: %v", msg.ID, err)
					}
					w.redis.XAck(ctx, event.StreamKey, w.group, msg.ID)
				}
			}
		}
	}
}

func (w *CommunitySyncWorker) processMessage(ctx context.Context, msg redis.XMessage) error {
	eventType, ok := msg.Values["type"].(string)
	if !ok {
		return fmt.Errorf("missing type")
	}
	payloadStr, ok := msg.Values["payload"].(string)
	if !ok {
		return fmt.Errorf("missing payload")
	}

	var payload map[string]interface{}
	if err := json.Unmarshal([]byte(payloadStr), &payload); err != nil {
		return err
	}

	if eventType == string(event.EventPostCreated) {
		postIDStr := payload["post_id"].(string)
		postID, err := uuid.Parse(postIDStr)
		if err != nil {
			return err
		}

		// 1. Fetch Post
		post, err := w.queries.GetPost(ctx, pgtype.UUID{Bytes: postID, Valid: true})
		if err != nil {
			return fmt.Errorf("failed to fetch post: %w", err)
		}

		// 2. Fetch User
		user, err := w.queries.GetUser(ctx, post.UserID)
		if err != nil {
			return fmt.Errorf("failed to fetch user: %w", err)
		}

		// 3. Construct View
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

		viewJSON, _ := json.Marshal(view)

		// 4. Update Redis
		pipe := w.redis.Pipeline()
		pipe.Set(ctx, "post:view:"+postIDStr, viewJSON, 0)
		pipe.ZAdd(ctx, "feed:global", redis.Z{
			Score:  float64(post.CreatedAt.Time.Unix()),
			Member: postIDStr,
		})
		_, err = pipe.Exec(ctx)
		return err
	}

	return nil
}
