package service

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"log"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/db"
)

var (
	ErrAppleUserCreateFailed = errors.New("apple user create failed")
	ErrAppleUserLinkFailed   = errors.New("apple user link failed")
)

type appleAccountStore interface {
	GetUserByAppleID(ctx context.Context, appleID pgtype.Text) (db.User, error)
	GetUserByEmail(ctx context.Context, email string) (db.User, error)
	CreateSocialUser(ctx context.Context, arg db.CreateSocialUserParams) (db.User, error)
	LinkAppleUser(ctx context.Context, arg db.LinkAppleUserParams) (db.User, error)
	UpdateUserLastLogin(ctx context.Context, id pgtype.UUID) error
	UpsertUserSession(ctx context.Context, arg db.UpsertUserSessionParams) (db.UserSession, error)
}

type AppleAccountService struct {
	store        appleAccountStore
	randomString func(int) string
	newUUID      func() uuid.UUID
}

type AppleAuthenticatedUser struct {
	ID       pgtype.UUID
	Username string
	Email    string
	Nickname pgtype.Text
}

type AppleSessionMetadata struct {
	DeviceID        string
	DeviceName      string
	DeviceType      string
	IPAddress       string
	UserAgent       string
	RefreshTokenJTI string
}

func NewAppleAccountService(queries *db.Queries) *AppleAccountService {
	return &AppleAccountService{
		store:        queries,
		randomString: randomHexString,
		newUUID:      uuid.New,
	}
}

func (s *AppleAccountService) FindOrCreateUser(ctx context.Context, claims *AppleClaims) (AppleAuthenticatedUser, error) {
	userNeedsLink := false
	user, err := s.store.GetUserByAppleID(ctx, pgtype.Text{String: claims.Subject, Valid: true})
	if err != nil {
		if claims.Email != "" {
			user, err = s.store.GetUserByEmail(ctx, claims.Email)
			if err == nil {
				userNeedsLink = true
			}
		}

		if err != nil {
			created, createErr := s.createAppleUser(ctx, claims)
			if createErr != nil {
				return AppleAuthenticatedUser{}, fmt.Errorf("%w: %v", ErrAppleUserCreateFailed, createErr)
			}
			user = created
		}
	}

	if userNeedsLink || !user.AppleID.Valid {
		linked, linkErr := s.store.LinkAppleUser(ctx, db.LinkAppleUserParams{
			ID:      user.ID,
			AppleID: pgtype.Text{String: claims.Subject, Valid: true},
		})
		if linkErr != nil {
			return AppleAuthenticatedUser{}, fmt.Errorf("%w: %v", ErrAppleUserLinkFailed, linkErr)
		}
		user = linked
	}

	return AppleAuthenticatedUser{
		ID:       user.ID,
		Username: user.Username,
		Email:    user.Email,
		Nickname: user.Nickname,
	}, nil
}

func (s *AppleAccountService) UpdateLastLogin(ctx context.Context, userID pgtype.UUID) error {
	return s.store.UpdateUserLastLogin(ctx, userID)
}

func (s *AppleAccountService) UpsertUserSession(ctx context.Context, userID pgtype.UUID, sessionID string, metadata AppleSessionMetadata) error {
	sessionUUID := s.newUUID()
	var pgSessionID pgtype.UUID
	copy(pgSessionID.Bytes[:], sessionUUID[:])
	pgSessionID.Valid = true

	_, err := s.store.UpsertUserSession(ctx, db.UpsertUserSessionParams{
		ID:              pgSessionID,
		UserID:          userID,
		SessionID:       sessionID,
		DeviceID:        textOrNull(metadata.DeviceID),
		DeviceName:      textOrNull(metadata.DeviceName),
		DeviceType:      textOrNull(metadata.DeviceType),
		IpAddress:       pgtype.Text{String: metadata.IPAddress, Valid: metadata.IPAddress != ""},
		UserAgent:       textOrNull(metadata.UserAgent),
		RefreshTokenJti: pgtype.Text{String: metadata.RefreshTokenJTI, Valid: true},
	})
	return err
}

func (s *AppleAccountService) createAppleUser(ctx context.Context, claims *AppleClaims) (db.User, error) {
	username := fmt.Sprintf("apple_%s", s.randomString(8))
	email := claims.Email
	if email == "" {
		email = fmt.Sprintf("%s@apple-user.com", username)
	}

	newID := s.newUUID()
	var pgID pgtype.UUID
	copy(pgID.Bytes[:], newID[:])
	pgID.Valid = true

	return s.store.CreateSocialUser(ctx, db.CreateSocialUserParams{
		ID:                 pgID,
		Username:           username,
		Email:              email,
		HashedPassword:     s.randomString(32),
		Nickname:           pgtype.Text{String: claims.Name, Valid: claims.Name != ""},
		RegistrationSource: "apple",
		IsActive:           true,
		AppleID:            pgtype.Text{String: claims.Subject, Valid: true},
	})
}

func randomHexString(n int) string {
	b := make([]byte, n/2)
	if _, err := rand.Read(b); err != nil {
		log.Printf("[WARN] randomHexString failed: %v", err)
		return ""
	}
	return hex.EncodeToString(b)
}

func textOrNull(value string) pgtype.Text {
	return pgtype.Text{String: value, Valid: value != ""}
}
