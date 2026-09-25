"""WT378-02/03 复核修复（wt379 轮2）：P-03 抑制态读写诚实性.

轮1猎缺 + 轮2独立复核 CONFIRMED 的同根缺陷（服务层吞错）：
- 02 写假成功：``_update_explicit`` 捕获一切写异常后静默返回，record_ignore_today /
  record_mute 照常返回成功 payload，端点 200「Suggestion feedback recorded」——
  DB 瞬断时用户看到「不再提醒」已生效，抑制态零落库，nudge 照发。
- 03 读 fail-open：``_read_explicit`` 读异常返回 {}，get_suppression 判「未抑制」——
  mute 被瞬时读错误击穿。

修复契约：
- 写失败如实抛 ``ProactiveSuggestionFeedbackError``（API 映射 503，不谎报成功）；
- 读失败 fail-closed（抛错，由调用方按「不可得 ≠ 未抑制」处理：celery 重试 /
  事件处理失败留痕），绝不把读失败当成「没有抑制」。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.v1.notification_center as notification_center_api
from app.models.notification import Notification
from app.schemas.unified_notification import SuggestionActionRequest
from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService


class _ExplodingSession:
    """写/读路径必炸的 session 替身（模拟 DB 瞬断：连接闪断/锁超时）。"""

    def __init__(self) -> None:
        self.rollback_called = False

    async def execute(self, _stmt):
        raise RuntimeError("db flash cut (probe)")

    async def rollback(self) -> None:
        self.rollback_called = True

    async def commit(self) -> None:
        raise RuntimeError("db flash cut (probe)")

    def add(self, _obj) -> None:  # pragma: no cover - 写失败路径不应触达
        raise RuntimeError("db flash cut (probe)")


@pytest.mark.asyncio
async def test_write_failure_raises_not_fake_success():
    """WT378-02：写失败必须抛错；修前返回 cooldown 成功 payload（假成功）。"""
    from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackError

    service = ProactiveSuggestionFeedbackService(_ExplodingSession())  # type: ignore[arg-type]

    with pytest.raises(ProactiveSuggestionFeedbackError):
        await service.record_ignore_today("11111111-1111-1111-1111-111111111111", "comeback_nudge")

    with pytest.raises(ProactiveSuggestionFeedbackError):
        await service.record_mute("11111111-1111-1111-1111-111111111111", "comeback_nudge")


@pytest.mark.asyncio
async def test_read_failure_fails_closed_not_open():
    """WT378-03：读失败必须 fail-closed（抛错）；修前返回 None =「未抑制」击穿静音。"""
    service = ProactiveSuggestionFeedbackService(_ExplodingSession())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError):
        await service.get_suppression("11111111-1111-1111-1111-111111111111", "comeback_nudge")


@pytest.mark.asyncio
async def test_api_maps_persist_failure_to_503(
    db_session: AsyncSession, test_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """API 层不谎报成功：落库失败 → 503（修前 200 + 成功 message）。"""
    from fastapi import HTTPException

    from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackError

    notification = Notification(
        user_id=test_user.id,
        title="你的学习计划状态",
        content="距离「计算机网络」目标截止还有 3 天。",
        type="comeback_nudge",
        data={"suggestion_type": "comeback_nudge"},
        is_read=False,
    )
    db_session.add(notification)
    await db_session.commit()

    async def _broken(self, user_id, suggestion_type, *, now=None):  # noqa: ANN001
        raise ProactiveSuggestionFeedbackError("persist failed (probe)")

    monkeypatch.setattr(ProactiveSuggestionFeedbackService, "record_ignore_today", _broken)

    with pytest.raises(HTTPException) as exc_info:
        await notification_center_api.record_suggestion_action(
            notification.id,
            SuggestionActionRequest(action="ignore_today"),
            current_user=test_user,
            db=db_session,
        )

    assert exc_info.value.status_code == 503
    assert "recorded" not in str(exc_info.value.detail).lower()
