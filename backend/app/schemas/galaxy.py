from __future__ import annotations
from datetime import datetime
from enum import Enum
import math
import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.services.node_sector_service import (
    blend_sector_colors,
    build_sector_visuals,
    dominant_sector_from_weights,
    normalize_sector_weights,
    parse_sector_code,
    resolve_sector_weights,
)


class SectorCode(str, Enum):
    COSMOS = "COSMOS"
    TECH = "TECH"
    ART = "ART"
    CIVILIZATION = "CIVILIZATION"
    LIFE = "LIFE"
    WISDOM = "WISDOM"
    VOID = "VOID"


class NodeStatus(str, Enum):
    LOCKED = "locked"  # 未解锁
    UNLIT = "unlit"  # 已解锁但未学习
    GLIMMER = "glimmer"  # 微光 (0-30)
    SHINING = "shining"  # 闪耀 (30-80)
    BRILLIANT = "brilliant"  # 璀璨 (80-95)
    MASTERED = "mastered"  # 精通 (95-100)
    COLLAPSED = "collapsed"  # 坍缩


# ==========================================
# 请求模型
# ==========================================
class SparkRequest(BaseModel):
    study_minutes: int = Field(..., ge=1, le=480, description="学习时长(分钟)")
    task_id: UUID | None = Field(None, description="关联的任务ID")
    trigger_expansion: bool = Field(True, description="是否触发知识拓展")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(10, ge=1, le=50)
    threshold: float = Field(0.3, ge=0.0, le=1.0)


class ExpansionFeedbackRequest(BaseModel):
    trigger_node_id: UUID
    expansion_queue_id: UUID | None = None
    rating: int | None = Field(None, ge=1, le=5)
    implicit_score: float | None = Field(None, ge=0.0, le=1.0)
    feedback_type: str = Field("explicit")
    prompt_version: str | None = None
    metadata: dict[str, Any] | None = None


class NodeExpansionCandidateRequest(BaseModel):
    count: int = Field(3, ge=1, le=3)


class NodeExpansionCandidate(BaseModel):
    candidate_id: str
    name: str
    name_en: str | None = None
    description: str
    importance_level: int = Field(3, ge=1, le=5)
    relation_to_trigger: str = "related"
    relation_strength: float = Field(0.7, ge=0.0, le=1.0)
    keywords: list[str] = Field(default_factory=list)
    sector_weights: dict[str, int] = Field(default_factory=dict)


class NodeExpansionCandidatesResponse(BaseModel):
    trigger_node_id: UUID
    prompt_version: str
    candidates: list[NodeExpansionCandidate]


class ApplyNodeExpansionRequest(BaseModel):
    prompt_version: str | None = None
    candidates: list[NodeExpansionCandidate] = Field(default_factory=list)


class ApplyNodeExpansionResponse(BaseModel):
    success: bool = True
    created_count: int = 0
    created_nodes: list[NodeBase] = Field(default_factory=list)


# ==========================================
# 响应模型
# ==========================================
class NodeBase(BaseModel):
    id: UUID
    name: str
    name_en: str | None = None
    description: str | None = None
    importance_level: int
    sector_code: SectorCode
    sector_weights: dict[str, int] = Field(default_factory=dict)
    base_color: str | None = None
    glow_color: str | None = None
    is_seed: bool
    parent_id: UUID | None = None
    parent_name: str | None = None  # Added for context
    tags: list[str] = Field(default_factory=list)
    global_spark_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, node) -> "NodeBase":
        sector_weights = resolve_sector_weights(node)
        sector_code = dominant_sector_from_weights(sector_weights)
        base_color, glow_color = cls._resolve_sector_colors(node, sector_weights)
        return cls(
            id=node.id,
            name=node.name,
            name_en=node.name_en,
            description=node.description,
            importance_level=node.importance_level,
            sector_code=sector_code,
            sector_weights=sector_weights,
            base_color=base_color,
            glow_color=glow_color,
            is_seed=node.is_seed,
            parent_id=node.parent_id,
            parent_name=node.parent.name if getattr(node, "parent", None) else None,
            tags=NodeWithStatus._build_auto_tags(node, sector_code),
            global_spark_count=node.global_spark_count,
        )

    @staticmethod
    def _resolve_sector_colors(node, sector_weights: dict[str, int]) -> tuple[str, str]:
        dominant_sector = dominant_sector_from_weights(sector_weights)
        subject = getattr(node, "subject", None)
        if (
            subject is not None
            and parse_sector_code(getattr(subject, "sector_code", None)) == dominant_sector
            and len(sector_weights) == 1
        ):
            base_color = getattr(subject, "hex_color", None)
            glow_color = getattr(subject, "glow_color", None)
            if base_color and glow_color:
                return base_color, glow_color
        return blend_sector_colors(sector_weights)


