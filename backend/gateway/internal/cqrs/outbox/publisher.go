// Package outbox provides the Outbox pattern implementation for reliable event publishing.
// Core: infra
// Phase: execute
// Stage: v1 网关基座
//
// 发件箱模式事件发布（事务性保证）.

package outbox

import (
	"context"
	"sync/atomic"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
)

// Publisher polls the outbox table and publishes events to the event bus.
type Publisher struct {
	repo     Repository
	eventBus event.EventBus
	metrics  *metrics.CQRSMetrics
	logger   *zap.Logger

	// Configuration
	batchSize    int
	pollInterval time.Duration
	maxBackoff   time.Duration

	// State
	running atomic.Bool

	// Backoff state — owned exclusively by the Run loop goroutine.
	consecutiveFailures int
	firstFailureAt      time.Time
}

// PublisherConfig configures the outbox publisher.
type PublisherConfig struct {
	// BatchSize is the maximum number of events to publish per poll.
	BatchSize int

	// PollInterval is how often to poll for new events.
	PollInterval time.Duration

	// MaxBackoff caps the exponential retry delay after consecutive publish
	// failures (PROD-FIX-2 defect #6). Zero means DefaultMaxBackoff.
	MaxBackoff time.Duration
}

// DefaultMaxBackoff caps the failure backoff: a persistent outage settles at
// one poll attempt per minute instead of the historical 10/s error storm
// (8,494 spurious "Failed to publish batch" logs during a 16h DB outage).
const DefaultMaxBackoff = time.Minute

// DefaultPublisherConfig returns sensible defaults for production.
func DefaultPublisherConfig() PublisherConfig {
	return PublisherConfig{
		BatchSize:    100,
		PollInterval: 100 * time.Millisecond,
		MaxBackoff:   DefaultMaxBackoff,
	}
}

// NewPublisher creates a new outbox publisher.
func NewPublisher(
	repo Repository,
	eventBus event.EventBus,
	metrics *metrics.CQRSMetrics,
	logger *zap.Logger,
	config ...PublisherConfig,
) *Publisher {
	cfg := DefaultPublisherConfig()
	if len(config) > 0 {
		cfg = config[0]
	}
	if cfg.MaxBackoff <= 0 {
		cfg.MaxBackoff = DefaultMaxBackoff
	}

	return &Publisher{
		repo:         repo,
		eventBus:     eventBus,
		metrics:      metrics,
		logger:       logger.Named("outbox-publisher"),
		batchSize:    cfg.BatchSize,
		pollInterval: cfg.PollInterval,
		maxBackoff:   cfg.MaxBackoff,
	}
}

// Run starts the publisher loop. Blocks until context is cancelled.
//
// Failure cadence (PROD-FIX-2 defect #6): consecutive publishBatch failures
// back off exponentially (pollInterval → 2× → 4× … capped at maxBackoff) and
// the error log is rate-limited to the first failure plus every 10th
// consecutive one; the OutboxPublishErrors counter still ticks per attempt.
// Any success resets the cadence to the normal pollInterval.
func (p *Publisher) Run(ctx context.Context) error {
	if !p.running.CompareAndSwap(false, true) {
		return nil // Already running
	}
	defer p.running.Store(false)

	p.logger.Info("Outbox publisher started",
		zap.Int("batch_size", p.batchSize),
		zap.Duration("poll_interval", p.pollInterval),
		zap.Duration("max_backoff", p.maxBackoff),
	)

	delay := p.pollInterval
	for {
		select {
		case <-ctx.Done():
			p.logger.Info("Outbox publisher stopping")
			return ctx.Err()
		case <-time.After(delay):
		}

		if err := p.publishBatch(ctx); err != nil {
			delay = p.noteFailure(err)
			continue
		}
		delay = p.pollInterval
		p.noteSuccess()
	}
}

