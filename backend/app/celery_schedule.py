
from app.workers.cleanup_worker import cleanup_galaxy_outbox, cleanup_outbox_events


def setup_periodic_tasks(sender, **kwargs):
    # Execute daily at midnight
    sender.add_periodic_task(
        86400.0,
        cleanup_outbox_events.s(),
        name='cleanup-outbox-every-day'
    )

    sender.add_periodic_task(
        86400.0,
        cleanup_galaxy_outbox.s(),
        name='cleanup-galaxy-outbox-every-day'
    )

    # Aurora scheduled wake scanner — every 15 minutes
    from app.core.celery_tasks import scan_aurora_scheduled_wakes
    sender.add_periodic_task(
        900.0,
        scan_aurora_scheduled_wakes.s(),
        name='scan-aurora-scheduled-wakes-every-15min'
    )

    # Community error pattern aggregation — every 6 hours
    from app.core.celery_tasks import aggregate_community_error_patterns
    sender.add_periodic_task(
        21600.0,
        aggregate_community_error_patterns.s(),
        name='aggregate-community-errors-every-6h'
    )

    # Trace compaction daily sweep — compact traces beyond retention window
    from app.core.celery_tasks import scan_trace_compaction
    sender.add_periodic_task(
        86400.0,
        scan_trace_compaction.s(),
        name='scan-trace-compaction-every-day'
    )

    # Aurora DualCore → SGW outcome evaluator — every hour
    from app.core.celery_tasks import evaluate_routing_outcomes
    sender.add_periodic_task(
        3600.0,
        evaluate_routing_outcomes.s(),
        name='evaluate-routing-outcomes-every-hour'
    )

    # L4 daily learning loop — yesterday's bottleneck → today's focus
    from app.core.celery_tasks import run_daily_goal_reflections
    sender.add_periodic_task(
        86400.0,
        run_daily_goal_reflections.s(),
        name='run-daily-goal-reflections-every-day'
    )

    # State decay/retraction maintenance — prevents stale short-term state from becoming identity
    from app.core.celery_tasks import apply_memory_decay, spine_auto_deprecate_skills, spine_expire_stale_states
    sender.add_periodic_task(
        21600.0,
        spine_expire_stale_states.s(),
        name='spine-expire-stale-states-every-6h'
    )
    sender.add_periodic_task(
        86400.0,
        spine_auto_deprecate_skills.s(),
        name='spine-auto-deprecate-skills-every-day'
    )
    sender.add_periodic_task(
        86400.0,
        apply_memory_decay.s(),
        name='apply-memory-decay-every-day'
    )
