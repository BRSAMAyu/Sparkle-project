package service

import (
	"context"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"

	"github.com/sparkle/gateway/internal/db"
)

// UserIdentityService resolves user identity from IDs or emails.
type UserIdentityService interface {
	GetUserByUUID(ctx context.Context, id uuid.UUID) (db.User, error)
	GetUserByEmail(ctx context.Context, email string) (db.User, error)
}

// DBUserIdentityService implements UserIdentityService using sqlc queries.
type DBUserIdentityService struct {
	queries dbQueries
}

type dbQueries interface {
	GetUser(ctx context.Context, id pgtype.UUID) (db.User, error)
	GetUserByEmail(ctx context.Context, email string) (db.User, error)
}

func NewDBUserIdentityService(q *db.Queries) *DBUserIdentityService {
	return &DBUserIdentityService{queries: q}
}

func (s *DBUserIdentityService) GetUserByUUID(ctx context.Context, id uuid.UUID) (db.User, error) {
	return s.queries.GetUser(ctx, pgtype.UUID{Bytes: id, Valid: true})
}

func (s *DBUserIdentityService) GetUserByEmail(ctx context.Context, email string) (db.User, error) {
	return s.queries.GetUserByEmail(ctx, email)
}
