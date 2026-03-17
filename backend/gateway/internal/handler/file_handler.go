package handler

import (
	"bytes"
	"context"
	"errors"
	"io"
	"log"
	"mime"
	"net/http"
	"os"
	"path"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/hashicorp/golang-lru/v2/expirable"
	"github.com/sparkle/gateway/internal/service"
	"golang.org/x/time/rate"
)

// isDevelopmentMode checks if running in development environment
func isDevelopmentModeForErrors() bool {
	env := strings.ToLower(os.Getenv("ENVIRONMENT"))
	return env == "" || env == "dev" || env == "development"
}

// sanitizeError returns a safe error message for client consumption
// In production, internal error details are hidden; in development, full details are shown
func sanitizeError(err error, fallback string) string {
	if err == nil {
		return fallback
	}
	if isDevelopmentModeForErrors() {
		return err.Error()
	}
	// Production: hide internal error details
	log.Printf("[FileHandler] Internal error (hidden from client): %v", err)
	return fallback
}

// sanitizeErrorWithDetail returns sanitized error with optional context
func sanitizeErrorWithDetail(err error, fallback string, detail string) gin.H {
	if err == nil {
		return gin.H{"error": fallback}
	}
	if isDevelopmentModeForErrors() {
		return gin.H{"error": fallback, "detail": err.Error()}
	}
	// Production: log but don't expose details
	log.Printf("[FileHandler] Internal error (hidden from client): %v, context: %s", err, detail)
	return gin.H{"error": fallback}
}

var allowedMimeTypesByExt = map[string]map[string]bool{
	".bin":  {"application/octet-stream": true},
	".csv":  {"text/csv": true},
	".gif":  {"image/gif": true},
	".jpeg": {"image/jpeg": true},
	".jpg":  {"image/jpeg": true},
	".json": {"application/json": true},
	".md":   {"text/markdown": true, "text/plain": true},
	".pdf":  {"application/pdf": true},
	".png":  {"image/png": true},
	".txt":  {"text/plain": true},
	".webp": {"image/webp": true},
	".zip":  {"application/zip": true, "application/x-zip-compressed": true},
	".doc":  {"application/msword": true},
	".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": true},
	".xls":  {"application/vnd.ms-excel": true},
	".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": true},
	".ppt":  {"application/vnd.ms-powerpoint": true},
	".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation": true},
	".svg":  {"image/svg+xml": true},
}

type FileHandler struct {
	storage    FileStorageProvider
	metadata   FileMetadataProvider
	processor  FileProcessingProvider
	limiters   *expirable.LRU[string, *rate.Limiter]
	limitersMu sync.Mutex
}

