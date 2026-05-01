package service

import (
	"context"
	"encoding/json"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

type FileStatusEvent struct {
	Type            string `json:"type"`
	FileID          string `json:"file_id"`
	UserID          string `json:"user_id"`
	Status          string `json:"status"`
	Stage           string `json:"stage,omitempty"`
	Progress        int    `json:"progress"`
	ProgressPercent int    `json:"progress_percent,omitempty"`
	JobID           string `json:"job_id,omitempty"`
	NodesFound      *int   `json:"nodes_found,omitempty"`
	Error           string `json:"error,omitempty"`
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
		event.normalize()
		s.hub.Send(event.UserID, event)
	}
}

func (e *FileStatusEvent) normalize() {
	if e.ProgressPercent == 0 && e.Progress > 0 {
		e.ProgressPercent = e.Progress
	}
	if e.Progress == 0 && e.ProgressPercent > 0 {
		e.Progress = e.ProgressPercent
	}
	if e.Stage == "" {
		e.Stage = documentStage(e.Status, e.ProgressPercent)
	}
	if e.Status == "processing" {
		e.Status = e.Stage
	}
	if e.Status == "processed" {
		e.Status = "done"
	}
}

func documentStage(status string, progress int) string {
	switch status {
	case "failed":
		return "failed"
	case "processed", "done":
		return "done"
	case "uploading", "uploaded", "queued":
		return "queued"
	}
	if progress < 25 {
		return "extracting"
	}
	if progress < 70 {
		return "embedding"
	}
	return "building_nodes"
}