class UserStatusInfo(BaseModel):
    mastery_score: float
    total_study_minutes: int
    study_count: int
    is_unlocked: bool
    is_collapsed: bool
    is_favorite: bool
    first_unlock_at: datetime | None = None
    last_study_at: datetime | None = None
    next_review_at: datetime | None = None
    decay_paused: bool

    # 计算属性
    status: NodeStatus
    brightness: float  # 0-1，用于前端渲染


class NodeWithStatus(NodeBase):
    """节点 + 用户状态"""

    user_status: UserStatusInfo | None = None

    # 布局信息
    position_angle: float  # 在星域中的角度
    position_radius: float  # 距离中心的半径
    position_x: float
    position_y: float

    @classmethod
    def from_models(cls, node, status):
        user_status = None
        if status:
            # 计算视觉状态
            visual_status = cls._calculate_status(status)
            brightness = cls._calculate_brightness(status)

            user_status = UserStatusInfo(
                mastery_score=status.mastery_score,
                total_study_minutes=status.total_study_minutes,
                study_count=status.study_count,
                is_unlocked=status.is_unlocked,
                is_collapsed=status.is_collapsed,
                is_favorite=status.is_favorite,
                first_unlock_at=status.first_unlock_at,
                last_study_at=status.last_study_at,
                next_review_at=status.next_review_at,
                decay_paused=status.decay_paused,
                status=visual_status,
                brightness=brightness,
            )

        sector_weights = resolve_sector_weights(node)
        sector_code = dominant_sector_from_weights(sector_weights)
        base_color, glow_color = cls._resolve_sector_colors(node, sector_weights)
        sector_visuals = build_sector_visuals(
            node,
            importance_level=node.importance_level,
            sector_weights=sector_weights,
            keep_position=(node.position_x, node.position_y),
        )
        position_angle = sector_visuals.position_angle
        position_radius = sector_visuals.position_radius
        position_x, position_y = cls._resolve_position(
            node=node,
            angle=position_angle,
            radius=position_radius,
        )

        return cls(
            id=node.id,
            name=node.name,
            name_en=node.name_en,
            description=node.description,
            importance_level=node.importance_level,
            sector_code=sector_code,
            sector_weights=sector_weights,
            base_color=base_color,
            glow_color=glow_color,
            is_seed=node.is_seed,
            parent_id=node.parent_id,
            parent_name=node.parent.name if getattr(node, "parent", None) else None,
            tags=cls._build_auto_tags(node, sector_code),
            global_spark_count=node.global_spark_count,
            user_status=user_status,
            position_angle=position_angle,
            position_radius=position_radius,
            position_x=position_x,
            position_y=position_y,
        )

    @staticmethod
    def _calculate_status(status) -> NodeStatus:
        if status.is_collapsed:
            return NodeStatus.COLLAPSED
        if not status.is_unlocked:
            return NodeStatus.LOCKED

        score = status.mastery_score
        if score >= 95:
            return NodeStatus.MASTERED
        elif score >= 80:
            return NodeStatus.BRILLIANT
        elif score >= 30:
            return NodeStatus.SHINING
        elif score > 0:
            return NodeStatus.GLIMMER
        else:
            return NodeStatus.UNLIT

    @staticmethod
    def _calculate_brightness(status) -> float:
        if not status.is_unlocked:
            return 0.2
        if status.is_collapsed:
            return 0.1
        return 0.3 + (status.mastery_score / 100.0) * 0.7

    @staticmethod
    def _resolve_position(node, angle: float, radius: float) -> tuple[float, float]:
        if node.position_x is not None and node.position_y is not None:
            return float(node.position_x), float(node.position_y)

        seed = node.id.int % 360
        jitter_radius = 40.0 + (node.importance_level * 12.0) + (seed % 29)
        effective_angle = math.radians(angle + (seed % 37) - 18)
        effective_radius = radius + jitter_radius
        return (
            math.cos(effective_angle) * effective_radius,
            math.sin(effective_angle) * effective_radius,
        )

    @staticmethod
    def _resolve_sector_colors(node, sector_weights: dict[str, int]) -> tuple[str, str]:
        return NodeBase._resolve_sector_colors(node, sector_weights)

    @staticmethod
    def _build_auto_tags(node, sector_code: SectorCode) -> list[str]:
        tags: list[str] = []
        seen: set[str] = set()

        def add_tag(raw: str | None) -> None:
            if raw is None:
                return
            tag = raw.strip()
            if not tag:
                return
            normalized = tag.lower()
            if normalized in seen:
                return
            seen.add(normalized)
            tags.append(tag)

        for keyword in node.keywords or []:
            add_tag(str(keyword))

        if not tags:
            source = f"{node.name or ''} {node.description or ''}"
            for token in re.findall(r"[\w\u4e00-\u9fff]{2,}", source):
                add_tag(token)
                if len(tags) >= 3:
                    break

        if sector_code != SectorCode.VOID:
            add_tag(sector_code.value.lower())
        if node.is_seed:
            add_tag("seed")
        if node.importance_level >= 4:
            add_tag("core")

        return tags[:5]


