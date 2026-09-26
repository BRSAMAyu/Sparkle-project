"""V3-FIX-257（P3，wt533 B-02 审计 F2 面）：guest 转正不清洗种子伪造行为统计。

缺陷实录（台账 257 行）：``upgrade_guest`` 原位翻转 registration_source
（app/api/v1/auth.py:1077），但 ``guest_seed_service`` 种下的伪造行为统计随
用户进入生产 cohort——streak 7/30/45、6 成就、13 条 FocusSession≈540 分钟、
demo 节点掌握度。FIX-01（全局榜）/FIX-08（社区）/FIX-20（群推荐）等 cohort
排除词表只挡 registration_source ∈ ('guest','seed') 的身份，转正后排除失效：
全局榜综合分（知识点数×1.0 + 打卡天数×0.5 + 成就数×2.0 + 最长连胜×1.5）
四因子全部来自种子字段。

双断言红测（纪律 1）：
① 转正前 guest cohort 排除生效（FIX-01 现行为，防回归锚点）；
② 原位翻转 registration_source 后伪造统计污染生产面（修前实录）。

守卫用例（纪律 2）：用户 guest 期自建的真实数据必须保留——
catalog 指纹相同但写入晚于种子窗口、或指纹已被真实行为改写的行，
清洗绝不触碰（宁可保守，绝不误删真实学习记录）。

裁决（wt537 读码后小裁决，详见台账 257 行）：
- 裁决 A 清洗面 = 伪造行为统计四表（UserStreakStats / 6 条 catalog 成就 /
  13 条 catalog FocusSession / demo 节点 UserNodeStatus 掌握行）。演示内容面
  （计划/任务/胶囊/日历/聊天等）按 J-01 ``source="example"`` 标记与 GJ02
  demo→own 升级路径的既有裁决保留，不在本修范围。
- 裁决 B 转正事务内原子清洗：auth 端点 get_db 成功路径统一 commit，
  清洗以 SAVEPOINT 隔离 best-effort（与 seed_guest_user_data 同型），
  失败降级告警不阻塞转正；无后置任务窗口。
- 裁决 C 演示好友（spark_friend_*）是跨访客共享的全局 catalog
  （_ensure_demo_user 复用同一批行），删除会破坏其他在途访客的演示体验；
  其生产面由 'seed' 词表永久排除——保持 FIX-01/08/20 现口径，不随转正删除。
"""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.achievement import UserAchievement, UserStreakStats
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.schemas.leaderboard import LeaderboardRequest, LeaderboardType
from app.services.guest_seed_service import seed_guest_user_data

# 种子 catalog 伪造专注分钟（13 行精确总和；台账行「≈540 分钟」的精确值）
SEED_FOCUS_MINUTES = 515
SEED_FOCUS_ROWS = 13


