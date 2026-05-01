from __future__ import annotations

import math
import re
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.sector import SectorCode
from app.services.node_sector_service import (
    blend_sector_colors,
    build_sector_visuals,
    dominant_sector_from_weights,
    parse_sector_code,
    resolve_sector_weights,
)


class NodeStatus(StrEnum):
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
    threshold: float = Field(0.6, ge=0.0, le=1.0)  # cosine distance threshold; 0.6 ≈ similarity>0.4, suitable for Chinese embeddings


class CreateGalaxyNodeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    name_en: str | None = Field(None, max_length=255)
    description: str = Field("", max_length=500)
    importance_level: int = Field(3, ge=1, le=5)
    subject_id: int | None = None
    parent_node_id: UUID | None = None
    relation_to_parent: str = Field("related")
    relation_strength: float = Field(0.7, ge=0.0, le=1.0)
    keywords: list[str] = Field(default_factory=list)
    sector_weights: dict[str, int] = Field(default_factory=dict)


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
    requested_count: int = 0
    applied_count: int = 0
    created_count: int = 0
    reused_count: int = 0
    created_nodes: list[NodeBase] = Field(default_factory=list)
    reused_nodes: list[NodeBase] = Field(default_factory=list)


class SuggestedNodeSimilarity(BaseModel):
    node_id: UUID
    name: str
    similarity: float = Field(..., ge=0.0, le=1.0)


class SuggestedDocumentNode(BaseModel):
    node_id: UUID
    name: str
    description: str | None = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    similarity_to_existing: list[SuggestedNodeSimilarity] = Field(default_factory=list)


class SuggestedDocumentNodesResponse(BaseModel):
    file_id: UUID
    suggested_nodes: list[SuggestedDocumentNode] = Field(default_factory=list)


class DraftGalaxyNode(SuggestedDocumentNode):
    source_file_id: UUID | None = None
    source_file_name: str | None = None
    created_at: datetime | None = None


class DraftGalaxyNodesResponse(BaseModel):
    drafts: list[DraftGalaxyNode] = Field(default_factory=list)


class ReviewNodeDecision(BaseModel):
    node_id: UUID
    action: str = Field(..., pattern="^(approve|reject|merge)$")
    edited_name: str | None = Field(None, min_length=1, max_length=255)
    edited_description: str | None = None
    merge_into_node_id: UUID | None = None


class ReviewDocumentNodesRequest(BaseModel):
    decisions: list[ReviewNodeDecision] = Field(default_factory=list)


class ReviewNodeResult(BaseModel):
    node_id: UUID
    action: str
    status: str
    merge_into_node_id: UUID | None = None


class ReviewDocumentNodesResponse(BaseModel):
    file_id: UUID
    approved_count: int = 0
    rejected_count: int = 0
    merged_count: int = 0
    results: list[ReviewNodeResult] = Field(default_factory=list)


# ==========================================
# 响应模型
# ==========================================
class NodeHistoryErrorItem(BaseModel):
    id: UUID
    question_text: str | None = None
    question_image_url: str | None = None
    subject_code: str | None = None
    chapter: str | None = None
    mastery_level: float = 0.0
    review_count: int = 0
    analysis_summary: str | None = None
    affected_node_id: UUID | None = None
    linked_knowledge_node_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    last_reviewed_at: datetime | None = None


class NodeHistoryResponse(BaseModel):
    node_id: str
    resolved_node_id: UUID | None = None
    node_label: str | None = None
    mastery: float = Field(0.0, ge=0.0, le=1.0)
    last_studied_at: datetime | None = None
    study_count: int = 0
    related_errors: list[NodeHistoryErrorItem] = Field(default_factory=list)


class GalaxyContributionNode(BaseModel):
    node_id: UUID
    node_name: str
    reason: str | None = None
    mastery_delta: int = 0
    updated_at: datetime | None = None


class UserGalaxyContribution(BaseModel):
    first_activation_count: int = 0
    error_repaired_count: int = 0
    conversation_updated_count: int = 0
    first_activated_nodes: list[GalaxyContributionNode] = Field(default_factory=list)
    error_repaired_nodes: list[GalaxyContributionNode] = Field(default_factory=list)
    conversation_updated_nodes: list[GalaxyContributionNode] = Field(default_factory=list)


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
    def from_model(cls, node) -> NodeBase:
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
    mastery_last_updated_at: datetime | None = None
    next_review_at: datetime | None = None
    decay_paused: bool

    # Evidence-mode: recent errors on this node (last 14 days)
    recent_error_count: int = 0

    # Predictive review overlay: 0.0-1.0 urgency + top recommendation marker.
    review_urgency_score: float = 0.0
    is_review_recommended: bool = False
    review_urgency_reason: str | None = None
    days_since_mastery_update: float = 0.0

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
    def from_models(cls, node, status, recent_error_count: int = 0, review_signal=None):
        user_status = None
        if status:
            # 计算视觉状态
            visual_status = cls._calculate_status(status)
            brightness = cls._calculate_brightness(status)
            mastery_last_updated_at = next(
                (
                    value
                    for value in (
                        getattr(review_signal, "mastery_last_updated_at", None),
                        getattr(status, "bkt_last_updated_at", None),
                        getattr(status, "last_study_at", None),
                        getattr(status, "updated_at", None),
                    )
                    if isinstance(value, datetime)
                ),
                None,
            )

            user_status = UserStatusInfo(
                mastery_score=status.mastery_score,
                total_study_minutes=status.total_study_minutes,
                study_count=status.study_count,
                is_unlocked=status.is_unlocked,
                is_collapsed=status.is_collapsed,
                is_favorite=status.is_favorite,
                first_unlock_at=status.first_unlock_at,
                last_study_at=status.last_study_at,
                mastery_last_updated_at=mastery_last_updated_at,
                next_review_at=status.next_review_at,
                decay_paused=status.decay_paused,
                recent_error_count=recent_error_count,
                review_urgency_score=float(getattr(review_signal, "score", 0.0) or 0.0),
                is_review_recommended=bool(getattr(review_signal, "is_recommended", False)),
                review_urgency_reason=getattr(review_signal, "reason", None),
                days_since_mastery_update=float(getattr(review_signal, "days_since_mastery_update", 0.0) or 0.0),
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


class NodeDocumentRef(BaseModel):
    file_id: UUID
    filename: str
    file_type: str | None = None
    upload_date: datetime | None = None
    chunk_count: int = 0
    preview_chunks: list[str] = Field(default_factory=list)


class NodeKnowledgeStats(BaseModel):
    total_documents: int = 0
    total_chunks: int = 0
    has_personal_uploads: bool = False
    last_material_added: datetime | None = None


class NodeSourceChunk(BaseModel):
    chunk_id: UUID
    file_id: UUID
    filename: str
    file_type: str | None = None
    chunk_index: int
    content: str
    preview: str
    page_numbers: list[int] = Field(default_factory=list)
    section_title: str | None = None
    quality_score: float | None = None
    created_at: datetime | None = None


class NodeChunksResponse(BaseModel):
    node_id: UUID
    chunks: list[NodeSourceChunk] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class NodeDetailResponse(BaseModel):
    node: NodeWithStatus
    relations: list[NodeRelationInfo]
    source_documents: list[NodeDocumentRef] = Field(default_factory=list)
    knowledge_stats: NodeKnowledgeStats = Field(default_factory=NodeKnowledgeStats)
    # 可以添加更多详情，如学习记录历史等
