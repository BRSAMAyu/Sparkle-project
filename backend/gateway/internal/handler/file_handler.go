package handler

import (
	"context"
	"errors"
	"net/http"
	"path"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/sparkle/gateway/internal/service"
	"golang.org/x/time/rate"
)

type FileHandler struct {
	storage    FileStorageProvider
	metadata   FileMetadataProvider
	processor  FileProcessingProvider
	limiters   map[string]*rate.Limiter
	limitersMu sync.Mutex
}

func NewFileHandler(
	storage FileStorageProvider,
	metadata FileMetadataProvider,
	processor FileProcessingProvider,
) *FileHandler {
	return &FileHandler{
		storage:    storage,
		metadata:   metadata,
		processor:  processor,
		limiters:   make(map[string]*rate.Limiter),
	}
}

func (h *FileHandler) RegisterRoutes(router *gin.RouterGroup, authMiddleware gin.HandlerFunc) {
	files := router.Group("/files", authMiddleware)
	{
		files.POST("/upload/prepare", h.PrepareUpload)
		files.POST("/upload/complete", h.CompleteUpload)
		files.GET("/:file_id", h.GetFile)
		files.GET("/:file_id/download", h.GetDownloadURL)
		files.GET("/:file_id/thumbnail", h.GetThumbnailURL)
	}

	me := router.Group("/me", authMiddleware)
	{
		me.GET("/files", h.ListMyFiles)
		me.GET("/files/search", h.SearchMyFiles)
		me.DELETE("/files/:file_id", h.DeleteMyFile)
	}
}

type PrepareUploadRequest struct {
	Filename string `json:"filename" binding:"required"`
	FileSize int64  `json:"file_size" binding:"required"`
	MimeType string `json:"mime_type" binding:"required"`
}

type CompleteUploadRequest struct {
	UploadID   string `json:"upload_id" binding:"required"`
	GroupID    string `json:"group_id"`
	Visibility string `json:"visibility"`
}

