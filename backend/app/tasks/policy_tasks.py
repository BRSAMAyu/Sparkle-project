from __future__ import annotations

from celery import shared_task

from app.db.session import get_db_context
from app.services.policy_scheduler_service import PolicySchedulerService


@shared_task(
    name="tasks.policy.process_due_policies",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def process_due_policies() -> dict[str, int]:
    import asyncio

    async def _run() -> dict[str, int]:
        with get_db_context() as db:
            return await PolicySchedulerService(db).process_due_policies()

    return asyncio.run(_run())
