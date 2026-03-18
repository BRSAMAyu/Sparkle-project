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
    KnowledgeNode,
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
    UserNodeStatus,
    UserStreakStats,
    UserTitle,
    ChatMessage,
    ChatSession,
)
from app.models.galaxy import NodeRelation


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

    # Knowledge Nodes (Galaxy) - Create a rich demo knowledge graph
    # Mirrors the 6-sector structure from DemoDataService (COSMOS/TECH/ART/CIVILIZATION/LIFE/WISDOM)
    import math

    # Define nodes: (name, description, importance, keywords, sector_label, unlocked, mastery, study_count)
    _DEMO_NODES = [
        # === COSMOS 星域 - 自然科学基础 ===
        ("高等数学", "微积分、极限、导数、积分等基础数学知识", 5, ["数学", "基础"], "COSMOS", True, 85, 12),
        ("线性代数", "矩阵、向量空间、线性变换", 4, ["数学", "线性代数"], "COSMOS", True, 70, 8),
        ("概率论与数理统计", "概率、随机变量、统计推断", 4, ["数学", "统计"], "COSMOS", True, 60, 6),
        ("离散数学", "集合论、图论、组合数学、数理逻辑", 4, ["数学", "离散"], "COSMOS", True, 55, 5),
        ("大学物理", "力学、电磁学、热学、光学基础", 4, ["物理", "基础"], "COSMOS", True, 65, 7),
        ("经典力学", "牛顿力学、动量、能量", 3, ["物理", "力学"], "COSMOS", True, 70, 5),
        ("电磁学基础", "电场、磁场、电磁感应", 3, ["物理", "电磁"], "COSMOS", True, 50, 4),
        ("普通化学", "化学反应、元素周期表、化学键", 3, ["化学", "基础"], "COSMOS", True, 45, 3),
        ("有机化学", "有机物结构、反应机理", 2, ["化学", "有机"], "COSMOS", False, 0, 0),
        # === TECH 星域 - 科技与工程 ===
        ("程序设计基础", "变量、控制流、函数、基本算法", 5, ["编程", "基础"], "TECH", True, 90, 15),
        ("Python编程", "Python语法、数据结构、面向对象", 4, ["Python", "编程"], "TECH", True, 80, 10),
        ("C/C++编程", "C语言基础、指针、C++面向对象", 4, ["C++", "编程"], "TECH", True, 75, 9),
        ("Java编程", "Java语法、OOP、集合框架", 4, ["Java", "编程"], "TECH", True, 70, 8),
        ("数据结构", "线性表、栈、队列、树、图", 5, ["数据结构", "算法"], "TECH", True, 85, 12),
        ("算法设计与分析", "排序、搜索、动态规划、贪心算法", 5, ["算法", "优化"], "TECH", True, 70, 8),
        ("计算机组成原理", "CPU、内存、I/O系统", 4, ["计算机系统", "硬件"], "TECH", True, 65, 7),
        ("操作系统", "进程、内存管理、文件系统", 5, ["操作系统", "OS"], "TECH", True, 60, 6),
        ("计算机网络", "TCP/IP、HTTP、网络协议", 4, ["网络", "协议"], "TECH", True, 55, 5),
        ("数据库系统", "SQL、关系模型、事务处理", 4, ["数据库", "SQL"], "TECH", True, 70, 8),
        ("Web前端开发", "HTML、CSS、JavaScript基础", 3, ["Web", "前端"], "TECH", True, 60, 6),
        ("Web后端开发", "RESTful API、服务器开发", 3, ["Web", "后端"], "TECH", True, 50, 4),
        ("人工智能基础", "机器学习、神经网络入门", 4, ["AI", "机器学习"], "TECH", True, 40, 3),
        ("机器学习", "监督学习、非监督学习、模型评估", 4, ["机器学习", "ML"], "TECH", False, 0, 0),
        # === ART 星域 - 艺术与人文 ===
        ("中国文学", "古代文学、现代文学、诗词赏析", 4, ["文学", "中国"], "ART", True, 75, 9),
        ("外国文学", "西方文学、世界文学经典", 3, ["文学", "外国"], "ART", True, 60, 6),
        ("写作技巧", "议论文、说明文、创意写作", 3, ["写作", "技巧"], "ART", True, 65, 7),
        ("美术基础", "素描、色彩、构图", 2, ["美术", "绘画"], "ART", True, 45, 4),
        ("音乐欣赏", "音乐史、乐理、作品欣赏", 2, ["音乐", "欣赏"], "ART", True, 50, 5),
        ("设计思维", "UI/UX设计、平面设计原理", 3, ["设计", "UI"], "ART", True, 55, 5),
        ("摄影基础", "构图、光影、后期处理", 2, ["摄影", "艺术"], "ART", True, 60, 6),
        ("影视制作", "视频拍摄、剪辑、叙事技巧", 2, ["影视", "制作"], "ART", False, 0, 0),
        # === CIVILIZATION 星域 - 社会与文明 ===
        ("中国近现代史", "辛亥革命、新中国成立、改革开放", 4, ["历史", "中国"], "CIVILIZATION", True, 80, 10),
        ("世界历史", "文艺复兴、工业革命、两次世界大战", 4, ["历史", "世界"], "CIVILIZATION", True, 70, 8),
        ("马克思主义基本原理", "唯物辩证法、政治经济学", 4, ["政治", "马克思主义"], "CIVILIZATION", True, 75, 9),
        ("经济学原理", "微观经济、宏观经济、市场机制", 4, ["经济", "市场"], "CIVILIZATION", True, 60, 6),
        ("管理学基础", "组织管理、领导力、战略规划", 3, ["管理", "组织"], "CIVILIZATION", True, 55, 5),
        ("法律基础", "宪法、民法、刑法基础知识", 3, ["法律", "权利"], "CIVILIZATION", True, 50, 4),
        ("社会学导论", "社会结构、群体行为、社会问题", 3, ["社会", "群体"], "CIVILIZATION", True, 45, 3),
        # === LIFE 星域 - 生命科学 ===
        ("普通生物学", "细胞、遗传、进化、生态", 4, ["生物", "基础"], "LIFE", True, 70, 8),
        ("人体生理学", "循环系统、消化系统、神经系统", 3, ["生理", "人体"], "LIFE", True, 60, 6),
        ("基因与遗传", "DNA、基因表达、遗传规律", 3, ["遗传", "基因"], "LIFE", True, 55, 5),
        ("健康与养生", "营养、运动、睡眠、疾病预防", 3, ["健康", "养生"], "LIFE", True, 75, 9),
        ("急救与安全", "CPR、止血、常见急症处理", 3, ["急救", "安全"], "LIFE", True, 65, 7),
        ("心理学导论", "认知、情绪、人格、行为", 4, ["心理", "认知"], "LIFE", True, 70, 8),
        ("发展心理学", "儿童、青少年、成人心理发展", 3, ["心理", "发展"], "LIFE", True, 50, 4),
        ("社会心理学", "态度、说服、群体影响", 3, ["心理", "社会"], "LIFE", True, 45, 3),
        # === WISDOM 星域 - 智慧与思考 ===
        ("哲学导论", "形而上学、认识论、伦理学", 4, ["哲学", "思考"], "WISDOM", True, 65, 7),
        ("中国哲学", "儒家、道家、佛家思想", 3, ["哲学", "中国"], "WISDOM", True, 60, 6),
        ("西方哲学", "古希腊哲学、近代哲学、现代哲学", 3, ["哲学", "西方"], "WISDOM", True, 55, 5),
        ("批判性思维", "逻辑推理、论证分析、谬误识别", 5, ["思维", "逻辑"], "WISDOM", True, 70, 8),
        ("创新思维", "发散思维、联想、头脑风暴", 4, ["思维", "创新"], "WISDOM", True, 60, 6),
        ("系统思维", "整体观、反馈循环、涌现特性", 4, ["思维", "系统"], "WISDOM", True, 50, 4),
        ("学习科学", "记忆原理、遗忘曲线、刻意练习", 5, ["学习", "方法"], "WISDOM", True, 80, 10),
        ("时间管理", "四象限法则、番茄钟、GTD", 4, ["效率", "时间"], "WISDOM", True, 75, 9),
    ]

    # Sector layout: each sector occupies a 60° arc, nodes spread within it
    _SECTOR_ANGLES = {
        "COSMOS": 0, "TECH": 60, "ART": 120,
        "CIVILIZATION": 180, "LIFE": 240, "WISDOM": 300,
    }
    _sector_counters: dict[str, int] = {}

    created_nodes: dict[str, KnowledgeNode] = {}  # name -> node (for relations)

    for node_tuple in _DEMO_NODES:
        name, desc, importance, keywords, sector, unlocked, mastery, study_count = node_tuple

        existing = (await session.execute(
            select(KnowledgeNode).where(KnowledgeNode.name == name)
        )).scalar_one_or_none()
        if existing:
            created_nodes[name] = existing
            continue

        # Calculate position within sector
        sector_idx = _sector_counters.get(sector, 0)
        _sector_counters[sector] = sector_idx + 1
        base_angle_deg = _SECTOR_ANGLES[sector]
        # Spread nodes within 50° range, offset from sector center
        angle_deg = base_angle_deg + 5 + (sector_idx * 5) % 50
        angle_rad = math.radians(angle_deg)
        # Vary radius by importance (more important = closer to center)
        radius = 150.0 + (5 - importance) * 40 + (sector_idx % 3) * 20

        node = KnowledgeNode(
            name=name,
            description=desc,
            importance_level=importance,
            is_seed=True,
            source_type="seed",
            keywords=keywords,
            position_x=radius * math.cos(angle_rad),
            position_y=radius * math.sin(angle_rad),
        )
        session.add(node)
        await session.flush()
        created_nodes[name] = node

    # Create relations between nodes (prerequisite/related edges)
    _RELATIONS = [
        ("高等数学", "线性代数", "prerequisite", 0.9),
        ("高等数学", "概率论与数理统计", "prerequisite", 0.8),
        ("高等数学", "离散数学", "related", 0.6),
        ("大学物理", "经典力学", "prerequisite", 0.9),
        ("大学物理", "电磁学基础", "prerequisite", 0.8),
        ("普通化学", "有机化学", "prerequisite", 0.7),
        ("程序设计基础", "Python编程", "prerequisite", 0.9),
        ("程序设计基础", "C/C++编程", "prerequisite", 0.9),
        ("程序设计基础", "Java编程", "prerequisite", 0.8),
        ("程序设计基础", "数据结构", "prerequisite", 0.9),
        ("数据结构", "算法设计与分析", "prerequisite", 0.9),
        ("计算机组成原理", "操作系统", "prerequisite", 0.8),
        ("操作系统", "计算机网络", "related", 0.6),
        ("数据库系统", "Web后端开发", "prerequisite", 0.7),
        ("Web前端开发", "设计思维", "related", 0.5),
        ("人工智能基础", "机器学习", "prerequisite", 0.9),
        ("概率论与数理统计", "机器学习", "prerequisite", 0.8),
        ("线性代数", "人工智能基础", "prerequisite", 0.7),
        ("心理学导论", "发展心理学", "prerequisite", 0.8),
        ("心理学导论", "社会心理学", "prerequisite", 0.8),
        ("普通生物学", "人体生理学", "prerequisite", 0.8),
        ("普通生物学", "基因与遗传", "prerequisite", 0.7),
        ("哲学导论", "中国哲学", "prerequisite", 0.7),
        ("哲学导论", "西方哲学", "prerequisite", 0.7),
        ("批判性思维", "学习科学", "related", 0.6),
        ("学习科学", "时间管理", "related", 0.7),
        # Cross-sector relations
        ("离散数学", "数据结构", "prerequisite", 0.8),
        ("离散数学", "算法设计与分析", "prerequisite", 0.7),
        ("心理学导论", "学习科学", "related", 0.7),
        ("批判性思维", "写作技巧", "application", 0.5),
        ("经济学原理", "管理学基础", "related", 0.6),
    ]

    for src_name, tgt_name, rel_type, strength in _RELATIONS:
        src = created_nodes.get(src_name)
        tgt = created_nodes.get(tgt_name)
        if not src or not tgt:
            continue
        rel_exists = (await session.execute(
            select(NodeRelation).where(
                NodeRelation.source_node_id == src.id,
                NodeRelation.target_node_id == tgt.id,
            )
        )).scalar_one_or_none()
        if not rel_exists:
            session.add(NodeRelation(
                source_node_id=src.id,
                target_node_id=tgt.id,
                relation_type=rel_type,
                strength=strength,
                created_by="seed",
            ))

    await session.flush()

    # Create UserNodeStatus for unlocked nodes
    for node_tuple in _DEMO_NODES:
        name, _, _, _, _, unlocked, mastery, study_count = node_tuple
        if not unlocked:
            continue
        node = created_nodes.get(name)
        if not node:
            continue
        status_exists = (await session.execute(
            select(UserNodeStatus).where(
                UserNodeStatus.user_id == user.id,
                UserNodeStatus.node_id == node.id,
            )
        )).scalar_one_or_none()
        if not status_exists:
            session.add(UserNodeStatus(
                user_id=user.id,
                node_id=node.id,
                is_unlocked=True,
                mastery_score=mastery,
                total_study_minutes=study_count * 15,
                study_count=study_count,
                first_unlock_at=now - timedelta(days=max(1, study_count)),
                last_study_at=now - timedelta(hours=study_count),
            ))

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

    # Community feed posts — guest user + friend posts for a lively feed
    _feed_posts = [
        (user, "连续一周打卡成功！今天的专注时间达到了 120 分钟。", "学习分享", 12, 3),
        (user, "分享一个高效学习番茄钟设置方法，欢迎交流。", "学习分享", 8, 2),
    ]
    # Add posts from friends if they were created
    if len(friends) >= 3:
        _feed_posts.extend([
            (friends[0], "刚做完数据结构的链表练习，感觉指针终于理解了！💡", "学习心得", 15, 4),
            (friends[1], "推荐一本《算法导论》配套笔记，图论部分写得特别清楚。", "资源分享", 20, 6),
            (friends[2], "今天的番茄钟完成了8个，创个人纪录！🍅", "打卡", 10, 2),
        ])
    for post_user, content, topic, likes, comments in _feed_posts:
        post_exists = await session.execute(
            select(Post).where(Post.user_id == post_user.id, Post.content == content)
        )
        if not post_exists.scalar_one_or_none():
            session.add(
                Post(
                    user_id=post_user.id,
                    content=content,
                    image_urls=["https://picsum.photos/seed/sparkle/600/400"],
                    topic=topic,
                    visibility="public",
                    like_count=likes,
                    comment_count=comments,
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

    await session.flush()

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

    await session.flush()
    logger.info(f"Guest data seeded for user_id={user.id} username={user.username}")
