package service

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	"github.com/sparkle/gateway/internal/db"
)

// CreateNodeRequest contains data for creating a new knowledge node.
type CreateNodeRequest struct {
	UserID          uuid.UUID
	SubjectID       *int32
	ParentID        *uuid.UUID
	Name            string
	NameEn          string
	Description     string
	Keywords        []string
	ImportanceLevel int32
	IsSeed          bool
	SourceType      string
	SourceTaskID    *uuid.UUID
}

// UnlockNodeRequest contains data for unlocking a knowledge node.
type UnlockNodeRequest struct {
	UserID uuid.UUID
	NodeID uuid.UUID
}

// UpdateMasteryRequest contains data for updating mastery score.
type UpdateMasteryRequest struct {
	UserID        uuid.UUID
	NodeID        uuid.UUID
	MasteryDelta  float64
	StudyMinutes  int32
	ActivityType  string // "study", "practice", "review"
}

// CreateRelationRequest contains data for creating a node relation.
type CreateRelationRequest struct {
	UserID        uuid.UUID
	SourceNodeID  uuid.UUID
	TargetNodeID  uuid.UUID
	RelationType  string // "prerequisite", "related", "extends"
	Strength      float64
}

// GalaxyCommandService handles write operations for the knowledge galaxy module.
// Uses the Outbox pattern for reliable event publishing with transactional consistency.
type GalaxyCommandService struct {
	pool       *pgxpool.Pool
	queries    *db.Queries
	unitOfWork *outbox.UnitOfWork
}

// NewGalaxyCommandService creates a new galaxy command service.
func NewGalaxyCommandService(pool *pgxpool.Pool) *GalaxyCommandService {
	return &GalaxyCommandService{
		pool:       pool,
		queries:    db.New(pool),
		unitOfWork: outbox.NewUnitOfWork(pool),
	}
}

