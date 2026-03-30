import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from random import randint, uniform

from loguru import logger
from sqlalchemy import delete, select, update

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.security import get_password_hash
from app.data.populate_achievements import sync_achievement_definitions
from app.db.session import AsyncSessionLocal
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
    PostLike,
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
from app.models.shop import PhotonTransactionHistory, PhotonTransactionType

DEMO_USERNAME = "chat_test"
DEMO_PASSWORD = "Chat123456"
DEMO_EMAIL = "chat_test@sparkle.demo"
LEGACY_DEMO_ACHIEVEMENT_IDS = {
    "study_100h",
    "sprint_master",
    "hidden_night",
    "task_50",
    "capsule_10",
    "perfect_day",
    "social_butterfly",
}
LEGACY_ACHIEVEMENT_REMAP = {
    "study_100h": "study_100hours",
    "sprint_master": "sprint_first",
    "hidden_night": "night_owl",
}


def random_date(start, end):
    """Generate random datetime between start and end"""
    delta = end - start
    random_seconds = randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


async def _cleanup_legacy_demo_achievements(session, user: User) -> None:
    for legacy_id, canonical_id in LEGACY_ACHIEVEMENT_REMAP.items():
        await session.execute(
            update(UserTitle)
            .where(UserTitle.source_achievement_id == legacy_id)
            .values(source_achievement_id=canonical_id)
        )
    await session.execute(
        delete(UserAchievement).where(
            UserAchievement.achievement_id.in_(LEGACY_DEMO_ACHIEVEMENT_IDS),
        )
    )
    await session.execute(
        delete(Achievement).where(
            Achievement.id.in_(LEGACY_DEMO_ACHIEVEMENT_IDS),
        )
    )

    sprinter_title = await session.execute(
        select(UserTitle).where(
            UserTitle.user_id == user.id,
            UserTitle.title_id == "title_sprinter",
        )
    )
    existing_title = sprinter_title.scalar_one_or_none()
    if existing_title is not None:
        existing_title.source_achievement_id = "sprint_first"


async def _get_or_create_user(session, username: str, email: str, password: str) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        user.email = email
        user.hashed_password = get_password_hash(password)
        user.nickname = "AI_Learner_02"
        user.avatar_url = (
            "https://api.dicebear.com/9.x/avataaars/png?seed=AI_Learner_02"
        )
        user.flame_level = 15
        user.flame_brightness = 0.85
        user.depth_preference = 0.7
        user.curiosity_preference = 0.8
        user.is_active = True
        return user

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        nickname="AI_Learner_02",
        avatar_url="https://api.dicebear.com/9.x/avataaars/png?seed=AI_Learner_02",
        flame_level=15,
        flame_brightness=0.85,
        depth_preference=0.7,
        curiosity_preference=0.8,
        registration_source="email",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _ensure_achievements(session):
    await sync_achievement_definitions(session)


async def _ensure_galaxy_skins(session):
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
            unlock_requirement={"achievement_id": "study_100hours"},
            rarity=AchievementRarity.EPIC,
            sort_order=2,
        ),
        dict(
            id="skin_quantum",
            name="量子纠缠",
            description="量子场主题皮肤",
            preview_url="/skins/quantum.png",
            unlock_type="achievement",
            unlock_requirement={"achievement_id": "night_owl"},
            rarity=AchievementRarity.LEGENDARY,
            sort_order=3,
        ),
    ]
    for item in skins:
        existing = await session.execute(
            select(GalaxySkin).where(GalaxySkin.id == item["id"])
        )
        if existing.scalar_one_or_none():
            continue
        session.add(GalaxySkin(**item, created_at=now, updated_at=now))


