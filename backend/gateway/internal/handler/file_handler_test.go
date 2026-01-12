package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/sparkle/gateway/internal/service"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// Mocks

type MockFileStorage struct {
	mock.Mock
}

func (m *MockFileStorage) Bucket() string {
	args := m.Called()
	return args.String(0)
}

func (m *MockFileStorage) MaxUploadSize() int64 {
	args := m.Called()
	return args.Get(0).(int64)
}

func (m *MockFileStorage) PresignExpirySeconds() int {
	args := m.Called()
	return args.Int(0)
}

func (m *MockFileStorage) PresignPost(ctx context.Context, objectKey string, contentType string, minSize int64, maxSize int64) (string, map[string]string, error) {
	args := m.Called(ctx, objectKey, contentType, minSize, maxSize)
	return args.String(0), args.Get(1).(map[string]string), args.Error(2)
}

func (m *MockFileStorage) PresignGet(ctx context.Context, objectKey string) (string, error) {
	args := m.Called(ctx, objectKey)
	return args.String(0), args.Error(1)
}

func (m *MockFileStorage) PresignPut(ctx context.Context, objectKey string) (string, error) {
	args := m.Called(ctx, objectKey)
	return args.String(0), args.Error(1)
}

func (m *MockFileStorage) DeleteObject(ctx context.Context, bucket string, objectKey string) error {
	args := m.Called(ctx, bucket, objectKey)
	return args.Error(0)
}

type MockFileMetadata struct {
	mock.Mock
}

func (m *MockFileMetadata) CreatePendingFile(ctx context.Context, fileID uuid.UUID, userID uuid.UUID, fileName string, mimeType string, fileSize int64, bucket string, objectKey string) (service.StoredFile, error) {
	args := m.Called(ctx, fileID, userID, fileName, mimeType, fileSize, bucket, objectKey)
	return args.Get(0).(service.StoredFile), args.Error(1)
}

func (m *MockFileMetadata) UpdateFileStatus(ctx context.Context, fileID uuid.UUID, userID uuid.UUID, status string, visibility string) (service.StoredFile, error) {
	args := m.Called(ctx, fileID, userID, status, visibility)
	return args.Get(0).(service.StoredFile), args.Error(1)
}

func (m *MockFileMetadata) GetFile(ctx context.Context, fileID uuid.UUID, userID uuid.UUID) (service.StoredFile, error) {
	args := m.Called(ctx, fileID, userID)
	return args.Get(0).(service.StoredFile), args.Error(1)
}

func (m *MockFileMetadata) GetFileForGroupView(ctx context.Context, fileID uuid.UUID, groupID uuid.UUID, userID uuid.UUID) (service.StoredFile, error) {
	args := m.Called(ctx, fileID, groupID, userID)
	return args.Get(0).(service.StoredFile), args.Error(1)
}

func (m *MockFileMetadata) GetFileForGroupDownload(ctx context.Context, fileID uuid.UUID, groupID uuid.UUID, userID uuid.UUID) (service.StoredFile, error) {
	args := m.Called(ctx, fileID, groupID, userID)
	return args.Get(0).(service.StoredFile), args.Error(1)
}

func (m *MockFileMetadata) ListFiles(ctx context.Context, userID uuid.UUID, status string, limit int, offset int) ([]service.StoredFile, error) {
	args := m.Called(ctx, userID, status, limit, offset)
	return args.Get(0).([]service.StoredFile), args.Error(1)
}

func (m *MockFileMetadata) SearchFiles(ctx context.Context, userID uuid.UUID, query string, limit int) ([]service.StoredFile, error) {
	args := m.Called(ctx, userID, query, limit)
	return args.Get(0).([]service.StoredFile), args.Error(1)
}

func (m *MockFileMetadata) SoftDeleteFile(ctx context.Context, fileID uuid.UUID, userID uuid.UUID) (service.StoredFile, error) {
	args := m.Called(ctx, fileID, userID)
	return args.Get(0).(service.StoredFile), args.Error(1)
}

type MockFileProcessing struct {
	mock.Mock
}

func (m *MockFileProcessing) TriggerProcessing(ctx context.Context, req service.FileProcessingRequest) error {
	args := m.Called(ctx, req)
	return args.Error(0)
}

func setupTest() (*gin.Engine, *MockFileStorage, *MockFileMetadata, *MockFileProcessing) {
	gin.SetMode(gin.TestMode)
	r := gin.New()

	mockStorage := new(MockFileStorage)
	mockMetadata := new(MockFileMetadata)
	mockProcessor := new(MockFileProcessing)

	h := NewFileHandler(mockStorage, mockMetadata, mockProcessor)

	authMiddleware := func(c *gin.Context) {
		c.Set("user_id", "550e8400-e29b-41d4-a716-446655440000")
		c.Next()
	}

	h.RegisterRoutes(r.Group("/api/v1"), authMiddleware)

	return r, mockStorage, mockMetadata, mockProcessor
}

