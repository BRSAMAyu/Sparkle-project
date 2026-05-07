package service

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

type PostView struct {
	ID          string    `json:"id"`
	UserID      string    `json:"user_id"`
	Content     string    `json:"content"`
	ImageURLs   []string  `json:"image_urls"`
	Topic       string    `json:"topic"`
	LikeCount   int       `json:"like_count"`
	IsLikedByMe bool      `json:"is_liked_by_me"`
	CreatedAt   time.Time `json:"created_at"`
	User        UserView  `json:"user"`
}

type UserView struct {
	ID        string `json:"id"`
	Username  string `json:"username"`
	AvatarURL string `json:"avatar_url"`
}

type CommunityQueryService struct {
	redis *redis.Client
	pool  *pgxpool.Pool
}

func NewCommunityQueryService(rdb *redis.Client, pool *pgxpool.Pool) *CommunityQueryService {
	return &CommunityQueryService{redis: rdb, pool: pool}
}

func (s *CommunityQueryService) GetGlobalFeed(ctx context.Context, userID string, page, limit int) ([]PostView, error) {
	start := int64((page - 1) * limit)
	stop := start + int64(limit) - 1

	// Get IDs from ZSet (RevRange for newest first)
	ids, err := s.redis.ZRevRange(ctx, "feed:global", start, stop).Result()
	if err != nil {
		return nil, err
	}

	if len(ids) == 0 {
		// Cold start / Redis flush: fall back to DB
		if s.pool != nil {
			posts, dbErr := s.fetchRecentPostsFromDB(ctx, limit)
			if dbErr != nil {
				return nil, dbErr
			}
			s.populateIsLikedByMe(ctx, userID, posts)
			return posts, nil
		}
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
	missedIDs := make([]string, 0)
	for i, jsonStr := range jsonList {
		if jsonStr == nil {
			if i < len(ids) {
				missedIDs = append(missedIDs, ids[i])
			}
			continue
		}
		var post PostView
		if str, ok := jsonStr.(string); ok {
			if err := json.Unmarshal([]byte(str), &post); err != nil {
				continue
			}
			posts = append(posts, post)
		}
	}

	// DB fallback for cache misses
	if len(missedIDs) > 0 && s.pool != nil {
		dbPosts, err := s.fetchPostsFromDB(ctx, missedIDs)
		if err == nil && len(dbPosts) > 0 {
			posts = append(posts, dbPosts...)
			// Rehydrate cache for missed posts
			for _, p := range dbPosts {
				data, marshalErr := json.Marshal(p)
				if marshalErr == nil {
					_ = s.redis.Set(ctx, "post:view:"+p.ID, data, 10*time.Minute).Err()
				}
			}
		}
	}

	s.populateIsLikedByMe(ctx, userID, posts)
	return posts, nil
}

func (s *CommunityQueryService) fetchPostsFromDB(ctx context.Context, ids []string) ([]PostView, error) {
	if s.pool == nil || len(ids) == 0 {
		return nil, nil
	}

	query := `
		SELECT p.id, p.user_id, p.content, p.image_urls, p.topic, p.like_count, p.created_at,
		       u.id, u.username, u.avatar_url
		FROM community_posts p
		JOIN users u ON p.user_id = u.id
		WHERE p.id = ANY($1)
		ORDER BY p.created_at DESC
	`

	rows, err := s.pool.Query(ctx, query, ids)
	if err != nil {
		return nil, fmt.Errorf("query posts from DB: %w", err)
	}
	defer rows.Close()

	var result []PostView
	for rows.Next() {
		var p PostView
		if err := rows.Scan(
			&p.ID, &p.UserID, &p.Content, &p.ImageURLs, &p.Topic, &p.LikeCount, &p.CreatedAt,
			&p.User.ID, &p.User.Username, &p.User.AvatarURL,
		); err != nil {
			continue
		}
		result = append(result, p)
	}
	return result, nil
}

// fetchRecentPostsFromDB loads the most recent posts directly from DB,
// used as cold-start fallback when feed:global ZSet is empty.
func (s *CommunityQueryService) fetchRecentPostsFromDB(ctx context.Context, limit int) ([]PostView, error) {
	if s.pool == nil {
		return []PostView{}, nil
	}

	query := `
		SELECT p.id, p.user_id, p.content, p.image_urls, p.topic, p.like_count, p.created_at,
		       u.id, u.username, u.avatar_url
		FROM community_posts p
		JOIN users u ON p.user_id = u.id
		ORDER BY p.created_at DESC
		LIMIT $1
	`

	rows, err := s.pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("query recent posts from DB: %w", err)
	}
	defer rows.Close()

	var result []PostView
	for rows.Next() {
		var p PostView
		if err := rows.Scan(
			&p.ID, &p.UserID, &p.Content, &p.ImageURLs, &p.Topic, &p.LikeCount, &p.CreatedAt,
			&p.User.ID, &p.User.Username, &p.User.AvatarURL,
		); err != nil {
			continue
		}
		result = append(result, p)
	}
	return result, nil
}

// populateIsLikedByMe batch-checks which posts the given user has liked
// using Redis sets of the form "post:likes:{post_id}".
func (s *CommunityQueryService) populateIsLikedByMe(ctx context.Context, userID string, posts []PostView) {
	if userID == "" || len(posts) == 0 {
		return
	}
	for i := range posts {
		key := "post:likes:" + posts[i].ID
		isMember, err := s.redis.SIsMember(ctx, key, userID).Result()
		if err == nil {
			posts[i].IsLikedByMe = isMember
		}
	}
}
