package service

import (
	"context"
	"testing"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/db"
)

type mockQueries struct {
	userByEmail db.User
	userByUUID  db.User
	errByEmail  error
	errByUUID   error
}

func (m *mockQueries) GetUser(_ context.Context, _ pgtype.UUID) (db.User, error) {
	return m.userByUUID, m.errByUUID
}

func (m *mockQueries) GetUserByEmail(_ context.Context, _ string) (db.User, error) {
	return m.userByEmail, m.errByEmail
}

func TestDBUserIdentityService_GetUserByUUID(t *testing.T) {
	id := uuid.New()
	svc := &DBUserIdentityService{queries: &mockQueries{userByUUID: db.User{ID: pgtype.UUID{Bytes: id, Valid: true}}}}

	user, err := svc.GetUserByUUID(context.Background(), id)
	require.NoError(t, err)
	assert.Equal(t, id[:], user.ID.Bytes[:])
}

func TestDBUserIdentityService_GetUserByEmail(t *testing.T) {
	svc := &DBUserIdentityService{queries: &mockQueries{userByEmail: db.User{Email: "test@example.com"}}}

	user, err := svc.GetUserByEmail(context.Background(), "test@example.com")
	require.NoError(t, err)
	assert.Equal(t, "test@example.com", user.Email)
}