// noteFailure records a failed publishBatch, returns the delay before the
// next attempt, and rate-limits the error log for persistent outages.
func (p *Publisher) noteFailure(err error) time.Duration {
	p.metrics.OutboxPublishErrors.Inc()
	if p.consecutiveFailures == 0 {
		p.firstFailureAt = time.Now()
	}
	p.consecutiveFailures++
	delay := p.backoffDelay()

	// Same-cause log aggregation: first failure and every 10th consecutive
	// failure are logged at Error; the in-between attempts stay silent here
	// (the metric above keeps the true rate). "Still failing" lines make a
	// 16h outage visible without an error per attempt.
	if p.consecutiveFailures == 1 || p.consecutiveFailures%10 == 0 {
		p.logger.Error("Failed to publish batch",
			zap.Error(err),
			zap.Int("consecutive_failures", p.consecutiveFailures),
			zap.Duration("next_retry_in", delay),
		)
	}
	return delay
}

// noteSuccess resets the backoff cadence and reports recovery from a failure
// streak with its duration.
func (p *Publisher) noteSuccess() {
	if p.consecutiveFailures > 0 {
		p.logger.Info("Outbox publish recovered",
			zap.Int("consecutive_failures", p.consecutiveFailures),
			zap.Duration("failure_duration", time.Since(p.firstFailureAt)),
		)
	}
	p.consecutiveFailures = 0
	p.firstFailureAt = time.Time{}
}

// backoffDelay returns the wait before the next attempt after
// p.consecutiveFailures consecutive failures: pollInterval doubled per
// failure, capped at maxBackoff.
func (p *Publisher) backoffDelay() time.Duration {
	d := p.pollInterval
	for i := 0; i < p.consecutiveFailures; i++ {
		d *= 2
		if d >= p.maxBackoff {
			return p.maxBackoff
		}
	}
	return d
}

// publishBatch fetches and publishes a batch of events.
//
// Delivery contract (GW-P3-7, documented by design): publishing and
// MarkPublished are intentionally NOT one transaction — an at-least-once
// semantic. A crash between eventBus.Publish and MarkPublished replays the
// affected entries on the next poll; GetUnpublished uses
// FOR UPDATE SKIP LOCKED, so concurrent publisher instances stay safe.
// Consequence: every event-bus consumer MUST tolerate duplicates. The
// read-side projection consumers (internal/cqrs/projection) satisfy this via
// position semantics (LastProcessedPosition) — see the package contract note
// in projection/handlers.go.
func (p *Publisher) publishBatch(ctx context.Context) error {
	// Fetch unpublished entries
	entries, err := p.repo.GetUnpublished(ctx, p.batchSize)
	if err != nil {
		return err
	}

	if len(entries) == 0 {
		return nil
	}

	p.logger.Debug("Processing outbox batch", zap.Int("count", len(entries)))

	// Track successfully published IDs
	publishedIDs := make([]uuid.UUID, 0, len(entries))

	for _, entry := range entries {
		// Convert to domain event
		domainEvent, err := entry.ToDomainEvent()
		if err != nil {
			p.logger.Error("Failed to convert outbox entry",
				zap.String("entry_id", entry.ID.String()),
				zap.Error(err),
			)
			continue
		}

		// Publish to event bus
		if err := p.eventBus.Publish(ctx, *domainEvent); err != nil {
			p.logger.Error("Failed to publish event",
				zap.String("event_id", domainEvent.ID),
				zap.String("event_type", string(domainEvent.Type)),
				zap.Error(err),
			)
			continue
		}

		publishedIDs = append(publishedIDs, entry.ID)

		// Update metrics
		p.metrics.EventsPublished.WithLabelValues(string(entry.EventType)).Inc()

		// Track publish lag
		lag := time.Since(entry.CreatedAt)
		p.metrics.OutboxLag.Observe(lag.Seconds())

		p.logger.Debug("Published event",
			zap.String("event_id", domainEvent.ID),
			zap.String("event_type", string(domainEvent.Type)),
			zap.Duration("lag", lag),
		)
	}

	// Mark successfully published entries
	if len(publishedIDs) > 0 {
		if err := p.repo.MarkPublished(ctx, publishedIDs); err != nil {
			p.logger.Error("Failed to mark entries as published",
				zap.Int("count", len(publishedIDs)),
				zap.Error(err),
			)
			return err
		}
	}

	return nil
}

