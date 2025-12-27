package service

import (
	"context"
	"encoding/json"
	"time"

	"github.com/redis/go-redis/v9"
)

type PostView struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id"`
	Content   string    `json:"content"`
	ImageURLs []string  `json:"image_urls"`
	Topic     string    `json:"topic"`
	LikeCount int       `json:"like_count"`
	CreatedAt time.Time `json:"created_at"`
	User      UserView  `json:"user"`
}

type UserView struct {
	ID        string `json:"id"`
	Username  string `json:"username"`
	AvatarURL string `json:"avatar_url"`
}

type CommunityQueryService struct {
	redis *redis.Client
}

func NewCommunityQueryService(rdb *redis.Client) *CommunityQueryService {
	return &CommunityQueryService{redis: rdb}
}

func (s *CommunityQueryService) GetGlobalFeed(ctx context.Context, page, limit int) ([]PostView, error) {
	start := int64((page - 1) * limit)
	stop := start + int64(limit) - 1

	// Get IDs from ZSet (RevRange for newest first)
	ids, err := s.redis.ZRevRange(ctx, "feed:global", start, stop).Result()
	if err != nil {
		return nil, err
	}

	if len(ids) == 0 {
		return []PostView{}, nil
	}

	// Prepare keys for MGET
	keys := make([]string, len(ids))
	for i, id := range ids {
		keys[i] = "post:view:" + id
	}

	// MGET full objects
	jsonList, err := s.redis.MGet(ctx, keys...).Result()
	if err != nil {
		return nil, err
	}

	posts := make([]PostView, 0, len(ids))
	for _, jsonStr := range jsonList {
		if jsonStr == nil {
			continue // Handle cache miss
		}
		var post PostView
		if str, ok := jsonStr.(string); ok {
			if err := json.Unmarshal([]byte(str), &post); err != nil {
				continue
			}
			posts = append(posts, post)
		}
	}

	return posts, nil
}
