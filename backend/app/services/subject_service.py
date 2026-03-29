"""
学科服务
Subject Service - 管理学科标准和映射 (v2.1)
"""
import json

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subject import Subject


_SECTOR_COLORS = {
    "COSMOS": "#00BFFF",
    "TECH": "#C0C0C0",
    "ART": "#FF00FF",
    "CIVILIZATION": "#FFD700",
    "LIFE": "#32CD32",
    "WISDOM": "#FFFFFF",
    "VOID": "#2F4F4F",
}

_SECTOR_GLOWS = {
    "COSMOS": "#87CEEB",
    "TECH": "#E8E8E8",
    "ART": "#FFB6C1",
    "CIVILIZATION": "#FFF8DC",
    "LIFE": "#90EE90",
    "WISDOM": "#F0F8FF",
    "VOID": "#696969",
}

_SECTOR_ANGLES = {
    "WISDOM": 0.0,
    "COSMOS": 300.0,
    "TECH": 60.0,
    "ART": 240.0,
    "CIVILIZATION": 120.0,
    "LIFE": 180.0,
    "VOID": 0.0,
}

_DEFAULT_SUBJECTS = [
    {
        "name": "数学",
        "category": "理学",
        "aliases": ["Math", "Mathematics", "高数", "代数", "几何"],
        "sector_code": "COSMOS",
        "sort_order": 10,
        "icon_name": "calculate",
    },
    {
        "name": "物理",
        "category": "理学",
        "aliases": ["Physics", "力学", "电磁学"],
        "sector_code": "COSMOS",
        "sort_order": 20,
        "icon_name": "science",
    },
    {
        "name": "化学",
        "category": "理学",
        "aliases": ["Chemistry", "有机化学", "无机化学"],
        "sector_code": "COSMOS",
        "sort_order": 30,
        "icon_name": "biotech",
    },
    {
        "name": "生物",
        "category": "理学",
        "aliases": ["Biology", "生命科学"],
        "sector_code": "LIFE",
        "sort_order": 40,
        "icon_name": "eco",
    },
    {
        "name": "英语",
        "category": "语言",
        "aliases": ["English", "英文"],
        "sector_code": "ART",
        "sort_order": 50,
        "icon_name": "translate",
    },
    {
        "name": "语文",
        "category": "语言",
        "aliases": ["Chinese", "中文", "文学"],
        "sector_code": "ART",
        "sort_order": 60,
        "icon_name": "menu_book",
    },
    {
        "name": "历史",
        "category": "人文",
        "aliases": ["History", "世界史", "中国史"],
        "sector_code": "CIVILIZATION",
        "sort_order": 70,
        "icon_name": "history_edu",
    },
    {
        "name": "地理",
        "category": "人文",
        "aliases": ["Geography", "地球科学"],
        "sector_code": "CIVILIZATION",
        "sort_order": 80,
        "icon_name": "public",
    },
    {
        "name": "政治",
        "category": "人文",
        "aliases": ["Politics", "思想政治"],
        "sector_code": "CIVILIZATION",
        "sort_order": 90,
        "icon_name": "gavel",
    },
    {
        "name": "计算机",
        "category": "工学",
        "aliases": ["Computer Science", "CS", "编程", "软件工程"],
        "sector_code": "TECH",
        "sort_order": 100,
        "icon_name": "computer",
    },
    {
        "name": "经济",
        "category": "商科",
        "aliases": ["Economics", "金融", "Finance"],
        "sector_code": "CIVILIZATION",
        "sort_order": 110,
        "icon_name": "trending_up",
    },
    {
        "name": "心理学",
        "category": "社科",
        "aliases": ["Psychology", "心理"],
        "sector_code": "LIFE",
        "sort_order": 120,
        "icon_name": "psychology",
    },
]


class SubjectService:
    """学科标准化服务"""

    # 内存缓存
    _cache: dict[str, str] = {}
    _aliases_map: dict[str, str] = {}
    _loaded: bool = False

    async def ensure_default_subjects(self, db: AsyncSession) -> int:
        """Seed baseline subjects when the table is empty."""
        result = await db.execute(select(func.count(Subject.id)))
        subject_count = result.scalar_one() or 0
        if subject_count > 0:
            return 0

        logger.info("Subjects table is empty, seeding default subjects")
        for item in _DEFAULT_SUBJECTS:
            sector_code = item["sector_code"]
            db.add(
                Subject(
                    name=item["name"],
                    category=item["category"],
                    aliases=item["aliases"],
                    sector_code=sector_code,
                    hex_color=_SECTOR_COLORS[sector_code],
                    glow_color=_SECTOR_GLOWS[sector_code],
                    position_angle=_SECTOR_ANGLES[sector_code],
                    icon_name=item["icon_name"],
                    is_active=True,
                    sort_order=item["sort_order"],
                )
            )
        await db.flush()
        logger.info("Seeded {} default subjects", len(_DEFAULT_SUBJECTS))
        return len(_DEFAULT_SUBJECTS)

    async def load_cache(self, db: AsyncSession) -> None:
        """加载学科缓存"""
        logger.info("Loading subject cache...")
        result = await db.execute(
            select(Subject).where(Subject.is_active)
        )
        subjects = result.scalars().all()

        self._cache = {s.name: s.name for s in subjects}
        self._aliases_map = {}

        for subject in subjects:
            # 别名映射到标准名
            if subject.aliases:
                try:
                    # aliases 是 JSON 类型，SQLAlchemy 会自动反序列化
                    aliases = subject.aliases if isinstance(subject.aliases, list) else json.loads(subject.aliases)
                    for alias in aliases:
                        self._aliases_map[alias.lower()] = subject.name
                except Exception as e:
                    logger.error(f"Failed to parse aliases for subject {subject.name}: {e}")

        self._loaded = True
        logger.info(f"Subject cache loaded. {len(subjects)} subjects, {len(self._aliases_map)} aliases.")

    def normalize(self, raw_subject: str) -> str:
        """
        将 AI 输出或用户输入的学科名映射到标准名

        示例:
        - "Data Structure" -> "数据结构与算法"
        - "DS" -> "数据结构与算法"
        - "数据结构" -> "数据结构与算法"
        """
        if not raw_subject:
            return "其他"

        # 1. 精确匹配
        if raw_subject in self._cache:
            return raw_subject

        # 2. 别名匹配（不区分大小写）
        normalized = self._aliases_map.get(raw_subject.lower())
        if normalized:
            return normalized

        # 3. 无法匹配，返回"其他"
        return "其他"

    async def get_all_subjects(self, db: AsyncSession) -> list[Subject]:
        """获取所有启用的学科（供前端下拉选择）"""
        result = await db.execute(
            select(Subject)
            .where(Subject.is_active)
            .order_by(Subject.sort_order, Subject.name)
        )
        return result.scalars().all()