async def _seed_historical_tasks(session, user: User, now: datetime):
    """Create historical tasks simulating long-term usage"""
    task_templates = [
        # Completed tasks - past 30 days
        {
            "title": "线性代数 - 矩阵运算练习",
            "type": TaskType.TRAINING,
            "tags": ["Math", "Linear Algebra"],
            "estimated_minutes": 60,
            "difficulty": 2,
            "energy_cost": 2,
            "status": TaskStatus.COMPLETED,
            "priority": 2,
            "days_ago": 3,
            "actual_minutes": 55,
        },
        {
            "title": "Web前端 - React组件开发",
            "type": TaskType.TRAINING,
            "tags": ["Web", "React", "Frontend"],
            "estimated_minutes": 120,
            "difficulty": 3,
            "energy_cost": 2,
            "status": TaskStatus.COMPLETED,
            "priority": 2,
            "days_ago": 5,
            "actual_minutes": 140,
            "user_note": "实现了Todo List组件，学会了useState和useEffect",
        },
        {
            "title": "摄影技巧 - 夜景拍摄实践",
            "type": TaskType.LEARNING,
            "tags": ["Photography", "Hobby"],
            "estimated_minutes": 60,
            "difficulty": 2,
            "energy_cost": 1,
            "status": TaskStatus.COMPLETED,
            "priority": 1,
            "days_ago": 4,
            "actual_minutes": 70,
        },
        {
            "title": "计算机系统 - CPU调度算法模拟",
            "type": TaskType.TRAINING,
            "tags": ["OS", "Scheduling"],
            "estimated_minutes": 90,
            "difficulty": 3,
            "energy_cost": 3,
            "status": TaskStatus.COMPLETED,
            "priority": 2,
            "days_ago": 2,
            "actual_minutes": 85,
        },
        {
            "title": "数据库 - SQL查询优化",
            "type": TaskType.ERROR_FIX,
            "tags": ["Database", "SQL", "Performance"],
            "estimated_minutes": 45,
            "difficulty": 3,
            "energy_cost": 2,
            "status": TaskStatus.COMPLETED,
            "priority": 2,
            "days_ago": 7,
            "actual_minutes": 50,
        },
        {
            "title": "算法 - 动态规划入门",
            "type": TaskType.LEARNING,
            "tags": ["Algorithm", "DP"],
            "estimated_minutes": 90,
            "difficulty": 4,
            "energy_cost": 4,
            "status": TaskStatus.COMPLETED,
            "priority": 3,
            "days_ago": 10,
            "actual_minutes": 95,
        },
        {
            "title": "计算机网络 - HTTP协议详解",
            "type": TaskType.LEARNING,
            "tags": ["Network", "HTTP"],
            "estimated_minutes": 75,
            "difficulty": 3,
            "energy_cost": 3,
            "status": TaskStatus.COMPLETED,
            "priority": 2,
            "days_ago": 12,
            "actual_minutes": 80,
        },
        {
            "title": "操作系统 - 内存管理",
            "type": TaskType.LEARNING,
            "tags": ["OS", "Memory"],
            "estimated_minutes": 100,
            "difficulty": 4,
            "energy_cost": 4,
            "status": TaskStatus.COMPLETED,
            "priority": 3,
            "days_ago": 15,
            "actual_minutes": 110,
        },
        # Abandoned tasks
        {
            "title": "汇编语言基础",
            "type": TaskType.LEARNING,
            "tags": ["Assembly", "Low-level"],
            "estimated_minutes": 120,
            "difficulty": 4,
            "energy_cost": 4,
            "status": TaskStatus.ABANDONED,
            "priority": 1,
            "days_ago": 20,
        },
        {
            "title": "编译原理实践",
            "type": TaskType.PLANNING,
            "tags": ["Compiler", "Theory"],
            "estimated_minutes": 200,
            "difficulty": 5,
            "energy_cost": 5,
            "status": TaskStatus.ABANDONED,
            "priority": 2,
            "days_ago": 25,
        },
        # In progress tasks
        {
            "title": "数据结构 - 二叉树遍历算法",
            "type": TaskType.LEARNING,
            "tags": ["CS", "Data Structures", "Tree"],
            "estimated_minutes": 90,
            "difficulty": 4,
            "energy_cost": 4,
            "status": TaskStatus.IN_PROGRESS,
            "priority": 3,
            "started_minutes_ago": 30,
        },
        {
            "title": "操作系统 - 死锁处理机制",
            "type": TaskType.LEARNING,
            "tags": ["OS", "Concurrency"],
            "estimated_minutes": 75,
            "difficulty": 4,
            "energy_cost": 3,
            "status": TaskStatus.PENDING,
            "priority": 3,
        },
        {
            "title": "离散数学 - 图论着色问题",
            "type": TaskType.LEARNING,
            "tags": ["Math", "Graph Theory"],
            "estimated_minutes": 120,
            "difficulty": 4,
            "energy_cost": 4,
            "status": TaskStatus.PENDING,
            "priority": 3,
            "days_offset": 2,
        },
        {
            "title": "计算机网络 - TCP协议分析",
            "type": TaskType.LEARNING,
            "tags": ["Network", "Protocol"],
            "estimated_minutes": 90,
            "difficulty": 3,
            "energy_cost": 3,
            "status": TaskStatus.PENDING,
            "priority": 2,
            "days_offset": 3,
        },
        {
            "title": "英语口语 - TED演讲学习",
            "type": TaskType.LEARNING,
            "tags": ["English", "Speaking"],
            "estimated_minutes": 45,
            "difficulty": 2,
            "energy_cost": 1,
            "status": TaskStatus.PENDING,
            "priority": 1,
            "days_offset": 6,
        },
        {
            "title": "《深度工作》阅读与反思",
            "type": TaskType.REFLECTION,
            "tags": ["Reading", "Self-improvement"],
            "estimated_minutes": 90,
            "difficulty": 2,
            "energy_cost": 2,
            "status": TaskStatus.PENDING,
            "priority": 1,
            "days_offset": 14,
        },
    ]

    for template in task_templates:
        exists = await session.execute(
            select(Task).where(Task.user_id == user.id, Task.title == template["title"])
        )
        if exists.scalar_one_or_none():
            continue

        task_data = {
            "user_id": user.id,
            "title": template["title"],
            "type": template["type"],
            "tags": template["tags"],
            "estimated_minutes": template["estimated_minutes"],
            "difficulty": template["difficulty"],
            "energy_cost": template["energy_cost"],
            "status": template["status"],
            "priority": template["priority"],
        }

        # Handle dates based on task status
        if template["status"] == TaskStatus.COMPLETED:
            days_ago = template.get("days_ago", 1)
            completed_at = now - timedelta(days=days_ago)
            task_data.update({
                "due_date": (completed_at + timedelta(hours=randint(1, 24))).date(),
                "completed_at": completed_at,
                "actual_minutes": template.get("actual_minutes", template["estimated_minutes"]),
                "created_at": completed_at - timedelta(days=randint(1, 5)),
                "user_note": template.get("user_note"),
            })
        elif template["status"] == TaskStatus.ABANDONED:
            days_ago = template.get("days_ago", 1)
            abandoned_at = now - timedelta(days=days_ago)
            task_data.update({
                "due_date": abandoned_at.date(),
                "created_at": abandoned_at - timedelta(days=randint(1, 3)),
            })
        elif template["status"] == TaskStatus.IN_PROGRESS:
            started_minutes_ago = template.get("started_minutes_ago", 60)
            started_at = now - timedelta(minutes=started_minutes_ago)
            task_data.update({
                "due_date": now.date(),
                "started_at": started_at,
                "created_at": started_at - timedelta(hours=randint(1, 6)),
            })
        else:  # PENDING
            days_offset = template.get("days_offset", 0)
            due_date = now + timedelta(days=days_offset)
            task_data.update({
                "due_date": due_date.date(),
                "created_at": now - timedelta(days=randint(1, 7)),
            })

        session.add(Task(**task_data))


