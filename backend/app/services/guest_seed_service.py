"""
Guest Seed Service
Automatically seeds demo data for new guest users so they experience
the full app with realistic pre-populated content.
"""
from datetime import date, datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models import (
    Achievement,
    AchievementRarity,
    AchievementType,
    CapsuleFeedback,
    CapsuleFavorite,
    CapsuleGenerationJob,
    CuriosityCapsule,
    DepthLevel,
    Friendship,
    FriendshipStatus,
    GalaxySkin,
    GenerationType,
    Group,
    GroupMember,
    GroupMessage,
    GroupRole,
    GroupType,
    MessageRole,
    MessageType,
    Plan,
    PlanType,
    Post,
    Task,
    TaskStatus,
    TaskType,
    User,
    UserAchievement,
    UserGalaxySkin,
    UserStreakStats,
    UserTitle,
    ChatMessage,
    ChatSession,
)


async def _ensure_achievements(session: AsyncSession):
    now = datetime.utcnow()
    items = [
        dict(
            id="streak_7",
            name="一周坚持",
            description="连续学习7天",
            icon_url="/icons/streak_7.png",
            type=AchievementType.STREAK,
            rarity=AchievementRarity.COMMON,
            trigger_code="STREAK_DAYS_7",
            trigger_config={"days": 7},
            category="streak",
        ),
        dict(
            id="streak_30",
            name="月度冠军",
            description="连续学习30天",
            icon_url="/icons/streak_30.png",
            type=AchievementType.STREAK,
            rarity=AchievementRarity.RARE,
            trigger_code="STREAK_DAYS_30",
            trigger_config={"days": 30},
            category="streak",
        ),
        dict(
            id="nodes_100",
            name="星图探索者",
            description="解锁100个知识点",
            icon_url="/icons/nodes_100.png",
            type=AchievementType.NODE_EXPLORE,
            rarity=AchievementRarity.RARE,
            trigger_code="NODES_UNLOCKED_100",
            trigger_config={"count": 100},
            category="exploration",
        ),
        dict(
            id="study_100h",
            name="百小时学者",
            description="累计学习100小时",
            icon_url="/icons/study_100h.png",
            type=AchievementType.STUDY_TIME,
            rarity=AchievementRarity.EPIC,
            trigger_code="STUDY_HOURS_100",
            trigger_config={"hours": 100},
            category="study_time",
        ),
        dict(
            id="sprint_master",
            name="冲刺达人",
            description="完成一次冲刺计划",
            icon_url="/icons/sprint_master.png",
            type=AchievementType.SPRINT,
            rarity=AchievementRarity.RARE,
            trigger_code="SPRINT_COMPLETE_1",
            trigger_config={"count": 1},
            category="sprint",
        ),
        dict(
            id="hidden_night",
            name="夜猫学霸",
            description="在凌晨2点后仍在学习（隐藏成就）",
            icon_url="/icons/hidden_night.png",
            type=AchievementType.HIDDEN,
            rarity=AchievementRarity.LEGENDARY,
            trigger_code="NIGHT_OWL",
            trigger_config={"hour": 2},
            category="hidden",
            is_hidden=True,
            hint="深夜灵感突然爆发…",
        ),
    ]
    for item in items:
        existing = await session.execute(
            select(Achievement).where(Achievement.id == item["id"])
        )
        if existing.scalar_one_or_none():
            continue
        session.add(Achievement(**item, created_at=now, updated_at=now))


async def _ensure_galaxy_skins(session: AsyncSession):
    now = datetime.utcnow()
    skins = [
        dict(
            id="skin_nebula",
            name="星云幻彩",
            description="轻量星云渐变皮肤",
            preview_url="/skins/nebula.png",
            unlock_type="achievement",
            unlock_requirement={"achievement_id": "streak_7"},
            rarity=AchievementRarity.RARE,
            sort_order=1,
        ),
        dict(
            id="skin_solar",
            name="日耀核心",
            description="高亮太阳核心皮肤",
            preview_url="/skins/solar.png",
            unlock_type="achievement",
            unlock_requirement={"achievement_id": "study_100h"},
            rarity=AchievementRarity.EPIC,
            sort_order=2,
        ),
    ]
    for item in skins:
        existing = await session.execute(
            select(GalaxySkin).where(GalaxySkin.id == item["id"])
        )
        if existing.scalar_one_or_none():
            continue
        session.add(GalaxySkin(**item, created_at=now, updated_at=now))


