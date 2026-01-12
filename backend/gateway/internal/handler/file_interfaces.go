package handler

import (
	"context"

	"github.com/google/uuid"
	"github.com/sparkle/gateway/internal/service"
)

type FileStorageProvider interface {
	Bucket() string
	MaxUploadSize() int64
	PresignExpirySeconds() int
	PresignPost(ctx context.Context, objectKey string, contentType string, minSize int64, maxSize int64) (string, map[string]string, error)
	PresignGet(ctx context.Context, objectKey string) (string, error)
	PresignPut(ctx context.Context, objectKey string) (string, error)
	DeleteObject(ctx context.Context, bucket string, objectKey string) error
}

type FileMetadataProvider interface {
	CreatePendingFile(ctx context.Context, fileID uuid.UUID, userID uuid.UUID, fileName string, mimeType string, fileSize int64, bucket string, objectKey string) (service.StoredFile, error)
	UpdateFileStatus(ctx context.Context, fileID uuid.UUID, userID uuid.UUID, status string, visibility string) (service.StoredFile, error)
	GetFile(ctx context.Context, fileID uuid.UUID, userID uuid.UUID) (service.StoredFile, error)
	GetFileForGroupView(ctx context.Context, fileID uuid.UUID, groupID uuid.UUID, userID uuid.UUID) (service.StoredFile, error)
	GetFileForGroupDownload(ctx context.Context, fileID uuid.UUID, groupID uuid.UUID, userID uuid.UUID) (service.StoredFile, error)
	ListFiles(ctx context.Context, userID uuid.UUID, status string, limit int, offset int) ([]service.StoredFile, error)
	SearchFiles(ctx context.Context, userID uuid.UUID, query string, limit int) ([]service.StoredFile, error)
	SoftDeleteFile(ctx context.Context, fileID uuid.UUID, userID uuid.UUID) (service.StoredFile, error)
}

type FileProcessingProvider interface {
	TriggerProcessing(ctx context.Context, req service.FileProcessingRequest) error
}
