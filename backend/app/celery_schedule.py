from celery.schedules import crontab

from app.workers.cleanup_worker import cleanup_galaxy_outbox, cleanup_outbox_events


def setup_periodic_tasks(sender, **kwargs):
    # GDPR: clean up login attempts older than 90 days — daily at 04:00
    from app.tasks.login_attempt_cleanup import cleanup_old_login_attempts
    sender.add_periodic_task(
        crontab(hour=4, minute=0),
        cleanup_old_login_attempts.s(),
        name='cleanup-old-login-attempts-daily'
    )

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

    # Aurora DualCore → SGW outcome evaluator — every 30 minutes
    # EI-08：仅保留 celery_app.conf.beat_schedule 里的 "routing-outcome-evaluation"
    # （1800s + args=(200,)）。此处原 3600s 条目与它构成双频执行，已删除。

    # L4 daily learning loop — yesterday's bottleneck → today's focus
    from app.core.celery_tasks import run_daily_goal_reflections
    sender.add_periodic_task(
        86400.0,
        run_daily_goal_reflections.s(),
        name='run-daily-goal-reflections-every-day'
    )

    # L4 Job 2: PolicyEffectCompaction — every 6 hours
    from app.core.celery_tasks import run_l4_policy_effect_compaction
    sender.add_periodic_task(
        21600.0,
        run_l4_policy_effect_compaction.s(),
        name='run-l4-policy-effect-compaction-every-6h'
    )

    # L4 Job 3: SkillCandidate extraction — daily
    from app.core.celery_tasks import run_l4_skill_candidate_extraction
    sender.add_periodic_task(
        86400.0,
        run_l4_skill_candidate_extraction.s(),
        name='run-l4-skill-candidate-extraction-every-day'
    )

    # L4 Job 4: SourceEffectiveness analysis — daily
    from app.core.celery_tasks import run_l4_source_effectiveness
    sender.add_periodic_task(
        86400.0,
        run_l4_source_effectiveness.s(),
        name='run-l4-source-effectiveness-every-day'
    )

    # L4 Job 5: CommunityAggregation — every 6 hours
    from app.core.celery_tasks import run_l4_community_aggregation
    sender.add_periodic_task(
        21600.0,
        run_l4_community_aggregation.s(),
        name='run-l4-community-aggregation-every-6h'
    )

    # L4 Job 6: StateDecayAndRetraction — every 6 hours
    from app.core.celery_tasks import run_l4_state_decay_and_retraction
    sender.add_periodic_task(
        21600.0,
        run_l4_state_decay_and_retraction.s(),
        name='run-l4-state-decay-and-retraction-every-6h'
    )

    # L4AsyncEngine (Aurora runtime) periodic sweep — every 4 hours
    from app.core.celery_tasks import run_l4_async_engine_sweep
    sender.add_periodic_task(
        14400.0,
        run_l4_async_engine_sweep.s(),
        name='run-l4-async-engine-sweep-every-4h'
    )

    # P4-RES research improvement loop — every 6 hours
    from app.core.celery_tasks import run_research_improvement_loop
    sender.add_periodic_task(
        21600.0,
        run_research_improvement_loop.s(),
        name='run-research-improvement-loop-every-6h'
    )

    # P4-PCI community privacy maintenance — every 4 hours
    from app.core.celery_tasks import run_community_privacy_maintenance
    sender.add_periodic_task(
        14400.0,
        run_community_privacy_maintenance.s(),
        name='run-community-privacy-maintenance-every-4h'
    )

    # P4 counterfactual policy evaluation — daily report generation
    from app.core.celery_tasks import run_counterfactual_evaluations
    sender.add_periodic_task(
        86400.0,
        run_counterfactual_evaluations.s(),
        name='run-counterfactual-evaluations-every-day'
    )

    # EI-08：spine_expire_stale_states / spine_auto_deprecate_skills / apply_memory_decay
    # 只在 celery_app.conf.beat_schedule 注册（带 crontab 与 args 的确定性条目：
    # spine-expire-stale-states */6h@:30 args=500、spine-auto-deprecate-skills 04:00 args=500、
    # memory-decay 03:30 args=200）。此处原先的 interval 版条目与它们构成双频执行，已删除。

    # SafeExperiment guardrail monitor — pause unsafe canaries/live experiments within 30 minutes
    from app.core.celery_tasks import monitor_safe_experiment_guardrails
    sender.add_periodic_task(
        1800.0,
        monitor_safe_experiment_guardrails.s(),
        name='monitor-safe-experiment-guardrails-every-30min'
    )

    # FV-03: SparkleGoalBench regression benchmark — Sundays at 03:00.
    from app.core.celery_tasks import run_weekly_benchmark
    sender.add_periodic_task(
        crontab(day_of_week='sun', hour=3, minute=0),
        run_weekly_benchmark.s('full'),
        name='run-weekly-sparkle-goal-bench'
    )
