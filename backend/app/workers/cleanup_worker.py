import asyncio
from celery import shared_task
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)

async def _run_cleanup_query(query_str: str, params: dict, description: str):
    """Internal helper to run cleanup queries asynchronously"""
    logger.info(f"Starting {description}")
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(text(query_str), params)
            await db.commit()
            logger.info(f"Finished {description}: Deleted {result.rowcount} rows")
            return result.rowcount
        except Exception as e:
            await db.rollback()
            logger.error(f"Error during {description}: {e}")
            return 0

@shared_task(name="cleanup_outbox_events")
def cleanup_outbox_events():
    """
    Delete processed outbox events older than 7 days from event_outbox table.
    (Used by Go Gateway/CQRS infrastructure)
    """
    query = """
        DELETE FROM event_outbox 
        WHERE published_at IS NOT NULL 
        AND published_at < NOW() - INTERVAL '7 days'
    """
    # Celery tasks are sync by default, we run the async part using asyncio.run or loop
    return asyncio.run(_run_cleanup_query(query, {}, "event_outbox cleanup"))

@shared_task(name="cleanup_galaxy_outbox")
def cleanup_galaxy_outbox():
    """
    Delete processed outbox events older than 7 days from outbox_events table.
    (Used by Python GalaxyService)
    """
    query = """
        DELETE FROM outbox_events
        WHERE status = 'processed'
        AND processed_at < NOW() - INTERVAL '7 days'
    """
    return asyncio.run(_run_cleanup_query(query, {}, "outbox_events (galaxy) cleanup"))


async def _run_inbox_decay():
    """
    Process inbox decay for learning assets.

    Archives INBOX assets where inbox_expires_at < NOW() using the service layer.
    This ensures proper event_outbox writes with sequence_number.
    """
    from app.services.learning_asset_service import learning_asset_service

    logger.info("Starting learning assets inbox decay")
    async with AsyncSessionLocal() as db:
        try:
            archived_count = await learning_asset_service.process_inbox_expiry(db)
            await db.commit()
            logger.info(f"Inbox decay completed: archived {archived_count} assets")
            return archived_count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error during inbox decay: {e}")
            return 0


@shared_task(name="process_inbox_decay")
def process_inbox_decay():
    """
    Celery task to archive expired INBOX learning assets.

    Runs daily to archive assets where inbox_expires_at < NOW().
    Uses the learning_asset_service to ensure proper event_outbox writes.
    """
    return asyncio.run(_run_inbox_decay())