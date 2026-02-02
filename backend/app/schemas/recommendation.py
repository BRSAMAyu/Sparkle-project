"""
协同过滤推荐 Schema
Collaborative Filtering Recommendation Schemas

基于用户行为相似度的个性化推荐
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RecommendationItemType(str, Enum):
    """推荐物品类型"""
    KNOWLEDGE_NODE = "knowledge_node"    # 知识点
    TASK = "task"                         # 任务
    STUDY_PLAN = "study_plan"             # 学习计划
    CAPSULE = "capsule"                   # 好奇心胶囊
    SUBJECT = "subject"                   # 学科


class UserSimilarityScore(BaseModel):
    """用户相似度分数"""
    user_id: UUID = Field(description="相似用户ID")
    username: str = Field(description="用户名")
    avatar_url: str | None = Field(default=None, description="头像URL")
    similarity: float = Field(..., ge=0.0, le=1.0, description="相似度 0-1")
    common_items: int = Field(description="共同学习物品数量")
    common_subjects: list[str] = Field(default_factory=list, description="共同学科")
    last_interaction: datetime | None = Field(default=None, description="最后互动时间")


class CollaborativeRecommendation(BaseModel):
    """协同过滤推荐结果"""
    item_id: UUID = Field(description="物品ID")
    item_type: RecommendationItemType = Field(description="物品类型")
    title: str = Field(description="标题")
    description: str | None = Field(default=None, description="描述")
    reason: str = Field(description="推荐理由")
    similar_users: list[UUID] = Field(default_factory=list, description="相似用户ID列表")
    similar_usernames: list[str] = Field(default_factory=list, description="相似用户名")
    predicted_score: float = Field(description="预测兴趣分数 0-1")
    confidence: float = Field(..., ge=0.0, le=1.0, description="推荐置信度")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class ItemSimilarity(BaseModel):
    """物品相似度"""
    item_id: UUID = Field(description="物品ID")
    item_type: RecommendationItemType = Field(description="物品类型")
    title: str = Field(description="标题")
    similarity: float = Field(..., ge=0.0, le=1.0, description="相似度 0-1")
    common_learners: int = Field(description="共同学习人数")


class CollaborativeFilteringRequest(BaseModel):
    """协同过滤推荐请求"""
    user_id: UUID = Field(description="用户ID")
    limit: int = Field(default=10, ge=1, le=50, description="推荐数量限制")
    item_type: RecommendationItemType | None = Field(default=None, description="筛选物品类型")
    subject_id: UUID | None = Field(default=None, description="筛选学科")
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0, description="最小用户相似度阈值")


class SimilarUsersRequest(BaseModel):
    """相似用户查询请求"""
    user_id: UUID = Field(description="用户ID")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量")
    min_common_items: int = Field(default=3, ge=1, description="最小共同物品数")


class SimilarItemsRequest(BaseModel):
    """相似物品查询请求"""
    item_id: UUID = Field(description="物品ID")
    item_type: RecommendationItemType = Field(description="物品类型")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量")


class RecommendationStats(BaseModel):
    """推荐统计"""
    total_users_compared: int = Field(description="比较的用户总数")
    similar_users_found: int = Field(description="找到的相似用户数")
    recommendations_generated: int = Field(description="生成的推荐数")
    cache_hit: bool = Field(description="是否命中缓存")
    computation_time_ms: float = Field(description="计算耗时（毫秒）")


class CollaborativeFilteringResponse(BaseModel):
    """协同过滤推荐响应"""
    recommendations: list[CollaborativeRecommendation] = Field(description="推荐列表")
    similar_users: list[UserSimilarityScore] = Field(default_factory=list, description="相似用户列表")
    stats: RecommendationStats = Field(description="统计信息")


class UserInteractionSummary(BaseModel):
    """用户交互摘要"""
    user_id: UUID = Field(description="用户ID")
    total_items_learned: int = Field(description="学习的物品总数")
    subjects: list[str] = Field(description="学习的学科列表")
    recent_items: list[UUID] = Field(description="最近学习的物品ID")
    mastery_levels: dict[str, float] = Field(default_factory=dict, description="各学科掌握度")
