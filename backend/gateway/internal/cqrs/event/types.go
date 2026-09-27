// Package event provides domain event types and interfaces for the CQRS architecture.
// Core: infra
// Phase: none
// Stage: v1 网关基座
//
// CQRS 事件类型定义.
package event

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

// Type represents the type of a domain event.
type Type string

// Domain event types organized by aggregate.
const (
	// Community events
	EventPostCreated Type = "community.post.created"
	EventPostUpdated Type = "community.post.updated"
	EventPostDeleted Type = "community.post.deleted"
	EventPostLiked   Type = "community.post.liked"
	EventPostUnliked Type = "community.post.unliked"

	// Task events
	EventTaskCreated   Type = "task.created"
	EventTaskUpdated   Type = "task.updated"
	EventTaskStarted   Type = "task.started"
	EventTaskCompleted Type = "task.completed"
	EventTaskAbandoned Type = "task.abandoned"
	EventTaskDeleted   Type = "task.deleted"
	EventTaskPaused    Type = "task.paused"
	EventTaskResumed   Type = "task.resumed"
	EventTaskStuck     Type = "task.stuck"
	EventTaskReopened  Type = "task.reopened"

	// Plan events
	EventPlanCreated   Type = "plan.created"
	EventPlanUpdated   Type = "plan.updated"
	EventPlanCompleted Type = "plan.completed"
	EventPlanDeleted   Type = "plan.deleted"

	// Knowledge Galaxy events
	EventNodeCreated      Type = "galaxy.node.created"
	EventNodeUnlocked     Type = "galaxy.node.unlocked"
	EventNodeExpanded     Type = "galaxy.node.expanded"
	EventMasteryUpdated   Type = "galaxy.mastery.updated"
	EventRelationCreated  Type = "galaxy.relation.created"
	EventStudyRecordAdded Type = "galaxy.study.recorded"

	// Chat events
	EventMessageSent     Type = "chat.message.sent"
	EventMessageReceived Type = "chat.message.received"
	EventSessionCreated  Type = "chat.session.created"
	EventSessionEnded    Type = "chat.session.ended"

	// User events
	EventUserCreated         Type = "user.created"
	EventUserUpdated         Type = "user.updated"
	EventUserDeleted         Type = "user.deleted"
	EventUserStatusChanged   Type = "user.status.changed"
	EventPreferencesUpdated  Type = "user.preferences.updated"
	EventPreferencesInferred Type = "user.preferences.inferred"

	// Push notification events
	EventPushScheduled Type = "push.scheduled"
	EventPushSent      Type = "push.sent"
	EventPushDelivered Type = "push.delivered"
	EventPushClicked   Type = "push.clicked"
)

// AggregateType represents the type of aggregate that owns an event.
type AggregateType string

const (
	AggregatePost          AggregateType = "Post"
	AggregateTask          AggregateType = "Task"
	AggregatePlan          AggregateType = "Plan"
	AggregateKnowledgeNode AggregateType = "KnowledgeNode"
	AggregateChatSession   AggregateType = "ChatSession"
	AggregateUser          AggregateType = "User"
	AggregatePush          AggregateType = "Push"
)

// DomainEvent represents a domain event with full metadata.
type DomainEvent struct {
	ID   string `json:"id"`
	Type Type   `json:"type"`
	// Version is int32 to match the event_version column (sqlc model), so no
	// narrowing conversion happens at the persistence boundary (gosec G115).
	Version       int32                  `json:"version"`
	AggregateType AggregateType          `json:"aggregate_type"`
	AggregateID   uuid.UUID              `json:"aggregate_id"`
	Timestamp     time.Time              `json:"timestamp"`
	Payload       map[string]interface{} `json:"payload"`
	Metadata      Metadata               `json:"metadata"`
}

// Metadata contains tracing and context information.
type Metadata struct {
	TraceID       string    `json:"trace_id,omitempty"`
	SpanID        string    `json:"span_id,omitempty"`
	UserID        uuid.UUID `json:"user_id,omitempty"`
	CorrelationID string    `json:"correlation_id,omitempty"`
	CausationID   string    `json:"causation_id,omitempty"`
	Source        string    `json:"source,omitempty"`
}

// OutboxEntry represents a pending event in the outbox table.
type OutboxEntry struct {
	ID            uuid.UUID
	AggregateType AggregateType
	AggregateID   uuid.UUID
	EventType     Type
	// EventVersion is int32 to match the event_version column (sqlc model);
	// see DomainEvent.Version.
	EventVersion   int32
	Payload        []byte
	Metadata       []byte
	SequenceNumber int64
	CreatedAt      time.Time
	PublishedAt    *time.Time
}

