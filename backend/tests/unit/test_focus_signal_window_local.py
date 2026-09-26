"""V3-FIX-211（focus_signal_processor 墙钟余族）红绿测：14 天偏好窗口端点切墙上钟。

定界（V3-FIX-37 双存储钟实录 + 本卡逐列核）：
- ``FocusSession.start_time`` 是客户端本地墙上钟列；
- ``process_focus_event``（:37-42）修前 ``since = _utcnow() - 14d``（UTC
  瞬间）直比墙上钟列，窗口端点在本地日界附近随时刻漂移 ±8h（V3-FIX-208
  同族）：UTC+8 晚间漏计 14 天前上午的会话，推断偏好样本被漏采。
- ``recency_weight(start_time, now=...)`` 是连续衰减权重（非窗口边界），
  不在本卡登记面，保持不动。

修法：since 改 ``local_midnight_wall(today - WINDOW_DAYS)``（本地零点
naive，V3-FIX-208 先例；勿用 local_midnight_as_utc_naive——那是 UTC 存储
列的换算）。

冻结钟 NOW_EVENING = 2026-09-25 12:00 UTC（上海 = 09-25 20:00）：14 天前
（09-11）本地上午 08:30 的会话必须进入样本，修前被 ``>= 09-11 12:00``
排除 → 偏好更新整批不发生。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus import FocusSession, FocusStatus
from app.models.user import PushPreference, User
from app.services.focus_signal_processor import FocusSignalProcessor
from app.services.profile_write_service import ProfileWriteService

NOW_EVENING = dt.datetime(2026, 9, 25, 12, 0)  # naive UTC；上海本地 = 2026-09-25 20:00


async def test_preference_window_counts_local_fortnight_ago_morning(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海晚间：14 天前本地上午的会话必须进入偏好推断样本。

    修前 since = 09-25 12:00 − 14d = 09-11 12:00（UTC 瞬间）直比墙上钟列，
    09-11 08:30 的 50 分钟会话被漏计 → 样本为空 → preferred_focus_duration
    不写入；修后窗口起点=本地零点 09-11 00:00 → 计入并写入 50 分钟。
    """
    monkeypatch.setattr("app.services.focus_signal_processor._utcnow", lambda: NOW_EVENING)
    captured: list[dict] = []

    async def _spy(self, *, user_id, updates, **_kwargs):  # noqa: ANN001
        captured.append(dict(updates))
        return 1

    monkeypatch.setattr(ProfileWriteService, "update_inferred_preference", _spy)

    user = User(
        username=f"wt507-{uuid4().hex[:8]}",
        email=f"wt507-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    db_session.add(PushPreference(user_id=user.id, timezone="Asia/Shanghai"))
    db_session.add(
        FocusSession(
            user_id=user.id,
            # start_time 是客户端本地墙上钟列（无时区后缀 naive）
            start_time=dt.datetime(2026, 9, 11, 8, 30),
            end_time=dt.datetime(2026, 9, 11, 9, 20),
            duration_minutes=50,
            status=FocusStatus.COMPLETED,
        )
    )
    await db_session.commit()

    await FocusSignalProcessor(db_session).process_focus_event(user.id)

    assert captured, "窗口内会话存在时必须产出偏好更新（修前样本被 UTC 瞬间窗口漏采，整批不发生）"
    assert (
        captured[0].get("preferred_focus_duration") == 50
    ), f"14 天前本地上午会话应计入样本并推出 50 分钟偏好；修前 since=09-11 12:00 把它漏计：{captured}"
