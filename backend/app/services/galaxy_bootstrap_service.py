"""Bootstrap a minimal galaxy from onboarding goal data.

Creates 5 scaffold knowledge nodes the moment a user completes onboarding,
so the galaxy is a navigable map from day 1 rather than an empty screen.
"""
from __future__ import annotations

from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode
from app.services.galaxy_service import GalaxyService

# Seed templates by goal type — abstract enough to apply to any subject,
# specific enough to feel relevant to the user's goal.
_GOAL_TYPE_SEEDS: dict[str, list[dict[str, str]]] = {
    "exam": [
        {
            "title": "核心概念理解",
            "summary": "目标学科的基础概念与定义，是所有题型的底层支撑。",
        },
        {
            "title": "典型题型训练",
            "summary": "高频考题结构与解题方法，建立答题的肌肉记忆。",
        },
        {
            "title": "错题归因分析",
            "summary": "分析失分原因，找到可以立即改进的具体卡点。",
        },
        {
            "title": "阶段性自测",
            "summary": "通过模拟测验评估当前水平，识别与目标的差距。",
        },
        {
            "title": "备考节奏规划",
            "summary": "复习周期与时间分配策略，让努力不内耗。",
        },
    ],
    "skill": [
        {
            "title": "基础技能搭建",
            "summary": "该技能的核心入门知识，没有这层基础后面容易卡住。",
        },
        {
            "title": "实践项目练习",
            "summary": "通过具体项目积累经验，学得再多不如做一个项目深。",
        },
        {
            "title": "难点突破",
            "summary": "当前阶段最容易卡住的地方，提前预判可以节省大量时间。",
        },
        {
            "title": "进阶技巧",
            "summary": "区分初级和中级水平的关键能力，值得专项投入。",
        },
        {
            "title": "应用场景拓展",
            "summary": "把技能用到真实场景中，巩固理解并建立信心。",
        },
    ],
    "interest": [
        {
            "title": "领域全景概览",
            "summary": "这个兴趣领域的整体地图，先知道边界再决定去哪里深挖。",
        },
        {
            "title": "入门资源精选",
            "summary": "最值得先接触的内容，避免信息过载从错误地方开始。",
        },
        {
            "title": "核心概念",
            "summary": "真正理解这个领域绕不开的几个核心概念。",
        },
        {
            "title": "深度探索方向",
            "summary": "最有深度可挖的几个方向，根据你的兴趣点选一个先突破。",
        },
        {
            "title": "实践与表达",
            "summary": "用行动加深理解，兴趣只有落地才能持续。",
        },
    ],
}

_DEFAULT_SEEDS: list[dict[str, str]] = [
    {
        "title": "目标拆解",
        "summary": "将大目标分解为可执行的小步骤，每个步骤都能在一次专注中完成。",
    },
    {
        "title": "基础知识盘点",
        "summary": "梳理已知与未知的边界，让学习从已知的地方开始延伸。",
    },
    {
        "title": "核心难点识别",
        "summary": "找出最需要突破的卡点，集中火力比全面铺开更有效。",
    },
    {
        "title": "学习节奏建立",
        "summary": "建立稳定、可持续的学习习惯，节奏比强度更重要。",
    },
    {
        "title": "进展追踪",
        "summary": "定期回顾目标与实际进度，及时发现偏差并调整。",
    },
]


class GalaxyBootstrapService:
    """Creates scaffold knowledge nodes from onboarding goal data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._galaxy = GalaxyService(db)

    async def seed_from_goal(
        self,
        *,
        user_id: UUID,
        learning_goal: str | None,
        goal_type: str | None,
    ) -> list[KnowledgeNode]:
        """Create 5 scaffold nodes for the user's galaxy based on their stated goal.

        These nodes start at mastery_score=0 (dim stars). As the user completes
        tasks and logs knowledge, the nodes will brighten with mastery.
        """
        seeds = _GOAL_TYPE_SEEDS.get(str(goal_type or "").strip().lower(), _DEFAULT_SEEDS)
        tags = [
            "onboarding_seed",
            f"goal_type:{goal_type or 'general'}",
        ]
        if learning_goal:
            # Truncate goal to avoid overly long tags
            tags.append(f"goal:{learning_goal[:40]}")

        created: list[KnowledgeNode] = []
        for i, seed in enumerate(seeds[:5]):
            try:
                node = await self._galaxy.create_node(
                    user_id=user_id,
                    title=seed["title"],
                    summary=seed["summary"],
                    tags=[*tags, f"seed_rank:{i}"],
                )
                created.append(node)
            except Exception as exc:
                logger.warning(
                    "GalaxyBootstrapService: failed to create seed node '{}' for user {}: {}",
                    seed["title"],
                    user_id,
                    exc,
                )
        logger.info(
            "GalaxyBootstrapService: seeded {} nodes for user {} (goal_type={})",
            len(created),
            user_id,
            goal_type,
        )
        return created
