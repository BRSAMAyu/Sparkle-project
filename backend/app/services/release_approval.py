from __future__ import annotations

import html
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.config import settings
from app.core.email_service import email_service
from app.models.base import GUID, BaseModel
from app.models.notification import Notification
from app.models.user import User

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class ApprovalCategory(StrEnum):
    POLICY_PUBLISH = "policy_publish"
    EXPERIMENT_PROMOTE = "experiment_promote"
    SKILL_SYSTEMIZE = "skill_systemize"
    DOMAIN_PACK_RELEASE = "domain_pack_release"
    KILL_SWITCH_PROMOTE = "kill_switch_promote"
    HIGH_RISK_CONFIG = "high_risk_config"


DOUBLE_APPROVAL_CATEGORIES = {
    ApprovalCategory.POLICY_PUBLISH.value,
    ApprovalCategory.EXPERIMENT_PROMOTE.value,
    ApprovalCategory.SKILL_SYSTEMIZE.value,
}


class ReleaseApprovalRequest(BaseModel):
    __tablename__ = "release_approval_requests"

    category = Column(String(64), nullable=False, index=True)
    object_type = Column(String(64), nullable=False, index=True)
    object_id = Column(String(128), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    payload = Column(JSONBCompat, nullable=False, default=dict)

    status = Column(String(32), nullable=False, default=ApprovalStatus.DRAFT.value, index=True)
    requested_by_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    submitted_at = Column(DateTime, nullable=True, index=True)

    required_approvals = Column(Integer, nullable=False, default=1)
    approvals = Column(JSONBCompat, nullable=False, default=list)
    rejections = Column(JSONBCompat, nullable=False, default=list)
    reviewer_ids = Column(JSONBCompat, nullable=False, default=list)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    applied_at = Column(DateTime, nullable=True, index=True)
    applied_by_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    apply_result = Column(JSONBCompat, nullable=True)
    notification_state = Column(JSONBCompat, nullable=False, default=dict)
    needs_admin_attention = Column(Boolean, nullable=False, default=False, index=True)

    requested_by = relationship("User", foreign_keys=[requested_by_id])
    applied_by = relationship("User", foreign_keys=[applied_by_id])


Index(
    "idx_release_approval_category_status_created",
    ReleaseApprovalRequest.category,
    ReleaseApprovalRequest.status,
    ReleaseApprovalRequest.created_at,
)
Index(
    "idx_release_approval_object_status",
    ReleaseApprovalRequest.object_type,
    ReleaseApprovalRequest.object_id,
    ReleaseApprovalRequest.status,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_identifier(value: Any) -> str:
    return str(value or "").strip().lower()


def _approval_event(user: User, comment: str | None = None) -> dict[str, Any]:
    return {
        "approver_id": str(user.id),
        "approver_email": getattr(user, "email", None),
        "approver_username": getattr(user, "username", None),
        "comment": comment,
        "at": _utcnow().isoformat(),
    }


class ReleaseApprovalService:
    """State machine and governance checks for high-risk release approvals."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(
        self,
        *,
        category: str,
        object_type: str,
        object_id: str,
        title: str,
        requested_by: User | None,
        description: str | None = None,
        payload: dict[str, Any] | None = None,
        submit: bool = False,
    ) -> ReleaseApprovalRequest:
        category = self._validate_category(category)
        required_approvals = self.required_approvals_for(category)
        request = ReleaseApprovalRequest(
            category=category,
            object_type=object_type.strip(),
            object_id=object_id.strip(),
            title=title.strip(),
            description=description,
            payload=payload or {},
            requested_by_id=getattr(requested_by, "id", None),
            required_approvals=required_approvals,
            status=ApprovalStatus.DRAFT.value,
            approvals=[],
            rejections=[],
            reviewer_ids=[],
            notification_state={},
            needs_admin_attention=False,
        )
        self._validate_request(request)
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)

        if submit:
            await self.submit_request(request, actor=requested_by)
        return request

    async def get_request(self, request_id: UUID | str) -> ReleaseApprovalRequest:
        request = await self.db.get(ReleaseApprovalRequest, request_id)
        if not request or request.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release approval request not found")
        return request

    async def list_requests(
        self,
        *,
        status_filter: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReleaseApprovalRequest]:
        query = select(ReleaseApprovalRequest).where(ReleaseApprovalRequest.deleted_at.is_(None))
        if status_filter:
            query = query.where(ReleaseApprovalRequest.status == self._validate_status(status_filter))
        if category:
            query = query.where(ReleaseApprovalRequest.category == self._validate_category(category))
        query = query.order_by(ReleaseApprovalRequest.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_draft(
        self,
        request: ReleaseApprovalRequest,
        *,
        title: str | None = None,
        description: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ReleaseApprovalRequest:
        if request.status != ApprovalStatus.DRAFT.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft approval requests can be edited")
        if title is not None:
            request.title = title.strip()
        if description is not None:
            request.description = description
        if payload is not None:
            request.payload = payload
        self._validate_request(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def submit_request(self, request: ReleaseApprovalRequest, *, actor: User | None) -> ReleaseApprovalRequest:
        if request.status != ApprovalStatus.DRAFT.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft requests can be submitted")
        request.status = ApprovalStatus.PENDING_REVIEW.value
        request.submitted_at = _utcnow()
        request.needs_admin_attention = True
        await self._notify_approvers(request, actor=actor)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def approve(
        self,
        request: ReleaseApprovalRequest,
        *,
        approver: User,
        comment: str | None = None,
    ) -> ReleaseApprovalRequest:
        if request.status != ApprovalStatus.PENDING_REVIEW.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending requests can be approved")
        self._ensure_authorized_approver(request.category, approver)

        approver_id = str(approver.id)
        if approver_id == str(request.requested_by_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requester cannot approve their own release")

        reviewer_ids = list(request.reviewer_ids or [])
        if approver_id in reviewer_ids:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approver already reviewed this request")

        approvals = list(request.approvals or [])
        approvals.append(_approval_event(approver, comment))
        reviewer_ids.append(approver_id)
        request.approvals = approvals
        request.reviewer_ids = reviewer_ids

        if len(approvals) >= request.required_approvals:
            request.status = ApprovalStatus.APPROVED.value
            request.reviewed_at = _utcnow()
            request.needs_admin_attention = False

        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def reject(
        self,
        request: ReleaseApprovalRequest,
        *,
        reviewer: User,
        reason: str,
    ) -> ReleaseApprovalRequest:
        if request.status != ApprovalStatus.PENDING_REVIEW.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending requests can be rejected")
        self._ensure_authorized_approver(request.category, reviewer)

        reviewer_id = str(reviewer.id)
        reviewer_ids = list(request.reviewer_ids or [])
        if reviewer_id in reviewer_ids:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reviewer already reviewed this request")

        rejections = list(request.rejections or [])
        rejections.append(_approval_event(reviewer, reason))
        reviewer_ids.append(reviewer_id)
        request.rejections = rejections
        request.reviewer_ids = reviewer_ids
        request.rejection_reason = reason
        request.status = ApprovalStatus.REJECTED.value
        request.reviewed_at = _utcnow()
        request.needs_admin_attention = False
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def apply(
        self,
        request: ReleaseApprovalRequest,
        *,
        actor: User,
        result: dict[str, Any] | None = None,
    ) -> ReleaseApprovalRequest:
        if request.status != ApprovalStatus.APPROVED.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only approved requests can be applied")
        request.status = ApprovalStatus.APPLIED.value
        request.applied_at = _utcnow()
        request.applied_by_id = actor.id
        request.apply_result = result or {"status": "recorded", "applied_by": str(actor.id)}
        request.needs_admin_attention = False
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def soft_delete(self, request: ReleaseApprovalRequest) -> None:
        if request.status not in (ApprovalStatus.DRAFT.value, ApprovalStatus.REJECTED.value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft or rejected approval requests can be deleted",
            )
        request.soft_delete()
        await self.db.flush()

    async def dashboard_summary(self) -> dict[str, Any]:
        pending_result = await self.db.execute(
            select(func.count(ReleaseApprovalRequest.id)).where(
                ReleaseApprovalRequest.deleted_at.is_(None),
                ReleaseApprovalRequest.status == ApprovalStatus.PENDING_REVIEW.value,
            )
        )
        attention_result = await self.db.execute(
            select(func.count(ReleaseApprovalRequest.id)).where(
                ReleaseApprovalRequest.deleted_at.is_(None),
                ReleaseApprovalRequest.needs_admin_attention.is_(True),
            )
        )
        pending_count = int(pending_result.scalar() or 0)
        attention_count = int(attention_result.scalar() or 0)
        by_category: dict[str, int] = {}
        rows = await self.db.execute(
            select(ReleaseApprovalRequest.category, func.count(ReleaseApprovalRequest.id))
            .where(
                ReleaseApprovalRequest.deleted_at.is_(None),
                ReleaseApprovalRequest.status == ApprovalStatus.PENDING_REVIEW.value,
            )
            .group_by(ReleaseApprovalRequest.category)
        )
        for category, count in rows.all():
            by_category[str(category)] = int(count or 0)
        return {
            "pending_count": pending_count,
            "attention_count": attention_count,
            "red_dot": bool(attention_count),
            "pending_by_category": by_category,
        }

    def required_approvals_for(self, category: str) -> int:
        if category in DOUBLE_APPROVAL_CATEGORIES:
            return 2
        return 1

    def approver_identifiers_for(self, category: str) -> list[str]:
        raw = getattr(settings, "RELEASE_APPROVERS_BY_CATEGORY", {}) or {}
        if not isinstance(raw, dict):
            return []
        identifiers: list[str] = []
        for key in (category, "*"):
            values = raw.get(key) or []
            if isinstance(values, str):
                values = [values]
            identifiers.extend(_normalize_identifier(value) for value in values if _normalize_identifier(value))
        return identifiers

    def _validate_category(self, category: str) -> str:
        value = str(category or "").strip()
        allowed = {item.value for item in ApprovalCategory}
        if value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported release approval category: {value}",
            )
        return value

    def _validate_status(self, value: str) -> str:
        status_value = str(value or "").strip()
        allowed = {item.value for item in ApprovalStatus}
        if status_value not in allowed:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unsupported status: {value}")
        return status_value

    def _validate_request(self, request: ReleaseApprovalRequest) -> None:
        if not request.object_type or not request.object_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="object_type and object_id are required")
        if not request.title:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="title is required")
        if request.category == ApprovalCategory.KILL_SWITCH_PROMOTE.value:
            target_mode = str((request.payload or {}).get("target_mode") or "").lower()
            source_mode = str((request.payload or {}).get("source_mode") or "").lower()
            if source_mode == "shadow" and target_mode == "live":
                return
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="kill_switch_promote approvals are only for shadow -> live changes",
            )

    def _ensure_authorized_approver(self, category: str, user: User) -> None:
        identifiers = self.approver_identifiers_for(category)
        if not identifiers:
            if user.is_superuser:
                return
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Release approver is not configured")

        user_identifiers = {
            _normalize_identifier(user.id),
            _normalize_identifier(getattr(user, "email", None)),
            _normalize_identifier(getattr(user, "username", None)),
        }
        if not user_identifiers.intersection(identifiers):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not an approver for this category")

    async def _notify_approvers(self, request: ReleaseApprovalRequest, *, actor: User | None) -> None:
        users = await self._resolve_approver_users(request.category)
        created_notifications = 0
        sent_emails = 0
        for user in users:
            notification = Notification(
                user_id=user.id,
                title="Release approval pending",
                content=f"{request.category}: {request.title}",
                type="release_approval",
                data={
                    "request_id": str(request.id),
                    "category": request.category,
                    "object_type": request.object_type,
                    "object_id": request.object_id,
                    "requested_by": str(getattr(actor, "id", "") or ""),
                    "admin_path": f"/api/v1/release_approvals/{request.id}",
                },
            )
            self.db.add(notification)
            created_notifications += 1
            if user.email:
                sent = await email_service._send(
                    user.email,
                    f"[Sparkle] Release approval pending: {request.title}",
                    self._approval_email_html(request),
                )
                sent_emails += int(bool(sent))

        request.notification_state = {
            "notified_at": _utcnow().isoformat(),
            "notification_count": created_notifications,
            "email_sent_count": sent_emails,
        }
        if not users:
            logger.warning("release_approval_no_approvers category={} request_id={}", request.category, request.id)

    async def _resolve_approver_users(self, category: str) -> list[User]:
        identifiers = self.approver_identifiers_for(category)
        if not identifiers:
            result = await self.db.execute(
                select(User).where(User.is_superuser.is_(True), User.is_active.is_(True)).limit(50)
            )
            return list(result.scalars().all())

        result = await self.db.execute(
            select(User).where(
                User.is_active.is_(True),
                (
                    func.lower(User.email).in_(identifiers)
                    | func.lower(User.username).in_(identifiers)
                    | User.id.in_([value for value in identifiers if self._looks_like_uuid(value)])
                ),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _looks_like_uuid(value: str) -> bool:
        try:
            UUID(value)
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _approval_email_html(request: ReleaseApprovalRequest) -> str:
        title = html.escape(request.title)
        category = html.escape(request.category)
        object_type = html.escape(request.object_type)
        object_id = html.escape(request.object_id)
        return f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #222;">
    <h2>Sparkle release approval pending</h2>
    <p><strong>{title}</strong></p>
    <p>Category: {category}</p>
    <p>Object: {object_type}/{object_id}</p>
    <p>Open the admin dashboard to approve or reject this request.</p>
  </body>
</html>
"""