type FileResponse struct {
	ID         string    `json:"id"`
	UserID     string    `json:"user_id"`
	FileName   string    `json:"file_name"`
	MimeType   string    `json:"mime_type"`
	FileSize   int64     `json:"file_size"`
	Bucket     string    `json:"bucket"`
	ObjectKey  string    `json:"object_key"`
	Status     string    `json:"status"`
	Visibility string    `json:"visibility"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}

func (h *FileHandler) PrepareUpload(c *gin.Context) {
	userID, err := getUserID(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}

	// Rate limiting: 10 uploads per minute per user
	limiter := h.getLimiter(userID.String())
	if !limiter.Allow() {
		c.JSON(http.StatusTooManyRequests, gin.H{"error": "upload rate limit exceeded"})
		return
	}

	var req PrepareUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.FileSize <= 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file_size must be positive"})
		return
	}
	if req.FileSize > h.storage.MaxUploadSize() {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file_size exceeds limit"})
		return
	}

	filename := sanitizeFilename(req.Filename)
	ext := strings.ToLower(path.Ext(filename))
	if ext == "" {
		ext = ".bin"
	}
	fileID := uuid.New()
	objectKey := userID.String() + "/" + fileID.String() + "/original" + ext

	record, err := h.metadata.CreatePendingFile(
		c.Request.Context(),
		fileID,
		userID,
		filename,
		req.MimeType,
		req.FileSize,
		h.storage.Bucket(),
		objectKey,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create file record"})
		return
	}

	url, fields, err := h.storage.PresignPost(
		c.Request.Context(),
		objectKey,
		req.MimeType,
		1,
		h.storage.MaxUploadSize(),
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate upload url"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"upload_id":     record.ID.String(),
		"file_id":       record.ID.String(),
		"presigned_url": url,
		"expires_in":    h.storage.PresignExpirySeconds(),
		"fields":        fields,
		"bucket":        record.Bucket,
		"object_key":    record.ObjectKey,
	})
}

func (h *FileHandler) CompleteUpload(c *gin.Context) {
	userID, err := getUserID(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}

	var req CompleteUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	fileID, err := uuid.Parse(req.UploadID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid upload_id"})
		return
	}
	visibility := req.Visibility
	if visibility == "" {
		visibility = "private"
	}

	record, err := h.metadata.UpdateFileStatus(c.Request.Context(), fileID, userID, "uploaded", visibility)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update file status"})
		return
	}

	if h.processor != nil {
		downloadURL, err := h.storage.PresignGet(c.Request.Context(), record.ObjectKey)
		if err == nil {
			thumbnailKey := fileID.String() + "/thumbnail.jpg"
			thumbnailURL, thumbErr := h.storage.PresignPut(c.Request.Context(), thumbnailKey)
			if thumbErr != nil {
				thumbnailURL = ""
			}
			payload := service.FileProcessingRequest{
				FileID:             record.ID.String(),
				UserID:             record.UserID.String(),
				DownloadURL:        downloadURL,
				FileName:           record.FileName,
				MimeType:           record.MimeType,
				ThumbnailUploadURL: thumbnailURL,
			}
			go func() {
				if err := h.processor.TriggerProcessing(context.Background(), payload); err != nil {
					_ = err
				}
			}()
		}
	}

	c.JSON(http.StatusOK, fileToResponse(record))
}

func (h *FileHandler) GetFile(c *gin.Context) {
	userID, err := getUserID(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}
	fileID, err := uuid.Parse(c.Param("file_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid file_id"})
		return
	}
	var record service.StoredFile
	groupIDParam := c.Query("group_id")
	if groupIDParam != "" {
		groupID, parseErr := uuid.Parse(groupIDParam)
		if parseErr != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid group_id"})
			return
		}
		record, err = h.metadata.GetFileForGroupView(c.Request.Context(), fileID, groupID, userID)
	} else {
		record, err = h.metadata.GetFile(c.Request.Context(), fileID, userID)
	}
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "file not found"})
		return
	}

	c.JSON(http.StatusOK, fileToResponse(record))
}

func (h *FileHandler) GetDownloadURL(c *gin.Context) {
	userID, err := getUserID(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}
	fileID, err := uuid.Parse(c.Param("file_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid file_id"})
		return
	}

	var record service.StoredFile
	groupIDParam := c.Query("group_id")
	if groupIDParam != "" {
		groupID, parseErr := uuid.Parse(groupIDParam)
		if parseErr != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid group_id"})
			return
		}
		record, err = h.metadata.GetFileForGroupDownload(c.Request.Context(), fileID, groupID, userID)
	} else {
		record, err = h.metadata.GetFile(c.Request.Context(), fileID, userID)
	}
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "file not found"})
		return
	}

	url, err := h.storage.PresignGet(c.Request.Context(), record.ObjectKey)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate download url"})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"download_url": url,
		"expires_in":   h.storage.PresignExpirySeconds(),
	})
}

func (h *FileHandler) GetThumbnailURL(c *gin.Context) {
	userID, err := getUserID(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}
	fileID, err := uuid.Parse(c.Param("file_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid file_id"})
		return
	}

	groupIDParam := c.Query("group_id")
	if groupIDParam != "" {
		groupID, parseErr := uuid.Parse(groupIDParam)
		if parseErr != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid group_id"})
			return
		}
		_, err = h.metadata.GetFileForGroupView(c.Request.Context(), fileID, groupID, userID)
	} else {
		_, err = h.metadata.GetFile(c.Request.Context(), fileID, userID)
	}
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "file not found"})
		return
	}

	thumbnailKey := fileID.String() + "/thumbnail.jpg"
	url, err := h.storage.PresignGet(c.Request.Context(), thumbnailKey)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate thumbnail url"})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"thumbnail_url": url,
		"expires_in":    h.storage.PresignExpirySeconds(),
	})
}

func (h *FileHandler) ListMyFiles(c *gin.Context) {
	userID, err := getUserID(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}

	limit := parseIntQuery(c, "limit", 20)
	offset := parseIntQuery(c, "offset", 0)
	status := c.Query("status")

	files, err := h.metadata.ListFiles(c.Request.Context(), userID, status, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list files"})
		return
	}

	resp := make([]FileResponse, 0, len(files))
	for _, file := range files {
		resp = append(resp, fileToResponse(file))
	}
	c.JSON(http.StatusOK, resp)
}

func (h *FileHandler) DeleteMyFile(c *gin.Context) {
	userID, err := getUserID(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}
	fileID, err := uuid.Parse(c.Param("file_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid file_id"})
		return
	}

	record, err := h.metadata.SoftDeleteFile(c.Request.Context(), fileID, userID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "file not found"})
		return
	}

	if err := h.storage.DeleteObject(c.Request.Context(), record.Bucket, record.ObjectKey); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete object"})
		return
	}

	c.JSON(http.StatusOK, fileToResponse(record))
}

func (h *FileHandler) SearchMyFiles(c *gin.Context) {
	userID, err := getUserID(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}
	query := strings.TrimSpace(c.Query("q"))
	if query == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "q is required"})
		return
	}
	limit := parseIntQuery(c, "limit", 20)

	files, err := h.metadata.SearchFiles(c.Request.Context(), userID, query, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to search files"})
		return
	}

	resp := make([]FileResponse, 0, len(files))
	for _, file := range files {
		resp = append(resp, fileToResponse(file))
	}
	c.JSON(http.StatusOK, resp)
}

func fileToResponse(file service.StoredFile) FileResponse {
	return FileResponse{
		ID:         file.ID.String(),
		UserID:     file.UserID.String(),
		FileName:   file.FileName,
		MimeType:   file.MimeType,
		FileSize:   file.FileSize,
		Bucket:     file.Bucket,
		ObjectKey:  file.ObjectKey,
		Status:     file.Status,
		Visibility: file.Visibility,
		CreatedAt:  file.CreatedAt,
		UpdatedAt:  file.UpdatedAt,
	}
}

func getUserID(c *gin.Context) (uuid.UUID, error) {
	userIDStr, exists := c.Get("user_id")
	if !exists {
		return uuid.UUID{}, errors.New("missing user id")
	}
	userID, ok := userIDStr.(string)
	if !ok {
		return uuid.UUID{}, errors.New("invalid user id type")
	}
	return uuid.Parse(userID)
}

func sanitizeFilename(name string) string {
	base := path.Base(strings.TrimSpace(name))
	if base == "" || base == "." || base == "/" {
		return "file"
	}
	return base
}

func parseIntQuery(c *gin.Context, key string, fallback int) int {
	value := c.DefaultQuery(key, "")
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func (h *FileHandler) getLimiter(userID string) *rate.Limiter {
	h.limitersMu.Lock()
	defer h.limitersMu.Unlock()

	limiter, exists := h.limiters[userID]
	if !exists {
		// 10 requests per minute (approx 1 every 6 seconds), burst of 3
		limiter = rate.NewLimiter(rate.Every(time.Minute/10), 3)
		h.limiters[userID] = limiter
	}
	return limiter
}
