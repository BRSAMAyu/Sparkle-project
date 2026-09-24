from __future__ import annotations

from typing import cast

from celery import shared_task

from app.core.celery_app import _run_async
from app.db.session import AsyncSessionLocal
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
    # NOTE(EI-01): 会话生命周期必须完整位于协程内部（与 app/core/celery_tasks.py 的
    # _run_async 模式一致）。禁止把 `with get_db_context()` 写进 async 函数体 ——
    # 其 __exit__ 里的 asyncio.run() 在运行中的事件循环上会抛 RuntimeError。
    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as db:
            result = await PolicySchedulerService(db).process_due_policies()
            await db.commit()
            return result

    return cast("dict[str, int]", (_run_async(_run())))
