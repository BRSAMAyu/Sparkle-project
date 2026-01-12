import json
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_superuser
from app.core.cache import cache_service
from app.schemas.dlq import DlqEntry, DlqReplayRequest
from app.services.analytics.cognitive_stream_worker import CognitiveStreamWorker


router = APIRouter(prefix="/dlq", tags=["DLQ"])


@router.get("/", response_model=List[DlqEntry])
async def list_dlq_events(
    limit: int = 50,
    _admin=Depends(get_current_active_superuser),
) -> List[DlqEntry]:
    if not cache_service.redis:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis unavailable")

    entries = await cache_service.redis.xrevrange(
        CognitiveStreamWorker.DLQ_STREAM,
        count=limit
    )
    results: List[DlqEntry] = []
    for message_id, data in entries:
        payload_raw = data.get("data")
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except json.JSONDecodeError:
            payload = {"raw": payload_raw}
        results.append(DlqEntry(message_id=message_id, payload=payload))
    return results


@router.post("/replay", response_model=Dict[str, Any])
async def replay_dlq_events(
    request: DlqReplayRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_active_superuser),
) -> Dict[str, Any]:
    if request.approver_id == str(admin.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approver must differ from admin")

    if not cache_service.redis:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis unavailable")

    worker = CognitiveStreamWorker(db, cache_service.redis)
    replayed = []
    failed = []

    for message_id in request.message_ids:
        entry = await cache_service.redis.xrange(CognitiveStreamWorker.DLQ_STREAM, message_id, message_id)
        if not entry:
            failed.append({"message_id": message_id, "error": "not_found"})
            continue

        _, data = entry[0]
        payload_raw = data.get("data")
        if not payload_raw:
            failed.append({"message_id": message_id, "error": "empty_payload"})
            continue

        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            failed.append({"message_id": message_id, "error": "invalid_payload"})
            continue

        dlq_event = payload.get("event")
        if not dlq_event:
            failed.append({"message_id": message_id, "error": "missing_event"})
            continue

        try:
            await worker.replay_dlq_event(
                dlq_event,
                audit_headers={
                    "x-audit-admin-id": str(admin.id),
                    "x-audit-approver-id": request.approver_id,
                    "x-audit-reason-code": request.reason_code,
                },
            )
            if request.delete_after:
                await cache_service.redis.xdel(CognitiveStreamWorker.DLQ_STREAM, message_id)
            replayed.append(message_id)
        except Exception as exc:
            failed.append({"message_id": message_id, "error": str(exc)})

    return {"replayed": replayed, "failed": failed}
