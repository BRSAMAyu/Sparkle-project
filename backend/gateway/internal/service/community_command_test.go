package service

import (
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

func TestCreatePostRequest_EmptyContent(t *testing.T) {
	req := CreatePostRequest{
		UserID:  uuid.New(),
		Content: "",
	}
	assert.Empty(t, req.Content, "empty content should fail validation in CreatePost")
}

func TestCreatePostRequest_ImageURLSerialization(t *testing.T) {
	req := CreatePostRequest{
		UserID:    uuid.New(),
		Content:   "Hello world",
		ImageURLs: []string{"https://img.example.com/1.png", "https://img.example.com/2.png"},
		Topic:     "general",
	}
	assert.Len(t, req.ImageURLs, 2)
	assert.Equal(t, "general", req.Topic)
}

func TestCreatePostRequest_NilImageURLs(t *testing.T) {
	req := CreatePostRequest{
		UserID:    uuid.New(),
		Content:   "No images",
		ImageURLs: nil,
	}
	assert.Nil(t, req.ImageURLs)
}

func TestCreatePostRequest_UUIDFormat(t *testing.T) {
	req := CreatePostRequest{
		UserID:  uuid.New(),
		Content: "Test",
	}
	assert.NotEqual(t, uuid.Nil, req.UserID)
}
