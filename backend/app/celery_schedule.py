
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
