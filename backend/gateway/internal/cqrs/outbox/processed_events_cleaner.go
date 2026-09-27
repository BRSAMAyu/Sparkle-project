// Processed events retention cleaner (V3-FIX-487).
package outbox

// Periodic purge of the processed_events durable idempotency gate.
//
// V3-FIX-487: since V3-FIX-469 every processed event really INSERTs one
// processed_events row (ON CONFLICT DO NOTHING), so the authoritative
// duplicate gate grew monotonically — ProcessedEventsRepository.Cleanup sat at
// zero callers repo-wide while outbox.DeleteOld had the outbox.Cleaner and the
// DLQ had DLQCleaner. This runner gives the table the same periodic
// maintenance posture: a dedicated ticker goroutine wired in
// cmd/server/setup.go startCQRSWorkers, instead of per-BaseWorker cleanup
// (both gateway workers share the one table; per-worker sweeps would
// duplicate the DELETE scan and tie retention to one stream's liveness).
//
// Retention window argument (why 7 days is safe, not just conventional):
// the gate exists to absorb redeliveries of already-marked messages. The only
// path that can redeliver a marked message is the V3-FIX-461 own-PEL drain
// (markProcessed succeeded, XAck lost to a crash/Redis error) — in a healthy
// process that gap is seconds (drain runs every loop iteration, ~block
// timeout); across a crash it equals the gateway downtime, because the fixed
// consumer name drains its PEL first thing on restart. So the window must
// simply exceed any plausible downtime with an intact Redis stream/group/PEL.
// 7 days is 3 orders of magnitude beyond routine deploy windows and matches
// the sibling retention policies in this package family (outbox.Cleaner
// RetentionDays=7, DLQ MaxAge=7d) — the direction the ledger row prescribes.
// Residual tail, accepted and stated: a gateway down for more than the whole
// window while its PEL survives would replay one at-least-once reprocess per
// expired key on revival — inside the documented at-least-once contract
// (see Publisher.publishBatch delivery contract; projection handlers are
// rebuildable). Not sized for: disaster-recovery full replay (consumer group
// recreated at "0"), where reprocessing old events is the operator's intent
// under any finite window; and DLQ retries, which XAdd NEW stream message IDs
// and never depend on old rows. The DELETE is unindexed on processed_at (only
// the (event_id, consumer_group) PK exists), so the window bounds both the
// table and the scan — a dedicated index would be an Alembic migration and is
// deliberately out of scope here.

import (
	"context"
	"time"

	"go.uber.org/zap"
)

// DefaultProcessedEventsRetentionDays keeps every absorption row for a week —
// long past any plausible markProcessed→PEL-replay gap (see the retention
// argument above), aligned with outbox.Cleaner and DLQ retention.
const DefaultProcessedEventsRetentionDays = 7

// DefaultProcessedEventsCleanInterval sweeps once a day like DLQCleaner: the
// table only needs to stay bounded at ~retention-window size, and each sweep
// is an unindexed scan, so a daily cadence is the cheap bound.
const DefaultProcessedEventsCleanInterval = 24 * time.Hour

// ProcessedEventsCleanupStore is the cleanup-facing slice of
// ProcessedEventsRepository; *ProcessedEventsRepository satisfies it.
type ProcessedEventsCleanupStore interface {
	// Cleanup removes rows processed longer than retentionDays ago.
	Cleanup(ctx context.Context, retentionDays int) (int64, error)
}

// ProcessedEventsCleaner periodically purges old processed_events rows.
type ProcessedEventsCleaner struct {
	repo          ProcessedEventsCleanupStore
	logger        *zap.Logger
	retentionDays int
	cleanInterval time.Duration
}

// ProcessedEventsCleanerConfig configures the processed events cleaner.
type ProcessedEventsCleanerConfig struct {
	// RetentionDays is how long a processed_events absorption row is kept.
	// Must stay beyond the maximum markProcessed→PEL-replay window (see the
	// package file comment). Zero or negative falls back to the default
	// rather than purging the whole table.
	RetentionDays int

	// CleanInterval is how often to sweep. Zero or negative falls back to
	// the default (time.NewTicker panics on non-positive intervals).
	CleanInterval time.Duration
}

// DefaultProcessedEventsCleanerConfig returns the documented defaults.
func DefaultProcessedEventsCleanerConfig() ProcessedEventsCleanerConfig {
	return ProcessedEventsCleanerConfig{
		RetentionDays: DefaultProcessedEventsRetentionDays,
		CleanInterval: DefaultProcessedEventsCleanInterval,
	}
}

// NewProcessedEventsCleaner creates a new processed events cleaner.
func NewProcessedEventsCleaner(
	repo ProcessedEventsCleanupStore,
	logger *zap.Logger,
	config ...ProcessedEventsCleanerConfig,
) *ProcessedEventsCleaner {
	cfg := DefaultProcessedEventsCleanerConfig()
	if len(config) > 0 {
		cfg = config[0]
	}
	if cfg.RetentionDays <= 0 {
		cfg.RetentionDays = DefaultProcessedEventsRetentionDays
	}
	if cfg.CleanInterval <= 0 {
		cfg.CleanInterval = DefaultProcessedEventsCleanInterval
	}

	return &ProcessedEventsCleaner{
		repo:          repo,
		logger:        logger.Named("processed-events-cleaner"),
		retentionDays: cfg.RetentionDays,
		cleanInterval: cfg.CleanInterval,
	}
}

// Run starts the cleaner loop: one sweep at startup (reclaims any legacy
// accumulation the moment the fix deploys, without waiting a full interval),
// then once per clean interval. Blocks until context is cancelled. Errors are
// logged and retried on the next tick — a transient DB outage must not kill
// the maintenance loop (same posture as outbox.Cleaner and DLQCleaner).
func (c *ProcessedEventsCleaner) Run(ctx context.Context) error {
	c.logger.Info("Processed events cleaner started",
		zap.Int("retention_days", c.retentionDays),
		zap.Duration("clean_interval", c.cleanInterval),
	)

	if err := c.sweep(ctx); err != nil && ctx.Err() == nil {
		c.logger.Error("Processed events cleanup failed", zap.Error(err))
	}

	ticker := time.NewTicker(c.cleanInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			c.logger.Info("Processed events cleaner stopping")
			return ctx.Err()
		case <-ticker.C:
			if err := c.sweep(ctx); err != nil && ctx.Err() == nil {
				c.logger.Error("Processed events cleanup failed", zap.Error(err))
			}
		}
	}
}

func (c *ProcessedEventsCleaner) sweep(ctx context.Context) error {
	deleted, err := c.repo.Cleanup(ctx, c.retentionDays)
	if err != nil {
		return err
	}
	if deleted > 0 {
		c.logger.Info("Cleaned up old processed events",
			zap.Int64("deleted_count", deleted),
			zap.Int("retention_days", c.retentionDays),
		)
	}
	return nil
}
