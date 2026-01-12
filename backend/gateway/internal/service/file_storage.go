package service

import (
	"context"
	"errors"
	"time"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/sparkle/gateway/internal/config"
	"go.uber.org/zap"
)

type FileStorageService struct {
	client        *minio.Client
	bucket        string
	presignExpiry time.Duration
	maxUploadSize int64
}

func NewFileStorageService(cfg *config.Config, logger *zap.Logger) (*FileStorageService, error) {
	client, err := minio.New(cfg.MinioEndpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(cfg.MinioAccessKey, cfg.MinioSecretKey, ""),
		Secure: cfg.MinioUseSSL,
		Region: cfg.MinioRegion,
	})
	if err != nil {
		return nil, err
	}

	service := &FileStorageService{
		client:        client,
		bucket:        cfg.MinioBucket,
		presignExpiry: time.Duration(cfg.FilePresignExpiresSeconds) * time.Second,
		maxUploadSize: cfg.FileMaxUploadSize,
	}
	if service.maxUploadSize <= 0 {
		service.maxUploadSize = 52428800
	}
	if service.presignExpiry <= 0 {
		service.presignExpiry = 7 * time.Minute
	}

	if cfg.MinioAutoCreateBucket {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		exists, err := client.BucketExists(ctx, cfg.MinioBucket)
		if err != nil {
			return nil, err
		}
		if !exists {
			if err := client.MakeBucket(ctx, cfg.MinioBucket, minio.MakeBucketOptions{Region: cfg.MinioRegion}); err != nil {
				if logger != nil {
					logger.Warn("Failed to create MinIO bucket", zap.Error(err))
				}
				return nil, err
			}
		}
	}

	return service, nil
}

func (s *FileStorageService) Bucket() string {
	return s.bucket
}

func (s *FileStorageService) MaxUploadSize() int64 {
	return s.maxUploadSize
}

func (s *FileStorageService) PresignExpirySeconds() int {
	return int(s.presignExpiry.Seconds())
}

func (s *FileStorageService) PresignPost(
	ctx context.Context,
	objectKey string,
	contentType string,
	minSize int64,
	maxSize int64,
) (string, map[string]string, error) {
	if minSize < 1 {
		minSize = 1
	}
	if maxSize < minSize {
		maxSize = minSize
	}
	if maxSize > s.maxUploadSize {
		maxSize = s.maxUploadSize
	}

	policy := minio.NewPostPolicy()
	policy.SetBucket(s.bucket)
	policy.SetKey(objectKey)
	policy.SetExpires(time.Now().Add(s.presignExpiry))
	policy.SetContentLengthRange(minSize, maxSize)
	if contentType != "" {
		policy.SetContentType(contentType)
	}

	url, formData, err := s.client.PresignedPostPolicy(ctx, policy)
	if err != nil {
		return "", nil, err
	}
	return url.String(), formData, nil
}

func (s *FileStorageService) PresignGet(ctx context.Context, objectKey string) (string, error) {
	url, err := s.client.PresignedGetObject(ctx, s.bucket, objectKey, s.presignExpiry, nil)
	if err != nil {
		return "", err
	}
	return url.String(), nil
}

func (s *FileStorageService) PresignPut(ctx context.Context, objectKey string) (string, error) {
	url, err := s.client.PresignedPutObject(ctx, s.bucket, objectKey, s.presignExpiry)
	if err != nil {
		return "", err
	}
	return url.String(), nil
}

func (s *FileStorageService) DeleteObject(ctx context.Context, bucket string, objectKey string) error {
	if bucket == "" {
		bucket = s.bucket
	}
	opts := minio.RemoveObjectOptions{}
	err := s.client.RemoveObject(ctx, bucket, objectKey, opts)
	if err == nil {
		return nil
	}

	var resp minio.ErrorResponse
	if errors.As(err, &resp) && resp.Code == "NoSuchKey" {
		return nil
	}
	return err
}
