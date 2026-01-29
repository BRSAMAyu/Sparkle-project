"""
推荐系统数据模型
Recommendation System Models

用于协同过滤推荐的用户相似度、物品相似度、交互记录等
"""
import enum
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class InteractionType(str, enum.Enum):
    """用户交互类型"""
    VIEWED = "viewed"           # 查看
    LEARNED = "learned"         # 学习完成
    BOOKMARKED = "bookmarked"   # 收藏
    SHARED = "shared"           # 分享
    PRACTICED = "practiced"     # 练习
    REVIEWED = "reviewed"       # 复习


class UserSimilarity(BaseModel):
    """
    用户相似度缓存表

    设计说明：
    - 缓存用户之间的相似度计算结果
    - 每日定时任务更新
    - 使用Jaccard相似度：|A ∩ B| / |A ∪ B|
    """
    __tablename__ = "user_similarities"

    # 用户对（保证唯一性，user_id_1 < user_id_2）
    user_id_1 = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 相似度分数
    similarity_score = Column(Float, nullable=False, index=True)  # 0-1

    # 统计信息
    common_items_count = Column(Integer, default=0, nullable=False)  # 共同学习物品数
    common_subjects = Column(JSON, nullable=True)  # 共同学科列表

    # 计算信息
    last_calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    calculation_version = Column(Integer, default=1, nullable=False)  # 用于批量更新时标记版本

    # 元数据
    meta = Column(JSON, nullable=True)  # 额外的相似度信息

    # 关系
    user_1 = relationship("User", foreign_keys=[user_id_1])
    user_2 = relationship("User", foreign_keys=[user_id_2])

    __table_args__ = (
        Index('idx_user_similarity_user1', 'user_id_1'),
        Index('idx_user_similarity_user2', 'user_id_2'),
        Index('idx_user_similarity_score', 'similarity_score'),
        Index('idx_user_similarity_calculated', 'last_calculated_at'),
    )


class ItemSimilarity(BaseModel):
    """
    物品相似度表

    设计说明：
    - 计算知识点/任务之间的相似度
    - 基于用户共同学习行为
    - 用于"学过X的人也学Y"推荐
    """
    __tablename__ = "item_similarities"

    # 物品对（保证唯一性）
    item_id_1 = Column(GUID(), nullable=False, index=True)
    item_type_1 = Column(String(50), nullable=False)  # knowledge_node, task, etc.

    item_id_2 = Column(GUID(), nullable=False, index=True)
    item_type_2 = Column(String(50), nullable=False)

    # 相似度分数
    similarity_score = Column(Float, nullable=False, index=True)

    # 统计信息
    common_learners = Column(Integer, default=0, nullable=False)
    total_learners_either = Column(Integer, default=0, nullable=False)

    # 计算信息
    last_calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 额外信息
    subject_id = Column(GUID(), nullable=True)  # 所属学科（可选）
    meta = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_item_similarity_item1', 'item_id_1', 'item_type_1'),
        Index('idx_item_similarity_item2', 'item_id_2', 'item_type_2'),
        Index('idx_item_similarity_score', 'similarity_score'),
    )


class UserItemInteraction(BaseModel):
    """
    用户-物品交互记录表

    设计说明：
    - 记录用户与各种学习物品的交互历史
    - 用于协同过滤算法的输入
    - 支持多种交互类型
    """
    __tablename__ = "user_item_interactions"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 物品信息
    item_id = Column(GUID(), nullable=False, index=True)
    item_type = Column(String(50), nullable=False)  # knowledge_node, task, capsule, etc.

    # 交互类型
    interaction_type = Column(String(50), nullable=False, index=True)

    # 交互强度（用于加权）
    interaction_weight = Column(Float, default=1.0, nullable=False)

    # 上下文信息
    subject_id = Column(GUID(), nullable=True)
    session_id = Column(String(100), nullable=True)  # 学习会话ID
    meta = Column(JSON, nullable=True)

    # 关系
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_user_interaction_user', 'user_id'),
        Index('idx_user_interaction_item', 'item_id'),
        Index('idx_user_interaction_type', 'interaction_type'),
        Index('idx_user_interaction_user_item', 'user_id', 'item_id'),
        Index('idx_user_interaction_time', 'created_at'),
    )


class UserLearningProfile(BaseModel):
    """
    用户学习画像表

    设计说明：
    - 聚合用户的学习偏好和行为模式
    - 用于推荐算法
    - 定期更新
    """
    __tablename__ = "user_learning_profiles"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 学习偏好
    preferred_difficulty = Column(Float, nullable=True)  # 偏好难度 1-5
    preferred_duration_minutes = Column(Integer, nullable=True)  # 偏好时长
    preferred_time_of_day = Column(String(20), nullable=True)  # morning, afternoon, evening

    # 学科分布
    subject_distribution = Column(JSON, nullable=True)  # {"数学": 0.4, "英语": 0.3, ...}

    # 学习统计
    total_study_minutes = Column(Integer, default=0, nullable=False)
    total_items_completed = Column(Integer, default=0, nullable=False)
    average_session_duration = Column(Float, nullable=True)

    # 协同过滤相关
    learning_vector = Column(JSON, nullable=True)  # 学习向量（用于相似度计算）
    cluster_id = Column(Integer, nullable=True)  # 聚类ID

    # 更新信息
    last_updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    update_version = Column(Integer, default=1, nullable=False)

    # 关系
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<UserLearningProfile(user_id={self.user_id}, cluster={self.cluster_id})>"


class RecommendationCache(BaseModel):
    """
    推荐结果缓存表

    设计说明：
    - 缓存用户的推荐结果
    - 减少实时计算压力
    - 定期刷新
    """
    __tablename__ = "recommendation_cache"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 推荐类型
    recommendation_type = Column(String(50), nullable=False, index=True)  # collaborative, hybrid, etc.

    # 缓存的推荐结果
    cached_recommendations = Column(JSON, nullable=False)  # JSON数组

    # 缓存元信息
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    hit_count = Column(Integer, default=0, nullable=False)

    # 关系
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_rec_cache_user_type', 'user_id', 'recommendation_type'),
        Index('idx_rec_cache_expires', 'expires_at'),
    )


class LeaderboardSnapshot(BaseModel):
    """
    排行榜快照表

    设计说明：
    - 定期保存排行榜快照
    - 用于计算排名变化趋势
    - 支持历史排名查询
    """
    __tablename__ = "leaderboard_snapshots"

    # 快照标识
    snapshot_type = Column(String(50), nullable=False, index=True)  # global, friends, weekly, etc.
    period = Column(String(20), nullable=False)  # daily, weekly, all_time
    subject_id = Column(GUID(), nullable=True)  # 学科ID（学科榜）

    # 快照时间
    snapshot_date = Column(DateTime, nullable=False, index=True)
    snapshot_version = Column(Integer, nullable=False)

    # 快照数据
    rankings = Column(JSON, nullable=False)  # 排名数据
    total_participants = Column(Integer, nullable=False)

    # 统计信息
    generation_time_ms = Column(Float, nullable=True)

    __table_args__ = (
        Index('idx_leaderboard_snapshot_type_date', 'snapshot_type', 'snapshot_date'),
        Index('idx_leaderboard_snapshot_period', 'period'),
    )