func NewFileHandler(
	storage FileStorageProvider,
	metadata FileMetadataProvider,
	processor FileProcessingProvider,
) *FileHandler {
	// 使用LRU缓存，最多保存1000个用户的限流器，每个条目5分钟后过期
	return &FileHandler{
		storage:   storage,
		metadata:  metadata,
		processor: processor,
		limiters:  expirable.NewLRU[string, *rate.Limiter](1000, nil, 5*time.Minute),
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
		c.JSON(http.StatusBadRequest, sanitizeError(err, "invalid request body"))
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

	mimeType, err := normalizeMimeType(req.MimeType)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid mime_type"})
		return
	}

	filename := sanitizeFilename(req.Filename)
	ext := strings.ToLower(path.Ext(filename))
	if ext == "" {
		inferredExt, ok := inferExtensionFromMimeType(mimeType)
		if !ok {
			c.JSON(http.StatusBadRequest, gin.H{"error": "unsupported mime_type"})
			return
		}
		ext = inferredExt
	}
	if !isAllowedMimeType(ext, mimeType) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "mime_type does not match filename extension"})
		return
	}
	fileID := uuid.New()
	objectKey := userID.String() + "/" + fileID.String() + "/original" + ext

	record, err := h.metadata.CreatePendingFile(
		c.Request.Context(),
		fileID,
		userID,
		filename,
		mimeType,
		req.FileSize,
		h.storage.Bucket(),
		objectKey,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, sanitizeErrorWithDetail(err, "failed to create file record", "CreatePendingFile"))
		return
	}

	url, fields, err := h.storage.PresignPost(
		c.Request.Context(),
		objectKey,
		mimeType,
		1,
		h.storage.MaxUploadSize(),
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, sanitizeErrorWithDetail(err, "failed to generate upload url", "PresignPost"))
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
		c.JSON(http.StatusBadRequest, sanitizeError(err, "invalid request body"))
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
		return uuid.UUID{}, errors.New("authentication required")
	}
	userID, ok := userIDStr.(string)
	if !ok {
		return uuid.UUID{}, errors.New("invalid authentication")
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

func normalizeMimeType(raw string) (string, error) {
	mediaType, _, err := mime.ParseMediaType(raw)
	if err != nil {
		return "", err
	}
	if !strings.Contains(mediaType, "/") {
		return "", errors.New("invalid mime type")
	}
	return strings.ToLower(mediaType), nil
}

func inferExtensionFromMimeType(mimeType string) (string, bool) {
	for ext, allowed := range allowedMimeTypesByExt {
		if allowed[mimeType] {
			return ext, true
		}
	}
	return "", false
}

func isAllowedMimeType(ext string, mimeType string) bool {
	allowed, ok := allowedMimeTypesByExt[ext]
	if !ok {
		return false
	}
	return allowed[mimeType]
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

	// 使用LRU缓存的Get或Add模式
	limiter, exists := h.limiters.Get(userID)
	if !exists {
		// 10 requests per minute (approx 1 every 6 seconds), burst of 3
		limiter = rate.NewLimiter(rate.Every(time.Minute/10), 3)
		h.limiters.Add(userID, limiter)
	}
	return limiter
}

// validateFileByMagicBytes 通过魔数验证文件内容
// 返回: (是否有效, 错误信息)
func validateFileByMagicBytes(file io.Reader, ext string) (bool, string) {
	// 读取前512字节用于魔数检测
	header := make([]byte, 512)
	n, err := io.ReadFull(file, header)
	if err != nil && err != io.ErrUnexpectedEOF && err != io.EOF {
		return false, "Failed to read file header"
	}
	header = header[:n]

	// 根据扩展名验证魔数
	switch strings.ToLower(ext) {
	case ".pdf":
		// PDF文件以 %PDF- 开头
		if !bytes.HasPrefix(header, []byte("%PDF-")) {
			return false, "Invalid PDF file: missing PDF magic bytes"
		}
	case ".docx":
		// DOCX/XLSX/PPTX都是ZIP格式，以PK\x03\x04开头
		fallthrough
	case ".xlsx":
		fallthrough
	case ".pptx":
		if !bytes.HasPrefix(header, []byte{0x50, 0x4B, 0x03, 0x04}) {
			return false, "Invalid Office document: missing ZIP magic bytes"
		}
	case ".png":
		// PNG以 \x89PNG\r\n\x1a\n 开头
		if !bytes.HasPrefix(header, []byte{0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A}) {
			return false, "Invalid PNG file: missing PNG magic bytes"
		}
	case ".jpg", ".jpeg":
		// JPEG以 \xFF\xD8\xFF 开头
		if !bytes.HasPrefix(header, []byte{0xFF, 0xD8, 0xFF}) {
			return false, "Invalid JPEG file: missing JPEG magic bytes"
		}
	case ".gif":
		// GIF以 GIF87a 或 GIF89a 开头
		if !(bytes.HasPrefix(header, []byte("GIF87a")) || bytes.HasPrefix(header, []byte("GIF89a"))) {
			return false, "Invalid GIF file: missing GIF magic bytes"
		}
	case ".webp":
		// WebP以 RIFF....WEBP 开头
		if len(header) < 12 || !bytes.HasPrefix(header, []byte("RIFF")) {
			return false, "Invalid WebP file: missing RIFF header"
		}
		if !bytes.Equal(header[8:12], []byte("WEBP")) {
			return false, "Invalid WebP file: missing WEBP marker"
		}
	}

	return true, ""
}
