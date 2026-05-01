package service

import (
	"context"
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/db"
)

type dataConsistencyStore interface {
	GetMessageByID(ctx context.Context, arg db.GetMessageByIDParams) (db.ChatMessage, error)
}

type dataConsistencyCache interface {
	LRange(ctx context.Context, key string, start, stop int64) *redis.StringSliceCmd
}

type DataConsistencyService struct {
	chatHistory *ChatHistoryService
	store       dataConsistencyStore
	cache       dataConsistencyCache
}

type CacheMessageResult struct {
	Exists  bool
	Message map[string]interface{}
}

type DatabaseMessageResult struct {
	Exists  bool
	Message map[string]interface{}
}

func NewDataConsistencyService(chatHistory *ChatHistoryService, queries *db.Queries, cache *redis.Client) *DataConsistencyService {
	return &DataConsistencyService{
		chatHistory: chatHistory,
		store:       queries,
		cache:       cache,
	}
}

func (s *DataConsistencyService) CheckCache(ctx context.Context, messageID, conversationID string) (CacheMessageResult, error) {
	cacheKey := "chat:history:" + conversationID
	result, err := s.cache.LRange(ctx, cacheKey, 0, -1).Result()
	if err != nil {
		return CacheMessageResult{}, err
	}

	for _, msg := range result {
		var msgData map[string]interface{}
		if err := json.Unmarshal([]byte(msg), &msgData); err != nil {
			continue
		}

		if msgID, ok := msgData["id"].(string); ok && msgID == messageID {
			return CacheMessageResult{Exists: true, Message: msgData}, nil
		}
	}

	return CacheMessageResult{Exists: false}, nil
}

func (s *DataConsistencyService) CheckDatabase(ctx context.Context, messageID, conversationID uuid.UUID) (DatabaseMessageResult, error) {
	pgMessageID := uuidToPgtype(messageID)
	pgSessionID := uuidToPgtype(conversationID)

	message, err := s.store.GetMessageByID(ctx, db.GetMessageByIDParams{
		ID:        pgMessageID,
		SessionID: pgSessionID,
	})
	if err != nil {
		return DatabaseMessageResult{Exists: false}, nil
	}

	return DatabaseMessageResult{
		Exists: true,
		Message: map[string]interface{}{
			"id":              message.ID.String(),
			"conversation_id": message.SessionID.String(),
			"role":            message.Role,
			"content":         message.Content,
			"timestamp":       message.CreatedAt.Time.Format(time.RFC3339),
		},
	}, nil
}

func uuidToPgtype(id uuid.UUID) pgtype.UUID {
	var pgID pgtype.UUID
	copy(pgID.Bytes[:], id[:])
	pgID.Valid = true
	return pgID
}
