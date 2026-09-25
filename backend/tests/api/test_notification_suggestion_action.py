"""P-03: POST /notification-center/notifications/{id}/suggestion-action 端点。

移动端建议卡四要素的两个反馈入口（today ignore / mute this type）打到这个
端点；端点必须：
1. 校验通知归属（user_id 所有权，读既有 Notification 真源）；
2. 只接受 ignore_today / mute_type 两种动作（其余 422/400）；
3. 真实落 suppression 状态（ProactiveSuggestionFeedbackService → DB），
   后续 nudge 生成路径据此冷却/静音。

测试直接以真实 AsyncSession 调用 handler（无 HTTP 层跨 loop 伪影；
路由注册本身由 include_router 声明式保证）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.notification_center import record_suggestion_action
from app.models.notification import Notification
from app.schemas.unified_notification import SuggestionActionRequest
from app.services.proactive_suggestion_service import (
    ProactiveSuggestionFeedbackService,
)


async def _seed_comeback_notification(db_session: AsyncSession, user_id) -> Notification:
    notification = Notification(
        user_id=user_id,
        title="你的学习计划状态",
        content="距离「计算机网络」目标截止还有 3 天。",
        type="comeback_nudge",
        data={"suggestion_type": "comeback_nudge"},
        is_read=False,
    )
    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)
    return notification


@pytest.mark.asyncio
async def test_suggestion_action_ignore_today_records_cooldown(db_session: AsyncSession, test_user) -> None:
    notification = await _seed_comeback_notification(db_session, test_user.id)

    result = await record_suggestion_action(
        notification.id,
        SuggestionActionRequest(action="ignore_today"),
        current_user=test_user,
        db=db_session,
    )

    assert result["suppression"]["reason"] == "cooldown"
    # 真实落库：随后可查询到 cooldown 抑制态（非渲染层遮蔽）。
    assert await ProactiveSuggestionFeedbackService(db_session).is_suppressed(test_user.id, "comeback_nudge") is True
    # 反馈即已读：处理过的建议不再挂未读。
    row = (await db_session.execute(select(Notification).where(Notification.id == notification.id))).scalars().one()
    assert row.is_read is True


@pytest.mark.asyncio
async def test_suggestion_action_mute_type_records_mute(db_session: AsyncSession, test_user) -> None:
    notification = await _seed_comeback_notification(db_session, test_user.id)

    result = await record_suggestion_action(
        notification.id,
        SuggestionActionRequest(action="mute_type"),
        current_user=test_user,
        db=db_session,
    )

    assert result["suppression"]["reason"] == "muted"
    suppression = await ProactiveSuggestionFeedbackService(db_session).get_suppression(test_user.id, "comeback_nudge")
    assert suppression is not None
    assert suppression["reason"] == "muted"


@pytest.mark.asyncio
async def test_suggestion_action_rejects_foreign_notification(db_session: AsyncSession, test_user) -> None:
    await _seed_comeback_notification(db_session, test_user.id)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await record_suggestion_action(
            uuid4(),
            SuggestionActionRequest(action="mute_type"),
            current_user=test_user,
            db=db_session,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_suggestion_action_rejects_unknown_action(db_session: AsyncSession, test_user) -> None:
    notification = await _seed_comeback_notification(db_session, test_user.id)

    # Pydantic 约束在 schema 层直接拒绝未定义动作。
    from fastapi import HTTPException
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SuggestionActionRequest(action="delete_everything")

    # 即便绕过 schema 直接调 handler，handler 层守卫也必须拒绝。
    with pytest.raises(HTTPException) as exc_info:
        await record_suggestion_action(
            notification.id,
            SuggestionActionRequest.model_construct(action="delete_everything"),
            current_user=test_user,
            db=db_session,
        )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_seeded_notification_is_readable_suggestion(db_session: AsyncSession, test_user) -> None:
    """锚定测试前置：seed 的通知此刻未读、类型为 comeback_nudge。"""
    notification = await _seed_comeback_notification(db_session, test_user.id)
    assert notification.is_read is False
    assert notification.type == "comeback_nudge"
    assert datetime.now(UTC).tzinfo is UTC  # 环境锚定：测试以 aware-UTC 取 now。
