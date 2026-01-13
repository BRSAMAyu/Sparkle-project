// Package event provides domain event types and interfaces for the CQRS architecture.
package event

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

// EventType represents the type of a domain event.
type EventType string

// Domain event types organized by aggregate.
const (
	// Community events
	EventPostCreated EventType = "community.post.created"
	EventPostUpdated EventType = "community.post.updated"
	EventPostDeleted EventType = "community.post.deleted"
	EventPostLiked   EventType = "community.post.liked"
	EventPostUnliked EventType = "community.post.unliked"

	// Task events
	EventTaskCreated   EventType = "task.created"
	EventTaskUpdated   EventType = "task.updated"
	EventTaskStarted   EventType = "task.started"
	EventTaskCompleted EventType = "task.completed"
	EventTaskAbandoned EventType = "task.abandoned"
	EventTaskDeleted   EventType = "task.deleted"

	// Plan events
	EventPlanCreated   EventType = "plan.created"
	EventPlanUpdated   EventType = "plan.updated"
	EventPlanCompleted EventType = "plan.completed"
	EventPlanDeleted   EventType = "plan.deleted"

	// Knowledge Galaxy events
	EventNodeCreated       EventType = "galaxy.node.created"
	EventNodeUnlocked      EventType = "galaxy.node.unlocked"
	EventNodeExpanded      EventType = "galaxy.node.expanded"
	EventMasteryUpdated    EventType = "galaxy.mastery.updated"
	EventRelationCreated   EventType = "galaxy.relation.created"
	EventStudyRecordAdded  EventType = "galaxy.study.recorded"

	// Chat events
	EventMessageSent      EventType = "chat.message.sent"
	EventMessageReceived  EventType = "chat.message.received"
	EventSessionCreated   EventType = "chat.session.created"
	EventSessionEnded     EventType = "chat.session.ended"

	// User events
	EventUserCreated      EventType = "user.created"
	EventUserUpdated      EventType = "user.updated"
	EventUserDeleted      EventType = "user.deleted"
	EventUserStatusChanged EventType = "user.status.changed"

	// Push notification events
	EventPushScheduled    EventType = "push.scheduled"
	EventPushSent         EventType = "push.sent"
	EventPushDelivered    EventType = "push.delivered"
	EventPushClicked      EventType = "push.clicked"
)

// AggregateType represents the type of aggregate that owns an event.
type AggregateType string

const (
	AggregatePost         AggregateType = "Post"
	AggregateTask         AggregateType = "Task"
	AggregatePlan         AggregateType = "Plan"
	AggregateKnowledgeNode AggregateType = "KnowledgeNode"
	AggregateChatSession  AggregateType = "ChatSession"
	AggregateUser         AggregateType = "User"
	AggregatePush         AggregateType = "Push"
)

// DomainEvent represents a domain event with full metadata.
type DomainEvent struct {
	ID            string                 `json:"id"`
	Type          EventType              `json:"type"`
	Version       int                    `json:"version"`
	AggregateType AggregateType          `json:"aggregate_type"`
	AggregateID   uuid.UUID              `json:"aggregate_id"`
	Timestamp     time.Time              `json:"timestamp"`
	Payload       map[string]interface{} `json:"payload"`
	Metadata      EventMetadata          `json:"metadata"`
}

// EventMetadata contains tracing and context information.
type EventMetadata struct {
	TraceID       string    `json:"trace_id,omitempty"`
	SpanID        string    `json:"span_id,omitempty"`
	UserID        uuid.UUID `json:"user_id,omitempty"`
	CorrelationID string    `json:"correlation_id,omitempty"`
	CausationID   string    `json:"causation_id,omitempty"`
	Source        string    `json:"source,omitempty"`
}

// OutboxEntry represents a pending event in the outbox table.
type OutboxEntry struct {
	ID             uuid.UUID
	AggregateType  AggregateType
	AggregateID    uuid.UUID
	EventType      EventType
	EventVersion   int
	Payload        []byte
	Metadata       []byte
	SequenceNumber int64
	CreatedAt      time.Time
	PublishedAt    *time.Time
}

// EventStoreEntry represents a persisted event in the event store.
type EventStoreEntry struct {
	ID             int64
	AggregateType  AggregateType
	AggregateID    uuid.UUID
	EventType      EventType
	EventVersion   int
	SequenceNumber int64
	Payload        []byte
	Metadata       []byte
	CreatedAt      time.Time
}

// NewDomainEvent creates a new domain event with generated ID and timestamp.
func NewDomainEvent(
	eventType EventType,
	aggregateType AggregateType,
	aggregateID uuid.UUID,
	payload map[string]interface{},
	metadata EventMetadata,
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

	var metadata EventMetadata
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
func (e EventType) StreamKey() string {
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
		e == EventUserDeleted || e == EventUserStatusChanged:
		return "cqrs:stream:user"
	case e == EventPushScheduled || e == EventPushSent ||
		e == EventPushDelivered || e == EventPushClicked:
		return "cqrs:stream:push"
	default:
		return "cqrs:stream:default"
	}
}

// ConsumerGroup returns the recommended consumer group name for an event type.
func (e EventType) ConsumerGroup() string {
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