async def _seeded_guest(db_session) -> User:
    """种满 demo 数据的访客（与 test_guest_seed_example_marker 同构）。"""
    user = User(
        username="guest_upgrade_clean",
        email="guest_upgrade_clean@test.local",
        hashed_password="hashed",
        registration_source="guest",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await seed_guest_user_data(db_session, user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _my_global_entry(db_session, user: User):
    """全局榜中「我」的条目（cohort 排除后缺席即 None）。"""
    from app.services.leaderboard_service import LeaderboardService

    response = await LeaderboardService(db_session)._get_global_leaderboard(
        LeaderboardRequest(type=LeaderboardType.GLOBAL, limit=100), user.id
    )
    return next((e for e in response.entries if e.user_id == user.id), None)


async def _focus_minutes(db_session, user_id) -> int:
    rows = (await db_session.execute(select(FocusSession).where(FocusSession.user_id == user_id))).scalars().all()
    return sum(row.duration_minutes for row in rows)


# ── 红测①：转正前 guest cohort 排除生效（FIX-01 防回归锚点）──


@pytest.mark.asyncio
async def test_seeded_guest_is_excluded_from_global_board_before_upgrade(db_session):
    user = await _seeded_guest(db_session)
    entry = await _my_global_entry(db_session, user)
    assert entry is None, "转正前 guest 必须被 FIX-01 cohort 词表挡在全局榜外"


# ── 红测②：原位翻转 registration_source 后伪造统计污染生产面（缺陷实录）──


@pytest.mark.asyncio
async def test_registration_source_flip_admits_seed_statistics_into_global_board(db_session):
    """upgrade_guest 原位翻转（auth.py:1077）后，种子字段四因子全部进榜。"""
    user = await _seeded_guest(db_session)

    # 模拟 upgrade_guest 的原位翻转（修前无清洗）
    user.registration_source = "email"
    await db_session.commit()

    entry = await _my_global_entry(db_session, user)
    assert entry is not None, "转正后用户进入生产 cohort（全局榜可见）——缺陷现场"
    stats = entry.stats
    assert stats["study_days"] == 45, "打卡天数因子 = 种子 total_checkin_days=45"
    assert stats["streak"] == 30, "最长连胜因子 = 种子 longest_streak=30"
    assert stats["achievements"] == 6, "成就数因子 = 种子 6 条 UserAchievement"
    assert stats["knowledge_nodes"] >= 40, "知识点数因子 = 种子 demo 节点掌握行（mastery≥50）"
    assert entry.score > 0
    # 伪造专注分钟同样在库（telemetry/adaptive_replanner 消费面）
    assert await _focus_minutes(db_session, user.id) == SEED_FOCUS_MINUTES


# ── 修后绿：转正清洗清零种子伪造统计 ──


@pytest.mark.asyncio
async def test_upgrade_cleanup_removes_seed_catalog_statistics(db_session):
    from app.services.guest_seed_service import cleanup_guest_seed_statistics_for_upgrade

    user = await _seeded_guest(db_session)
    user.registration_source = "email"
    await db_session.commit()

    removed = await cleanup_guest_seed_statistics_for_upgrade(db_session, user)
    await db_session.commit()

    assert removed["streak_stats"] == 1
    assert removed["achievements"] == 6
    assert removed["focus_sessions"] == SEED_FOCUS_ROWS
    assert removed["node_status"] >= 40
    assert removed["total"] > 50

    entry = await _my_global_entry(db_session, user)
    assert entry is not None
    assert entry.stats == {
        "knowledge_nodes": 0,
        "achievements": 0,
        "streak": 0,
        "study_days": 0,
    }, "转正清洗后全局榜四因子必须清零（伪造统计不再进生产 cohort）"
    assert await _focus_minutes(db_session, user.id) == 0
    assert (await db_session.scalar(select(UserStreakStats).where(UserStreakStats.user_id == user.id))) is None


@pytest.mark.asyncio
async def test_upgrade_cleanup_is_idempotent(db_session):
    from app.services.guest_seed_service import cleanup_guest_seed_statistics_for_upgrade

    user = await _seeded_guest(db_session)
    user.registration_source = "email"
    await db_session.commit()

    first = await cleanup_guest_seed_statistics_for_upgrade(db_session, user)
    await db_session.commit()
    second = await cleanup_guest_seed_statistics_for_upgrade(db_session, user)
    await db_session.commit()

    assert first["total"] > 0
    assert second == {"streak_stats": 0, "achievements": 0, "focus_sessions": 0, "node_status": 0, "total": 0}


# ── 守卫：用户自建真实数据绝不误删 ──


@pytest.mark.asyncio
async def test_upgrade_cleanup_preserves_user_created_real_data(db_session):
    """真实学习记录三重守卫：晚于种子窗口的自建专注、被真实行为改写的
    streak/节点掌握、非 catalog 成就与任务——清洗后全部保留。"""
    from app.services.guest_seed_service import cleanup_guest_seed_statistics_for_upgrade

    user = await _seeded_guest(db_session)
    real_time = user.created_at + timedelta(hours=2)

    # 自建任务（非 catalog 标题）
    real_task = Task(
        user_id=user.id,
        title="我的真实自建任务",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
    )
    db_session.add(real_task)
    await db_session.flush()
    real_task.created_at = real_time

    # 自建专注会话：catalog 签名相同（25 分钟番茄/完成/白噪音 1、挂在种子任务上）
    # 但写入晚于种子窗口——必须保留（时间窗是防误删的第二道闸）
    seeded_primary_task = (
        await db_session.execute(select(Task).where(Task.user_id == user.id, Task.title == "数据结构 - 二叉树遍历算法"))
    ).scalar_one()
    real_focus = FocusSession(
        user_id=user.id,
        task_id=seeded_primary_task.id,
        start_time=real_time,
        end_time=real_time + timedelta(minutes=25),
        duration_minutes=25,
        focus_type=FocusType.POMODORO,
        status=FocusStatus.COMPLETED,
        white_noise_type=1,
    )
    db_session.add(real_focus)
    await db_session.flush()
    real_focus.created_at = real_time

    # 真实解锁覆盖了种子 streak_7（生产单行 PK：真实达成会原位更新该行，
    # 解锁时间移到真实时刻——时间窗闸必须保守保留）
    real_achievement = (
        await db_session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id,
                UserAchievement.achievement_id == "streak_7",
            )
        )
    ).scalar_one()
    real_achievement.unlocked_at = real_time
    real_achievement.last_progress_update = real_time

    # 真实打卡改写了 streak 行（指纹破坏：current 8 / days 46）
    streak = (await db_session.execute(select(UserStreakStats).where(UserStreakStats.user_id == user.id))).scalar_one()
    streak.current_streak = 8
    streak.total_checkin_days = 46
    streak.last_activity_date = real_time

    # 真实学习改写了 demo 节点掌握（高等数学 85→88）
    node_id = (
        await db_session.execute(
            select(UserNodeStatus.node_id)
            .join(KnowledgeNode, KnowledgeNode.id == UserNodeStatus.node_id)
            .where(UserNodeStatus.user_id == user.id, KnowledgeNode.name == "高等数学")
        )
    ).scalar_one()
    mastered_node = (
        await db_session.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user.id, UserNodeStatus.node_id == node_id)
        )
    ).scalar_one()
    mastered_node.mastery_score = 88
    mastered_node.study_count = 13
    mastered_node.total_study_minutes = 195
    mastered_node.last_study_at = real_time
    await db_session.commit()

    removed = await cleanup_guest_seed_statistics_for_upgrade(db_session, user)
    await db_session.commit()

    # 种子行照常清洗
    assert removed["achievements"] == 5, "6 条种子成就中 streak_7 已被真实解锁改写，只清 5 条"
    assert removed["streak_stats"] == 0, "streak 行被真实打卡改写，必须保守保留"
    assert removed["focus_sessions"] == SEED_FOCUS_ROWS, "13 条种子专注清除；真实 1 条不在 catalog 窗口"
    assert removed["node_status"] >= 40

    # 守卫断言：真实数据全保留
    assert (await db_session.scalar(select(Task.id).where(Task.id == real_task.id))) is not None
    kept_focus = (await db_session.execute(select(FocusSession).where(FocusSession.user_id == user.id))).scalars().all()
    assert [row.id for row in kept_focus] == [real_focus.id]
    assert await _focus_minutes(db_session, user.id) == 25
    assert (
        await db_session.scalar(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id,
                UserAchievement.achievement_id == "streak_7",
            )
        )
    ) is not None, "真实解锁的 streak_7 必须保留"
    kept_streak = (
        await db_session.execute(select(UserStreakStats).where(UserStreakStats.user_id == user.id))
    ).scalar_one()
    assert kept_streak.current_streak == 8 and kept_streak.total_checkin_days == 46
    kept_node = (
        await db_session.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user.id, UserNodeStatus.node_id == node_id)
        )
    ).scalar_one()
    assert kept_node.mastery_score == 88 and kept_node.study_count == 13


# ── 裁决 C：演示好友（全局共享 catalog）不随转正删除 ──


@pytest.mark.asyncio
async def test_upgrade_cleanup_keeps_shared_demo_friends(db_session):
    from app.services.guest_seed_service import cleanup_guest_seed_statistics_for_upgrade

    user = await _seeded_guest(db_session)
    user.registration_source = "email"
    await db_session.commit()

    await cleanup_guest_seed_statistics_for_upgrade(db_session, user)
    await db_session.commit()

    aze = (await db_session.execute(select(User).where(User.username == "spark_friend_1"))).scalar_one()
    assert aze.registration_source == "seed", "演示好友保持 seed cohort（FIX-01/08/20 词表永久排除）"
    aze_achievements = (
        (await db_session.execute(select(UserAchievement).where(UserAchievement.user_id == aze.id))).scalars().all()
    )
    assert len(aze_achievements) == 2, "阿泽的学习档案（2 成就）不随主用户转正被清洗"
