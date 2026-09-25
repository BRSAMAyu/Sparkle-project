"""WT378-01 复核修复（wt379 轮2）：study_minutes 容错解析——自由文本偏好不得 500.

机制（轮1猎缺 + 轮2独立复核 CONFIRMED）：
- ``collect_first_action_context`` 曾对 study_minutes 直接 ``int()``，无
  TypeError/ValueError 防护；
- 上游 ``profile_transparency._coerce_preference_value`` 允许自由文本落库
  （``"30分钟"`` → ``{"value": "30分钟"}``）；
- 用户留下非纯数字 study_time_preference 后，GET/POST /journey/first-action
  每次都 500（GET 是重开 App 回放唯一来源）——持久性破坏。

契约：collect 对任意显式偏好形态不抛错——数值/数值字符串原样解析；自由文本
尽力提取数字（"30分钟"→30）；无数字则 study_minutes=None（与同函数对
knowledge_level/learning_style 的 str() 容错口径对齐）。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryGoal
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.services.first_action_service import collect_first_action_context


@pytest.fixture(name="goal_user")
async def goal_user_fixture(db_session: AsyncSession) -> User:
    """active goal + 偏好行（偏好值由各用例覆写）。"""
    user = User(username="wt379u", email="wt379@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        MemoryGoal(
            user_id=user.id,
            title="三个月内跑通一个 side project",
            status="active",
            source_type="user_state",
            metadata_payload={"goal_type": "project"},
        )
    )
    db_session.add(UserPreferencesCenter(user_id=user.id, explicit={}))
    await db_session.commit()
    return user


async def _set_study_pref(db_session: AsyncSession, user: User, explicit_value) -> None:
    row = (
        (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user.id)))
        .scalars()
        .one()
    )
    row.explicit = {"study_time_preference": explicit_value}
    await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("explicit_value", "expected"),
    [
        ({"value": "30分钟"}, 30),  # 轮1探针原始形态：自由文本带单位 → 提取数字
        ({"value": "看情况"}, None),  # 纯文字无数字 → None，绝不 500
        ({"minutes": 25}, 25),  # onboarding 结构化形态
        (45, 45),  # plain int 形态
        ("60", 60),  # 纯数字字符串
    ],
)
async def test_study_minutes_free_text_never_raises(
    db_session: AsyncSession, goal_user: User, explicit_value, expected
) -> None:
    """任意 study_time_preference 形态下 collect 都不崩（修前 ValueError 冒泡 → 500）。"""
    await _set_study_pref(db_session, goal_user, explicit_value)

    context = await collect_first_action_context(db_session, user_id=goal_user.id)

    assert context is not None, "active goal 存在时必须产出 context"
    assert context.study_minutes == expected


@pytest.mark.asyncio
async def test_free_text_preference_still_yields_goal_context(db_session: AsyncSession, goal_user: User) -> None:
    """自由文本偏好在场时，goal 投影与其余字段照常返回（500 之外的退化面不得波及）。"""
    await _set_study_pref(db_session, goal_user, {"value": "1小时"})

    context = await collect_first_action_context(db_session, user_id=goal_user.id)

    assert context is not None
    assert context.goal_title == "三个月内跑通一个 side project"
    assert context.goal_type == "project"
    assert context.study_minutes == 1  # "1小时" 提取数字 1