async def _seed_multiple_chat_sessions(session, user: User, now: datetime):
    """Create multiple chat sessions simulating different topics"""
    chat_specs = [
        {
            "title": "关于数学复习的建议",
            "is_active": True,
            "messages": [
                ("USER", "我觉得最近学习效率有点低，总是忍不住想玩手机，怎么办？"),
                ("ASSISTANT", "理解你的感受。这种焦虑和自责其实是恶性循环的一部分。可以从一个小任务开始找回节奏。"),
                ("USER", "确实，那我先复习一下链表吧，但是我有点忘了怎么实现了。"),
                ("ASSISTANT", "链表的核心是节点结构。每个节点包含数据域和指针域。我们可以先从单向链表开始，实现基本的增删改查操作。"),
                ("USER", "好的，那我先写一个简单的链表节点类"),
            ],
            "days_ago": 0,
        },
        {
            "title": "二叉树遍历算法讨论",
            "is_active": True,
            "messages": [
                ("USER", "二叉树的前序、中序、后序遍历有什么区别？"),
                ("ASSISTANT", "主要区别在于访问根节点的时机。前序是根-左-右，中序是左-根-右，后序是左-右-根"),
                ("USER", "那递归实现的时候要注意什么？"),
                ("ASSISTANT", "关键是确定好基准情况（空节点）和递归情况（分别处理左右子树）"),
            ],
            "days_ago": 1,
        },
        {
            "title": "操作系统死锁问题",
            "is_active": False,
            "messages": [
                ("USER", "死锁的四个必要条件是什么？"),
                ("ASSISTANT", "互斥、占有并等待、非抢占、循环等待"),
                ("USER", "怎么预防死锁呢？"),
                ("ASSISTANT", "可以破坏其中任意一个条件。常用的方法是资源有序分配，破坏循环等待条件"),
            ],
            "days_ago": 3,
        },
        {
            "title": "职业规划咨询",
            "is_active": False,
            "messages": [
                ("USER", "我想以后做前端开发，应该怎么规划学习路径？"),
                ("ASSISTANT", "前端开发的学习路径可以分为：HTML/CSS基础 → JavaScript核心 → 框架学习（React/Vue）→ 工程化（Webpack等）→ 性能优化"),
                ("USER", "大概需要多长时间？"),
                ("ASSISTANT", "如果每天学习2-3小时，基础部分1-2个月，框架部分2-3个月，然后通过项目实践巩固"),
            ],
            "days_ago": 7,
        },
        {
            "title": "TCP协议理解",
            "is_active": False,
            "messages": [
                ("USER", "TCP三次握手的具体过程是什么？"),
                ("ASSISTANT", "第一次：客户端发送SYN包；第二次：服务器回复SYN+ACK；第三次：客户端发送ACK确认"),
                ("USER", "为什么需要三次而不是两次？"),
                ("ASSISTANT", "主要是为了确认双方的收发能力都正常，并同步初始序列号"),
            ],
            "days_ago": 14,
        },
    ]

    for spec in chat_specs:
        session_result = await session.execute(
            select(ChatSession).where(
                ChatSession.user_id == user.id,
                ChatSession.title == spec["title"],
            )
        )
        chat_session = session_result.scalar_one_or_none()
        if chat_session:
            continue

        days_ago = spec["days_ago"]
        last_msg_time = now - timedelta(days=days_ago, hours=randint(1, 12))

        chat_session = ChatSession(
            user_id=user.id,
            title=spec["title"],
            is_active=spec["is_active"],
            last_message_at=last_msg_time,
            created_at=last_msg_time - timedelta(minutes=30),
        )
        session.add(chat_session)
        await session.flush()

        # Add messages
        for i, msg_spec in enumerate(spec["messages"]):
            msg_time = last_msg_time - timedelta(minutes=len(spec["messages"]) - i)
            session.add(
                ChatMessage(
                    user_id=user.id,
                    session_id=chat_session.id,
                    role=MessageRole[msg_spec[0]],
                    content=msg_spec[1],
                    created_at=msg_time,
                )
            )