class NodeRelationInfo(BaseModel):
    source_node_id: UUID
    target_node_id: UUID
    relation_type: str
    strength: float


class GalaxyUserStats(BaseModel):
    total_nodes: int = 0
    unlocked_count: int = 0
    mastered_count: int = 0
    total_study_minutes: int = 0
    sector_distribution: dict[str, int] = {}  # {sector_code: count}
    streak_days: int = 0  # 连续学习天数


class GalaxyGraphResponse(BaseModel):
    """星图完整数据响应"""

    nodes: list[NodeWithStatus]
    relations: list[NodeRelationInfo] = []  # Alias: edges (for Flutter compatibility)
    edges: list[NodeRelationInfo] | None = None  # Flutter expects this field name
    user_stats: GalaxyUserStats
    user_flame_intensity: float = 0.85  # Flutter expects this field (0.0-1.0)


class SparkEvent(BaseModel):
    """点亮动画事件"""

    node_id: UUID
    node_name: str
    sector_code: SectorCode
    old_mastery: float
    new_mastery: float
    is_first_unlock: bool  # 首次点亮 (播放特殊动画)
    is_level_up: bool  # 升级 (跨越阈值)

    # 前端动画参数
    particle_count: int = 20
    animation_duration_ms: int = 1500


class SparkResult(BaseModel):
    spark_event: SparkEvent
    expansion_queued: bool
    expanded_nodes: list[NodeBase] | None = None  # 如果同步返回
    updated_status: Any | None = None  # UserStatusInfo or dict


class SearchResultItem(BaseModel):
    node: NodeBase
    similarity: float
    user_status: UserStatusInfo | None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total_count: int = 0


class ExpansionFeedbackResponse(BaseModel):
    success: bool = True
    feedback_id: UUID


class ReviewSuggestion(BaseModel):
    node_id: UUID
    node_name: str
    sector_code: SectorCode
    current_mastery: float
    days_since_study: int
    urgency: str  # 'high' | 'normal'


class ReviewSuggestionsResponse(BaseModel):
    suggestions: list[ReviewSuggestion]
    next_review_count: int = 0  # 未来 7 天需要复习的总数


class NodeDetailResponse(BaseModel):
    node: NodeWithStatus
    relations: list[NodeRelationInfo]
    # 可以添加更多详情，如学习记录历史等
