package service

import (
	"context"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/db"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type fakeGroupChatStore struct {
	membershipArg db.IsGroupMemberParams
	member        bool
	rows          []db.GetGroupMessagesRow
	messagesArg   db.GetGroupMessagesParams
}

func (f *fakeGroupChatStore) IsGroupMember(_ context.Context, arg db.IsGroupMemberParams) (bool, error) {
	f.membershipArg = arg
	return f.member, nil
}

func (f *fakeGroupChatStore) GetGroupMessages(_ context.Context, arg db.GetGroupMessagesParams) ([]db.GetGroupMessagesRow, error) {
	f.messagesArg = arg
	return f.rows, nil
}

func TestGroupChatServiceCheckGroupMembershipDelegatesToStore(t *testing.T) {
	userID := pgUUID("55555555-5555-5555-5555-555555555555")
	groupID := pgUUID("66666666-6666-6666-6666-666666666666")
	store := &fakeGroupChatStore{member: true}
	svc := &GroupChatService{store: store}

	member, err := svc.CheckGroupMembership(context.Background(), userID, groupID)

	require.NoError(t, err)
	assert.True(t, member)
	assert.Equal(t, userID, store.membershipArg.UserID)
	assert.Equal(t, groupID, store.membershipArg.GroupID)
}

func TestGroupChatServiceGetGroupMessagesMapsRows(t *testing.T) {
	groupID := pgUUID("77777777-7777-7777-7777-777777777777")
	senderID := pgUUID("88888888-8888-8888-8888-888888888888")
	createdAt := pgtype.Timestamp{Time: time.Unix(100, 0), Valid: true}
	store := &fakeGroupChatStore{
		rows: []db.GetGroupMessagesRow{{
			ID:              pgUUID("99999999-9999-9999-9999-999999999999"),
			GroupID:         groupID,
			SenderID:        senderID,
			MessageType:     db.MessagetypeTEXT,
			Content:         pgtype.Text{String: "hello", Valid: true},
			CreatedAt:       createdAt,
			SenderUsername:  pgtype.Text{String: "sender", Valid: true},
			SenderAvatarUrl: pgtype.Text{String: "avatar", Valid: true},
			ReplyType:       db.NullMessagetype{Messagetype: db.MessagetypeSYSTEM, Valid: true},
		}},
	}
	svc := &GroupChatService{store: store}

	messages, err := svc.GetGroupMessages(context.Background(), groupID, 25, 5)

	require.NoError(t, err)
	require.Len(t, messages, 1)
	assert.Equal(t, groupID, store.messagesArg.GroupID)
	assert.Equal(t, int32(25), store.messagesArg.Limit)
	assert.Equal(t, int32(5), store.messagesArg.Offset)
	assert.Equal(t, senderID, messages[0].SenderID)
	assert.Equal(t, "TEXT", messages[0].MessageType)
	assert.Equal(t, "SYSTEM", messages[0].ReplyType)
	assert.Equal(t, "avatar", messages[0].SenderAvatarURL.String)
}