async def _seed_extended_capsules(session, user: User, now: datetime):
    """Create more curiosity capsules with variety"""
    capsules = [
        {
            "title": "为什么二叉树的遍历有三种方式？",
            "content": "二叉树的三种遍历方式（前序、中序、后序）源于访问节点的不同时机。前序适合复制树结构，中序用于二叉搜索树得到有序序列，后序用于删除或释放内存。",
            "related_subject": "数据结构",
            "depth_level": DepthLevel.DEEP,
            "generation_method": "knowledge_gap_analysis",
            "quality_score": 0.92,
            "days_ago": 0,
            "is_read": False,
        },
        {
            "title": "进程和线程的本质区别是什么？",
            "content": "进程=资源容器+执行轨迹；线程=共享资源+独立执行轨迹。进程间通信需要特殊机制（IPC），而线程间可以直接共享内存。进程创建开销大，线程开销小。",
            "related_subject": "操作系统",
            "depth_level": DepthLevel.DEEP,
            "generation_method": "concept_clarification",
            "quality_score": 0.88,
            "days_ago": 1,
            "is_read": True,
            "is_favorite": True,
        },
        {
            "title": "TCP为什么需要三次握手？",
            "content": "三次握手用于同步序列号并确认双方收发能力。第一次：客户端告知服务器自己的发送能力；第二次：服务器告知客户端自己的发送和接收能力；第三次：客户端告知服务器自己的接收能力。",
            "related_subject": "计算机网络",
            "depth_level": DepthLevel.MEDIUM,
            "generation_method": "why_question",
            "quality_score": 0.85,
            "days_ago": 2,
            "is_read": True,
        },
        {
            "title": "动态规划的核心思想是什么？",
            "content": "动态规划的核心是'重叠子问题'和'最优子结构'。通过存储子问题的解避免重复计算，用空间换时间。关键是要找到状态转移方程。",
            "related_subject": "算法",
            "depth_level": DepthLevel.MEDIUM,
            "generation_method": "concept_clarification",
            "quality_score": 0.90,
            "days_ago": 5,
            "is_read": True,
            "is_favorite": True,
        },
        {
            "title": "什么是虚拟内存？",
            "content": "虚拟内存是操作系统给每个进程的错觉，让它以为自己独占了所有内存。通过页表实现虚拟地址到物理地址的映射，使得程序可以使用比实际物理内存更大的地址空间。",
            "related_subject": "操作系统",
            "depth_level": DepthLevel.MEDIUM,
            "generation_method": "concept_clarification",
            "quality_score": 0.87,
            "days_ago": 7,
            "is_read": True,
        },
        {
            "title": "快速排序的时间复杂度为什么是O(n log n)？",
            "content": "理想情况下每次partition都将数组分成两个相等的部分，递归深度是log n，每层需要O(n)时间处理，所以是O(n log n)。最坏情况（已排序）会退化到O(n²)。",
            "related_subject": "算法",
            "depth_level": DepthLevel.DEEP,
            "generation_method": "why_question",
            "quality_score": 0.93,
            "days_ago": 10,
            "is_read": True,
            "is_favorite": True,
        },
        {
            "title": "HTTP和HTTPS的主要区别是什么？",
            "content": "HTTPS在HTTP下加入了SSL/TLS层，提供数据加密、身份验证和消息完整性校验。HTTP使用明文传输，HTTPS使用加密传输。默认端口HTTP是80，HTTPS是443。",
            "related_subject": "计算机网络",
            "depth_level": DepthLevel.MEDIUM,
            "generation_method": "comparison",
            "quality_score": 0.86,
            "days_ago": 12,
            "is_read": True,
        },
        {
            "title": "什么是时间局部性和空间局部性？",
            "content": "时间局部性：如果一个数据被访问，那么不久后很可能再次被访问。空间局部性：如果一个数据被访问，那么它附近的数据很可能也被访问。这是缓存系统设计的基础。",
            "related_subject": "计算机系统",
            "depth_level": DepthLevel.DEEP,
            "generation_method": "concept_clarification",
            "quality_score": 0.91,
            "days_ago": 15,
            "is_read": True,
            "is_favorite": True,
        },
        {
            "title": "图的BFS和DFS有什么适用场景？",
            "content": "BFS适合找最短路径（在无权图中）和层级遍历。DFS适合路径搜索、拓扑排序、连通性检测。BFS用队列实现，DFS用栈或递归实现。",
            "related_subject": "数据结构",
            "depth_level": DepthLevel.MEDIUM,
            "generation_method": "comparison",
            "quality_score": 0.89,
            "days_ago": 18,
            "is_read": True,
        },
        {
            "title": "数据库索引为什么使用B+树？",
            "content": "B+树的特点是：1）所有数据都在叶子节点，查询稳定；2）叶子节点通过指针连接，适合范围查询；3）内部节点只存索引，可以存更多key，减少树的高度；4）适合磁盘存储，减少IO次数。",
            "related_subject": "数据库",
            "depth_level": DepthLevel.DEEP,
            "generation_method": "why_question",
            "quality_score": 0.94,
            "days_ago": 20,
            "is_read": True,
            "is_favorite": True,
        },
    ]

    for capsule_spec in capsules:
        exists = await session.execute(
            select(CuriosityCapsule).where(
                CuriosityCapsule.user_id == user.id,
                CuriosityCapsule.title == capsule_spec["title"],
            )
        )
        if exists.scalar_one_or_none():
            continue

        created_at = now - timedelta(days=capsule_spec["days_ago"])
        capsule = CuriosityCapsule(
            user_id=user.id,
            title=capsule_spec["title"],
            content=capsule_spec["content"],
            related_subject=capsule_spec["related_subject"],
            depth_level=capsule_spec["depth_level"],
            generation_method=capsule_spec["generation_method"],
            quality_score=capsule_spec["quality_score"],
            is_read=capsule_spec["is_read"],
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(capsule)
        await session.flush()

        if capsule_spec.get("is_favorite"):
            session.add(
                CapsuleFavorite(
                    user_id=user.id,
                    capsule_id=capsule.id,
                )
            )

        # Add some feedback
        if capsule_spec["days_ago"] > 1 and randint(0, 1) == 1:
            rating = randint(4, 5)
            session.add(
                CapsuleFeedback(
                    user_id=user.id,
                    capsule_id=capsule.id,
                    rating=rating,
                    helpful=True,
                    category="just_right" if rating == 5 else "useful",
                    comment="内容很有帮助" if rating == 5 else "内容不错",
                )
            )


async def _seed_extended_community(session, user: User, friends: list, now: datetime):
    """Create more community posts and interactions"""

    # More posts from demo user
    post_contents = [
        {
            "content": "连续一周打卡成功！今天的专注时间达到了 120 分钟。感觉番茄工作法真的很有用，推荐大家试试🍅",
            "topic": "学习分享",
            "days_ago": 0,
            "likes": 15,
            "comments": 4,
        },
        {
            "content": "分享一个高效学习番茄钟设置方法：25分钟专注+5分钟休息，4个循环后休息15-30分钟。关键是在专注时间内把手机拿远点！",
            "topic": "学习方法",
            "days_ago": 1,
            "likes": 23,
            "comments": 7,
        },
        {
            "content": "今天终于搞懂了快速排序的partition过程！感觉打开了新世界的大门🎉 分享一下我的理解：选一个pivot，比它小的放左边，大的放右边，然后递归处理两边。关键是理解'分治'的思想！",
            "topic": "学习心得",
            "days_ago": 2,
            "likes": 31,
            "comments": 8,
        },
        {
            "content": "数据库事务这块真的太抽象了...有没有大佬能通俗地解释一下ACID？尤其是隔离性的几个级别🤔",
            "topic": "求助",
            "days_ago": 3,
            "likes": 8,
            "comments": 12,
        },
        {
            "content": "今天用Sparkle的认知棱镜发现了自己的学习模式：我在下午3-5点效率最高！以后要把难题放在这个时间段解决✨ 数据驱动真的有用！",
            "topic": "学习心得",
            "days_ago": 5,
            "likes": 42,
            "comments": 6,
        },
        {
            "content": "机器学习入门推荐Andrew Ng的课程！讲得真的很清楚，而且有配套作业。现在已经能自己实现线性回归了🎓",
            "topic": "课程推荐",
            "days_ago": 7,
            "likes": 38,
            "comments": 9,
        },
        {
            "content": "今天在图书馆学习了6个小时，虽然累但很充实！配合番茄工作法，效率真的提升了不少🍅 大家也试试看！",
            "topic": "学习日常",
            "days_ago": 10,
            "likes": 27,
            "comments": 5,
        },
        {
            "content": "终于完成了数据结构的期中项目！实现了一个完整的AVL树，debug了两天😭 但看到测试全过的那一刻，真的太爽了！",
            "topic": "项目分享",
            "days_ago": 12,
            "likes": 56,
            "comments": 14,
        },
    ]

    for post_spec in post_contents:
        existing = await session.execute(
            select(Post).where(
                Post.user_id == user.id,
                Post.content == post_spec["content"],
            )
        )
        if existing.scalar_one_or_none():
            continue

        created_at = now - timedelta(days=post_spec["days_ago"])
        post = Post(
            user_id=user.id,
            content=post_spec["content"],
            image_urls=["https://picsum.photos/seed/sparkle/600/400"] if post_spec["likes"] > 30 else None,
            topic=post_spec["topic"],
            visibility="public",
            like_count=post_spec["likes"],
            comment_count=post_spec["comments"],
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(post)
        await session.flush()

        # Add likes from friends
        for friend in friends[:randint(1, 3)]:
            like_exists = await session.execute(
                select(PostLike).where(
                    PostLike.post_id == post.id,
                    PostLike.user_id == friend.id,
                )
            )
            if not like_exists.scalar_one_or_none():
                session.add(
                    PostLike(
                        post_id=post.id,
                        user_id=friend.id,
                    )
                )

    # Posts from friends
    friend_posts = [
        {
            "friend_idx": 0,
            "content": "今天学习了Java的反射机制，感觉有点难理解。有没有好的学习资源推荐？",
            "topic": "求助",
            "days_ago": 1,
            "likes": 12,
        },
        {
            "friend_idx": 0,
            "content": "Vue3的Composition API真的比Options API好用很多！代码组织更清晰了",
            "topic": "技术分享",
            "days_ago": 4,
            "likes": 28,
        },
        {
            "friend_idx": 1,
            "content": "有没有人一起组队刷LeetCode？感觉一个人刷太容易放弃了...",
            "topic": "组队",
            "days_ago": 2,
            "likes": 19,
        },
        {
            "friend_idx": 1,
            "content": "刚学会了Git的rebase，感觉比merge干净多了！",
            "topic": "工具分享",
            "days_ago": 6,
            "likes": 34,
        },
        {
            "friend_idx": 2,
            "content": "Python的装饰器真的很好用！写了一个计时装饰器，测试函数性能方便多了",
            "topic": "Python",
            "days_ago": 3,
            "likes": 22,
        },
        {
            "friend_idx": 2,
            "content": "今天看书看到一句话：'程序 = 算法 + 数据结构'。突然感觉以前太重视语法，忽略了算法思维",
            "topic": "感悟",
            "days_ago": 8,
            "likes": 45,
        },
    ]

    for post_spec in friend_posts:
        friend = friends[post_spec["friend_idx"]]
        existing = await session.execute(
            select(Post).where(
                Post.user_id == friend.id,
                Post.content == post_spec["content"],
            )
        )
        if existing.scalar_one_or_none():
            continue

        created_at = now - timedelta(days=post_spec["days_ago"])
        post = Post(
            user_id=friend.id,
            content=post_spec["content"],
            topic=post_spec["topic"],
            visibility="public",
            like_count=post_spec["likes"],
            comment_count=randint(2, 8),
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(post)
        await session.flush()

        # Demo user likes some friend posts
        if randint(0, 1) == 1:
            session.add(
                PostLike(
                    post_id=post.id,
                    user_id=user.id,
                )
            )


async def _seed_multiple_groups(session, user: User, friends: list, now: datetime):
    """Create multiple groups with different focus"""

    groups = [
        {
            "name": "算法冲刺小队",
            "description": "一起冲刺算法与数据结构的学习群",
            "type": GroupType.SPRINT,
            "focus_tags": ["数据结构", "算法"],
            "days_to_deadline": 10,
            "sprint_goal": "完成算法专题复习并拿下期中考试",
            "members": [user] + friends[:2],
            "messages": [
                ("今晚 20:00 一起复盘二叉树遍历？", 0),
                ("好的！我也正好想练练", 1),
                ("我也来", 2),
                ("那就这样定了，大家准备一下", 0),
            ],
        },
        {
            "name": "前端学习互助组",
            "description": "前端技术交流和学习互助",
            "type": GroupType.SQUAD,
            "focus_tags": ["React", "Vue", "前端"],
            "days_to_deadline": 60,
            "members": [user, friends[0]],
            "messages": [
                ("有人用过React的useEffect吗？第二个参数的依赖数组要注意什么？", 0),
                ("如果不传依赖数组，每次render都会执行。传空数组只执行一次", 1),
                ("原来如此！谢谢", 0),
            ],
        },
        {
            "name": "晨跑打卡群",
            "description": "每天早上7点一起跑步打卡",
            "type": GroupType.SPRINT,
            "focus_tags": ["运动", "健康"],
            "days_to_deadline": 30,
            "members": [user] + friends,
            "messages": [
                ("明天有人一起跑吗？", 1),
                ("我可以", 0),
                ("+1", 2),
                ("明天早上7点操场见", 1),
            ],
        },
    ]

    for group_spec in groups:
        group_result = await session.execute(
            select(Group).where(Group.name == group_spec["name"])
        )
        group = group_result.scalar_one_or_none()
        if group:
            continue

        group = Group(
            name=group_spec["name"],
            description=group_spec["description"],
            avatar_url=f"https://picsum.photos/seed/{group_spec['name']}/200/200",
            type=group_spec["type"],
            focus_tags=group_spec["focus_tags"],
            deadline=now + timedelta(days=group_spec["days_to_deadline"]),
            sprint_goal=group_spec.get("sprint_goal"),
            max_members=30,
            is_public=True,
            join_requires_approval=False,
        )
        session.add(group)
        await session.flush()

        # Add members
        for idx, member in enumerate(group_spec["members"]):
            member_exists = await session.execute(
                select(GroupMember).where(
                    GroupMember.group_id == group.id,
                    GroupMember.user_id == member.id,
                )
            )
            if member_exists.scalar_one_or_none():
                continue

            session.add(
                GroupMember(
                    group_id=group.id,
                    user_id=member.id,
                    role=GroupRole.OWNER if idx == 0 else GroupRole.MEMBER,
                    flame_contribution=randint(50, 150),
                    tasks_completed=randint(3, 12),
                    checkin_streak=randint(3, 10),
                    last_checkin_date=now - timedelta(days=randint(0, 2)),
                )
            )

        # Add messages
        for msg_spec in group_spec["messages"]:
            msg_exists = await session.execute(
                select(GroupMessage).where(
                    GroupMessage.group_id == group.id,
                    GroupMessage.content == msg_spec[0],
                )
            )
            if msg_exists.scalar_one_or_none():
                continue

            sender = group_spec["members"][msg_spec[1]]
            session.add(
                GroupMessage(
                    group_id=group.id,
                    sender_id=sender.id,
                    message_type=MessageType.TEXT,
                    content=msg_spec[0],
                    created_at=now - timedelta(hours=randint(1, 48)),
                )
            )


async def _seed_user_data(session, user: User):
    now = datetime.utcnow()

    # Achievements
    await _ensure_achievements(session)
    await _cleanup_legacy_demo_achievements(session, user)
    await session.flush()
    achievements = {
        row.id: row
        for row in (await session.execute(select(Achievement))).scalars().all()
    }

    def _upsert_user_achievement(achievement_id: str, progress: float, value: int, target: int, unlocked: bool):
        return UserAchievement(
            user_id=user.id,
            achievement_id=achievement_id,
            progress=progress,
            progress_value=value,
            progress_target=target,
            unlocked_at=now - timedelta(days=randint(1, 30)) if unlocked else None,
            is_pinned=unlocked,
            last_progress_update=now,
        )

    user_achievements = [
        _upsert_user_achievement("streak_7", 1.0, 7, 7, True),
        _upsert_user_achievement("streak_30", 0.83, 25, 30, False),
        _upsert_user_achievement("nodes_100", 0.68, 68, 100, False),
        _upsert_user_achievement("study_100hours", 0.87, 87, 100, False),
        _upsert_user_achievement("sprint_first", 1.0, 1, 1, True),
        _upsert_user_achievement("night_owl", 1.0, 10, 10, True),
        _upsert_user_achievement("tasks_100", 0.36, 36, 100, False),
    ]

    for item in user_achievements:
        exists = await session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id,
                UserAchievement.achievement_id == item.achievement_id,
            )
        )
        existing = exists.scalar_one_or_none()
        if existing is None:
            session.add(item)
            continue
        existing.progress = item.progress
        existing.progress_value = item.progress_value
        existing.progress_target = item.progress_target
        existing.unlocked_at = item.unlocked_at
        existing.is_pinned = item.is_pinned
        existing.last_progress_update = item.last_progress_update

    # Streak stats
    streak = await session.execute(
        select(UserStreakStats).where(UserStreakStats.user_id == user.id)
    )
    if not streak.scalar_one_or_none():
        session.add(
            UserStreakStats(
                user_id=user.id,
                current_streak=7,
                max_streak=30,
                longest_streak=30,
                total_checkin_days=52,
                last_activity_date=now - timedelta(hours=2),
                longest_streak_start=now - timedelta(days=32),
                longest_streak_end=now - timedelta(days=2),
                freeze_charges=2,
                max_freeze_charges=3,
            )
        )

    existing_photon_history = await session.execute(
        select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == user.id,
        )
    )
    if existing_photon_history.first() is None:
        photon_entries = [
            dict(
                transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT.value,
                amount=50,
                balance_before=0,
                balance_after=50,
                source="achievement:streak_7",
                related_item_id="streak_7",
                extra_data={"achievement_name": "一周坚持"},
            ),
            dict(
                transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT.value,
                amount=120,
                balance_before=50,
                balance_after=170,
                source="achievement:sprint_first",
                related_item_id="sprint_first",
                extra_data={"achievement_name": "初出茅庐"},
            ),
            dict(
                transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT.value,
                amount=180,
                balance_before=170,
                balance_after=350,
                source="achievement:night_owl",
                related_item_id="night_owl",
                extra_data={"achievement_name": "深夜学者"},
            ),
        ]
        for entry in photon_entries:
            session.add(
                PhotonTransactionHistory(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    created_at=now - timedelta(days=randint(1, 14)),
                    updated_at=now,
                    **entry,
                )
            )
        user.photon_balance = 350
        user.photon_updated_at = now

    # Galaxy skins + titles
    await _ensure_galaxy_skins(session)
    await session.flush()

    for skin_id in ["skin_nebula", "skin_solar"]:
        skin = await session.execute(select(GalaxySkin).where(GalaxySkin.id == skin_id))
        skin = skin.scalar_one_or_none()
        if skin:
            exists = await session.execute(
                select(UserGalaxySkin).where(
                    UserGalaxySkin.user_id == user.id,
                    UserGalaxySkin.skin_id == skin.id,
                )
            )
            if not exists.scalar_one_or_none():
                session.add(
                    UserGalaxySkin(
                        user_id=user.id,
                        skin_id=skin.id,
                        unlocked_at=now - timedelta(days=randint(3, 15)),
                        unlock_source="achievement",
                        is_equipped=(skin_id == "skin_nebula"),
                    )
                )
    user.equipped_skin = "skin_nebula"
    user.equipped_skin_source = "achievement"

    for title_spec in [
        ("title_sprinter", "冲刺高手", "🏃 冲刺高手", "sprint_first"),
        ("title_explorer", "星图探索者", "🌟 星图探索者", "nodes_100"),
    ]:
        title_exists = await session.execute(
            select(UserTitle).where(
                UserTitle.user_id == user.id,
                UserTitle.title_id == title_spec[0]
            )
        )
        existing_title = title_exists.scalar_one_or_none()
        is_equipped = title_spec[0] == "title_sprinter"
        if existing_title is None:
            session.add(
                UserTitle(
                    user_id=user.id,
                    title_id=title_spec[0],
                    title_name=title_spec[1],
                    title_display=title_spec[2],
                    source_achievement_id=title_spec[3],
                    is_equipped=is_equipped,
                    unlocked_at=now - timedelta(days=randint(2, 10)),
                )
            )
            continue
        existing_title.title_name = title_spec[1]
        existing_title.title_display = title_spec[2]
        existing_title.source_achievement_id = title_spec[3]
        existing_title.is_equipped = is_equipped
    user.equipped_title = "title_sprinter"
    user.equipped_title_source = "achievement"

    # Plans
    sprint_plan = await session.execute(
        select(Plan).where(Plan.user_id == user.id, Plan.name == "数据结构期中冲刺")
    )
    sprint_plan = sprint_plan.scalar_one_or_none()
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

    # Completed plan
    completed_plan = await session.execute(
        select(Plan).where(Plan.user_id == user.id, Plan.name == "Python基础强化")
    )
    completed_plan = completed_plan.scalar_one_or_none()
    if not completed_plan:
        session.add(
            Plan(
                user_id=user.id,
                name="Python基础强化",
                type=PlanType.SPRINT,
                description="系统性学习Python语法和常用库",
                target_date=date.today() - timedelta(days=15),
                daily_available_minutes=90,
                total_estimated_hours=15,
                mastery_level=0.85,
                progress=1.0,
                is_active=False,
                is_primary=False,
            )
        )

    growth_plan = await session.execute(
        select(Plan).where(Plan.user_id == user.id, Plan.name == "计算机科学基础巩固")
    )
    growth_plan = growth_plan.scalar_one_or_none()
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

    # Historical tasks
    await _seed_historical_tasks(session, user, now)

    # Extended capsules
    await _seed_extended_capsules(session, user, now)

    # Multiple chat sessions
    await _seed_multiple_chat_sessions(session, user, now)

    # Community users + friendships
    friend_specs = [
        ("spark_friend_1", "friend1@sparkle.demo", "阿泽"),
        ("spark_friend_2", "friend2@sparkle.demo", "小林"),
        ("spark_friend_3", "friend3@sparkle.demo", "Nora"),
        ("spark_friend_4", "friend4@sparkle.demo", "程序员小明"),
        ("spark_friend_5", "friend5@sparkle.demo", "算法爱好者"),
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
                flame_level=randint(5, 18),
                flame_brightness=round(uniform(0.4, 0.9), 2),
                depth_preference=round(uniform(0.4, 0.8), 2),
                curiosity_preference=round(uniform(0.4, 0.9), 2),
                registration_source="seed",
                is_active=True,
            )
            session.add(friend)
            await session.flush()
        friends.append(friend)

        uid_small, uid_large = sorted([user.id, friend.id])
        existing_friendship = await session.execute(
            select(Friendship).where(
                Friendship.user_id == uid_small,
                Friendship.friend_id == uid_large,
            )
        )
        if not existing_friendship.scalar_one_or_none():
            session.add(
                Friendship(
                    user_id=uid_small,
                    friend_id=uid_large,
                    status=FriendshipStatus.ACCEPTED,
                    initiated_by=user.id,
                    match_reason={"courses": ["数据结构", "操作系统"]},
                )
            )

    # Extended community
    await _seed_extended_community(session, user, friends, now)

    # Multiple groups
    await _seed_multiple_groups(session, user, friends, now)

    await session.commit()


async def seed_demo_user():
    async with AsyncSessionLocal() as session:
        user = await _get_or_create_user(
            session,
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
        )
        await session.commit()
        await session.refresh(user)

        await _seed_user_data(session, user)
        logger.success(f"✅ Enhanced demo user seeded: {DEMO_USERNAME}")


if __name__ == "__main__":
    asyncio.run(seed_demo_user())
