package service

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/metrics"
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

// Restart backoff bounds for RunWithRestart.
const (
	fileEventRestartBackoffBase = 250 * time.Millisecond
	fileEventRestartBackoffMax  = 5 * time.Second
	fileEventHealthyRunReset    = time.Minute
)

// RunWithRestart runs the subscriber for the lifetime of ctx, restarting the
// pubsub loop after terminal errors AND panics with a capped exponential
// backoff (R2-GW-3: the pre-fix goroutine recovered the panic and then died,
// leaving /ws/files pushes silently dead until process restart). Every
// restart increments sparkle_file_event_subscriber_restarts_total so the
// degraded window is observable and alertable. A run that stayed healthy for
// fileEventHealthyRunReset resets the backoff schedule.
func (s *FileEventSubscriber) RunWithRestart(ctx context.Context) {
	backoff := fileEventRestartBackoffBase
	for {
		start := time.Now()
		runErr := s.runOnce(ctx)
		if ctx.Err() != nil {
			// Deliberate shutdown, not a fault.
			return
		}
		if time.Since(start) >= fileEventHealthyRunReset {
			backoff = fileEventRestartBackoffBase
		}
		metrics.FileEventSubscriberRestarts.Inc()
		if s.logger != nil {
			s.logger.Error("File event subscriber exited; restarting",
				zap.Error(runErr),
				zap.Duration("backoff", backoff),
			)
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(backoff):
		}
		if backoff < fileEventRestartBackoffMax {
			backoff *= 2
			if backoff > fileEventRestartBackoffMax {
				backoff = fileEventRestartBackoffMax
			}
		}
	}
}

// runOnce guards a single Run lifecycle against panics (R2-GW-3), converting
// them into ordinary errors so the restart loop can continue.
func (s *FileEventSubscriber) runOnce(ctx context.Context) (err error) {
	defer func() {
		if r := recover(); r != nil {
			if s.logger != nil {
				s.logger.Error("File event subscriber panicked", zap.Any("panic", r))
			}
			err = fmt.Errorf("file event subscriber panic: %v", r)
		}
	}()
	return s.Run(ctx)
}

func (s *FileEventSubscriber) Run(ctx context.Context) error {
	pubsub := s.redis.Subscribe(ctx, "file_status")
	defer pubsub.Close()

	// go-redis's ReceiveMessage blocks on the socket and does not honor ctx
	// cancellation once the connection is established, so ctx shutdown is
	// implemented by closing the pubsub (which unblocks the receive with a
	// pool-closed error). watchDone prevents the watcher from leaking when
	// Run returns on its own (terminal error → RunWithRestart loop).
	watchDone := make(chan struct{})
	defer func() { close(watchDone) }()
	go func() {
		select {
		case <-ctx.Done():
			_ = pubsub.Close()
		case <-watchDone:
		}
	}()

	for {
		msg, err := pubsub.ReceiveMessage(ctx)
		if err != nil {
			if ctx.Err() != nil {
				return ctx.Err()
			}
			// R2-GW-3: propagate the failure to RunWithRestart instead of
			// busy-looping here (a closed Redis fails dial immediately, so
			// the old warn+continue spun hot) — the restart loop owns retry
			// policy: backoff, restart counter, and recovery.
			return err
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
