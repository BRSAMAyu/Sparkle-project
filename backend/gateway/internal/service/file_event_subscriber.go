package service

import (
	"context"
	"encoding/json"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

type FileStatusEvent struct {
	Type     string `json:"type"`
	FileID   string `json:"file_id"`
	UserID   string `json:"user_id"`
	Status   string `json:"status"`
	Progress int    `json:"progress"`
	Error    string `json:"error,omitempty"`
}

type FileEventSubscriber struct {
	redis  *redis.Client
	hub    *FileEventHub
	logger *zap.Logger
}

func NewFileEventSubscriber(redis *redis.Client, hub *FileEventHub, logger *zap.Logger) *FileEventSubscriber {
	return &FileEventSubscriber{
		redis:  redis,
		hub:    hub,
		logger: logger,
	}
}

func (s *FileEventSubscriber) Run(ctx context.Context) error {
	pubsub := s.redis.Subscribe(ctx, "file_status")
	defer pubsub.Close()

	for {
		msg, err := pubsub.ReceiveMessage(ctx)
		if err != nil {
			if ctx.Err() != nil {
				return ctx.Err()
			}
			if s.logger != nil {
				s.logger.Warn("File status subscriber error", zap.Error(err))
			}
			continue
		}

		var event FileStatusEvent
		if err := json.Unmarshal([]byte(msg.Payload), &event); err != nil {
			if s.logger != nil {
				s.logger.Warn("Invalid file status payload", zap.Error(err))
			}
			continue
		}
		if event.UserID == "" {
			continue
		}
		s.hub.Send(event.UserID, event)
	}
}
