from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class SectorCode(str, Enum):
    COSMOS = "COSMOS"
    TECH = "TECH"
    ART = "ART"
    CIVILIZATION = "CIVILIZATION"
    LIFE = "LIFE"
    WISDOM = "WISDOM"
    VOID = "VOID"


class NodeStatus(str, Enum):
    LOCKED = "locked"       # 未解锁
    UNLIT = "unlit"         # 已解锁但未学习
    GLIMMER = "glimmer"     # 微光 (0-30)
    SHINING = "shining"     # 闪耀 (30-80)
    BRILLIANT = "brilliant" # 璀璨 (80-95)
    MASTERED = "mastered"   # 精通 (95-100)
    COLLAPSED = "collapsed" # 坍缩


# ==========================================
# 请求模型
# ==========================================
class SparkRequest(BaseModel):
    study_minutes: int = Field(..., ge=1, le=480, description="学习时长(分钟)")
    task_id: Optional[UUID] = Field(None, description="关联的任务ID")
    trigger_expansion: bool = Field(True, description="是否触发知识拓展")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(10, ge=1, le=50)
    threshold: float = Field(0.3, ge=0.0, le=1.0)


# ==========================================
# 响应模型
# ==========================================
class NodeBase(BaseModel):
    id: UUID
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    importance_level: int
    sector_code: SectorCode
    is_seed: bool
    parent_name: Optional[str] = None # Added for context
    
    model_config = ConfigDict(from_attributes=True)


class UserStatusInfo(BaseModel):
    mastery_score: float
    total_study_minutes: int
    study_count: int
    is_unlocked: bool
    is_collapsed: bool
    is_favorite: bool
    last_study_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    decay_paused: bool
    
    # 计算属性
    status: NodeStatus
    brightness: float  # 0-1，用于前端渲染


class NodeWithStatus(NodeBase):
    """节点 + 用户状态"""
    user_status: Optional[UserStatusInfo] = None
    
    # 布局信息
    position_angle: float  # 在星域中的角度
    position_radius: float # 距离中心的半径
    
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
                last_study_at=status.last_study_at,
                next_review_at=status.next_review_at,
                decay_paused=status.decay_paused,
                status=visual_status,
                brightness=brightness
            )
        
        # 处理 subject 为空的异常情况
        sector_code = SectorCode.VOID
        position_angle = 0.0
        if node.subject:
            # 尝试匹配 SectorCode，如果不在枚举中则归为 VOID
            try:
                sector_code = SectorCode(node.subject.sector_code)
            except ValueError:
                sector_code = SectorCode.VOID
            
            position_angle = float(node.subject.position_angle) if node.subject.position_angle is not None else 0.0

        return cls(
            id=node.id,
            name=node.name,
            name_en=node.name_en,
            description=node.description,
            importance_level=node.importance_level,
            sector_code=sector_code,
            is_seed=node.is_seed,
            user_status=user_status,
            position_angle=position_angle,
            position_radius=100.0 + node.importance_level * 30.0  # 简化计算
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
    sector_distribution: Dict[str, int] = {} # {sector_code: count}
    streak_days: int = 0 # 连续学习天数


class GalaxyGraphResponse(BaseModel):
    """星图完整数据响应"""
    nodes: List[NodeWithStatus]
    relations: List[NodeRelationInfo]
    user_stats: GalaxyUserStats


class SparkEvent(BaseModel):
    """点亮动画事件"""
    node_id: UUID
    node_name: str
    sector_code: SectorCode
    old_mastery: float
    new_mastery: float
    is_first_unlock: bool  # 首次点亮 (播放特殊动画)
    is_level_up: bool      # 升级 (跨越阈值)
    
    # 前端动画参数
    particle_count: int = 20
    animation_duration_ms: int = 1500


class SparkResult(BaseModel):
    spark_event: SparkEvent
    expansion_queued: bool
    expanded_nodes: Optional[List[NodeBase]] = None  # 如果同步返回
    updated_status: Optional[Any] = None # UserStatusInfo or dict


class SearchResultItem(BaseModel):
    node: NodeBase
    similarity: float
    user_status: Optional[UserStatusInfo]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total_count: int = 0


class ReviewSuggestion(BaseModel):
    node_id: UUID
    node_name: str
    sector_code: SectorCode
    current_mastery: float
    days_since_study: int
    urgency: str  # 'high' | 'normal'


class ReviewSuggestionsResponse(BaseModel):
    suggestions: List[ReviewSuggestion]
    next_review_count: int = 0 # 未来 7 天需要复习的总数
    
class NodeDetailResponse(BaseModel):
    node: NodeWithStatus
    relations: List[NodeRelationInfo]
    # 可以添加更多详情，如学习记录历史等