from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.audit_log import DataAccessLog
from app.models.user import User
from app.signals.research_mode import ConsentTracker

router = APIRouter(prefix="/research/consent", tags=["research-consent"])


class ResearchConsentUpdate(BaseModel):
    consents: dict[str, bool] = Field(default_factory=dict)
    source: str = "settings_page"
    version: str = "1.0"


class ResearchConsentResponse(BaseModel):
    required_consents: list[str]
    statuses: dict[str, bool]
    records: list[dict[str, Any]]
    can_include_in_research: bool


@router.get("", response_model=ResearchConsentResponse)
async def get_research_consent(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchConsentResponse:
    tracker = ConsentTracker(db)
    statuses = await tracker.check_all_consents_db(str(current_user.id))
    records = await tracker.get_user_consents_db(str(current_user.id))
    return ResearchConsentResponse(
        required_consents=sorted(ConsentTracker.REQUIRED_CONSENTS),
        statuses=statuses,
        records=records,
        can_include_in_research=all(statuses.values()),
    )


@router.put("", response_model=ResearchConsentResponse)
async def update_research_consent(
    payload: ResearchConsentUpdate,
    *,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchConsentResponse:
    tracker = ConsentTracker(db)
    valid_types = ConsentTracker.REQUIRED_CONSENTS
    changed: dict[str, bool] = {}
    for consent_type, granted in payload.consents.items():
        if consent_type not in valid_types:
            continue
        if granted:
            await tracker.grant_consent_db(
                user_id=str(current_user.id),
                consent_type=consent_type,
                source=payload.source,
                version=payload.version,
            )
        else:
            await tracker.revoke_consent_db(
                user_id=str(current_user.id),
                consent_type=consent_type,
                source=payload.source,
            )
        changed[consent_type] = bool(granted)

    db.add(
        DataAccessLog(
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            resource_type="research_consent",
            resource_id=str(current_user.id),
            action="update",
            request_method=request.method,
            request_path=str(request.url.path),
            request_params={"changed": changed, "source": payload.source, "version": payload.version},
            response_status="200",
        )
    )
    await db.commit()
    return await get_research_consent(db=db, current_user=current_user)