// IsRunning returns true if the publisher is currently running.
func (p *Publisher) IsRunning() bool {
	return p.running.Load()
}

// Cleaner removes old published entries from the outbox table.
type Cleaner struct {
	repo          Repository
	metrics       *metrics.CQRSMetrics
	logger        *zap.Logger
	retentionDays int
	cleanInterval time.Duration
}

// CleanerConfig configures the outbox cleaner.
type CleanerConfig struct {
	// RetentionDays is how long to keep published entries.
	RetentionDays int

	// CleanInterval is how often to run the cleanup.
	CleanInterval time.Duration
}

// DefaultCleanerConfig returns sensible defaults.
func DefaultCleanerConfig() CleanerConfig {
	return CleanerConfig{
		RetentionDays: 7,
		CleanInterval: time.Hour,
	}
}

// NewCleaner creates a new outbox cleaner.
func NewCleaner(
	repo Repository,
	metrics *metrics.CQRSMetrics,
	logger *zap.Logger,
	config ...CleanerConfig,
) *Cleaner {
	cfg := DefaultCleanerConfig()
	if len(config) > 0 {
		cfg = config[0]
	}

	return &Cleaner{
		repo:          repo,
		metrics:       metrics,
		logger:        logger.Named("outbox-cleaner"),
		retentionDays: cfg.RetentionDays,
		cleanInterval: cfg.CleanInterval,
	}
}

// Run starts the cleaner loop. Blocks until context is cancelled.
func (c *Cleaner) Run(ctx context.Context) error {
	c.logger.Info("Outbox cleaner started",
		zap.Int("retention_days", c.retentionDays),
		zap.Duration("clean_interval", c.cleanInterval),
	)

	ticker := time.NewTicker(c.cleanInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			c.logger.Info("Outbox cleaner stopping")
			return ctx.Err()
		case <-ticker.C:
			if err := c.cleanup(ctx); err != nil {
				c.logger.Error("Cleanup failed", zap.Error(err))
			}
		}
	}
}

func (c *Cleaner) cleanup(ctx context.Context) error {
	deleted, err := c.repo.DeleteOld(ctx, c.retentionDays)
	if err != nil {
		return err
	}

	if deleted > 0 {
		c.logger.Info("Cleaned up old outbox entries",
			zap.Int64("deleted_count", deleted),
		)
	}

	return nil
}

// PendingMonitor periodically checks and reports the pending outbox count.
type PendingMonitor struct {
	repo     Repository
	metrics  *metrics.CQRSMetrics
	logger   *zap.Logger
	interval time.Duration
}

// NewPendingMonitor creates a new pending monitor.
func NewPendingMonitor(
	repo Repository,
	metrics *metrics.CQRSMetrics,
	logger *zap.Logger,
	interval time.Duration,
) *PendingMonitor {
	if interval == 0 {
		interval = 10 * time.Second
	}
	return &PendingMonitor{
		repo:     repo,
		metrics:  metrics,
		logger:   logger.Named("outbox-monitor"),
		interval: interval,
	}
}

// Run starts the monitor loop. Blocks until context is cancelled.
func (m *PendingMonitor) Run(ctx context.Context) error {
	m.logger.Info("Outbox pending monitor started",
		zap.Duration("interval", m.interval),
	)

	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			if err := m.check(ctx); err != nil {
				m.logger.Error("Monitor check failed", zap.Error(err))
			}
		}
	}
}

func (m *PendingMonitor) check(ctx context.Context) error {
	count, err := m.repo.GetPendingCount(ctx)
	if err != nil {
		return err
	}

	m.metrics.OutboxPendingGauge.Set(float64(count))

	// Warn if backlog is building up
	if count > 1000 {
		m.logger.Warn("Large outbox backlog detected",
			zap.Int64("pending_count", count),
		)
	}

	return nil
}
