"""J-02 · 最小 goal capture 服务端契约钉（value before profile 的真源面）.

卡面 Work 2「只问改变 first action 的问题；其他信息延后」的服务端语义：

``POST /profile/onboarding``（``submit_onboarding``）对部分载荷天然支持——
各显式偏好（learning_style / knowledge_level / study_time_minutes /
response_depth / curiosity_preference）逐字段条件写入，goal 独立落
``memory_goals``（``MemoryService.create_goal``，source_type="user_state"）。

本文件把「goal-only 提交」钉为契约：

1. goal 落 ``memory_goals``（J-04 first action 链的真源）——最小捕获即拿到
   useful action 的入场券；
2. 四项偏好零写入——「其他信息延后」在服务端成立（mobile 侧
   onboardingCompleted 推断依赖 study_time_preference/knowledge_level/
   response_style 偏好存在，goal-only 提交后保持 false →
   OnboardingResumeCard「继续引导」入口留存，五问经它可达，零裁减只延后）；
3. first_message 照常回包（goal-only 也有开场白，不假装失败）。

Goal-only 快车道本身是 mobile 侧行为（persona 屏 fast-path），服务端契约
为本卡的独立证据面（Reviewer 可据本文件直接复核服务端半边）。
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.api.v1.profile_transparency import OnboardingRequest, submit_onboarding
from app.models.memory import MemoryGoal
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter


async def _make_user(db_session) -> User:
    user = User(
        username="j02_min_goal",
        email="j02_min_goal@test.local",
        hashed_password="hashed",
        registration_source="email",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_goal_only_onboarding_creates_memory_goal_and_no_preferences(
    db_session,
):
    user = await _make_user(db_session)

    response = await submit_onboarding(
        payload=OnboardingRequest(
            learning_goal="两周内搞定高数期末",
            learning_goal_type="exam",
        ),
        db=db_session,
        current_user=user,
    )

    # 1) goal 落 memory_goals 真源（first action 链可读）。
    goals = (await db_session.execute(select(MemoryGoal).where(MemoryGoal.user_id == user.id))).scalars().all()
    assert len(goals) == 1
    goal = goals[0]
    assert goal.title == "两周内搞定高数期末"
    assert goal.status == "active"
    assert goal.source_type == "user_state"
    assert goal.metadata_payload == {"goal_type": "exam"}

    # 2) 四项偏好零写入——「其他信息延后」的服务端半边。
    center = (
        await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user.id))
    ).scalar_one_or_none()
    explicit_keys = set(center.explicit) if center is not None else set()
    assert not (
        {"learning_style", "knowledge_level"} & explicit_keys
    ), "goal-only 提交不得写学习风格/基础偏好（延后问）"
    assert "study_time_preference" not in explicit_keys
    assert "response_style" not in explicit_keys

    # 3) first_message 照常回包（不假装失败）。
    assert response["status"] == "ok"
    assert isinstance(response["first_message"], str)
    assert len(response["first_message"]) > 0


@pytest.mark.asyncio
async def test_full_onboarding_still_writes_goal_and_preferences(db_session):
    """对照锚：全量载荷路径不受最小捕获改动影响（五问仍全量可达）。"""
    user = await _make_user(db_session)

    response = await submit_onboarding(
        payload=OnboardingRequest(
            learning_goal="流利读英文论文",
            learning_goal_type="skill",
            learning_style="visual",
            study_time_minutes=90,
            knowledge_level="intermediate",
            response_depth=0.7,
            curiosity_preference=0.3,
        ),
        db=db_session,
        current_user=user,
    )

    updated = response["updated"]
    assert updated["learning_goal"] == "流利读英文论文"
    assert updated["learning_style"] == "visual"
    assert updated["knowledge_level"] == "intermediate"
    assert updated["study_time_preference"] == 90

    goal_count = await db_session.scalar(
        select(func.count()).select_from(MemoryGoal).where(MemoryGoal.user_id == user.id)
    )
    assert goal_count == 1
