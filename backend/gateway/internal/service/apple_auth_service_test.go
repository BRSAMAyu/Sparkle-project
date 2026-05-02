package service

import (
	"context"
	"errors"
	"testing"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/db"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type fakeAppleAccountStore struct {
	byAppleIDErr error
	byEmailUser  db.User
	byEmailErr   error
	createdUser  db.User
	linkedUser   db.User
	linkErr      error

	createCalled bool
	linkCalled   bool
	sessionArg   db.UpsertUserSessionParams
}

func (f *fakeAppleAccountStore) GetUserByAppleID(context.Context, pgtype.Text) (db.User, error) {
	return db.User{}, f.byAppleIDErr
}

func (f *fakeAppleAccountStore) GetUserByEmail(context.Context, string) (db.User, error) {
	return f.byEmailUser, f.byEmailErr
}

func (f *fakeAppleAccountStore) CreateSocialUser(_ context.Context, arg db.CreateSocialUserParams) (db.User, error) {
	f.createCalled = true
	user := f.createdUser
	user.ID = arg.ID
	user.Username = arg.Username
	user.Email = arg.Email
	user.Nickname = arg.Nickname
	user.AppleID = arg.AppleID
	return user, nil
}

func (f *fakeAppleAccountStore) LinkAppleUser(_ context.Context, arg db.LinkAppleUserParams) (db.User, error) {
	f.linkCalled = true
	if f.linkErr != nil {
		return db.User{}, f.linkErr
	}
	user := f.linkedUser
	user.ID = arg.ID
	user.AppleID = arg.AppleID
	return user, nil
}

func (f *fakeAppleAccountStore) UpdateUserLastLogin(context.Context, pgtype.UUID) error {
	return nil
}

func (f *fakeAppleAccountStore) UpsertUserSession(_ context.Context, arg db.UpsertUserSessionParams) (db.UserSession, error) {
	f.sessionArg = arg
	return db.UserSession{}, nil
}

func TestAppleAccountServiceFindOrCreateUserCreatesMissingAppleUser(t *testing.T) {
	store := &fakeAppleAccountStore{
		byAppleIDErr: errors.New("not found"),
		byEmailErr:   errors.New("not found"),
	}
	svc := &AppleAccountService{
		store:        store,
		randomString: func(n int) string { return "abcd1234abcd1234abcd1234abcd1234"[:n] },
		newUUID:      func() uuid.UUID { return uuid.MustParse("11111111-1111-1111-1111-111111111111") },
	}

	user, err := svc.FindOrCreateUser(context.Background(), &AppleClaims{
		Email:            "person@example.com",
		Name:             "Person",
		RegisteredClaims: jwt.RegisteredClaims{Subject: "apple-subject"},
	})

	require.NoError(t, err)
	assert.True(t, store.createCalled)
	assert.False(t, store.linkCalled)
	assert.Equal(t, "apple_abcd1234", user.Username)
	assert.Equal(t, "person@example.com", user.Email)
	assert.Equal(t, "Person", user.Nickname.String)
}

func TestAppleAccountServiceFindOrCreateUserLinksEmailMatch(t *testing.T) {
	existingID := pgUUID("22222222-2222-2222-2222-222222222222")
	store := &fakeAppleAccountStore{
		byAppleIDErr: errors.New("not found"),
		byEmailUser: db.User{
			ID:       existingID,
			Username: "existing",
			Email:    "person@example.com",
		},
		linkedUser: db.User{
			Username: "existing",
			Email:    "person@example.com",
		},
	}
	svc := &AppleAccountService{
		store:        store,
		randomString: func(int) string { return "unused" },
		newUUID:      uuid.New,
	}

	user, err := svc.FindOrCreateUser(context.Background(), &AppleClaims{
		Email:            "person@example.com",
		RegisteredClaims: jwt.RegisteredClaims{Subject: "apple-subject"},
	})

	require.NoError(t, err)
	assert.False(t, store.createCalled)
	assert.True(t, store.linkCalled)
	assert.Equal(t, existingID, user.ID)
	assert.Equal(t, "existing", user.Username)
}

func TestAppleAccountServiceUpsertUserSessionMapsMetadata(t *testing.T) {
	store := &fakeAppleAccountStore{}
	svc := &AppleAccountService{
		store:        store,
		randomString: func(int) string { return "unused" },
		newUUID:      func() uuid.UUID { return uuid.MustParse("33333333-3333-3333-3333-333333333333") },
	}
	userID := pgUUID("44444444-4444-4444-4444-444444444444")

	err := svc.UpsertUserSession(context.Background(), userID, "session-id", AppleSessionMetadata{
		DeviceID:        "device",
		DeviceName:      "phone",
		DeviceType:      "ios",
		IPAddress:       "127.0.0.1",
		UserAgent:       "agent",
		RefreshTokenJTI: "jti",
	})

	require.NoError(t, err)
	assert.Equal(t, userID, store.sessionArg.UserID)
	assert.Equal(t, "session-id", store.sessionArg.SessionID)
	assert.Equal(t, "device", store.sessionArg.DeviceID.String)
	assert.Equal(t, "jti", store.sessionArg.RefreshTokenJti.String)
}

func pgUUID(value string) pgtype.UUID {
	id := uuid.MustParse(value)
	var pgID pgtype.UUID
	copy(pgID.Bytes[:], id[:])
	pgID.Valid = true
	return pgID
}