async def seed_guest_user_data(session: AsyncSession, user: User) -> None:
    """
    Seed demo data for a new guest user.
    Idempotent — safe to call multiple times (checks before inserting).
    """
    now = datetime.utcnow()

    # Update guest profile to look like an active learner
    user.nickname = f"访客体验{user.username[-4:]}"
    user.flame_level = 15
    user.flame_brightness = 0.85
    user.depth_preference = 0.7
    user.curiosity_preference = 0.8
    user.avatar_url = f"https://api.dicebear.com/9.x/avataaars/png?seed={user.username}"

    # Achievements
    await _ensure_achievements(session)
    await session.flush()

    def _make_user_achievement(achievement_id: str, progress: float, value: int, target: int, unlocked: bool):
        return UserAchievement(
            user_id=user.id,
            achievement_id=achievement_id,
            progress=progress,
            progress_value=value,
            progress_target=target,
            unlocked_at=now - timedelta(days=1) if unlocked else None,
            is_pinned=unlocked,
            last_progress_update=now,
        )

    for ua in [
        _make_user_achievement("streak_7", 1.0, 7, 7, True),
        _make_user_achievement("streak_30", 0.23, 7, 30, False),
        _make_user_achievement("nodes_100", 0.45, 45, 100, False),
        _make_user_achievement("study_100h", 0.62, 62, 100, False),
        _make_user_achievement("sprint_master", 1.0, 1, 1, True),
        _make_user_achievement("hidden_night", 1.0, 1, 1, True),
    ]:
        exists = await session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id,
                UserAchievement.achievement_id == ua.achievement_id,
            )
        )
        if not exists.scalar_one_or_none():
            session.add(ua)

    # Streak stats
    streak_exists = await session.execute(
        select(UserStreakStats).where(UserStreakStats.user_id == user.id)
    )
    if not streak_exists.scalar_one_or_none():
        session.add(
            UserStreakStats(
                user_id=user.id,
                current_streak=7,
                max_streak=30,
                longest_streak=30,
                total_checkin_days=45,
                last_activity_date=now - timedelta(hours=2),
                longest_streak_start=now - timedelta(days=30),
                longest_streak_end=now - timedelta(days=1),
                freeze_charges=2,
                max_freeze_charges=3,
            )
        )

    # Galaxy skins
    await _ensure_galaxy_skins(session)
    await session.flush()

    skin = (await session.execute(select(GalaxySkin).where(GalaxySkin.id == "skin_nebula"))).scalar_one_or_none()
    if skin:
        skin_exists = await session.execute(
            select(UserGalaxySkin).where(
                UserGalaxySkin.user_id == user.id,
                UserGalaxySkin.skin_id == skin.id,
            )
        )
        if not skin_exists.scalar_one_or_none():
            session.add(
                UserGalaxySkin(
                    user_id=user.id,
                    skin_id=skin.id,
                    unlocked_at=now - timedelta(days=5),
                    unlock_source="achievement",
                    is_equipped=True,
                )
            )

    # Title
    title_exists = await session.execute(
        select(UserTitle).where(UserTitle.user_id == user.id, UserTitle.title_id == "title_sprinter")
    )
    if not title_exists.scalar_one_or_none():
        session.add(
            UserTitle(
                user_id=user.id,
                title_id="title_sprinter",
                title_name="冲刺高手",
                title_display="🏃 冲刺高手",
                source_achievement_id="sprint_master",
                is_equipped=True,
                unlocked_at=now - timedelta(days=2),
            )
        )

    # Plans
    sprint_plan = (await session.execute(
        select(Plan).where(Plan.user_id == user.id, Plan.name == "数据结构期中冲刺")
    )).scalar_one_or_none()
    if not sprint_plan:
        sprint_plan = Plan(
            user_id=user.id,
            name="数据结构期中冲刺",
            type=PlanType.SPRINT,
            description="集中攻克链表、栈、队列和二叉树，准备期中考试。",
            target_date=date.today() + timedelta(days=7),
            daily_available_minutes=120,
            total_estimated_hours=20,
            mastery_level=0.6,
            progress=0.7,
            is_active=True,
            is_primary=True,
        )
        session.add(sprint_plan)
        await session.flush()

    growth_plan = (await session.execute(
        select(Plan).where(Plan.user_id == user.id, Plan.name == "计算机科学基础巩固")
    )).scalar_one_or_none()
    if not growth_plan:
        growth_plan = Plan(
            user_id=user.id,
            name="计算机科学基础巩固",
            type=PlanType.GROWTH,
            description="系统性复习CS基础四大件，构建完整的知识体系。",
            target_date=date.today() + timedelta(days=90),
            daily_available_minutes=60,
            total_estimated_hours=100,
            mastery_level=0.3,
            progress=0.45,
            is_active=True,
        )
        session.add(growth_plan)
        await session.flush()

    # Tasks
    for task_data in [
        dict(
            title="数据结构 - 二叉树遍历算法",
            type=TaskType.LEARNING,
            tags=["CS", "Data Structures", "Tree"],
            estimated_minutes=90,
            difficulty=4,
            energy_cost=4,
            status=TaskStatus.IN_PROGRESS,
            priority=3,
            due_date=date.today(),
            started_at=now - timedelta(minutes=30),
            plan_id=sprint_plan.id,
        ),
        dict(
            title="操作系统 - 死锁处理机制",
            type=TaskType.LEARNING,
            tags=["OS", "Concurrency"],
            estimated_minutes=75,
            difficulty=4,
            energy_cost=3,
            status=TaskStatus.PENDING,
            priority=3,
            due_date=date.today(),
            plan_id=sprint_plan.id,
        ),
        dict(
            title="离散数学 - 图论着色问题",
            type=TaskType.LEARNING,
            tags=["Math", "Graph Theory"],
            estimated_minutes=120,
            difficulty=4,
            energy_cost=4,
            status=TaskStatus.PENDING,
            priority=3,
            due_date=date.today() + timedelta(days=2),
            plan_id=growth_plan.id,
        ),
        dict(
            title="计算机网络 - TCP协议分析",
            type=TaskType.LEARNING,
            tags=["Network", "Protocol"],
            estimated_minutes=90,
            difficulty=3,
            energy_cost=3,
            status=TaskStatus.PENDING,
            priority=2,
            due_date=date.today() + timedelta(days=3),
            plan_id=growth_plan.id,
        ),
    ]:
        exists = await session.execute(
            select(Task).where(Task.user_id == user.id, Task.title == task_data["title"])
        )
        if not exists.scalar_one_or_none():
            session.add(Task(user_id=user.id, **task_data))

    # Curiosity Capsules
    capsule_ids = []
    for capsule_data in [
        dict(
            title="为什么二叉树的遍历有三种方式？",
            content="二叉树的三种遍历方式（前序、中序、后序）源于访问节点的不同时机。前序先访问根，适合复制树结构；中序产生有序序列，适合BST；后序最后访问根，适合释放资源。",
            related_subject="数据结构",
            depth_level=DepthLevel.DEEP,
            generation_method="knowledge_gap_analysis",
            quality_score=0.92,
            feedback_count=0,
            share_count=0,
            is_read=False,
        ),
        dict(
            title="进程和线程的本质区别是什么？",
            content="进程=资源容器+执行轨迹；线程=共享资源+独立执行轨迹。进程是OS资源分配单位，线程是CPU调度单位。同一进程内线程共享内存空间，这是并发编程中数据竞争问题的根源。",
            related_subject="操作系统",
            depth_level=DepthLevel.DEEP,
            generation_method="concept_clarification",
            quality_score=0.88,
            feedback_count=1,
            share_count=2,
            is_read=True,
        ),
        dict(
            title="TCP为什么需要三次握手？",
            content="三次握手用于同步序列号并确认双方收发能力。一次握手无法确认服务器发送能力；两次握手会导致历史连接复用问题。三次是双方确认各自收发正常的最少次数。",
            related_subject="计算机网络",
            depth_level=DepthLevel.MEDIUM,
            generation_method="why_question",
            quality_score=0.85,
            feedback_count=0,
            share_count=1,
            is_read=True,
        ),
    ]:
        exists = await session.execute(
            select(CuriosityCapsule).where(
                CuriosityCapsule.user_id == user.id,
                CuriosityCapsule.title == capsule_data["title"],
            )
        )
        capsule = exists.scalar_one_or_none()
        if capsule:
            capsule_ids.append(capsule.id)
        else:
            capsule = CuriosityCapsule(user_id=user.id, **capsule_data)
            session.add(capsule)
            await session.flush()
            capsule_ids.append(capsule.id)

    if len(capsule_ids) >= 2:
        fav_exists = await session.execute(
            select(CapsuleFavorite).where(
                CapsuleFavorite.user_id == user.id,
                CapsuleFavorite.capsule_id == capsule_ids[1],
            )
        )
        if not fav_exists.scalar_one_or_none():
            session.add(CapsuleFavorite(user_id=user.id, capsule_id=capsule_ids[1]))

        feedback_exists = await session.execute(
            select(CapsuleFeedback).where(
                CapsuleFeedback.user_id == user.id,
                CapsuleFeedback.capsule_id == capsule_ids[1],
            )
        )
        if not feedback_exists.scalar_one_or_none():
            session.add(
                CapsuleFeedback(
                    user_id=user.id,
                    capsule_id=capsule_ids[1],
                    rating=5,
                    helpful=True,
                    category="just_right",
                    comment="内容很实用",
                )
            )

        job_exists = await session.execute(
            select(CapsuleGenerationJob).where(CapsuleGenerationJob.user_id == user.id)
        )
        if not job_exists.scalar_one_or_none():
            session.add(
                CapsuleGenerationJob(
                    user_id=user.id,
                    status="completed",
                    generation_type=GenerationType.DAILY.value,
                    depth_preference=0.7,
                    curiosity_preference=0.6,
                    requested_count=3,
                    actual_count=3,
                    capsule_ids=capsule_ids,
                    progress=1.0,
                    duration_ms=4200,
                    completed_at=now - timedelta(hours=2),
                )
            )

    # Community: seed friend accounts + friendships
    friend_specs = [
        ("spark_friend_1", "friend1@sparkle.demo", "阿泽"),
        ("spark_friend_2", "friend2@sparkle.demo", "小林"),
        ("spark_friend_3", "friend3@sparkle.demo", "Nora"),
    ]
    friends = []
    for username, email, nickname in friend_specs:
        result = await session.execute(select(User).where(User.username == username))
        friend = result.scalar_one_or_none()
        if not friend:
            friend = User(
                username=username,
                email=email,
                hashed_password=get_password_hash("DemoFriend123"),
                nickname=nickname,
                avatar_url=f"https://api.dicebear.com/9.x/avataaars/png?seed={username}",
                flame_level=8,
                flame_brightness=0.6,
                depth_preference=0.55,
                curiosity_preference=0.55,
                registration_source="seed",
                is_active=True,
            )
            session.add(friend)
            await session.flush()
        friends.append(friend)

        uid_small, uid_large = sorted([user.id, friend.id])
        friendship_exists = await session.execute(
            select(Friendship).where(
                Friendship.user_id == uid_small,
                Friendship.friend_id == uid_large,
            )
        )
        if not friendship_exists.scalar_one_or_none():
            session.add(
                Friendship(
                    user_id=uid_small,
                    friend_id=uid_large,
                    status=FriendshipStatus.ACCEPTED,
                    initiated_by=user.id,
                    match_reason={"courses": ["数据结构", "操作系统"]},
                )
            )

    # Community feed posts
    for content in [
        "连续一周打卡成功！今天的专注时间达到了 120 分钟。",
        "分享一个高效学习番茄钟设置方法，欢迎交流。",
    ]:
        post_exists = await session.execute(
            select(Post).where(Post.user_id == user.id, Post.content == content)
        )
        if not post_exists.scalar_one_or_none():
            session.add(
                Post(
                    user_id=user.id,
                    content=content,
                    image_urls=["https://picsum.photos/seed/sparkle/600/400"],
                    topic="学习分享",
                    visibility="public",
                    like_count=12,
                    comment_count=3,
                )
            )

    # Group
    group = (await session.execute(
        select(Group).where(Group.name == "算法冲刺小队")
    )).scalar_one_or_none()
    if not group:
        group = Group(
            name="算法冲刺小队",
            description="一起冲刺算法与数据结构的学习群",
            avatar_url="https://picsum.photos/seed/algosprint/200/200",
            type=GroupType.SPRINT,
            focus_tags=["数据结构", "算法"],
            deadline=now + timedelta(days=10),
            sprint_goal="完成算法专题复习并拿下期中考试",
            max_members=30,
            is_public=True,
            join_requires_approval=False,
        )
        session.add(group)
        await session.flush()

    for idx, member in enumerate([user] + friends[:2]):
        member_exists = await session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group.id,
                GroupMember.user_id == member.id,
            )
        )
        if not member_exists.scalar_one_or_none():
            session.add(
                GroupMember(
                    group_id=group.id,
                    user_id=member.id,
                    role=GroupRole.OWNER if idx == 0 else GroupRole.MEMBER,
                    flame_contribution=120 if idx == 0 else 60,
                    tasks_completed=8 if idx == 0 else 3,
                    checkin_streak=5,
                    last_checkin_date=now - timedelta(days=1),
                )
            )

    msg_exists = await session.execute(
        select(GroupMessage).where(
            GroupMessage.group_id == group.id,
            GroupMessage.content == "今晚 20:00 一起复盘二叉树遍历？",
        )
    )
    if not msg_exists.scalar_one_or_none():
        session.add(
            GroupMessage(
                group_id=group.id,
                sender_id=user.id,
                message_type=MessageType.TEXT,
                content="今晚 20:00 一起复盘二叉树遍历？",
            )
        )

    await session.commit()

    # Chat session + history
    chat_session = (await session.execute(
        select(ChatSession).where(
            ChatSession.user_id == user.id,
            ChatSession.title == "关于数学复习的建议",
        )
    )).scalar_one_or_none()
    if not chat_session:
        chat_session = ChatSession(
            user_id=user.id,
            title="关于数学复习的建议",
            is_active=True,
            last_message_at=now - timedelta(hours=1),
        )
        session.add(chat_session)
        await session.flush()

    msg_count = (await session.execute(
        select(ChatMessage).where(
            ChatMessage.user_id == user.id,
            ChatMessage.session_id == chat_session.id,
        )
    )).scalar_one_or_none()
    if not msg_count:
        session.add_all([
            ChatMessage(
                user_id=user.id,
                session_id=chat_session.id,
                role=MessageRole.USER,
                content="我觉得最近学习效率有点低，总是忍不住想玩手机，怎么办？",
            ),
            ChatMessage(
                user_id=user.id,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content="理解你的感受。这种焦虑和自责其实是恶性循环的一部分。可以从一个小任务开始找回节奏，比如先把二叉树遍历的代码手写一遍，15分钟完成，给自己一个小成就感。",
            ),
            ChatMessage(
                user_id=user.id,
                session_id=chat_session.id,
                role=MessageRole.USER,
                content="确实，那我先复习一下链表吧，但是我有点忘了怎么实现了。",
            ),
        ])
        chat_session.last_message_at = now

    await session.commit()
    logger.info(f"Guest data seeded for user_id={user.id} username={user.username}")
