package service

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
)

type PreferencesUpdatedPayload struct {
	UserID            string   `json:"user_id"`
	PreferenceVersion int      `json:"preference_version"`
	ChangedKeys       []string `json:"changed_keys"`
	UpdatedAt         int64    `json:"updated_at"`
	Source            string   `json:"source"` // "explicit" | "inferred"
}

type UserPreferencesService struct {
	pool       *pgxpool.Pool
	unitOfWork *outbox.UnitOfWork
	redis      *redis.Client
}

func NewUserPreferencesService(pool *pgxpool.Pool, redis *redis.Client) *UserPreferencesService {
	return &UserPreferencesService{
		pool:       pool,
		unitOfWork: outbox.NewUnitOfWork(pool),
		redis:      redis,
	}
}

// UpdatePreferences 更新偏好并发布事件
func (s *UserPreferencesService) UpdatePreferences(
	ctx context.Context,
	userID uuid.UUID,
	updates map[string]interface{},
) error {
	if len(updates) == 0 {
		return nil
	}

	updatesJSON, err := json.Marshal(updates)
	if err != nil {
		return err
	}

	var newVersion int
	err = s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		err := txCtx.QueryRow(ctx, `
			UPDATE user_preferences_center
			SET explicit = explicit || $2::jsonb,
				version = version + 1,
				last_explicit_update = NOW(),
				updated_at = NOW()
			WHERE user_id = $1
			RETURNING version
		`, userID, updatesJSON).Scan(&newVersion)
		if err != nil {
			return err
		}

		changedKeys := make([]string, 0, len(updates))
		for key := range updates {
			changedKeys = append(changedKeys, key)
		}

		payload := PreferencesUpdatedPayload{
			UserID:            userID.String(),
			PreferenceVersion: newVersion,
			ChangedKeys:       changedKeys,
			UpdatedAt:         time.Now().UnixMilli(),
			Source:            "explicit",
		}

		payloadBytes, err := json.Marshal(payload)
		if err != nil {
			return err
		}

		evt := event.NewDomainEvent(
			event.EventPreferencesUpdated,
			event.AggregateUser,
			userID,
			map[string]interface{}{"data": string(payloadBytes)},
			event.EventMetadata{UserID: userID, Source: "user_preferences_service"},
		)

		return txCtx.SaveEventToOutbox(ctx, &evt)
	})
	if err != nil {
		return err
	}

	s.invalidateCache(ctx, userID)

	return nil
}

func (s *UserPreferencesService) invalidateCache(ctx context.Context, userID uuid.UUID) {
	if s.redis == nil {
		return
	}

	keys := []string{
		fmt.Sprintf("user:context:%s", userID),
		fmt.Sprintf("user:context:snapshot:%s", userID),
		fmt.Sprintf("user:prefs:center:%s", userID),
		fmt.Sprintf("user:preferences:%s", userID),
		fmt.Sprintf("user:analytics:%s", userID),
		fmt.Sprintf("user:stats:%s", userID),
	}
	s.redis.Del(ctx, keys...)
}
