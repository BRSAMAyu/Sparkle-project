package service

import (
	"context"

	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/db"
)

type groupChatStore interface {
	IsGroupMember(ctx context.Context, arg db.IsGroupMemberParams) (bool, error)
	GetGroupMessages(ctx context.Context, arg db.GetGroupMessagesParams) ([]db.GetGroupMessagesRow, error)
}

type GroupChatService struct {
	store groupChatStore
}

type GroupChatMessage struct {
	ID                  pgtype.UUID
	GroupID             pgtype.UUID
	SenderID            pgtype.UUID
	MessageType         string
	Content             pgtype.Text
	ReplyToID           pgtype.UUID
	CreatedAt           pgtype.Timestamp
	UpdatedAt           pgtype.Timestamp
	SenderUsername      pgtype.Text
	SenderNickname      pgtype.Text
	SenderAvatarURL     pgtype.Text
	ReplyID             pgtype.UUID
	ReplyContent        pgtype.Text
	ReplyType           string
	ReplySenderUsername pgtype.Text
	ReplySenderNickname pgtype.Text
}

func NewGroupChatService(queries *db.Queries) *GroupChatService {
	return &GroupChatService{store: queries}
}

func (s *GroupChatService) CheckGroupMembership(ctx context.Context, userID, groupID pgtype.UUID) (bool, error) {
	return s.store.IsGroupMember(ctx, db.IsGroupMemberParams{
		GroupID: groupID,
		UserID:  userID,
	})
}

func (s *GroupChatService) GetGroupMessages(ctx context.Context, groupID pgtype.UUID, limit, offset int32) ([]GroupChatMessage, error) {
	rows, err := s.store.GetGroupMessages(ctx, db.GetGroupMessagesParams{
		GroupID: groupID,
		Limit:   limit,
		Offset:  offset,
	})
	if err != nil {
		return nil, err
	}

	messages := make([]GroupChatMessage, 0, len(rows))
	for _, row := range rows {
		messages = append(messages, GroupChatMessage{
			ID:                  row.ID,
			GroupID:             row.GroupID,
			SenderID:            row.SenderID,
			MessageType:         string(row.MessageType),
			Content:             row.Content,
			ReplyToID:           row.ReplyToID,
			CreatedAt:           row.CreatedAt,
			UpdatedAt:           row.UpdatedAt,
			SenderUsername:      row.SenderUsername,
			SenderNickname:      row.SenderNickname,
			SenderAvatarURL:     row.SenderAvatarUrl,
			ReplyID:             row.ReplyID,
			ReplyContent:        row.ReplyContent,
			ReplyType:           string(row.ReplyType.Messagetype),
			ReplySenderUsername: row.ReplySenderUsername,
			ReplySenderNickname: row.ReplySenderNickname,
		})
	}

	return messages, nil
}