// StoreEntry represents a persisted event in the event store.
type StoreEntry struct {
	ID            uuid.UUID
	AggregateType AggregateType
	AggregateID   uuid.UUID
	EventType     Type
	// EventVersion is int32 to match the event_version column (sqlc model);
	// see DomainEvent.Version.
	EventVersion   int32
	SequenceNumber int64
	Payload        []byte
	Metadata       []byte
	CreatedAt      time.Time
}

// NewDomainEvent creates a new domain event with generated ID and timestamp.
func NewDomainEvent(
	eventType Type,
	aggregateType AggregateType,
	aggregateID uuid.UUID,
	payload map[string]interface{},
	metadata Metadata,
) DomainEvent {
	return DomainEvent{
		ID:            uuid.New().String(),
		Type:          eventType,
		Version:       1,
		AggregateType: aggregateType,
		AggregateID:   aggregateID,
		Timestamp:     time.Now().UTC(),
		Payload:       payload,
		Metadata:      metadata,
	}
}

// ToOutboxEntry converts a DomainEvent to an OutboxEntry for database storage.
func (e *DomainEvent) ToOutboxEntry() (*OutboxEntry, error) {
	payload, err := json.Marshal(e.Payload)
	if err != nil {
		return nil, err
	}

	metadata, err := json.Marshal(e.Metadata)
	if err != nil {
		return nil, err
	}

	return &OutboxEntry{
		ID:            uuid.MustParse(e.ID),
		AggregateType: e.AggregateType,
		AggregateID:   e.AggregateID,
		EventType:     e.Type,
		EventVersion:  e.Version,
		Payload:       payload,
		Metadata:      metadata,
		CreatedAt:     e.Timestamp,
	}, nil
}

// ToDomainEvent converts an OutboxEntry back to a DomainEvent.
func (o *OutboxEntry) ToDomainEvent() (*DomainEvent, error) {
	var payload map[string]interface{}
	if err := json.Unmarshal(o.Payload, &payload); err != nil {
		return nil, err
	}

	var metadata Metadata
	if o.Metadata != nil {
		if err := json.Unmarshal(o.Metadata, &metadata); err != nil {
			return nil, err
		}
	}

	return &DomainEvent{
		ID:            o.ID.String(),
		Type:          o.EventType,
		Version:       o.EventVersion,
		AggregateType: o.AggregateType,
		AggregateID:   o.AggregateID,
		Timestamp:     o.CreatedAt,
		Payload:       payload,
		Metadata:      metadata,
	}, nil
}

// StreamKey returns the Redis stream key for an event type.
func (e Type) StreamKey() string {
	switch {
	case e == EventPostCreated || e == EventPostUpdated || e == EventPostDeleted ||
		e == EventPostLiked || e == EventPostUnliked:
		return "cqrs:stream:community"
	case e == EventTaskCreated || e == EventTaskUpdated || e == EventTaskStarted ||
		e == EventTaskCompleted || e == EventTaskAbandoned || e == EventTaskDeleted:
		return "cqrs:stream:task"
	case e == EventPlanCreated || e == EventPlanUpdated || e == EventPlanCompleted ||
		e == EventPlanDeleted:
		return "cqrs:stream:plan"
	case e == EventNodeCreated || e == EventNodeUnlocked || e == EventNodeExpanded ||
		e == EventMasteryUpdated || e == EventRelationCreated || e == EventStudyRecordAdded:
		return "cqrs:stream:galaxy"
	case e == EventMessageSent || e == EventMessageReceived ||
		e == EventSessionCreated || e == EventSessionEnded:
		return "cqrs:stream:chat"
	case e == EventUserCreated || e == EventUserUpdated ||
		e == EventUserDeleted || e == EventUserStatusChanged ||
		e == EventPreferencesUpdated || e == EventPreferencesInferred:
		return "cqrs:stream:user"
	case e == EventPushScheduled || e == EventPushSent ||
		e == EventPushDelivered || e == EventPushClicked:
		return "cqrs:stream:push"
	default:
		return "cqrs:stream:default"
	}
}

// ConsumerGroup returns the recommended consumer group name for an event type.
func (e Type) ConsumerGroup() string {
	switch {
	case e == EventPostCreated || e == EventPostUpdated || e == EventPostDeleted ||
		e == EventPostLiked || e == EventPostUnliked:
		return "community_projection_group"
	case e == EventTaskCreated || e == EventTaskUpdated || e == EventTaskStarted ||
		e == EventTaskCompleted || e == EventTaskAbandoned || e == EventTaskDeleted:
		return "task_projection_group"
	case e == EventNodeCreated || e == EventNodeUnlocked || e == EventNodeExpanded ||
		e == EventMasteryUpdated || e == EventRelationCreated || e == EventStudyRecordAdded:
		return "galaxy_projection_group"
	default:
		return "default_projection_group"
	}
}
