from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.community import Group, GroupMember, GroupMessage, GroupRole, GroupType, MessageReport, MessageType
from app.models.user import User
from app.schemas.community import (
    MessageFavoriteCreate,
    MessageForwardRequest,
    MessageReportCreate,
    MessageReportReview,
    ReportReasonEnum,
    ReportStatusEnum,
)
from app.services.community_advanced_service import FavoriteService, ForwardService, ReportService


async def _user(db_session, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _group_with_message(db_session, owner: User, content: str = "hello") -> tuple[Group, GroupMessage]:
    group = Group(name=f"{owner.username}-group", type=GroupType.SQUAD)
    db_session.add(group)
    await db_session.flush()
    db_session.add(GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER))
    message = GroupMessage(
        group_id=group.id,
        sender_id=owner.id,
        message_type=MessageType.TEXT,
        content=content,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(group)
    await db_session.refresh(message)
    return group, message


@pytest.mark.asyncio
async def test_favorite_group_message_requires_membership(db_session) -> None:
    owner = await _user(db_session, "favorite_owner")
    outsider = await _user(db_session, "favorite_outsider")
    _, message = await _group_with_message(db_session, owner)

    with pytest.raises(ValueError, match="无权访问"):
        await FavoriteService.add_favorite(
            db_session,
            outsider.id,
            MessageFavoriteCreate(group_message_id=message.id),
        )


@pytest.mark.asyncio
async def test_report_group_message_requires_membership(db_session) -> None:
    owner = await _user(db_session, "report_owner")
    outsider = await _user(db_session, "report_outsider")
    _, message = await _group_with_message(db_session, owner)

    with pytest.raises(ValueError, match="无权访问"):
        await ReportService.create_report(
            db_session,
            outsider.id,
            MessageReportCreate(
                group_message_id=message.id,
                reason=ReportReasonEnum.SPAM,
            ),
        )


@pytest.mark.asyncio
async def test_review_group_report_requires_group_admin(db_session) -> None:
    owner = await _user(db_session, "review_owner")
    member = await _user(db_session, "review_member")
    _, message = await _group_with_message(db_session, owner)
    db_session.add(GroupMember(group_id=message.group_id, user_id=member.id, role=GroupRole.MEMBER))
    await db_session.commit()

    report = await ReportService.create_report(
        db_session,
        member.id,
        MessageReportCreate(
            group_message_id=message.id,
            reason=ReportReasonEnum.SPAM,
        ),
    )
    await db_session.commit()

    with pytest.raises(ValueError, match="无权操作"):
        await ReportService.review_report(
            db_session,
            member.id,
            report.id,
            MessageReportReview(status=ReportStatusEnum.DISMISSED),
        )


@pytest.mark.asyncio
async def test_forward_group_message_requires_source_membership(db_session) -> None:
    owner = await _user(db_session, "forward_owner")
    outsider = await _user(db_session, "forward_outsider")
    _, source = await _group_with_message(db_session, owner)

    target_group = Group(name="target-group", type=GroupType.SQUAD)
    db_session.add(target_group)
    await db_session.flush()
    db_session.add(GroupMember(group_id=target_group.id, user_id=outsider.id, role=GroupRole.MEMBER))
    await db_session.commit()

    with pytest.raises(ValueError, match="无权访问"):
        await ForwardService.forward_message(
            db_session,
            outsider.id,
            MessageForwardRequest(
                source_type="group",
                source_message_id=source.id,
                target_group_id=target_group.id,
            ),
        )

    reports = (await db_session.execute(select(MessageReport))).scalars().all()
    assert len(reports) == 0
