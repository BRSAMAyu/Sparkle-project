from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User
from app.services.release_approval import ApprovalStatus, ReleaseApprovalService


@pytest.fixture(autouse=True)
def _disable_release_approval_email(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_send(*args, **kwargs) -> bool:
        return False

    monkeypatch.setattr("app.services.release_approval.email_service._send", _fake_send)


async def _user(db: AsyncSession, username: str, *, superuser: bool = True) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        is_superuser=superuser,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_policy_publish_requires_two_distinct_approvers(db_session: AsyncSession) -> None:
    requester = await _user(db_session, "requester")
    approver_one = await _user(db_session, "approver-one")
    approver_two = await _user(db_session, "approver-two")
    service = ReleaseApprovalService(db_session)

    request = await service.create_request(
        category="policy_publish",
        object_type="policy_rule",
        object_id="router.d0_guardrail",
        title="Promote D0 policy",
        requested_by=requester,
        payload={"diff_ref": "policy-rule-42"},
        submit=True,
    )

    assert request.status == ApprovalStatus.PENDING_REVIEW.value
    assert request.required_approvals == 2

    await service.approve(request, approver=approver_one, comment="checked")
    assert request.status == ApprovalStatus.PENDING_REVIEW.value

    await service.approve(request, approver=approver_two, comment="ship")
    assert request.status == ApprovalStatus.APPROVED.value
    assert len(request.approvals) == 2


@pytest.mark.asyncio
async def test_requester_cannot_self_approve(db_session: AsyncSession) -> None:
    requester = await _user(db_session, "self-approver")
    service = ReleaseApprovalService(db_session)
    request = await service.create_request(
        category="domain_pack_release",
        object_type="domain_pack",
        object_id="gaokao_math_v2",
        title="Release domain pack",
        requested_by=requester,
        submit=True,
    )

    with pytest.raises(HTTPException) as exc:
        await service.approve(request, approver=requester)

    assert exc.value.status_code == 403
    assert request.status == ApprovalStatus.PENDING_REVIEW.value


@pytest.mark.asyncio
async def test_reject_closes_pending_request(db_session: AsyncSession) -> None:
    requester = await _user(db_session, "skill-requester")
    reviewer = await _user(db_session, "skill-reviewer")
    service = ReleaseApprovalService(db_session)
    request = await service.create_request(
        category="skill_systemize",
        object_type="skill",
        object_id="skill_123",
        title="Systemize skill",
        requested_by=requester,
        submit=True,
    )

    await service.reject(request, reviewer=reviewer, reason="insufficient cohort evidence")

    assert request.status == ApprovalStatus.REJECTED.value
    assert request.rejection_reason == "insufficient cohort evidence"
    assert request.needs_admin_attention is False


@pytest.mark.asyncio
async def test_kill_switch_approval_only_accepts_shadow_to_live(db_session: AsyncSession) -> None:
    requester = await _user(db_session, "ops-requester")
    service = ReleaseApprovalService(db_session)

    with pytest.raises(HTTPException) as exc:
        await service.create_request(
            category="kill_switch_promote",
            object_type="kill_switch",
            object_id="aurora_stage24_policy",
            title="Promote kill switch",
            requested_by=requester,
            payload={"source_mode": "off", "target_mode": "live"},
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_submission_creates_admin_notification(db_session: AsyncSession) -> None:
    requester = await _user(db_session, "notification-requester")
    approver = await _user(db_session, "notification-approver")
    service = ReleaseApprovalService(db_session)

    request = await service.create_request(
        category="domain_pack_release",
        object_type="domain_pack",
        object_id="physics_v1",
        title="Publish physics pack",
        requested_by=requester,
        submit=True,
    )

    result = await db_session.execute(select(Notification).where(Notification.user_id == approver.id))
    notifications = list(result.scalars().all())
    assert request.notification_state["notification_count"] >= 1
    assert notifications
    assert notifications[0].data["request_id"] == str(request.id)
