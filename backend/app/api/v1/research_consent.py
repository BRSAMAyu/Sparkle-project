from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.signals.research_mode import ConsentTracker

router = APIRouter(prefix="/research/consent", tags=["research-consent"])


class ConsentRecordResponse(BaseModel):
    consent_id: str
    user_id: str
    protocol_id: str
    consent_type: str
    granted: bool
    granted_at: str
    revoked_at: str = ""
    scope: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    version: str
    source: str
    reason: str = ""
    initiator: str = "user"
    ip_hash: str = ""


class ConsentOverviewResponse(BaseModel):
    required_status: dict[str, bool]
    can_include_in_research: bool
    records: list[ConsentRecordResponse]


class ConsentRevokeRequest(BaseModel):
    protocol_id: str = Field(..., min_length=1, max_length=64)
    reason: str = Field(default="user_revoked", max_length=500)


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return None


def _serialize_record(record: dict[str, Any]) -> ConsentRecordResponse:
    protocol_id = str(record.get("protocol_id") or record.get("consent_type") or "")
    return ConsentRecordResponse(
        consent_id=str(record.get("consent_id") or ""),
        user_id=str(record.get("user_id") or ""),
        protocol_id=protocol_id,
        consent_type=str(record.get("consent_type") or protocol_id),
        granted=bool(record.get("granted")),
        granted_at=str(record.get("granted_at") or ""),
        revoked_at=str(record.get("revoked_at") or ""),
        scope=list(record.get("scope") or []),
        evidence=dict(record.get("evidence") or {}),
        version=str(record.get("version") or "1.0"),
        source=str(record.get("source") or "api"),
        reason=str(record.get("reason") or ""),
        initiator=str(record.get("initiator") or "user"),
        ip_hash=str(record.get("ip_hash") or ""),
    )


# route-tier: authed
@router.get("", response_model=ConsentOverviewResponse)
async def get_research_consent(
    include_revoked: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentOverviewResponse:
    tracker = ConsentTracker()
    user_id = str(current_user.id)
    records = await tracker.get_user_consents_async(user_id, db=db, include_revoked=include_revoked)
    required_status = await tracker.check_all_consents_async(user_id, db=db)
    return ConsentOverviewResponse(
        required_status=required_status,
        can_include_in_research=all(required_status.values()),
        records=[_serialize_record(record) for record in records],
    )


# route-tier: authed
@router.post("/revoke", response_model=ConsentRecordResponse)
async def revoke_research_consent(
    payload: ConsentRevokeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentRecordResponse:
    tracker = ConsentTracker()
    record = await tracker.revoke_consent_async(
        user_id=str(current_user.id),
        protocol_id=payload.protocol_id,
        reason=payload.reason,
        initiator="user",
        ip_address=_client_ip(request),
        db=db,
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active consent exists for this protocol",
        )
    return _serialize_record(record.to_dict())
