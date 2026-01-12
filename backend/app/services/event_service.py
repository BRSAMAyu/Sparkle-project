from __future__ import annotations

from datetime import datetime
import time
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.core.business_metrics import EVENT_INGEST_TOTAL, EVENT_INGEST_LATENCY, EVENT_DEDUPE_TOTAL
from app.models.event import TrackingEvent


class EventService:
    def __init__(self, db: AsyncSession, event_bus: Optional[EventBus] = None):
        self.db = db
        self.event_bus = event_bus or EventBus()

    async def ingest_events(
        self,
        user_id: UUID,
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        sources = {item.get("source") or "unknown" for item in events}
        source_label = list(sources)[0] if len(sources) == 1 else "mixed"
        event_ids = []
        seen_ids = set()
        for item in events:
            if not item.get("event_id"):
                item["event_id"] = uuid4().hex
            event_ids.append(item["event_id"])
            seen_ids.add(item["event_id"])

        existing = await self._fetch_existing_event_ids(event_ids)
        accepted = 0
        deduped = 0
        failed = 0
        results = []

        new_records: List[TrackingEvent] = []
        now_ms = int(datetime.utcnow().timestamp() * 1000)

        for item in events:
            event_id = item["event_id"]
            if event_id in existing:
                deduped += 1
                results.append({"event_id": event_id, "status": "deduped"})
                continue
            if event_id in seen_ids:
                seen_ids.remove(event_id)
            else:
                deduped += 1
                results.append({"event_id": event_id, "status": "deduped"})
                continue

            try:
                ts_ms = item.get("ts_ms") or now_ms
                record = TrackingEvent(
                    event_id=event_id,
                    user_id=user_id,
                    event_type=item["event_type"],
                    schema_version=item["schema_version"],
                    source=item["source"],
                    ts_ms=ts_ms,
                    entities=item.get("entities"),
                    payload=item.get("payload"),
                    received_at=datetime.utcnow(),
                )
                new_records.append(record)
                results.append({"event_id": event_id, "status": "accepted"})
                accepted += 1
            except Exception as exc:
                failed += 1
                results.append({"event_id": event_id, "status": "failed", "message": str(exc)})

        if new_records:
            self.db.add_all(new_records)
            await self.db.commit()

            for record in new_records:
                await self._publish_event(record)

        EVENT_INGEST_TOTAL.labels(status="accepted").inc(accepted)
        EVENT_INGEST_TOTAL.labels(status="deduped").inc(deduped)
        EVENT_INGEST_TOTAL.labels(status="failed").inc(failed)
        if deduped:
            EVENT_DEDUPE_TOTAL.labels(source=source_label).inc(deduped)
        EVENT_INGEST_LATENCY.labels(source=source_label).observe(time.perf_counter() - start_time)

        return {
            "accepted": accepted,
            "deduped": deduped,
            "failed": failed,
            "results": results,
        }

    async def get_event(self, user_id: UUID, event_id: str) -> Optional[TrackingEvent]:
        result = await self.db.execute(
            select(TrackingEvent)
            .where(TrackingEvent.event_id == event_id)
            .where(TrackingEvent.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def soft_delete_event(self, user_id: UUID, event_id: str) -> bool:
        event = await self.get_event(user_id, event_id)
        if not event:
            return False
        event.deleted_at = datetime.utcnow()
        event.payload = None
        event.entities = None
        await self.db.commit()
        return True

    async def _fetch_existing_event_ids(self, event_ids: List[str]) -> set[str]:
        if not event_ids:
            return set()
        result = await self.db.execute(
            select(TrackingEvent.event_id)
            .where(TrackingEvent.event_id.in_(event_ids))
        )
        return {row[0] for row in result.all()}

    async def _publish_event(self, record: TrackingEvent) -> None:
        payload = {
            "event_id": record.event_id,
            "event_name": record.event_type,
            "event_type": record.event_type,
            "user_id": str(record.user_id),
            "schema_version": record.schema_version,
            "source": record.source,
            "ts_ms": record.ts_ms,
            "entities": record.entities or {},
            "payload": record.payload or {},
        }
        await self.event_bus.publish(
            event_type=record.event_type,
            payload=payload,
            stream="stream:tracking_events",
        )
