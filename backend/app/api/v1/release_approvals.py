from __future__ import annotations

import html
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.models.user import User
from app.services.release_approval import (
    ApprovalCategory,
    ApprovalStatus,
    ReleaseApprovalRequest,
    ReleaseApprovalService,
)

router = APIRouter(
    prefix="/release_approvals",
    tags=["release-approvals"],
    dependencies=[Depends(get_current_active_superuser)],
)


class ReleaseApprovalCreate(BaseModel):
    category: ApprovalCategory
    object_type: str = Field(..., min_length=1, max_length=64)
    object_id: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    submit: bool = True


class ReleaseApprovalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    payload: dict[str, Any] | None = None


class ReviewPayload(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)


class RejectPayload(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class ApplyPayload(BaseModel):
    result: dict[str, Any] = Field(default_factory=dict)


class ReleaseApprovalResponse(BaseModel):
    id: UUID
    category: str
    object_type: str
    object_id: str
    title: str
    description: str | None
    payload: dict[str, Any]
    status: str
    requested_by_id: UUID | None
    submitted_at: datetime | None
    required_approvals: int
    approvals: list[dict[str, Any]]
    rejections: list[dict[str, Any]]
    reviewer_ids: list[str]
    reviewed_at: datetime | None
    rejection_reason: str | None
    applied_at: datetime | None
    applied_by_id: UUID | None
    apply_result: dict[str, Any] | None
    notification_state: dict[str, Any]
    needs_admin_attention: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


def _service(db: AsyncSession) -> ReleaseApprovalService:
    return ReleaseApprovalService(db)


@router.post("", response_model=ReleaseApprovalResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ReleaseApprovalResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_release_approval(
    payload: ReleaseApprovalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> ReleaseApprovalRequest:
    return await _service(db).create_request(
        category=payload.category.value,
        object_type=payload.object_type,
        object_id=payload.object_id,
        title=payload.title,
        description=payload.description,
        payload=payload.payload,
        requested_by=current_user,
        submit=payload.submit,
    )


@router.get("", response_model=list[ReleaseApprovalResponse])
@router.get("/", response_model=list[ReleaseApprovalResponse], include_in_schema=False)
async def list_release_approvals(
    status_filter: ApprovalStatus | None = Query(default=None, alias="status"),
    category: ApprovalCategory | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ReleaseApprovalRequest]:
    return await _service(db).list_requests(
        status_filter=status_filter.value if status_filter else None,
        category=category.value if category else None,
        limit=limit,
        offset=offset,
    )


@router.get("/dashboard-summary")
async def release_approval_dashboard_summary(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await _service(db).dashboard_summary()


@router.get("/admin-tab", response_class=HTMLResponse)
async def release_approval_admin_tab(db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    service = _service(db)
    summary = await service.dashboard_summary()
    pending = await service.list_requests(status_filter=ApprovalStatus.PENDING_REVIEW.value, limit=20)
    rows = "\n".join(
        (
            "<tr>"
            f"<td>{html.escape(item.category)}</td>"
            f"<td>{html.escape(item.title)}</td>"
            f"<td>{html.escape(item.object_type)}/{html.escape(item.object_id)}</td>"
            f"<td>{len(item.approvals or [])}/{item.required_approvals}</td>"
            f"<td>{item.created_at.isoformat()}</td>"
            "</tr>"
        )
        for item in pending
    )
    red_dot = "true" if summary["red_dot"] else "false"
    html = f"""
<section data-sparkle-admin-tab="release-approvals" data-red-dot="{red_dot}">
  <h2>Release approvals</h2>
  <p>Pending: {summary["pending_count"]} | Needs attention: {summary["attention_count"]}</p>
  <table>
    <thead>
      <tr><th>Category</th><th>Title</th><th>Object</th><th>Approvals</th><th>Created</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""
    return HTMLResponse(content=html)


@router.get("/{request_id}", response_model=ReleaseApprovalResponse)
async def get_release_approval(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ReleaseApprovalRequest:
    return await _service(db).get_request(request_id)


@router.patch("/{request_id}", response_model=ReleaseApprovalResponse)
async def update_release_approval(
    request_id: UUID,
    payload: ReleaseApprovalUpdate,
    db: AsyncSession = Depends(get_db),
) -> ReleaseApprovalRequest:
    service = _service(db)
    request = await service.get_request(request_id)
    return await service.update_draft(
        request,
        title=payload.title,
        description=payload.description,
        payload=payload.payload,
    )


@router.post("/{request_id}/submit", response_model=ReleaseApprovalResponse)
async def submit_release_approval(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> ReleaseApprovalRequest:
    service = _service(db)
    request = await service.get_request(request_id)
    return await service.submit_request(request, actor=current_user)


@router.post("/{request_id}/approve", response_model=ReleaseApprovalResponse)
async def approve_release_approval(
    request_id: UUID,
    payload: ReviewPayload | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> ReleaseApprovalRequest:
    service = _service(db)
    request = await service.get_request(request_id)
    return await service.approve(request, approver=current_user, comment=payload.comment if payload else None)


@router.post("/{request_id}/reject", response_model=ReleaseApprovalResponse)
async def reject_release_approval(
    request_id: UUID,
    payload: RejectPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> ReleaseApprovalRequest:
    service = _service(db)
    request = await service.get_request(request_id)
    return await service.reject(request, reviewer=current_user, reason=payload.reason)


@router.post("/{request_id}/apply", response_model=ReleaseApprovalResponse)
async def apply_release_approval(
    request_id: UUID,
    payload: ApplyPayload | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> ReleaseApprovalRequest:
    service = _service(db)
    request = await service.get_request(request_id)
    return await service.apply(request, actor=current_user, result=payload.result if payload else None)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_release_approval(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = _service(db)
    request = await service.get_request(request_id)
    await service.soft_delete(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
