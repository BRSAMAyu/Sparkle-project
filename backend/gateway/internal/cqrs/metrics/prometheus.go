// Package metrics provides Prometheus metrics for the CQRS infrastructure.
package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// CQRSMetrics contains all CQRS-related Prometheus metrics.
type CQRSMetrics struct {
	// Outbox metrics
	OutboxPendingGauge  prometheus.Gauge
	OutboxLag           prometheus.Histogram
	OutboxPublishErrors prometheus.Counter
	EventsPublished     *prometheus.CounterVec

	// Worker metrics
	EventsProcessed         *prometheus.CounterVec
	EventProcessingDuration *prometheus.HistogramVec
	WorkerErrors            *prometheus.CounterVec
	RetryAttempts           *prometheus.CounterVec
	DuplicateEvents         prometheus.Counter

	// DLQ metrics
	DLQMessages     *prometheus.CounterVec
	DLQPendingGauge prometheus.Gauge

	// Projection metrics
	ProjectionLag             *prometheus.GaugeVec
	ProjectionRebuildDuration *prometheus.HistogramVec
	ProjectionStatus          *prometheus.GaugeVec

	// Consumer lag
	ConsumerLag *prometheus.GaugeVec

	// Event store metrics
	EventStoreSize *prometheus.GaugeVec
	SnapshotCount  *prometheus.GaugeVec
}

// NewCQRSMetrics creates and registers all CQRS metrics.
func NewCQRSMetrics(namespace string) *CQRSMetrics {
	if namespace == "" {
		namespace = "sparkle"
	}

	subsystem := "cqrs"

	return &CQRSMetrics{
		// Outbox metrics
		OutboxPendingGauge: promauto.NewGauge(prometheus.GaugeOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "outbox_pending_count",
			Help:      "Number of unpublished events in the outbox table",
		}),

		OutboxLag: promauto.NewHistogram(prometheus.HistogramOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "outbox_publish_lag_seconds",
			Help:      "Time between event creation and publishing to the event bus",
			Buckets:   []float64{0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10},
		}),

		OutboxPublishErrors: promauto.NewCounter(prometheus.CounterOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "outbox_publish_errors_total",
			Help:      "Total number of errors when publishing from outbox",
		}),

		EventsPublished: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "events_published_total",
			Help:      "Total number of events published by event type",
		}, []string{"event_type"}),

		// Worker metrics
		EventsProcessed: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "events_processed_total",
			Help:      "Total number of events processed by event type and consumer group",
		}, []string{"event_type", "consumer_group"}),

		EventProcessingDuration: promauto.NewHistogramVec(prometheus.HistogramOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "event_processing_duration_seconds",
			Help:      "Duration of event processing by event type",
			Buckets:   prometheus.DefBuckets,
		}, []string{"event_type", "consumer_group"}),

		WorkerErrors: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "worker_errors_total",
			Help:      "Total number of worker errors by consumer group and error type",
		}, []string{"consumer_group", "error_type"}),

		RetryAttempts: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "retry_attempts_total",
			Help:      "Total number of retry attempts by consumer group",
		}, []string{"consumer_group"}),

		DuplicateEvents: promauto.NewCounter(prometheus.CounterOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "duplicate_events_total",
			Help:      "Total number of duplicate events detected (idempotency hits)",
		}),

		// DLQ metrics
		DLQMessages: promauto.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "dlq_messages_total",
			Help:      "Total number of messages sent to DLQ by error type",
		}, []string{"error_type", "consumer_group"}),

		DLQPendingGauge: promauto.NewGauge(prometheus.GaugeOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "dlq_pending_count",
			Help:      "Number of messages pending in the dead letter queue",
		}),

		// Projection metrics
		ProjectionLag: promauto.NewGaugeVec(prometheus.GaugeOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "projection_lag_messages",
			Help:      "Number of events behind the projection is from the stream",
		}, []string{"projection_name"}),

		ProjectionRebuildDuration: promauto.NewHistogramVec(prometheus.HistogramOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "projection_rebuild_duration_seconds",
			Help:      "Duration of projection rebuilds",
			Buckets:   []float64{1, 5, 10, 30, 60, 120, 300, 600, 1800},
		}, []string{"projection_name"}),

		ProjectionStatus: promauto.NewGaugeVec(prometheus.GaugeOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "projection_status",
			Help:      "Current status of projections (1=active, 0=inactive, -1=rebuilding)",
		}, []string{"projection_name"}),

		// Consumer lag
		ConsumerLag: promauto.NewGaugeVec(prometheus.GaugeOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "consumer_lag_messages",
			Help:      "Number of unprocessed messages per consumer group",
		}, []string{"stream", "consumer_group"}),

		// Event store metrics
		EventStoreSize: promauto.NewGaugeVec(prometheus.GaugeOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "event_store_size_total",
			Help:      "Total number of events in the event store by aggregate type",
		}, []string{"aggregate_type"}),

		SnapshotCount: promauto.NewGaugeVec(prometheus.GaugeOpts{
			Namespace: namespace,
			Subsystem: subsystem,
			Name:      "snapshot_count_total",
			Help:      "Total number of snapshots by projection name",
		}, []string{"projection_name"}),
	}
}

// RecordEventPublished records a successfully published event.
func (m *CQRSMetrics) RecordEventPublished(eventType string) {
	m.EventsPublished.WithLabelValues(eventType).Inc()
}

// RecordEventProcessed records a successfully processed event.
func (m *CQRSMetrics) RecordEventProcessed(eventType, consumerGroup string, duration float64) {
	m.EventsProcessed.WithLabelValues(eventType, consumerGroup).Inc()
	m.EventProcessingDuration.WithLabelValues(eventType, consumerGroup).Observe(duration)
}

// RecordWorkerError records a worker error.
func (m *CQRSMetrics) RecordWorkerError(consumerGroup, errorType string) {
	m.WorkerErrors.WithLabelValues(consumerGroup, errorType).Inc()
}

// RecordRetry records a retry attempt.
func (m *CQRSMetrics) RecordRetry(consumerGroup string) {
	m.RetryAttempts.WithLabelValues(consumerGroup).Inc()
}

// RecordDLQMessage records a message sent to DLQ.
func (m *CQRSMetrics) RecordDLQMessage(errorType, consumerGroup string) {
	m.DLQMessages.WithLabelValues(errorType, consumerGroup).Inc()
}

// RecordDuplicateEvent records a duplicate event detection.
func (m *CQRSMetrics) RecordDuplicateEvent() {
	m.DuplicateEvents.Inc()
}

// SetOutboxPending sets the current outbox pending count.
func (m *CQRSMetrics) SetOutboxPending(count float64) {
	m.OutboxPendingGauge.Set(count)
}

// SetConsumerLag sets the consumer lag for a stream/group.
func (m *CQRSMetrics) SetConsumerLag(stream, group string, lag float64) {
	m.ConsumerLag.WithLabelValues(stream, group).Set(lag)
}

// SetProjectionStatus sets the projection status.
func (m *CQRSMetrics) SetProjectionStatus(projectionName string, status float64) {
	m.ProjectionStatus.WithLabelValues(projectionName).Set(status)
}

// ProjectionStatusValues for SetProjectionStatus
const (
	ProjectionStatusActive     = 1.0
	ProjectionStatusInactive   = 0.0
	ProjectionStatusRebuilding = -1.0
)
