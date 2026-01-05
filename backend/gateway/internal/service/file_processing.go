package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type FileProcessingRequest struct {
	FileID             string `json:"file_id"`
	UserID             string `json:"user_id"`
	DownloadURL        string `json:"download_url"`
	FileName           string `json:"file_name"`
	MimeType           string `json:"mime_type"`
	ThumbnailUploadURL string `json:"thumbnail_upload_url,omitempty"`
}

type FileProcessingClient struct {
	baseURL        string
	internalAPIKey string
	httpClient     *http.Client
}

func NewFileProcessingClient(baseURL string, internalAPIKey string) *FileProcessingClient {
	return &FileProcessingClient{
		baseURL:        strings.TrimRight(baseURL, "/"),
		internalAPIKey: internalAPIKey,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (c *FileProcessingClient) TriggerProcessing(ctx context.Context, payload FileProcessingRequest) error {
	if c == nil || c.baseURL == "" {
		return nil
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/api/v1/files/process", bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.internalAPIKey != "" {
		req.Header.Set("X-Internal-Token", c.internalAPIKey)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("file processing trigger failed: %s", resp.Status)
	}
	return nil
}
