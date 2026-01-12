package service

import (
	"context"
	"time"

	"github.com/sparkle/gateway/internal/config"
	"go.uber.org/zap"
)

type FileGCService struct {
	metadata *FileMetadataService
	storage  *FileStorageService
	interval time.Duration
	grace    time.Duration
	batch    int
	logger   *zap.Logger
}

func NewFileGCService(
	metadata *FileMetadataService,
	storage *FileStorageService,
	cfg *config.Config,
	logger *zap.Logger,
) *FileGCService {
	interval := time.Duration(cfg.FileGCIntervalMinutes) * time.Minute
	if interval <= 0 {
		interval = time.Hour
	}
	grace := time.Duration(cfg.FileGCGraceHours) * time.Hour
	if grace <= 0 {
		grace = 24 * time.Hour
	}

	return &FileGCService{
		metadata: metadata,
		storage:  storage,
		interval: interval,
		grace:    grace,
		batch:    cfg.FileGCBatchSize,
		logger:   logger,
	}
}

func (s *FileGCService) Run(ctx context.Context) error {
	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			s.cleanupOnce(ctx)
		}
	}
}

func (s *FileGCService) cleanupOnce(ctx context.Context) {
	cutoff := time.Now().Add(-s.grace)
	files, err := s.metadata.ListStaleFiles(ctx, cutoff, s.batch)
	if err != nil {
		if s.logger != nil {
			s.logger.Warn("File GC query failed", zap.Error(err))
		}
		return
	}

	for _, file := range files {
		if err := s.storage.DeleteObject(ctx, file.Bucket, file.ObjectKey); err != nil {
			if s.logger != nil {
				s.logger.Warn("File GC delete object failed", zap.String("object_key", file.ObjectKey), zap.Error(err))
			}
			continue
		}
		if err := s.metadata.HardDeleteFile(ctx, file.ID); err != nil {
			if s.logger != nil {
				s.logger.Warn("File GC delete metadata failed", zap.String("file_id", file.ID.String()), zap.Error(err))
			}
		}
	}
}