// CreateNode creates a new knowledge node and publishes a NodeCreated event atomically.
func (s *GalaxyCommandService) CreateNode(ctx context.Context, req CreateNodeRequest) (*db.KnowledgeNode, error) {
	if req.Name == "" {
		return nil, fmt.Errorf("name cannot be empty")
	}

	keywordsJSON, err := json.Marshal(req.Keywords)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal keywords: %w", err)
	}

	var node db.KnowledgeNode

	err = s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Prepare nullable fields
		subjectID := pgtype.Int4{}
		if req.SubjectID != nil {
			subjectID = pgtype.Int4{Int32: *req.SubjectID, Valid: true}
		}

		parentID := pgtype.UUID{}
		if req.ParentID != nil {
			parentID = pgtype.UUID{Bytes: *req.ParentID, Valid: true}
		}

		sourceTaskID := pgtype.UUID{}
		if req.SourceTaskID != nil {
			sourceTaskID = pgtype.UUID{Bytes: *req.SourceTaskID, Valid: true}
		}

		// Insert node in transaction
		nodeID := uuid.New()
		row := txCtx.QueryRow(ctx, `
			INSERT INTO knowledge_nodes (
				id, subject_id, parent_id, name, name_en, description,
				keywords, importance_level, is_seed, source_type, source_task_id,
				created_at, updated_at
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
			RETURNING id, subject_id, parent_id, name, name_en, description,
			          keywords, importance_level, is_seed, source_type, source_task_id,
			          embedding, created_at, updated_at, deleted_at
		`,
			pgtype.UUID{Bytes: nodeID, Valid: true},
			subjectID,
			parentID,
			req.Name,
			pgtype.Text{String: req.NameEn, Valid: req.NameEn != ""},
			pgtype.Text{String: req.Description, Valid: req.Description != ""},
			keywordsJSON,
			req.ImportanceLevel,
			pgtype.Bool{Bool: req.IsSeed, Valid: true},
			pgtype.Text{String: req.SourceType, Valid: req.SourceType != ""},
			sourceTaskID,
		)

		err := row.Scan(
			&node.ID,
			&node.SubjectID,
			&node.ParentID,
			&node.Name,
			&node.NameEn,
			&node.Description,
			&node.Keywords,
			&node.ImportanceLevel,
			&node.IsSeed,
			&node.SourceType,
			&node.SourceTaskID,
			&node.Embedding,
			&node.CreatedAt,
			&node.UpdatedAt,
			&node.DeletedAt,
		)
		if err != nil {
			return fmt.Errorf("failed to create knowledge node: %w", err)
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventNodeCreated,
			event.AggregateKnowledgeNode,
			nodeID,
			map[string]interface{}{
				"node_id":          nodeID.String(),
				"user_id":          req.UserID.String(),
				"name":             req.Name,
				"importance_level": req.ImportanceLevel,
				"is_seed":          req.IsSeed,
			},
			event.EventMetadata{
				UserID: req.UserID,
				Source: "galaxy_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})

	if err != nil {
		return nil, err
	}

	return &node, nil
}

// UnlockNode unlocks a knowledge node for a user and publishes a NodeUnlocked event atomically.
func (s *GalaxyCommandService) UnlockNode(ctx context.Context, req UnlockNodeRequest) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Insert or update user_node_status
		_, err := txCtx.Tx().Exec(ctx, `
			INSERT INTO user_node_status (
				user_id, node_id, mastery_score, total_minutes, total_study_minutes,
				study_count, is_unlocked, is_collapsed, is_favorite, decay_paused,
				first_unlock_at, last_interacted_at, created_at, updated_at
			)
			VALUES ($1, $2, 0, 0, 0, 0, true, false, false, false, NOW(), NOW(), NOW(), NOW())
			ON CONFLICT (user_id, node_id) DO UPDATE SET
				is_unlocked = true,
				first_unlock_at = COALESCE(user_node_status.first_unlock_at, NOW()),
				last_interacted_at = NOW(),
				updated_at = NOW()
		`,
			pgtype.UUID{Bytes: req.UserID, Valid: true},
			pgtype.UUID{Bytes: req.NodeID, Valid: true},
		)

		if err != nil {
			return fmt.Errorf("failed to unlock node: %w", err)
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventNodeUnlocked,
			event.AggregateKnowledgeNode,
			req.NodeID,
			map[string]interface{}{
				"node_id": req.NodeID.String(),
				"user_id": req.UserID.String(),
			},
			event.EventMetadata{
				UserID: req.UserID,
				Source: "galaxy_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// UpdateMastery updates the mastery score for a user's knowledge node.
func (s *GalaxyCommandService) UpdateMastery(ctx context.Context, req UpdateMasteryRequest) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Update user_node_status mastery
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE user_node_status
			SET mastery_score = LEAST(GREATEST(mastery_score + $3, 0), 1),
			    total_study_minutes = total_study_minutes + $4,
			    study_count = study_count + 1,
			    last_study_at = NOW(),
			    last_interacted_at = NOW(),
			    updated_at = NOW()
			WHERE user_id = $1 AND node_id = $2 AND is_unlocked = true
		`,
			pgtype.UUID{Bytes: req.UserID, Valid: true},
			pgtype.UUID{Bytes: req.NodeID, Valid: true},
			req.MasteryDelta,
			req.StudyMinutes,
		)

		if err != nil {
			return fmt.Errorf("failed to update mastery: %w", err)
		}

		if result.RowsAffected() == 0 {
			return fmt.Errorf("node not found or not unlocked")
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventMasteryUpdated,
			event.AggregateKnowledgeNode,
			req.NodeID,
			map[string]interface{}{
				"node_id":        req.NodeID.String(),
				"user_id":        req.UserID.String(),
				"mastery_delta":  req.MasteryDelta,
				"study_minutes":  req.StudyMinutes,
				"activity_type":  req.ActivityType,
			},
			event.EventMetadata{
				UserID: req.UserID,
				Source: "galaxy_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// CreateRelation creates a relation between two knowledge nodes.
func (s *GalaxyCommandService) CreateRelation(ctx context.Context, req CreateRelationRequest) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		relationID := uuid.New()

		_, err := txCtx.Tx().Exec(ctx, `
			INSERT INTO node_relations (
				id, source_node_id, target_node_id, relation_type, strength,
				created_at, updated_at
			)
			VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
			ON CONFLICT DO NOTHING
		`,
			pgtype.UUID{Bytes: relationID, Valid: true},
			pgtype.UUID{Bytes: req.SourceNodeID, Valid: true},
			pgtype.UUID{Bytes: req.TargetNodeID, Valid: true},
			req.RelationType,
			req.Strength,
		)

		if err != nil {
			return fmt.Errorf("failed to create relation: %w", err)
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventRelationCreated,
			event.AggregateKnowledgeNode,
			req.SourceNodeID,
			map[string]interface{}{
				"relation_id":    relationID.String(),
				"source_node_id": req.SourceNodeID.String(),
				"target_node_id": req.TargetNodeID.String(),
				"relation_type":  req.RelationType,
				"strength":       req.Strength,
				"user_id":        req.UserID.String(),
			},
			event.EventMetadata{
				UserID: req.UserID,
				Source: "galaxy_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// RecordStudy records a study session for a knowledge node.
func (s *GalaxyCommandService) RecordStudy(ctx context.Context, userID, nodeID uuid.UUID, minutes int32, performanceScore float64) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		recordID := uuid.New()

		// Insert study record
		_, err := txCtx.Tx().Exec(ctx, `
			INSERT INTO study_records (
				id, user_id, node_id, duration_minutes, performance_score,
				created_at
			)
			VALUES ($1, $2, $3, $4, $5, NOW())
		`,
			pgtype.UUID{Bytes: recordID, Valid: true},
			pgtype.UUID{Bytes: userID, Valid: true},
			pgtype.UUID{Bytes: nodeID, Valid: true},
			minutes,
			performanceScore,
		)

		if err != nil {
			return fmt.Errorf("failed to record study: %w", err)
		}

		// Calculate mastery delta based on performance
		masteryDelta := performanceScore * 0.1 // Each study session can add up to 10% mastery

		// Update mastery score
		_, err = txCtx.Tx().Exec(ctx, `
			UPDATE user_node_status
			SET mastery_score = LEAST(GREATEST(mastery_score + $3, 0), 1),
			    total_study_minutes = total_study_minutes + $4,
			    study_count = study_count + 1,
			    last_study_at = NOW(),
			    last_interacted_at = NOW(),
			    updated_at = NOW()
			WHERE user_id = $1 AND node_id = $2
		`,
			pgtype.UUID{Bytes: userID, Valid: true},
			pgtype.UUID{Bytes: nodeID, Valid: true},
			masteryDelta,
			minutes,
		)

		if err != nil {
			return fmt.Errorf("failed to update mastery after study: %w", err)
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventStudyRecordAdded,
			event.AggregateKnowledgeNode,
			nodeID,
			map[string]interface{}{
				"record_id":         recordID.String(),
				"node_id":           nodeID.String(),
				"user_id":           userID.String(),
				"minutes":           minutes,
				"performance_score": performanceScore,
				"mastery_delta":     masteryDelta,
			},
			event.EventMetadata{
				UserID: userID,
				Source: "galaxy_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}

// ExpandNode marks a node as expanded (children loaded).
func (s *GalaxyCommandService) ExpandNode(ctx context.Context, userID, nodeID uuid.UUID) error {
	return s.unitOfWork.ExecuteInTransaction(ctx, func(txCtx *outbox.TransactionContext) error {
		// Update is_collapsed to false
		result, err := txCtx.Tx().Exec(ctx, `
			UPDATE user_node_status
			SET is_collapsed = false,
			    last_interacted_at = NOW(),
			    updated_at = NOW()
			WHERE user_id = $1 AND node_id = $2 AND is_unlocked = true
		`,
			pgtype.UUID{Bytes: userID, Valid: true},
			pgtype.UUID{Bytes: nodeID, Valid: true},
		)

		if err != nil {
			return fmt.Errorf("failed to expand node: %w", err)
		}

		if result.RowsAffected() == 0 {
			return fmt.Errorf("node not found or not unlocked")
		}

		// Create domain event
		domainEvent := event.NewDomainEvent(
			event.EventNodeExpanded,
			event.AggregateKnowledgeNode,
			nodeID,
			map[string]interface{}{
				"node_id": nodeID.String(),
				"user_id": userID.String(),
			},
			event.EventMetadata{
				UserID: userID,
				Source: "galaxy_command_service",
			},
		)

		if err := txCtx.SaveEventToOutbox(ctx, &domainEvent); err != nil {
			return fmt.Errorf("failed to save event to outbox: %w", err)
		}

		return nil
	})
}