func TestPrepareUpload(t *testing.T) {
	userID, _ := uuid.Parse("550e8400-e29b-41d4-a716-446655440000")

	t.Run("Success", func(t *testing.T) {
		r, mockStorage, mockMetadata, _ := setupTest()
		reqBody := PrepareUploadRequest{
			Filename: "test.png",
			FileSize: 1024,
			MimeType: "image/png",
		}
		body, _ := json.Marshal(reqBody)

		mockStorage.On("MaxUploadSize").Return(int64(10 * 1024 * 1024))
		mockStorage.On("Bucket").Return("sparkle-files")
		mockStorage.On("PresignExpirySeconds").Return(600)

		fileID := mock.MatchedBy(func(id uuid.UUID) bool { return true })
		objectKey := mock.MatchedBy(func(key string) bool { return true })

		mockMetadata.On("CreatePendingFile", mock.Anything, fileID, userID, "test.png", "image/png", int64(1024), "sparkle-files", objectKey).
			Return(service.StoredFile{
				ID:        uuid.New(),
				Bucket:    "sparkle-files",
				ObjectKey: "some-key",
			}, nil)

		mockStorage.On("PresignPost", mock.Anything, objectKey, "image/png", int64(1), int64(10*1024*1024)).
			Return("https://s3.example.com/upload", map[string]string{"key": "val"}, nil)

		req, _ := http.NewRequest(http.MethodPost, "/api/v1/files/upload/prepare", bytes.NewReader(body))
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		var resp map[string]interface{}
		json.Unmarshal(w.Body.Bytes(), &resp)
		assert.Contains(t, resp, "presigned_url")
	})

	t.Run("Invalid File Size", func(t *testing.T) {
		r, _, _, _ := setupTest()
		reqBody := PrepareUploadRequest{
			Filename: "test.png",
			FileSize: 0,
			MimeType: "image/png",
		}
		body, _ := json.Marshal(reqBody)

		req, _ := http.NewRequest(http.MethodPost, "/api/v1/files/upload/prepare", bytes.NewReader(body))
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})

	t.Run("Exceed Max Size", func(t *testing.T) {
		r, mockStorage, _, _ := setupTest()
		reqBody := PrepareUploadRequest{
			Filename: "test.png",
			FileSize: 100 * 1024 * 1024,
			MimeType: "image/png",
		}
		body, _ := json.Marshal(reqBody)

		mockStorage.On("MaxUploadSize").Return(int64(10 * 1024 * 1024))

		req, _ := http.NewRequest(http.MethodPost, "/api/v1/files/upload/prepare", bytes.NewReader(body))
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
		assert.Contains(t, w.Body.String(), "exceeds limit")
	})
}

func TestCompleteUpload(t *testing.T) {
	userID, _ := uuid.Parse("550e8400-e29b-41d4-a716-446655440000")
	fileID := uuid.New()

	t.Run("Success", func(t *testing.T) {
		r, mockStorage, mockMetadata, mockProcessor := setupTest()
		reqBody := CompleteUploadRequest{
			UploadID: fileID.String(),
		}
		body, _ := json.Marshal(reqBody)

		record := service.StoredFile{
			ID:        fileID,
			UserID:    userID,
			FileName:  "test.png",
			ObjectKey: "user/file/original.png",
			Status:    "uploaded",
		}

		mockMetadata.On("UpdateFileStatus", mock.Anything, fileID, userID, "uploaded", "private").
			Return(record, nil)

		mockStorage.On("PresignGet", mock.Anything, record.ObjectKey).Return("https://download.url", nil)
		mockStorage.On("PresignPut", mock.Anything, mock.Anything).Return("https://thumbnail.url", nil)

		mockProcessor.On("TriggerProcessing", mock.Anything, mock.MatchedBy(func(req service.FileProcessingRequest) bool {
			return req.FileID == fileID.String()
		})).Return(nil)

		req, _ := http.NewRequest(http.MethodPost, "/api/v1/files/upload/complete", bytes.NewReader(body))
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		// Wait a bit for the goroutine to trigger processor (actually we just want to ensure it doesn't crash)
		time.Sleep(50 * time.Millisecond)
	})

	t.Run("Invalid Upload ID", func(t *testing.T) {
		r, _, _, _ := setupTest()
		reqBody := CompleteUploadRequest{
			UploadID: "invalid-uuid",
		}
		body, _ := json.Marshal(reqBody)

		req, _ := http.NewRequest(http.MethodPost, "/api/v1/files/upload/complete", bytes.NewReader(body))
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})
}

func TestGetFile(t *testing.T) {
	userID, _ := uuid.Parse("550e8400-e29b-41d4-a716-446655440000")
	fileID := uuid.New()

	t.Run("Success", func(t *testing.T) {
		r, _, mockMetadata, _ := setupTest()
		mockMetadata.On("GetFile", mock.Anything, fileID, userID).
			Return(service.StoredFile{ID: fileID, UserID: userID, FileName: "test.txt"}, nil)

		req, _ := http.NewRequest(http.MethodGet, "/api/v1/files/"+fileID.String(), nil)
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("Not Found", func(t *testing.T) {
		r, _, mockMetadata, _ := setupTest()
		mockMetadata.On("GetFile", mock.Anything, fileID, userID).
			Return(service.StoredFile{}, errors.New("not found"))

		req, _ := http.NewRequest(http.MethodGet, "/api/v1/files/"+fileID.String(), nil)
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)

		assert.Equal(t, http.StatusNotFound, w.Code)
	})
}
