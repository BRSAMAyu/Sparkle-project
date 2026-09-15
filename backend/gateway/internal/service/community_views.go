package service

import "time"

// PostView and UserView are the read models consumed by the community
// projection handlers (internal/cqrs/projection) and the community sync
// worker (internal/worker/community_sync.go).
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
